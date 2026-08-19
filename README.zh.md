![logo](src/smile/resources/icons/smile-lol.png)
# Smile

**语言:** [English](README.md) · [Русский](README.ru.md) · [中文](README.zh.md)

基于 Python、Qt 和 MediaPipe 构建的实时人脸检测实验平台。

项目从网络摄像头抓取帧，在独立的 worker 线程中执行人脸与微笑检测，并在 PySide6 界面中绘制叠加层。

当前状态：

- 网络摄像头实时预览
- 人脸检测（多人脸）+ 人脸框跟踪与平滑
- 微笑检测（评分 0..1 + 表情符号状态）
- 手电筒设备检测（ImageNet 分类器 + 亮点）
- 带人脸与手电筒框的叠加层渲染
- 状态栏中的 FPS 指标（cam · face · smile · render）
- 归一化的人脸坐标
- 线程优雅退出

计划中：

- 摄像头设置界面
- 摄像头重连处理

---

## 技术栈

- Python 3.12
- PySide6 / Qt6
- OpenCV
- MediaPipe Tasks（FaceDetector + FaceLandmarker）
- NumPy

工具：

- uv
- just
- pytest（冒烟测试）
- GitHub Actions（CI）
- Git LFS（模型）

---

## 功能特性

- 网络摄像头实时采集
- 通过 MediaPipe 进行人脸检测
- 通过 FaceLandmarker 进行微笑检测：`openness`（嘴巴张开度）+ `spread`（嘴宽/眼间距），阈值已标定
- 人脸平滑与跟踪：基于中心的贪婪匹配 + EMA，人脸框不再在帧间跳动
- 手电筒检测：ImageNet 分类器（MobileNet V2，`torch` 类别——即使关灯也能识别）+ 亮斑定位 → 黄色框
- 状态栏中的 FPS 指标：cam · face · smile · render
- 四个工作线程（camera → face → smile + 手电筒并行），基于共享 mailbox 机制
- 通过 QPainter 进行 UI 线程安全的渲染
- 归一化边界框（0..1）
- 丢弃过期帧的低延迟策略
- 微笑状态：`🖖` 无人脸 / `😐` 中性 / `😊` 微笑 / `😄` 大笑
- 截图按钮 —— 将整个窗口保存到 `~/Pictures/smile/smile-YYYY-MM-DD_HH-MM-SS.png`
- 冒烟测试（offscreen Qt）

---

## 项目结构

```text
src/smile/
├── camera/          # CameraWorker, Frame
├── recognition/     # 人脸/微笑/手电筒检测 worker + 模型 (LFS)
│   ├── detectors/   # 检测器与 worker（人脸、微笑、手电筒）
│   ├── tracking/    # 人脸跟踪 (FaceTracker)
│   └── models/      # MediaPipe/ImageNet 模型 (Git LFS)
├── ui/              # main_window.ui + generated/
├── widgets/         # OverlayLabel
├── windows/         # MainWindow
├── utils/           # LatestValueMailbox, lerp, smooth, convert, FpsMeter
├── resources/       # 图标、图片、qrc
└── smile_app.py     # 应用 + 线程编排

smokes/              # pytest 冒烟测试（offscreen）
```

---

## 安装

### 环境要求

- Python 3.12+
- uv
- just

安装 uv：

https://docs.astral.sh/uv/

安装 just：

https://github.com/casey/just

---

## 配置

克隆：

```bash
git clone git@github.com:dmi3s/smile.git
cd smile
```

安装依赖：

```bash
uv sync
```

模型（`blaze_face_short_range.tflite`、`face_landmarker.task`、`mobilenet_v2_1.0_224.tflite`）存储在 Git LFS 中，如果安装了 LFS，克隆时会自动拉取：

```bash
git lfs install
```

---

## 运行

通过 just：

```bash
just bootstrap   # 首次
just run
```

或直接运行：

```bash
uv run smile
```

操作：

- `Ctrl+Q` — 退出
- `Screenshot` 按钮 — 将窗口快照保存到 `~/Pictures/smile/`

---

## 开发

生成 Qt UI 文件：

```bash
just gen-ui
```

生成 Qt 资源：

```bash
just gen-resources
```

代码检查：

```bash
just check            # ruff + mypy
uv run pytest smokes  # 冒烟测试
```

---

## 文档

架构详解与图表（输入缓冲区、流水线、类、实时循环）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。D2 源文件与生成的 SVG 位于 `docs/`。

