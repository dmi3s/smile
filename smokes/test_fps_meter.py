from smile.utils.fps_meter import FpsMeter


def test_initial_fps_is_zero():
    assert FpsMeter().fps == 0.0


def test_single_update_returns_zero():
    meter = FpsMeter()
    assert meter.update(1_000_000_000) == 0.0


def test_constant_rate_gives_expected_fps():
    meter = FpsMeter(alpha=1.0)
    fps = 0.0
    ts = 0
    for _ in range(5):
        ts += 50_000_000  # 50 ms interval -> 20 fps
        fps = meter.update(ts)
    assert fps == 20.0


def test_smoothing_produces_positive_fps():
    meter = FpsMeter(alpha=0.5)
    fps = 0.0
    ts = 0
    for i in range(20):
        ts += 50_000_000 + (i % 2) * 5_000_000
        fps = meter.update(ts)
    assert fps > 0.0


def test_reset_clears_state():
    meter = FpsMeter(alpha=1.0)
    meter.update(1_000_000_000)
    meter.update(1_050_000_000)
    assert meter.fps == 20.0
    meter.reset()
    assert meter.fps == 0.0


def test_invalid_alpha_rejected():
    try:
        FpsMeter(alpha=0.0)
    except ValueError:
        return
    raise AssertionError("FpsMeter accepted alpha=0.0")
