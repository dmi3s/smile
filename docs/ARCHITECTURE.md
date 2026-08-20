# Smile architecture: how it works in real time

**Read this in:** [English](ARCHITECTURE.md) · [Русский](ARCHITECTURE.ru.md) · [中文](ARCHITECTURE.zh.md)

The app is an asynchronous realtime pipeline of four worker threads
(`camera_worker` → `face_worker` → `smile_worker`, plus `flashlight_worker`
in parallel with face detection), orchestrated by `SmileApp` (a `QApplication`
subclass). Each worker lives in its own `QThread`; data crosses thread
boundaries through Qt signals, and inside a worker through the single-slot
`LatestValueMailbox` with latest-wins semantics.

The diagrams below are in `docs/generated/`, the D2 sources sit next to them
in `docs/*.d2` (rebuilt via `just build` in `docs/`).

## 1. Input buffer: how a frame lives and the mailbox

![Input buffer](generated/buffer_lifecycle.svg)

Two key mechanisms:

- **The frame is copied at the source.** `CameraWorker` reads a frame from
  OpenCV and immediately calls `Frame.create_copy()`: a private `read-only`
  snapshot (`image.copy() + writeable=False`). Both the QImage (UI) and the
  CV workers can read that copy without risk — nobody overwrites the camera
  buffer anymore, so torn frames are impossible. Inside the pipeline, the
  already-created copies are shared cheaply with `Frame.create_share()` (the
  same buffer, also read-only).

- **Mailbox is a single-slot input buffer.** `LatestValueMailbox<T>` holds
  exactly one `pending_data` and a `busy` flag:

  - `new_data(x)` — just puts the value into the slot, **overwriting** the old
    one (if the consumer did not keep up, the old value is lost — that is
    latest-wins);
  - `try_start()` — starts processing only if `running && !busy &&
    pending != None`; otherwise does nothing and waits for the next
    `new_data`;
  - `extract_data()` — takes the value and clears the slot;
  - `complete_and_should_continue()` — clears `busy`; if a new pending value
    arrived while processing, immediately starts the next pass.

  Consequence: a worker never "stacks up" frames — the input buffer behaves
  like a single fresh cell, not a queue.

## 2. Recognition pipeline

![Recognition pipeline](generated/recognition_pipeline.svg)

- `CameraWorker` captures frames (800×448 @ ~20 fps) and, via the
  `frame_ready` signal, sends a `Frame` **to the UI, the face worker and the
  flashlight worker**.
- `FaceDetectionWorker` halves the frame (`0.5x`, RGB) and runs it through
  MediaPipe `FaceDetector` (`RunningMode.VIDEO`). The result is a
  `FaceDetectionResult`: normalized face boxes (0..1) plus the downscaled
  RGB frame (`small_frame_rgb`). Between frames the boxes are tracked with
  greedy center-based matching and smoothed with EMA (`FaceTracker`).
- `SmileDetectionWorker` receives the face worker's result, runs
  `small_frame_rgb` through MediaPipe `FaceLandmarker` (478 points) and
  computes the smile score with `smile_score()` from mouth geometry:

  - `openness` — mouth height / mouth width;
  - `spread` — mouth width / inter-eye distance;
  - `corner_lift` — mouth-corner rise relative to the lip line (gate).

  The final score is `max(spread_score, open_score * lift_gate)` ∈ [0, 1],
  thresholds calibrated on real camera data.
- `FlashlightDetectionWorker`, in parallel with the face, runs the frame
  (400×224) through the ImageNet classifier MobileNet V2 (`RunningMode.VIDEO`):
  a `torch`/`flashlight` class in the top-5 with score ≥ `0.03` → "flashlight
  found" (works even when it is off). Then it looks for a glowing lens:
  brightness binarization (threshold 200) + connected components → the largest
  blob with area 0.5–60% of the frame → normalized box. The result is a
  `FlashlightDetectionResult` (`detected`, `score`, `bright_bbox`,
  `brightness`).

## 3. Classes and responsibilities

![Class map](generated/class_map.svg)

| Class / module | What it does |
|---|---|
| `SmileApp` | Orchestration: creates the workers and 4 threads, wires up signals, idempotent `shutdown()`, SIGINT/SIGTERM exit |
| `QThread` ×4 | One working thread per worker |
| `CameraWorker` | Camera capture: `QTimer` → `read()` → `Frame`; on failure — reconnect loop (`RETRY_DELAY_MS`, `camera_error` → `camera_recovered`), probing multiple sources (last known → indices 0..5 → `/dev/video*` on Linux) with a probe frame, no "dead" app |
| `Frame` | Immutable frame snapshot (`create_share` / `create_copy`) |
| `FaceDetectionWorker` | `FaceDetector` (VIDEO mode), box normalization, `small_frame_rgb` |
| `FaceTracker` | Greedy center-based box matching + EMA smoothing, `max_lost` |
| `SmileDetectionWorker` | `FaceLandmarker` (VIDEO mode), calls `smile_score()` |
| `smile_detection.py` | Pure scoring logic: `mouth_features()`, `smile_score()`, thresholds `OPEN`/`SPREAD`/`LIFT` |
| `FlashlightDetectionWorker` | `ImageClassifier` MobileNet V2 (VIDEO mode) + `detect_bright_spot()` → `FlashlightDetectionResult` |
| `flashlight_detection.py` | Pure logic: `is_flashlight()` (keywords `torch`/`flashlight`), `detect_bright_spot()` (threshold 200, area 0.5–60%) |
| `LatestValueMailbox<T>` | Single-slot latest-wins input buffer |
| `MainWindow` | Slots `update_frame` / `update_face_recognition` / `update_smile_status` / `update_flashlight`, screenshot, status bar (FPS + 🔦) |
| `OverlayLabel` | `QPainter`: video + face boxes + yellow flashlight box |
| `ExponentialJitterSmoother` | EMA smoothing of the smile score (α=0.3) |
| `FpsMeter` | EMA FPS meters: cam · face · smile · render |
| Models (Git LFS) | `blaze_face_short_range.tflite`, `face_landmarker.task`, `mobilenet_v2_1.0_224.tflite` |

## 4. Realtime loop

![Realtime loop](generated/realtime_loop.svg)

One "tick" of the live app:

1. `CameraWorker` reads a frame on a timer and emits `frame_ready` — the
   signal goes simultaneously to the UI thread (render), the face worker
   (detection) and the flashlight worker (flashlight).
2. The face worker puts the frame into its mailbox and, if free, immediately
   starts processing via `QTimer.singleShot(0)`; if busy — the frame simply
   overwrites the pending one (the old one is dropped).
3. The face-detection result goes to the UI (box update) and to the smile
   worker.
4. The smile worker processes `small_frame_rgb` through the same mailbox
   scheme, computes the scores and sends a `SmileDetectionResult` to the UI.
5. The flashlight worker, in parallel, classifies the frame and sends a
   `FlashlightDetectionResult` to the UI (yellow box + `🔦` in the status bar).
6. The UI thread's `update_smile_status` smooths the best score with EMA
   (α=0.3) and shows the emoji: `🖖` no face / `😐` neutral / `😊` smile / `😄`
   big smile.

**Why this is realtime:** latency matters more than completeness. A worker
always processes only the freshest input, stale frames are deliberately
dropped, camera capture is never blocked by detection, and all Qt rendering
runs strictly on the main UI thread.