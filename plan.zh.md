# 计划：重构与修复

**语言:** [English](plan.md) · [Русский](plan.ru.md) · [中文](plan.zh.md)

代码评审后的逐项修复清单。每一项都是独立的工作单元，并有各自的验收标准。

## 1. `eventFilter` 不应吞掉所有按键

- **问题**: `MainWindow.eventFilter` 对任意 `KeyPress` 都返回 `True`
  （`main_window.py:65`），因此任何未来的输入（例如相机设置输入框）都会被
  过滤器吃掉;
- **方案**: 只拦截 `Ctrl+Q`，其余事件交给基础处理;
- **验收**: `[x]` — 只有 `Ctrl+Q` 退出应用，其他按键能到达控件。

## 2. 把通用的 worker 模式抽取成基类

- **问题**: 三个检测 worker 逐字重复了 mailbox 机制和 `_process_next`
  循环（try/except/emit/finally）;
- **方案**: 在 `utils/mailbox_worker.py` 中提供基类 `MailboxWorker` —
  `wakeup`、`shutdown`、`_enqueue`、`_process_next`;子类实现 `_init_worker`
  和 `_process`;
- **验收**: `[x]` — 重复代码已消除，所有 worker 继承基类。

## 3. 手电筒的混合检测

- **问题**: `detected` 只取决于分类器，而亮斑总是被计算，却仅当 `detected`
  时绘制——如果分类器保持沉默但镜头在发光，就检测不到;
- **方案**: `detected = 分类器 OR 亮斑`;分数来自分类器，否则取镜头亮度;
- **验收**: `[x]` — 即使没有分类器确认，也能检测到发光的镜头。

## 4. 错误槽记录真实原因

- **问题**: `smile_worker_error`/`flashlight_worker_error` 忽略了参数
  （类型、值、回溯）并只显示通用消息;
- **方案**: 记录完整异常，并在状态栏显示简短原因;
- **验收**: `[x]` — 回溯进入日志，原因进入状态栏。

## 5. 死代码

- **问题**: no-op 槽 `smile_worker_progress`/`flashlight_worker_progress`、
  信号 `progress`（连接到空实现），以及评分中未使用的字段
  `SmileFeatures.corner_rise`;
- **方案**: 从 worker 中移除 `progress` 信号、槽和连接，并移除
  `corner_rise` 字段;
- **验收**: `[x]` — `ruff` 未发现未使用的代码，一切可编译。

## 6. 测试

- **问题**: `convert.py`/`lerp.py` 工具没有测试;测试窥探了私有字段
  （`label._image`、`label._face_boxes` 等）;
- **方案**: 为 `lerp` 和 `convert` 添加测试;在 `OverlayLabel` 上提供公共
  属性/方法（`image`、`face_boxes`、`flashlight_bbox`、`draw_rect`、
  `map_rect`）取代私有字段;
- **验收**: `[x]` — `just check` 通过，工具类已覆盖。

## 如何验证

- [x] `just check`（ruff + mypy + pytest）
- [x] `uv run pytest smokes` — 所有测试通过