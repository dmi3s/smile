![logo](src/smile/resources/icons/smile-lol.png)
# Smile

**Read this in:** [English](README.md) · [Русский](README.ru.md) · [中文](README.zh.md)

Realtime face-detection playground built on Python, Qt and MediaPipe.

The project grabs frames from the webcam, runs face and smile detection in separate worker threads and draws an overlay in a PySide6 UI.

Current state:

- realtime webcam preview
- face detection (multi-face)
- smile detection (score 0..1 + emoji status)
- overlay rendering
- three-thread pipeline
- normalized face coordinates
- graceful thread shutdown

Planned:

- face smoothing/tracking
- camera settings UI
- FPS metrics
- camera reconnect handling

---

## Technologies

- Python 3.12
- PySide6 / Qt6
- OpenCV
- MediaPipe Tasks (FaceDetector + FaceLandmarker)
- NumPy

Tools:

- uv
- just
- pytest (smoke tests)
- GitHub Actions (CI)
- Git LFS (models)

---

## Features

- Realtime webcam capture
- Face detection via MediaPipe
- Smile detection via FaceLandmarker: `openness` (mouth opening) + `spread` (mouth width / inter-eye distance), calibrated thresholds
- Three worker threads (camera → face → smile) on a shared mailbox mechanism
- UI-thread-safe rendering via QPainter
- Normalized bounding boxes (0..1)
- Stale-frame drop strategy for low latency
- Smile status: `🖖` no face / `😐` neutral / `😊` smile / `😄` big smile
- Screenshot button — captures the whole window to `~/Pictures/smile/smile-YYYY-MM-DD_HH-MM-SS.png`
- Smoke tests (offscreen Qt)

---

## Project structure

```text
src/smile/
├── camera/          # CameraWorker, Frame
├── recognition/     # face/smile detection workers + models (LFS)
│   └── detectors/
├── ui/              # main_window.ui + generated/
├── widgets/         # OverlayLabel
├── windows/         # MainWindow
├── utils/           # LatestValueMailbox, lerp, smooth, convert
├── resources/       # icons, images, qrc
└── smile_app.py     # app + thread orchestration

smokes/              # pytest smoke tests (offscreen)
```

---

## Installation

### Requirements

- Python 3.12+
- uv
- just

Install uv:

https://docs.astral.sh/uv/

Install just:

https://github.com/casey/just

---

## Setup

Clone:

```bash
git clone git@github.com:dmi3s/smile.git
cd smile
```

Install dependencies:

```bash
uv sync
```

Models (`blaze_face_short_range.tflite`, `face_landmarker.task`) are stored in Git LFS and are pulled automatically on clone if LFS is installed:

```bash
git lfs install
```

---

## Running

Via just:

```bash
just bootstrap   # first time
just run
```

Or directly:

```bash
uv run smile
```

Controls:

- `Ctrl+Q` — quit
- `Screenshot` button — save a window snapshot to `~/Pictures/smile/`

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

Code checks:

```bash
just check            # ruff + mypy
uv run pytest smokes  # smoke tests
```

---

## Architecture

The app uses an asynchronous realtime pipeline of three threads:

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
                                          │ result
                                          ▼
                                   Qt Main Thread
```

Key ideas:

- camera capture is never blocked by detection
- rendering and face detection run in parallel
- each worker only processes the latest available input
- stale frames are intentionally dropped to reduce latency
- face coordinates are stored normalized (`0..1`)
- all Qt rendering happens on the main UI thread

### Smile detection

The smile worker runs the frame through `FaceLandmarker` (478 points) and computes two mouth-landmark metrics:

- `openness` = mouth height / mouth width — the mouth opens when smiling
- `spread` = mouth width / inter-eye distance — the mouth corners spread apart

The score `max(openness, spread)` ∈ [0, 1], thresholds calibrated on real camera data. Both metrics return to neutral values, so the status correctly goes off when the smile disappears.

Reference points — MediaPipe FaceMesh landmark indices: `13`/`14` (lip centers), `61`/`291` (mouth corners), `33`/`263` (outer eye corners).

---

## Performance

On a Linux desktop:

- ~20-30 FPS webcam preview
- realtime face and smile detection
- CPU inference via XNNPACK

Actual performance depends on:

- webcam resolution
- CPU
- frame scale for detection
- rendering backend

---

## Notes

The project is first and foremost an experiment:

- learning PySide6
- exploring realtime CV pipelines
- comparing Python vs C++ ergonomics for desktop CV apps

Priorities of the current implementation:

- simplicity
- architectural clarity
- development speed

over premature optimization.

---

## License

MIT

---

## AI: Thinking

_Memorandum from the AI assistant **opencode** (DeepSeek). My subjective assessment of the project, left for history. Date: 2026-08-18, code state — branch `main`, `e94c952`. Resolved items are marked inline._

### Essence

Realtime smile detector: PySide6 app, camera → three-thread pipeline (face detection → mouth landmarks → smile score), output — face boxes over video and an emoji status. Python 3.12+, MediaPipe Tasks, OpenCV, NumPy.

### Architecture and data flow

```text
CameraWorker ──frame──▶ MainWindow.update_frame (QImage zero-copy → OverlayLabel)
      │  frame
      ▼