构建 PDF（Typst），在 `docs/` 目录下：

```bash
just build            # 一次性构建 → build/README.pdf
just r                # watch 模式：.typ/.d2 变化时自动重新构建
```

或直接使用 typst：

```bash
typst compile README.typ build/README.pdf
typst watch README.typ build/README.pdf
```

打开 PDF（watch 模式下 okular 会自动刷新）：

```bash
okular build/README.pdf
```

---

## 架构

应用使用四线程的异步实时流水线：

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

手电筒检测运行在独立的 worker 中，与人脸检测并行：

```text
 Camera Worker ── frame_ready ──▶ Flashlight Detection Worker
                                       │ result
                                       ▼
                                 Qt Main Thread (黄色框)
```

核心思想：

- 摄像头采集永远不会被检测阻塞
- 渲染与人脸检测并行执行
- 每个 worker 只处理最新的可用输入
- 故意丢弃过期帧以降低延迟
- 人脸坐标以归一化形式存储（`0..1`）
- 所有 Qt 渲染都在主 UI 线程中完成

### 人脸跟踪与平滑

人脸 worker 会在帧之间保留检测结果：通过基于中心的贪婪匹配将检测到的人脸框与轨迹关联，并对每个框进行指数平滑（EMA）。这消除了检测不稳定带来的抖动与闪烁，人脸消失后轨迹仍能存活几帧（`max_lost`）。

### 微笑检测

微笑 worker 将帧交给 `FaceLandmarker`（478 个关键点），并根据嘴唇关键点计算两个指标：

- `openness` = 嘴高 / 嘴宽 —— 微笑时嘴巴张开
- `spread` = 嘴宽 / 眼间距 —— 微笑时嘴角向两侧张开

评分 `max(openness, spread)` ∈ [0, 1]，阈值根据真实摄像头数据标定。两个指标在微笑消失时都会回归中性值，因此状态会正确"熄灭"。

参考关键点 —— MediaPipe FaceMesh 关键点索引：`13`/`14`（唇心）、`61`/`291`（嘴角）、`33`/`263`（外眼角）。

### 手电筒检测

手电筒 worker 是一个"图一乐"的混合启发式方法：

- **设备存在性**：将帧（400×224）送入 ImageNet 分类器 MobileNet V2；如果 top-5 中出现 `torch`/`flashlight` 类别且评分 ≥ `0.03`，则认为检测到手电筒——即使关灯也能识别；
- **亮斑定位**：亮度二值化（阈值 200）+ 连通域 → 面积占帧 0.5–60% 的最大斑块 → 黄色框，并在状态栏显示评分（`🔦`）。

检测评分不会影响微笑评分——这是流水线之上的一个独立小彩蛋。

---

## 性能

在 Linux 桌面环境下：

- ~20-30 FPS 摄像头预览
- 实时人脸与微笑检测
- 手电筒检测（MobileNet V2）通过 XNNPACK 在 CPU 上推理

实际性能取决于：

- 摄像头分辨率
- CPU
- 检测用帧缩放
- 渲染后端

---

## 备注

该项目首先是一个实验：

- 学习 PySide6
- 研究实时 CV 流水线
- 对比 Python 与 C++ 在桌面 CV 应用中的开发体验

当前实现的优先级：

- 简单性
- 架构清晰
- 开发速度

优先于过早优化。

---

## 许可证

MIT

---

## AI: Thinking

_来自 AI 助手 **opencode**（DeepSeek）的备忘录。我对项目的主观评估，留作历史记录。日期：2026-08-18，代码状态 —— `main` 分支，`e94c952`。已解决的项目以 inline 标注。_

### 核心

实时微笑检测器：PySide6 应用，摄像头 → 三线程流水线（人脸检测 → 嘴唇关键点 → 微笑评分），输出为人脸框叠加到视频上以及表情符号状态。Python 3.12+、MediaPipe Tasks、OpenCV、NumPy。

### 架构与数据流

```text
CameraWorker ──frame──▶ MainWindow.update_frame (QImage zero-copy → OverlayLabel)
      │  frame
      ▼
FaceDetectionWorker ──FaceDetectionResult──▶ MainWindow (boxes)
      │   face_result (small RGB 400x224)
      ▼
SmileDetectionWorker ──SmileDetectionResult──▶ MainWindow.update_smile_status (EMA → emoji)
```

