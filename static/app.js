"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const byId = (id) => document.getElementById(id);
  const scriptBox = byId("script");
  const voice = byId("voice");
  const speed = byId("speed");
  const format = byId("format");
  const generate = byId("generate");
  const buttonText = document.querySelector(".button-text");
  const result = byId("result");
  const player = byId("player");
  const download = byId("download");
  const message = byId("message");
  const counter = byId("counter");
  const wordCount = byId("word-count");
  const durationEstimate = byId("duration-estimate");
  const progressPanel = byId("progress-panel");
  const progressTitle = byId("progress-title");
  const progressBar = byId("progress-bar");
  const elapsed = byId("elapsed");
  const timelineItems = [...document.querySelectorAll(".timeline li")];
  let audioUrl = null;
  let timer = null;

  const formatTime = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;

  function updateStats() {
    const value = scriptBox.value;
    const length = Array.from(value).length;
    const words = (value.match(/\b[\p{L}\p{N}'-]+\b/gu) || []).length;
    const pauses = [...value.matchAll(/<#([0-9]+(?:\.[0-9]+)?)[sS]?#>/g)].reduce((sum, match) => sum + Math.min(Number(match[1]), 30), 0);
    const speedFactor = { slow: 0.85, normal: 1, fast: 1.15 }[speed.value];
    const seconds = words ? (words / (150 * speedFactor)) * 60 + pauses : 0;
    counter.textContent = `${length.toLocaleString()} / 10,000`;
    wordCount.textContent = `${words.toLocaleString()} ${words === 1 ? "word" : "words"}`;
    durationEstimate.textContent = `~${formatTime(seconds)} audio`;
    counter.classList.toggle("near-limit", length >= 9000);
  }

  function setProgress(step, percent, title) {
    progressTitle.textContent = title;
    progressBar.style.width = `${percent}%`;
    timelineItems.forEach((item, index) => {
      item.classList.toggle("complete", index + 1 < step);
      item.classList.toggle("active", index + 1 === step);
    });
  }

  function startProgress() {
    progressPanel.hidden = false;
    const started = Date.now();
    setProgress(1, 8, "Analyzing your script");
    timer = window.setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      elapsed.textContent = `${seconds}s elapsed`;
      if (seconds >= 3 && seconds < 12) setProgress(2, Math.min(62, 20 + seconds * 3), "Creating neural speech");
      else if (seconds >= 12 && seconds < 20) setProgress(3, 72, "Applying pauses and timing");
      else if (seconds >= 20) setProgress(4, Math.min(94, 78 + seconds / 4), `Encoding ${format.value.toUpperCase()} file`);
    }, 1000);
  }

  function stopProgress(success) {
    window.clearInterval(timer);
    timer = null;
    if (success) {
      setProgress(5, 100, "Audio ready to play and download");
      timelineItems.forEach((item) => { item.classList.add("complete"); item.classList.remove("active"); });
    } else {
      progressPanel.hidden = true;
    }
  }

  ["input", "change", "keyup", "paste"].forEach((eventName) => scriptBox.addEventListener(eventName, () => window.setTimeout(updateStats, 0)));
  speed.addEventListener("change", updateStats);
  updateStats();

  document.querySelectorAll(".pause").forEach((button) => button.addEventListener("click", () => {
    scriptBox.setRangeText(`<#${button.dataset.seconds}#>`, scriptBox.selectionStart, scriptBox.selectionEnd, "end");
    updateStats();
    scriptBox.focus();
  }));

  generate.addEventListener("click", async () => {
    message.textContent = "";
    result.hidden = true;
    if (!scriptBox.value.trim()) {
      message.textContent = "Please enter some text first.";
      scriptBox.focus();
      return;
    }

    generate.disabled = true;
    buttonText.textContent = "Creating audio...";
    startProgress();
    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: scriptBox.value, voice: voice.value, speed: speed.value, format: format.value }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Audio generation failed (server error ${response.status}).`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error("The server returned an empty audio file. Please try again.");
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      audioUrl = URL.createObjectURL(blob);
      player.src = audioUrl;
      download.href = audioUrl;
      download.download = `ai-audio-${Date.now()}.${format.value}`;
      download.textContent = `Download ${format.value.toUpperCase()}`;
      result.hidden = false;
      player.load();
      stopProgress(true);
      player.play().catch(() => {});
    } catch (error) {
      stopProgress(false);
      message.textContent = error instanceof Error ? error.message : "Audio generation failed.";
    } finally {
      generate.disabled = false;
      buttonText.textContent = "Generate audio";
    }
  });
});
