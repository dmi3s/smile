def lerp(a: float | int, b: float | int, t: float) -> float:
    """Linear interpolate on the scale given by a to b, using t as the point on that scale.

    Examples
    --------
        50 == lerp(0, 100, 0.5)
        4.2 == lerp(1, 5, 0.8)

    """
    return (1 - t) * a + t * b
