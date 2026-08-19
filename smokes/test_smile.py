from smile.recognition.detectors.smile_detection import (
    LEFT_EYE_OUTER,
    LEFT_MOUTH_CORNER,
    LOWER_LIP_CENTER,
    RIGHT_EYE_OUTER,
    RIGHT_MOUTH_CORNER,
    UPPER_LIP_CENTER,
    smile_score,
)


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _face(mouth: dict[int, tuple[float, float]]) -> list[Point]:
    landmarks = [Point(0.5, 0.5) for _ in range(478)]
    # inter-eye width 0.20, so neutral mouth width 0.12 gives spread 0.60
    landmarks[LEFT_EYE_OUTER] = Point(0.40, 0.30)
    landmarks[RIGHT_EYE_OUTER] = Point(0.60, 0.30)
    for index, (x, y) in mouth.items():
        landmarks[index] = Point(x, y)
    return landmarks


def _neutral() -> list[Point]:
    # mouth closed (lips together): openness ~0.008, spread 0.60
    return _face(
        {
            LEFT_MOUTH_CORNER: (0.44, 0.50),
            RIGHT_MOUTH_CORNER: (0.56, 0.50),
            UPPER_LIP_CENTER: (0.50, 0.499),
            LOWER_LIP_CENTER: (0.50, 0.500),
        }
    )


def _open_smile() -> list[Point]:
    # mouth opens wide AND corners pull up: openness 0.67, corner lift 0.33
    return _face(
        {
            LEFT_MOUTH_CORNER: (0.44, 0.44),
            RIGHT_MOUTH_CORNER: (0.56, 0.44),
            UPPER_LIP_CENTER: (0.50, 0.44),
            LOWER_LIP_CENTER: (0.50, 0.52),
        }
    )


def _grimace() -> list[Point]:
    # open mouth (openness 0.67) but corners NOT raised: lift 0.17
    return _face(
        {
            LEFT_MOUTH_CORNER: (0.44, 0.46),
            RIGHT_MOUTH_CORNER: (0.56, 0.46),
            UPPER_LIP_CENTER: (0.50, 0.44),
            LOWER_LIP_CENTER: (0.50, 0.52),
        }
    )


def _closed_lip_smile() -> list[Point]:
    # corners pull apart: mouth width 0.16 -> spread 0.80
    return _face(
        {
            LEFT_MOUTH_CORNER: (0.42, 0.47),
            RIGHT_MOUTH_CORNER: (0.58, 0.47),
            UPPER_LIP_CENTER: (0.50, 0.479),
            LOWER_LIP_CENTER: (0.50, 0.480),
        }
    )


def test_neutral_face_scores_zero():
    assert smile_score(_neutral()) == 0.0


def test_open_smile_scores_high():
    assert smile_score(_open_smile()) > 0.5


def test_grimace_open_mouth_scores_zero():
    assert smile_score(_grimace()) == 0.0


def test_closed_lip_smile_scores_positive():
    assert smile_score(_closed_lip_smile()) > 0.3


def test_degenerate_width_does_not_crash():
    degenerate = _face({LEFT_MOUTH_CORNER: (0.5, 0.5), RIGHT_MOUTH_CORNER: (0.5, 0.5)})
    assert smile_score(degenerate) == 0.0
