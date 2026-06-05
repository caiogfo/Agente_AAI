"""Generate a house-style 'XP' wordmark PNG for the letter header.

This is a generic, brand-styled placeholder (yellow square + 'XP' + 'investimentos'),
NOT the official XP logo. Drop the official asset at assets/xp_logo.png to override
it; render.py uses that file automatically if present.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from . import brand as B
from . import config

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _font(size: int, bold: bool = False):
    paths = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + _FONT_CANDIDATES
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate(path=None) -> str:
    path = str(path or (config.ASSETS_DIR / "xp_logo.png"))
    config.ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    W, H = 760, 200
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # yellow rounded square with black "XP"
    sq = 176
    d.rounded_rectangle([4, 12, 4 + sq, 12 + sq], radius=26, fill=B.XP_YELLOW)
    f_xp = _font(118, bold=True)
    tb = d.textbbox((0, 0), "XP", font=f_xp)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text((4 + (sq - tw) / 2 - tb[0], 12 + (sq - th) / 2 - tb[1]), "XP",
           font=f_xp, fill=B.XP_BLACK)

    # wordmark to the right of the square (for the dark header band)
    f_word = _font(60, bold=True)
    f_sub = _font(34, bold=False)
    d.text((212, 50), "XP", font=f_word, fill="white")
    d.text((280, 62), "investimentos", font=f_sub, fill=B.XP_YELLOW)

    img.save(path)
    return path


if __name__ == "__main__":
    print("logo ->", generate())
