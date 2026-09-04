#!/usr/bin/env python3
"""Draw src/res/drawable/ic_heart.png, the heart mark next to the heart rate.

The HEART_RATE system complication provider supplies no monochromatic image of
its own, and a literal U+2665 in the text gets claimed by the colour emoji font
and renders as a red blob, so the face ships its own mark.

Drawn white on transparent and tinted at render time, so the grey lives in the
watch face palette rather than being baked into the asset.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 64
SUPERSAMPLE = 8  # drawn large and downscaled, since PIL has no antialiased fill


def heart_points(n=400):
    """The classic parametric heart, normalised into a unit square."""
    raw = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        raw.append((x, -y))  # flip y: image coordinates grow downward

    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y)

    # Centre the glyph in the square after scaling by its longest axis.
    pad_x = (span - (max_x - min_x)) / 2
    pad_y = (span - (max_y - min_y)) / 2
    return [((x - min_x + pad_x) / span, (y - min_y + pad_y) / span) for x, y in raw]


def main():
    big = SIZE * SUPERSAMPLE
    img = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)

    # Inset slightly so the shape does not touch the edges of the bitmap.
    inset = big * 0.04
    extent = big - 2 * inset
    d.polygon(
        [(inset + x * extent, inset + y * extent) for x, y in heart_points()],
        fill=(255, 255, 255, 255),
    )

    img = img.resize((SIZE, SIZE), Image.LANCZOS)

    out = Path(__file__).resolve().parent.parent / "src/res/drawable/ic_heart.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
