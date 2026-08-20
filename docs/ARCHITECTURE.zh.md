# Smile 架构：实时运行原理

**语言:** [English](ARCHITECTURE.md) · [Русский](ARCHITECTURE.ru.md) · [中文](ARCHITECTURE.zh.md)

应用是一个由四个 worker 线程组成的异步实时流水线（`camera_worker` →
`face_worker` → `smile_worker`，外加与脸部检测并行的 `flashlight_worker`），
由 `SmileApp`（`QApplication` 的子类）统一编排。每个 worker 运行在自己的
`QThread` 中；线程间的数据通过 Qt 信号传递，worker 内部则通过单槽的
`LatestValueMailbox`（latest-wins 语义）传递。

下面的图表位于 `docs/generated/`，D2 源文件就在旁边的 `docs/*.d2` 中
（在 `docs/` 下通过 `just build` 重新构建）。

## 1. 输入缓冲区：帧的生存与 mailbox

![输入缓冲区](generated/buffer_lifecycle.svg)

两个关键机制：

- **帧在源头被复制。** `CameraWorker` 从 OpenCV 读入一帧后立即调用
  `Frame.create_copy()`：一份私有的 `read-only` 快照（`image.copy() +
  writeable=False`）。此后 QImage（UI）和 CV worker 都能无风险地读取这份
  副本——不再有人覆写相机缓冲区，因此撕裂帧不可能出现。在流水线内部，
  已创建的副本用便宜的 `Frame.create_share()` 共享（同一缓冲区，同样
  只读）。

- **Mailbox 是单槽输入缓冲区。** `LatestValueMailbox<T>` 恰好保存一个
  `pending_data` 和一个 `busy` 标志：

  - `new_data(x)` — 只是把值放入槽中，**覆盖**旧值（如果消费者来不及处理，
    旧值就丢失了——这就是 latest-wins）;
  - `try_start()` — 仅当 `running && !busy && pending != None` 时才开始
    处理;否则什么都不做，等待下一个 `new_data`;
  - `extract_data()` — 取出值并清空槽;
  - `complete_and_should_continue()` — 清除 `busy`;如果处理期间又来了新的
    pending 值，立即开始下一轮处理。

  结论：worker 从不"堆积"帧——输入缓冲区行为像一个新鲜单元，而不是队列。

## 2. 识别流水线

![识别流水线](generated/recognition_pipeline.svg)

- `CameraWorker` 捕获帧（800×448 @ ~20 fps），并通过 `frame_ready` 信号把
  `Frame` 同时发送**给 UI、face worker 和 flashlight worker**。
- `FaceDetectionWorker` 把帧缩小一半（`0.5x`，RGB）并通过 MediaPipe
  `FaceDetector`（`RunningMode.VIDEO`）处理。结果是 `FaceDetectionResult`：
  归一化的面部框（0..1）加上缩小后的 RGB 帧（`small_frame_rgb`）。帧与帧
  之间，框通过贪心中心匹配进行跟踪，并用 EMA 平滑（`FaceTracker`）。
- `SmileDetectionWorker` 接收 face worker 的结果，把 `small_frame_rgb` 送入
  MediaPipe `FaceLandmarker`（478 个点），并用 `smile_score()` 依据嘴部
  几何计算微笑分数：

  - `openness` — 嘴高 / 嘴宽;
  - `spread` — 嘴宽 / 两眼间距;
  - `corner_lift` — 嘴角相对唇线的抬升（门控）。

  最终分数为 `max(spread_score, open_score * lift_gate)` ∈ [0, 1]，阈值在
  真实摄像头数据上校准。
- `FlashlightDetectionWorker` 与脸部检测并行，把帧（400×224）送入 ImageNet
  分类器 MobileNet V2（`RunningMode.VIDEO`）：top-5 中出现 `torch`/
  `flashlight` 类且分数 ≥ `0.03` → "找到手电筒"（即使在关闭时也有效）。
  然后寻找发光的镜头：亮度二值化（阈值 200）+ 连通域 → 面积占画面
  0.5–60% 的最大色块 → 归一化框。结果是 `FlashlightDetectionResult`
  （`detected`、`score`、`bright_bbox`、`brightness`）。

