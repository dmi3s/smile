# Plan: refactoring and fixes

**Read this in:** [English](plan.md) · [Русский](plan.ru.md) · [中文](plan.zh.md)

A list of point-by-point fixes from the code review. Each item is a separate
unit of work with its own acceptance criterion.

## 1. `eventFilter` must not swallow all keys

- **problem**: `MainWindow.eventFilter` returns `True` for every `KeyPress`
  (`main_window.py:65`), so any future input (e.g. a camera-settings field)
  would be eaten by the filter;
- **solution**: intercept only `Ctrl+Q`, forward everything else to the base
  handling;
- **criterion**: `[x]` — only `Ctrl+Q` quits the app, other keys reach the
  widgets.

## 2. Extract the common worker pattern into a base class

- **problem**: the three detection workers verbatim duplicate the mailbox
  mechanics and the `_process_next` loop (try/except/emit/finally);
- **solution**: base `MailboxWorker` in `utils/mailbox_worker.py` — `wakeup`,
  `shutdown`, `_enqueue`, `_process_next`; subclasses implement `_init_worker`
  and `_process`;
- **criterion**: `[x]` — duplication removed, all workers inherit the base.

## 3. Hybrid flashlight detection

- **problem**: `detected` depended only on the classifier, while the bright
  spot was always computed but drawn only when `detected` — if the classifier
  stayed silent but the lens was glowing, nothing was detected;
- **solution**: `detected = classifier OR bright spot`; the score comes from
  the classifier, otherwise from the lens brightness;
- **criterion**: `[x]` — a glowing lens is detected even without classifier
  confirmation.

## 4. Error slots log the real cause

- **problem**: `smile_worker_error`/`flashlight_worker_error` ignored their
  parameters (type, value, traceback) and only showed a generic message;
- **solution**: log the full exception and show a short cause in the status
  bar;
- **criterion**: `[x]` — the traceback lands in the log, the cause in the
  status bar.

## 5. Dead code

- **problem**: no-op slots `smile_worker_progress`/`flashlight_worker_progress`,
  the `progress` signal (connected to stubs), and the `SmileFeatures.corner_rise`
  field was unused in scoring;
- **solution**: remove the `progress` signal from the workers, the slots and
  the connections, and the `corner_rise` field;
- **criterion**: `[x]` — `ruff` finds no unused code, everything compiles.

## 6. Tests

- **problem**: the `convert.py`/`lerp.py` utilities had no tests; tests peeked
  into private fields (`label._image`, `label._face_boxes`, ...);
- **solution**: tests for `lerp` and `convert`; public properties/methods on
  `OverlayLabel` (`image`, `face_boxes`, `flashlight_bbox`, `draw_rect`,
  `map_rect`) instead of private ones;
- **criterion**: `[x]` — `just check` is green, utility coverage added.

## How to verify

- [x] `just check` (ruff + mypy + pytest)
- [x] `uv run pytest smokes` — all tests pass