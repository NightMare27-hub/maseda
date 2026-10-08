import math
from math_utils import clamp


def distance(p1: tuple, p2: tuple) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class Rectangle:
    def __init__(self, width: float, height: float):
        if width < 0 or height < 0:
            raise ValueError("Dimensions must be non-negative")
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)


def is_inside_box(point: tuple, box: tuple) -> bool:
    x, y = point
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def scale_rectangle(rect: Rectangle, factor: float) -> Rectangle:
    safe_factor = clamp(factor, 0.1, 10.0)
    return Rectangle(rect.width * safe_factor, rect.height * safe_factor)

