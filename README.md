# AI Audio Studio

A GitHub- and Render-ready text-to-speech web app. It converts text to a natural neural voice, supports custom pause markers, previews the result in the browser, and downloads it as an MP3.

## Features

- Six English neural voices (India, US, and UK)
- Pause buttons for 0.5, 1, and 2 seconds
- Audio player and direct MP3 download
- MP3, WAV, OGG, and M4A downloads
- Slow, normal, and fast speech settings
- Live word count, estimated audio length, elapsed time, and conversion timeline
- Voice samples for choosing the right narrator
- Separate Generate & Play and Generate & Download actions
- HRMantra branded header and copyright footer
- Responsive interface for desktop and mobile
- Docker and Render Blueprint configuration included

## Run locally with Docker

```bash
docker build -t ai-audio-studio .
docker run --rm -p 10000:10000 ai-audio-studio
```

Open `http://localhost:10000`.

## Deploy on Render

1. Create a new GitHub repository and upload/push all files in this folder.
2. In Render, select **New → Blueprint**.
3. Connect the GitHub repository and apply the detected `render.yaml` configuration.
4. Wait for the Docker build to finish, then open the generated Render URL.

### Existing native Python service

This repository also supports an existing Render Python service. Use:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `PYTHON_VERSION=3.12.11`

The `.python-version` file pins Python 3.12 automatically. If the Render service already has a `PYTHON_VERSION` environment variable, update it to `3.12.11` because an environment variable overrides the repository file.

No API key is required. The speech service needs an internet connection at runtime.

## If audio generation fails

Open the Render service and select **Logs**. The updated app also displays a more useful error in the browser.

- If the message says **FFmpeg is missing**, delete the incorrectly configured service and deploy the repository using **New → Blueprint**. The included Dockerfile installs FFmpeg automatically.
- If the message says the speech providers cannot be reached, retry after a minute and look for a network error in Render Logs.
- After updating this repository, select **Manual Deploy → Deploy latest commit** so Render rebuilds the Docker image with the latest dependencies.

## Pause format

The buttons insert tags such as `<#0.5#>`, `<#1.0#>`, and `<#2.0#>`. You can also type a custom tag such as `<#1.5s#>`. Individual pauses are capped at 30 seconds.
