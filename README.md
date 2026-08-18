![logo](src/smile/resources/icons/smile-lol.png)
# Smile

Realtime face detection playground built with Python, Qt and MediaPipe.

The project captures webcam frames, runs face detection in a separate worker thread and renders detection overlays in a PySide6 UI.

Current status:

- realtime webcam preview
- face detection
- multi-face support
- overlay rendering
- threaded processing pipeline
- normalized face coordinates
- graceful thread shutdown

Planned:

- smile detection
- face smoothing/tracking
- camera settings UI
- FPS metrics
- camera reconnect handling

---

## Tech Stack

- Python 3.12
- PySide6 / Qt6
- OpenCV
- MediaPipe Tasks
- NumPy

Tooling:

- uv
- just
- PyCharm / Zed / Helix
- zsh + zellij

---

## Features

- Realtime webcam capture
- Face detection using MediaPipe
- Detection worker thread
- UI-thread-safe rendering
- Normalized bounding boxes
- Overlay rendering using QPainter
- Frame dropping strategy for low latency

---

## Project Structure

```text
src/smile/
├── camera/          # CameraWorker, Frame
├── recognition/     # face/smile detection workers + models
│   └── detectors/
├── ui/              # main_window.ui + generated/
├── widgets/         # OverlayLabel
├── windows/         # MainWindow
├── utils/           # LatestValueMailbox, lerp, smooth, convert
├── resources/       # icons, images, qrc
└── smile_app.py     # app + thread orchestration
```

---

## Installation

### Requirements

- Python 3.12+
- uv
- just

Install uv:

https://docs.astral.sh/uv/

Insstall just:

https://github.com/casey/just

---

## Setup

Clone the repository:

```bash
git clone https://github.com/yourname/smile.git
cd smile
```

Install dependencies:

```bash
uv sync
```

---

## Run

Using just:

First time:

```bash
just bootstrap
```

Then

```bash
just run
```

Or directly:

```bash
uv run smile
```

---

## Development

Generate Qt UI files:

```bash
just gen-ui
```

Generate Qt resources:

```bash
just gen-resources
```

---

## Architecture Notes

The application uses an asynchronous realtime pipeline:

```text
                ┌────────────────────┐
                │   Camera Worker    │
                └─────────┬──────────┘
                          │ frame_ready
          ┌───────────────┴────────────────┐
          │                                │
          ▼                                ▼
┌────────────────────┐        ┌──────────────────────────┐
│   UI Rendering     │        │   Face Detection Worker  │
│   (Qt Main Thread) │        │   (mailbox: latest frame)│
└────────────────────┘        └─────────────┬────────────┘
                                            │ result
                                            ▼
                            ┌──────────────────────────┐
                            │   Smile Detection Worker │
                            │ (mailbox: latest result) │
                            └─────────────┬────────────┘
                                          │ progress
                                          ▼
                                   Qt Main Thread
```

Key ideas:

- camera capture never blocks on detection
- rendering and face detection run in parallel
- each worker processes only the latest available input
- stale frames are dropped intentionally to reduce latency
- face coordinates are stored normalized (`0..1`)
- all Qt painting happens in the main UI thread

---

## Performance

Current performance on Linux desktop:

- ~30 FPS webcam preview
- realtime face detection
- CPU inference via XNNPACK

Actual performance depends on:

- webcam resolution
- CPU
- detector scale factor
- rendering backend

---

## Notes

This project is primarily an experiment:

- learning PySide6
- exploring realtime CV pipelines
- comparing Python vs C++ ergonomics for desktop CV applications

The current implementation prioritizes:

- simplicity
- architecture clarity
- development speed

over premature optimization.

---

## License

MIT
