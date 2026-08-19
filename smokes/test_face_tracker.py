from smile.recognition.detectors.face_detection import DetectedFaceBox, FaceBox
from smile.recognition.tracking.face_tracker import FaceTracker


def _face(fx: float, fy: float, fw: float, fh: float, score: float = 0.9):
    return DetectedFaceBox(bbox=FaceBox(fx, fy, fw, fh), score=score)


def test_single_face_initializes_on_first_frame():
    tracker = FaceTracker()
    out = tracker.update((_face(0.1, 0.2, 0.3, 0.4),))
    assert len(out) == 1
    assert out[0].bbox == FaceBox(0.1, 0.2, 0.3, 0.4)
    assert out[0].score == 0.9


def test_stable_face_reduces_jitter():
    tracker = FaceTracker()
    center = (0.3, 0.4)
    noisy = [
        _face(center[0] + dx, center[1] + dy, 0.3, 0.3)
        for dx, dy in (
            (0.05, -0.05),
            (-0.04, 0.04),
            (0.03, -0.03),
            (-0.05, 0.05),
            (0.04, -0.04),
        )
    ]

    raw_jitter = 0.0
    out_jitter = 0.0
    prev_raw = (0.3, 0.4)
    prev_out = (0.3, 0.4)
    for fb in noisy:
        raw_cx, raw_cy = fb.bbox.fx + fb.bbox.fw / 2, fb.bbox.fy + fb.bbox.fh / 2
        raw_jitter += abs(raw_cx - prev_raw[0]) + abs(raw_cy - prev_raw[1])
        prev_raw = (raw_cx, raw_cy)

        out = tracker.update((fb,))[0]
        out_cx, out_cy = out.bbox.fx + out.bbox.fw / 2, out.bbox.fy + out.bbox.fh / 2
        out_jitter += abs(out_cx - prev_out[0]) + abs(out_cy - prev_out[1])
        prev_out = (out_cx, out_cy)

    assert out_jitter < raw_jitter


def test_face_lost_for_few_frames_keeps_track():
    tracker = FaceTracker(max_lost=2)
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))

    for _ in range(2):
        out = tracker.update(())
        assert len(out) == 1
        assert out[0].bbox.fx == 0.1

    out = tracker.update(())
    assert out == ()


def test_face_returns_within_max_lost_keeps_same_id():
    tracker = FaceTracker(max_lost=2)
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))

    tracker.update(())
    tracker.update(())
    out = tracker.update((_face(0.11, 0.21, 0.3, 0.3),))
    assert len(out) == 1


def test_sudden_teleport_creates_new_track():
    tracker = FaceTracker()
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))
    out = tracker.update((_face(0.9, 0.8, 0.05, 0.05),))

    assert len(out) == 1
    assert out[0].bbox.fx == 0.9
    assert out[0].bbox.fy == 0.8


def test_jump_within_max_dist_is_smoothed():
    tracker = FaceTracker(max_dist=0.5)
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))
    out = tracker.update((_face(0.6, 0.2, 0.3, 0.3),))
    assert 0.1 < out[0].bbox.fx < 0.6


def test_two_static_faces_keep_count():
    tracker = FaceTracker()
    faces = (_face(0.1, 0.2, 0.3, 0.3), _face(0.6, 0.2, 0.3, 0.3))
    for _ in range(10):
        out = tracker.update(faces)
    assert len(out) == 2


def test_empty_input_after_tracks_prunes():
    tracker = FaceTracker(max_lost=1)
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))
    assert tracker.update(()) != ()
    assert tracker.update(()) == ()


def test_score_is_smoothed():
    tracker = FaceTracker(alpha=0.5)
    tracker.update((_face(0.1, 0.2, 0.3, 0.3, score=0.5),))
    out = tracker.update((_face(0.1, 0.2, 0.3, 0.3, score=1.0),))
    assert out[0].score == 0.75


def test_reset_clears_state():
    tracker = FaceTracker()
    tracker.update((_face(0.1, 0.2, 0.3, 0.3),))
    tracker.reset()
    assert tracker.update(()) == ()
    out = tracker.update((_face(0.5, 0.5, 0.2, 0.2),))
    assert len(out) == 1


def test_invalid_parameters():
    for kwargs in ({"alpha": 0.0}, {"alpha": 1.5}, {"max_dist": 0.0}, {"max_lost": -1}):
        try:
            FaceTracker(**kwargs)
        except ValueError:
            continue
        raise AssertionError(f"FaceTracker accepted invalid {kwargs}")
