#!/usr/bin/env python3
"""Draw the weather glyph set into src/res/drawable/.

[WEATHER.CONDITION] is an enum 0-15, which the face uses as an index into a
BitmapFont, so each value needs a glyph. Several conditions share one (light,
normal and heavy rain differ only in how many strokes fall), and CLEAR/SUNNY
get a sun by day and a moon by night.

Drawn white on transparent and tinted at render time, so the grey lives in the
watch face palette rather than being baked into the assets. Same approach as
tools/make_heart.py.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 96
SS = 4  # supersample factor; PIL has no antialiased fill
W = SIZE * SS
WHITE = (255, 255, 255, 255)
CLEAR = (255, 255, 255, 0)

OUT = Path(__file__).resolve().parent.parent / "src/res/drawable"


def canvas():
    img = Image.new("RGBA", (W, W), CLEAR)
    return img, ImageDraw.Draw(img)


def circle(d, cx, cy, r, fill=WHITE):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


def sun(d, cx, cy, r, rays=8, ray_len=None, ray_w=None):
    ray_len = ray_len if ray_len else r * 0.62
    ray_w = ray_w if ray_w else r * 0.30
    circle(d, cx, cy, r)
    for i in range(rays):
        a = 2 * math.pi * i / rays
        x0 = cx + math.cos(a) * (r + ray_len * 0.42)
        y0 = cy + math.sin(a) * (r + ray_len * 0.42)
        x1 = cx + math.cos(a) * (r + ray_len * 1.25)
        y1 = cy + math.sin(a) * (r + ray_len * 1.25)
        d.line((x0, y0, x1, y1), fill=WHITE, width=int(ray_w))


def moon(img, cx, cy, r):
    """Crescent: a disc with an offset disc punched out."""
    lay = Image.new("RGBA", img.size, CLEAR)
    ld = ImageDraw.Draw(lay)
    circle(ld, cx, cy, r)
    # Punch with a transparent offset disc.
    cut = Image.new("RGBA", img.size, CLEAR)
    cd = ImageDraw.Draw(cut)
    circle(cd, cx + r * 0.52, cy - r * 0.42, r * 0.92)
    lay.paste(CLEAR, (0, 0), cut)
    img.alpha_composite(lay)


def cloud(d, cx, cy, w):
    """Rounded cloud centred on (cx, cy) with overall width w."""
    r_big = w * 0.30
    r_mid = w * 0.24
    r_sml = w * 0.20
    base_y = cy + r_big * 0.52
    circle(d, cx - w * 0.20, cy + r_big * 0.10, r_mid)
    circle(d, cx + w * 0.02, cy - r_big * 0.28, r_big)
    circle(d, cx + w * 0.26, cy + r_big * 0.12, r_sml)
    d.rounded_rectangle(
        (cx - w * 0.40, base_y - r_big * 0.72, cx + w * 0.42, base_y + r_big * 0.30),
        radius=r_big * 0.5,
        fill=WHITE,
    )


def strokes(d, cx, y0, n, length, slant=0.28, width=None, spacing=None):
    """Falling strokes under a cloud, for rain and sleet."""
    width = width if width else W * 0.045
    spacing = spacing if spacing else W * 0.17
    start = cx - spacing * (n - 1) / 2
    for i in range(n):
        x = start + i * spacing
        d.line((x, y0, x - length * slant, y0 + length), fill=WHITE, width=int(width))


def flakes(d, cx, y0, n, r):
    start = cx - W * 0.17 * (n - 1) / 2
    for i in range(n):
        x = start + i * W * 0.17
        y = y0 + (W * 0.06 if i % 2 else 0)
        for k in range(3):
            a = math.pi * k / 3
            d.line(
                (
                    x - math.cos(a) * r,
                    y - math.sin(a) * r,
                    x + math.cos(a) * r,
                    y + math.sin(a) * r,
                ),
                fill=WHITE,
                width=int(W * 0.035),
            )


def snowflake(d, cx, cy, r, arms=6, branch=0.36):
    """Six-armed flake with a branch pair on each arm."""
    stroke = int(r * 0.20)
    for i in range(arms):
        a = math.pi * i / (arms / 2)
        ex, ey = cx + math.cos(a) * r, cy + math.sin(a) * r
        d.line((cx, cy, ex, ey), fill=WHITE, width=stroke)
        # Two branches angled off the arm, two thirds of the way out.
        bx, by = cx + math.cos(a) * r * 0.60, cy + math.sin(a) * r * 0.60
        for sign in (1, -1):
            ba = a + sign * math.pi / 4
            d.line(
                (bx, by, bx + math.cos(ba) * r * branch, by + math.sin(ba) * r * branch),
                fill=WHITE,
                width=stroke,
            )
    circle(d, cx, cy, r * 0.16)


def droplet(d, cx, cy, r):
    """Teardrop: a disc with a point drawn on top of it."""
    circle(d, cx, cy + r * 0.28, r * 0.72)
    d.polygon(
        [(cx, cy - r), (cx - r * 0.62, cy + r * 0.42), (cx + r * 0.62, cy + r * 0.42)], fill=WHITE
    )


def moon_phase(fraction, waxing):
    """A disc lit to `fraction`, terminator on the correct side.

    The terminator of a sphere lit from the side projects to an ellipse, so at
    height y the boundary sits at x = k*sqrt(1-y^2) with k = 1-2*fraction. That
    gives new (k=1, nothing lit) through full (k=-1, all lit) continuously,
    rather than faking each phase as a separate shape.
    """
    img, d = canvas()
    c = W / 2
    r = W * 0.40
    k = 1 - 2 * fraction
    px = img.load()
    for y in range(int(c - r), int(c + r) + 1):
        ny = (y - c) / r
        half = math.sqrt(max(0.0, 1 - ny * ny))
        xt = k * half
        for x in range(int(c - r), int(c + r) + 1):
            nx = (x - c) / r
            if nx * nx + ny * ny > 1:
                continue
            lit = nx >= xt if waxing else nx <= -xt
            if lit:
                px[x, y] = WHITE
    # New moon would be invisible on black, so outline it.
    if fraction <= 0.01:
        d.ellipse((c - r, c - r, c + r, c + r), outline=WHITE, width=int(W * 0.035))
    return img


def bolt(d, cx, cy, h):
    w = h * 0.46
    d.polygon(
        [
            (cx + w * 0.15, cy - h / 2),
            (cx - w * 0.55, cy + h * 0.12),
            (cx - w * 0.05, cy + h * 0.12),
            (cx - w * 0.25, cy + h / 2),
            (cx + w * 0.55, cy - h * 0.10),
            (cx + w * 0.02, cy - h * 0.10),
        ],
        fill=WHITE,
    )


def bars(d, cy, widths, gap, thickness):
    for i, frac in enumerate(widths):
        half = W * frac / 2
        y = cy + (i - (len(widths) - 1) / 2) * gap
        d.rounded_rectangle(
            (W / 2 - half, y - thickness / 2, W / 2 + half, y + thickness / 2),
            radius=thickness / 2,
            fill=WHITE,
        )


def save(img, name):
    img.resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f"{name}.png")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    c = W / 2

    img, d = canvas()
    sun(d, c, c, W * 0.20)
    save(img, "wx_sun")
    img, d = canvas()
    moon(img, c, c, W * 0.24)
    save(img, "wx_moon")
    img, d = canvas()
    cloud(d, c, c, W * 0.80)
    save(img, "wx_cloud")

    # Partly cloudy: small luminary tucked behind a cloud.
    img, d = canvas()
    sun(d, W * 0.36, W * 0.34, W * 0.13)
    cloud(d, c + W * 0.06, c + W * 0.12, W * 0.68)
    save(img, "wx_partly_day")

    img, d = canvas()
    moon(img, W * 0.38, W * 0.32, W * 0.15)
    d = ImageDraw.Draw(img)
    cloud(d, c + W * 0.06, c + W * 0.12, W * 0.68)
    save(img, "wx_partly_night")

    for name, n, ln in (("wx_rain", 2, W * 0.20), ("wx_heavy_rain", 3, W * 0.26)):
        img, d = canvas()
        cloud(d, c, c - W * 0.14, W * 0.74)
        strokes(d, c, c + W * 0.20, n, ln)
        save(img, name)

    # Snow and thunderstorm are bare symbols rather than cloud-plus-detail:
    # at 26px the detail under a cloud mushes together, while a flake and a
    # bolt read instantly on their own.
    img, d = canvas()
    snowflake(d, c, c, W * 0.40)
    save(img, "wx_snow")

    img, d = canvas()
    bolt(d, c, c, W * 0.95)
    save(img, "wx_storm")

    # Sleet is rain and snow together, so it pairs the two symbols. The old
    # version stacked a stroke and a flake under a cloud and was illegible.
    img, d = canvas()
    droplet(d, c - W * 0.22, c - W * 0.04, W * 0.27)
    snowflake(d, c + W * 0.22, c + W * 0.06, W * 0.26)
    save(img, "wx_sleet")

    img, d = canvas()
    bars(d, c, [0.62, 0.74, 0.56, 0.68], W * 0.15, W * 0.075)
    save(img, "wx_fog")

    # Wind: staggered bars, the top one curling back on itself.
    img, d = canvas()
    bars(d, c, [0.50, 0.70, 0.44], W * 0.19, W * 0.075)
    d.arc(
        (W * 0.60, c - W * 0.28, W * 0.86, c - W * 0.02),
        start=270,
        end=140,
        fill=WHITE,
        width=int(W * 0.075),
    )
    save(img, "wx_wind")

    img, d = canvas()
    bars(d, c, [0.34], 0, W * 0.085)
    save(img, "wx_unknown")

    # Moon phases, indexed by [MOON_PHASE_TYPE] 0-7. Waxing lights the right
    # limb, which is the northern-hemisphere view.
    phases = [
        (0.00, True),
        (0.25, True),
        (0.50, True),
        (0.75, True),
        (1.00, True),
        (0.75, False),
        (0.50, False),
        (0.25, False),
    ]
    for i, (frac, waxing) in enumerate(phases):
        save(moon_phase(frac, waxing), f"moon_{i}")

    print(
        f"wrote {len(list(OUT.glob('wx_*.png')))} weather "
        f"and {len(list(OUT.glob('moon_*.png')))} moon glyphs to {OUT}"
    )


if __name__ == "__main__":
    build()
