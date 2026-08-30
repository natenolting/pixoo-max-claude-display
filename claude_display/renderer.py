"""Variant A state screen: full-field color, white icon, corner count digit.

Design locked by the state-screen prototype ticket; see
.wayfinder/tickets/006-state-screen-prototype.md.
"""

from PIL import Image, ImageDraw

COLORS = {
    "NEEDS_PERMISSION": (200, 0, 0),
    "WAITING": (210, 130, 0),
    "WORKING": (0, 70, 200),
    "IDLE": (12, 12, 24),
    "OFF": (0, 0, 0),
}

WHITE = (255, 255, 255)
IDLE_INK = (90, 90, 140)

DIGITS_3X5 = {
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
}


def _digit(d, ch, ox, oy, color):
    for row, bits in enumerate(DIGITS_3X5[ch]):
        for col, bit in enumerate(bits):
            if bit == "1":
                d.point([(ox + col, oy + row)], fill=color)


def _bang(d, color):
    d.rectangle([14, 6, 17, 18], fill=color)
    d.rectangle([14, 22, 17, 25], fill=color)


def _hourglass(d, color):
    d.line([10, 7, 21, 7], fill=color)
    d.line([10, 24, 21, 24], fill=color)
    d.line([10, 8, 15, 15], fill=color)
    d.line([21, 8, 16, 15], fill=color)
    d.line([10, 23, 15, 16], fill=color)
    d.line([21, 23, 16, 16], fill=color)
    d.polygon([(13, 21), (18, 21), (15, 18)], fill=color)


def _play(d, color):
    d.polygon([(11, 8), (11, 24), (23, 16)], fill=color)


def _zzz(d, color):
    for ox, oy, s in [(8, 8, 2), (16, 14, 2), (12, 21, 1)]:
        w = 3 * s
        d.line([ox, oy, ox + w, oy], fill=color)
        d.line([ox + w, oy, ox, oy + w], fill=color)
        d.line([ox, oy + w, ox + w, oy + w], fill=color)


ICONS = {
    "NEEDS_PERMISSION": (_bang, WHITE),
    "WAITING": (_hourglass, WHITE),
    "WORKING": (_play, WHITE),
    "IDLE": (_zzz, IDLE_INK),
}


def render(state: str, count: int) -> Image.Image:
    img = Image.new("RGB", (32, 32), COLORS[state])
    d = ImageDraw.Draw(img)
    if state == "OFF":
        d.point([(31, 31)], fill=(30, 30, 30))
        return img
    icon, ink = ICONS[state]
    icon(d, ink)
    if count > 1:
        d.rectangle([26, 25, 31, 31], fill=(0, 0, 0))
        _digit(d, str(min(count, 9)), 28, 26, WHITE)
    return img