## 3. 类与职责

![类图](generated/class_map.svg)

| 类 / 模块 | 职责 |
|---|---|
| `SmileApp` | 编排：创建 worker 和 4 个线程、连接信号、幂等的 `shutdown()`、SIGINT/SIGTERM 退出 |
| `QThread` ×4 | 每个 worker 一个工作线程 |
| `CameraWorker` | 相机捕获：`QTimer` → `read()` → `Frame`;失败时进入重连循环（`RETRY_DELAY_MS`、`camera_error` → `camera_recovered`），用探测帧尝试多个来源（上次成功 → 索引 0..5 → Linux 下 `/dev/video*`），应用不会"卡死" |
| `Frame` | 不可变的帧快照（`create_share` / `create_copy`） |
| `FaceDetectionWorker` | `FaceDetector`（VIDEO 模式）、框归一化、`small_frame_rgb` |
| `FaceTracker` | 贪心中心匹配 + EMA 平滑、`max_lost` |
| `SmileDetectionWorker` | `FaceLandmarker`（VIDEO 模式），调用 `smile_score()` |
| `smile_detection.py` | 纯评分逻辑：`mouth_features()`、`smile_score()`、阈值 `OPEN`/`SPREAD`/`LIFT` |
| `FlashlightDetectionWorker` | `ImageClassifier` MobileNet V2（VIDEO 模式）+ `detect_bright_spot()` → `FlashlightDetectionResult` |
| `flashlight_detection.py` | 纯逻辑：`is_flashlight()`（关键词 `torch`/`flashlight`）、`detect_bright_spot()`（阈值 200、面积 0.5–60%） |
| `LatestValueMailbox<T>` | 单槽 latest-wins 输入缓冲区 |
| `MainWindow` | 槽 `update_frame` / `update_face_recognition` / `update_smile_status` / `update_flashlight`、截图、状态栏（FPS + 🔦） |
| `OverlayLabel` | `QPainter`：视频 + 面部框 + 手电筒黄色框 |
| `ExponentialJitterSmoother` | 微笑分数的 EMA 平滑（α=0.3） |
| `FpsMeter` | EMA FPS 计：cam · face · smile · render |
| 模型（Git LFS） | `blaze_face_short_range.tflite`、`face_landmarker.task`、`mobilenet_v2_1.0_224.tflite` |

## 4. 实时循环

![实时循环](generated/realtime_loop.svg)

实时应用的一个"节拍"：

1. `CameraWorker` 按定时器读取一帧并发出 `frame_ready`——信号同时到达 UI
   线程（渲染）、face worker（检测）和 flashlight worker（手电筒）。
2. face worker 把帧放入自己的 mailbox，若空闲则通过
   `QTimer.singleShot(0)` 立即开始处理;若忙碌——帧只是覆盖 pending（旧的
   被丢弃）。
3. 脸部检测结果进入 UI（更新框）和 smile worker。
4. smile worker 通过相同的 mailbox 方案处理 `small_frame_rgb`，计算分数，
   并把 `SmileDetectionResult` 发给 UI。
5. flashlight worker 并行地对帧进行分类，并把 `FlashlightDetectionResult`
   发给 UI（黄色框 + 状态栏中的 `🔦`）。
6. UI 线程的 `update_smile_status` 用 EMA（α=0.3）平滑最佳分数并显示表情：
   `🖖` 无脸 / `😐` 中性 / `😊` 微笑 / `😄` 大笑。

**为什么这是实时的：** 延迟比完整性更重要。worker 始终只处理最新输入，
过期的帧被有意丢弃，相机捕获永远不会被检测阻塞，所有 Qt 渲染都严格运行在
主 UI 线程上。