- 每个 worker 运行在自己的 `QThread` 中，数据通过 `LatestValueMailbox` 传递（latest-wins，`smile_app.py:126`、`latest_value_mailbox.py:7`）
- 停止：`stop_*` 信号 → `shutdown()` → `th.quit() + wait(3000)`（`smile_app.py:74-91`）
- 评分：`max(open_score, spread_score)`，阈值 `OPEN 0.12–0.30`、`SPREAD 0.72–0.85`（`smile_detection.py:28-31, 88-90`）
- 平滑：EMA `alpha=0.3`；表情符号 `🖖/😐/😊/😄` 阈值为 0.20/0.60（`main_window.py:77-85`）

### 做得好的地方

- **在源头抓帧快照**：camera worker 中的 `Frame.create_copy` —— QImage 与 CV worker 读取私有只读副本，杜绝了缓冲区覆盖竞态（正确性优先于速度）
- **Mailbox latest-wins** —— 实时场景的正确模型（延迟优先于完整性）
- 结构清晰：检测器与 worker 分离，平滑/lerp 辅助函数在 utils 中
- **完整 CI**：LFS checkout、gen-ui、ruff+format、mypy、pytest、`uv audit`、`uv build`（`ci.yml`）
- **测试**：offscreen 测试，包括标定的 `test_smile.py` 以及表情符号逻辑/平滑
- 正确的 SIGINT/SIGTERM 退出、模型使用 Git LFS、签名发布标签

### 问题与风险

1. **共享摄像头缓冲区竞态** —— 之前：`overlay_label.py:33` 中 QImage 持有摄像头缓冲区引用，而 OpenCV 在下一次 `read()` 时覆盖它（`camera_worker.py:87-97`），可能出现撕裂帧。**已解决**：在源头拷贝（`Frame.create_copy`），Frame 持有私有快照。
2. **`corner_lift` 未参与评分** —— 之前：没有微笑的龇牙咧嘴/张嘴也会触发表情符号（`smile_detection.py:72, 88-90`）。**已解决**：`score = max(spread_score, open_score * lift_gate)`（`05fef5d`）。
3. **日志路径脆弱** —— 之前：FileHandler 在未创建目录的情况下写入 `logs/smile-*.log`（`__main__.py:15`）。**已解决**：在创建 handler 前执行 `Path("logs").mkdir(...)`（`77fa726`）。
4. **mailbox 中的死代码** —— 之前：`can_schedule`、`has_pending_data`、`active()` 从未被使用（`latest_value_mailbox.py:59, 89, 111`）。**已解决**：已删除（`4952b41`）。
5. **`eventFilter` 吞掉所有按键** —— 对任何 KeyPress 都返回 `True`（`main_window.py:37-42`）；若添加输入框会出问题。
6. **日志中重复的 `Shutdown completed`** —— 之前：`shutdown()` 在信号退出时触发两次（`smile_app.py:70-72, 74`）。**已解决**：加守卫标志并移除 `processEvents()` 造成的重入（`7a6df3d`）。
7. **摄像头故障后无法重启** —— `camera_error` → 模态弹窗，应用实际上变成死状态。
8. **CI 中的 `uv audit --preview-features audit`** —— 是预览标志，uv 升级后可能失效。
9. **修复后版本未提升** —— 之前：0.1.5 该发了（SIGTERM 处理 + `corner_lift`）。**已解决**：提升到 0.1.5。
10. 小问题：测试会窥探私有属性（`label._image`），`convert.py`/`lerp.py` 是没有独立测试的辅助工具。

### 建议（按优先级）

1. ~~让 `corner_lift` 参与评分~~ —— **已完成**：openness 由嘴角上提门控（`05fef5d`）
2. ~~为 QImage 拷贝帧，或交替使用两个缓冲区~~ —— **已完成**：在源头做 `Frame.create_copy` 快照
3. ~~健壮的日志路径~~ —— **已完成**：启动时创建 `logs/`（`77fa726`）
4. ~~移除死代码、修复重复的 `shutdown`~~ —— **已完成**（`4952b41`、`7a6df3d`）
5. ~~提升到 0.1.5 并发布~~ —— **已完成**：版本 0.1.5

---

_由 AI 助手 **opencode** —— DeepSeek-V4 模型，会话 2026-08-18 —— 写入历史。这是一个真实的交互式 CV 实验项目，我觉得它很有意思。_