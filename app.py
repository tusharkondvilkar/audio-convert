import io
import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from flask import Flask, jsonify, render_template, request, send_file
from gtts import gTTS
from pydub import AudioSegment


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Use a bundled FFmpeg binary. This works on Render's native Python runtime
# as well as Docker and avoids relying on system-level packages.
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
AudioSegment.converter = FFMPEG_EXE
AudioSegment.ffmpeg = FFMPEG_EXE

VOICES = {
    "en-IN-NeerjaNeural": "Neerja (Female · India)",
    "en-IN-PrabhatNeural": "Prabhat (Male · India)",
    "en-US-JennyNeural": "Jenny (Female · US)",
    "en-US-GuyNeural": "Guy (Male · US)",
    "en-GB-SoniaNeural": "Sonia (Female · UK)",
    "en-GB-RyanNeural": "Ryan (Male · UK)",
}
PAUSE_PATTERN = re.compile(r"<#([0-9]+(?:\.[0-9]+)?)[sS]?#>")
FORMATS = {
    "mp3": ("audio/mpeg", {"format": "mp3", "bitrate": "192k"}),
    "wav": ("audio/wav", {"format": "wav"}),
    "ogg": ("audio/ogg", {"format": "ogg", "codec": "libvorbis"}),
    "m4a": ("audio/mp4", {"format": "mp4", "codec": "aac", "bitrate": "192k"}),
}
RATES = {"slow": "-15%", "normal": "+0%", "fast": "+15%"}


@app.get("/")
def index():
    return render_template("index.html", voices=VOICES)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/generate")
def generate_audio():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    voice = str(data.get("voice", "en-IN-NeerjaNeural"))
    output_format = str(data.get("format", "mp3")).lower()
    speed = str(data.get("speed", "normal")).lower()

    if not text:
        return jsonify(error="Please enter some text first."), 400
    if len(text) > 10_000:
        return jsonify(error="Please keep the script under 10,000 characters."), 400
    if voice not in VOICES:
        return jsonify(error="The selected voice is not available."), 400
    if output_format not in FORMATS:
        return jsonify(error="The selected audio format is not available."), 400
    if speed not in RATES:
        return jsonify(error="The selected speech speed is not available."), 400

    try:
        audio = build_audio(text, voice, output_format, speed)
        return send_file(
            audio,
            mimetype=FORMATS[output_format][0],
            as_attachment=False,
            download_name=f"ai-audio-studio.{output_format}",
        )
    except RuntimeError as error:
        app.logger.exception("Audio generation failed")
        return jsonify(error=str(error)), 503
    except Exception:
        app.logger.exception("Audio generation failed")
        return jsonify(
            error="Audio generation failed unexpectedly. Check the latest Render log entry."
        ), 500


def build_audio(text: str, voice: str, output_format: str, speed: str) -> io.BytesIO:
    if not Path(FFMPEG_EXE).is_file() and not shutil.which("ffmpeg"):
        raise RuntimeError(
            "The audio encoder is unavailable. Redeploy the latest repository version on Render."
        )

    parts = PAUSE_PATTERN.split(text)
    combined = AudioSegment.empty()

    with tempfile.TemporaryDirectory() as temp_dir:
        for index, part in enumerate(parts):
            if not part.strip():
                continue
            if index % 2:
                seconds = min(float(part), 30.0)
                combined += AudioSegment.silent(duration=int(seconds * 1000))
                continue

            speech_path = Path(temp_dir) / f"speech-{index}.mp3"
            create_speech(part.strip(), voice, speed, speech_path)
            combined += AudioSegment.from_mp3(speech_path)

    if not combined:
        raise ValueError("No speakable text supplied")

    result = io.BytesIO()
    combined.export(result, **FORMATS[output_format][1])
    result.seek(0)
    return result


def create_speech(text: str, voice: str, speed: str, output_path: Path) -> None:
    """Use the selected neural voice, with gTTS as a resilient fallback."""
    try:
        asyncio.run(
            edge_tts.Communicate(text, voice, rate=RATES[speed]).save(str(output_path))
        )
        if output_path.stat().st_size == 0:
            raise RuntimeError("The neural speech service returned an empty file")
        return
    except Exception as neural_error:
        app.logger.warning("Neural voice failed; trying gTTS: %s", neural_error)

    try:
        region = voice.split("-")[1] if "-" in voice else "US"
        tld = {"IN": "co.in", "GB": "co.uk", "US": "com"}.get(region, "com")
        gTTS(text=text, lang="en", tld=tld, slow=(speed == "slow")).save(str(output_path))
    except Exception as fallback_error:
        app.logger.exception("Both speech providers failed")
        raise RuntimeError(
            "The speech providers could not be reached from Render. Please retry in a minute and check the Render logs if it continues."
        ) from fallback_error


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