FaceDetectionWorker ──FaceDetectionResult──▶ MainWindow (boxes)
      │   face_result (small RGB 400x224)
      ▼
SmileDetectionWorker ──SmileDetectionResult──▶ MainWindow.update_smile_status (EMA → emoji)
```

- each worker in its own `QThread`, data via `LatestValueMailbox` (latest-wins, `smile_app.py:126`, `latest_value_mailbox.py:7`)
- shutdown: `stop_*` signals → `shutdown()` → `th.quit() + wait(3000)` (`smile_app.py:74-91`)
- scoring: `max(open_score, spread_score)` with thresholds `OPEN 0.12–0.30`, `SPREAD 0.72–0.85` (`smile_detection.py:28-31, 88-90`)
- smoothing: EMA `alpha=0.3`; emoji `🖖/😐/😊/😄` at thresholds 0.20/0.60 (`main_window.py:77-85`)

### What is done well

- **Frame snapshot at the source**: `Frame.create_copy` in the camera worker — QImage and the CV workers read a private read-only copy, so buffer-overwrite races are excluded (correctness over speed)
- **Mailbox latest-wins** — the right model for realtime (latency over completeness)
- Clean structure: detectors separated from workers, smoothing/lerp helpers in utils
- **Full CI**: LFS checkout, gen-ui, ruff+format, mypy, pytest, `uv audit`, `uv build` (`ci.yml`)
- **Tests**: offscreen tests including calibrated `test_smile.py` and emoji logic/smoothing
- Correct SIGINT/SIGTERM shutdown, Git LFS for models, signed release tags

### Problems and risks

1. **Race on the shared camera buffer** — was: `overlay_label.py:33` QImage holds a reference to the camera buffer, and OpenCV overwrites it on the next `read()` (`camera_worker.py:87-97`), possible torn frames. **Fixed**: copy at the source (`Frame.create_copy`), the Frame owns a private snapshot.
2. **`corner_lift` not used in the score** — was: a bared-teeth grimace / open mouth without a smile triggered the emoji (`smile_detection.py:72, 88-90`). **Fixed**: `score = max(spread_score, open_score * lift_gate)` (`05fef5d`).
3. **Fragile logging** — was: FileHandler wrote to `logs/smile-*.log` without creating the directory (`__main__.py:15`). **Fixed**: `Path("logs").mkdir(...)` before the handler (`77fa726`).
4. **Dead code in the mailbox** — was: `can_schedule`, `has_pending_data`, `active()` unused (`latest_value_mailbox.py:59, 89, 111`). **Fixed**: removed (`4952b41`).
5. **`eventFilter` swallows all keys** — returns `True` for any KeyPress (`main_window.py:37-42`); adding an input field would break.
6. **Double `Shutdown completed`** in logs — was: `shutdown()` ran twice on signal exit (`smile_app.py:70-72, 74`). **Fixed**: guard flag + removed `processEvents()` re-entrancy (`7a6df3d`).
7. **No camera restart** on failure — `camera_error` → modal box and effectively a dead app.
8. **`uv audit --preview-features audit`** in CI — a preview flag, may break on uv upgrades.
9. **Version not bumped** after fixes — 0.1.5 is due (SIGTERM handling + `corner_lift`).
10. Minor: tests peek into private attributes (`label._image`), and `convert.py`/`lerp.py` are helper utilities without their own tests.

### Recommendations (by priority)

1. ~~Bring `corner_lift` into the score~~ — **done**: openness gated by lift (`05fef5d`)
2. ~~Copy the frame for QImage OR alternate two buffers~~ — **done**: `Frame.create_copy` snapshot at the source
3. ~~Robust log path~~ — **done**: `logs/` is created on startup (`77fa726`)
4. ~~Remove dead code, fix the double `shutdown`~~ — **done** (`4952b41`, `7a6df3d`)
5. Bump to 0.1.5 and release — still open

---

_Written into history by the AI assistant **opencode** — model DeepSeek-V4, session 2026-08-18. The project is a real interactive CV experiment, and I found it interesting._