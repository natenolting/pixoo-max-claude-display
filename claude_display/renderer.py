"""The two display faces, both Variant A designs.

State Screen: full-field color, white icon, corner count digit
(.wayfinder/tickets/006-state-screen-prototype.md).
Usage Screen: big 7-segment five-hour percentage, five-hour bar, thin
seven-day bar (.wayfinder/tickets/011-usage-screen-prototype.md).
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


PULSE_LEVEL = 0.45


def _dim(color, factor=PULSE_LEVEL):
    return tuple(int(round(c * factor)) for c in color)


def _bang(d, color, pulse=False):
    ink = _dim(color) if pulse else color
    d.rectangle([14, 6, 17, 18], fill=ink)
    d.rectangle([14, 22, 17, 25], fill=ink)


def _caret(d, color, pulse=False):
    """A terminal prompt: solid chevron, cursor block blinking beside it.

    An hourglass was here first and meant the opposite of what everyone
    reads it as — every OS uses it for "the machine is busy", while this
    state means the machine is done and you are the holdup. The cursor
    block blinks off on alternate frames the way a real prompt does, which
    also supplies the liveness motion the pulse used to provide.
    """
    for t in range(3):
        d.line([9, 9 + t, 15, 15 + t], fill=color)
        d.line([9, 23 - t, 15, 17 - t], fill=color)
    if not pulse:
        d.rectangle([18, 9, 23, 23], fill=color)


def _play(d, color, pulse=False):
    d.polygon([(11, 8), (11, 24), (23, 16)], fill=color)


def _zzz(d, color, pulse=False):
    for ox, oy, s in [(8, 8, 2), (16, 14, 2), (12, 21, 1)]:
        w = 3 * s
        d.line([ox, oy, ox + w, oy], fill=color)
        d.line([ox + w, oy, ox, oy + w], fill=color)
        d.line([ox, oy + w, ox + w, oy + w], fill=color)


ICONS = {
    "NEEDS_PERMISSION": (_bang, WHITE),
    "WAITING": (_caret, WHITE),
    "WORKING": (_play, WHITE),
    "IDLE": (_zzz, IDLE_INK),
}


SEVERITY_CALM = (0, 130, 230)
SEVERITY_WARN = (220, 140, 0)
SEVERITY_ALARM = (230, 20, 20)
BAR_TRACK = (40, 40, 60)
BAR_TRACK_DIM = (20, 20, 30)

# 7-segment strokes per digit: a top, b top-right, c bottom-right,
# d bottom, e bottom-left, f top-left, g middle
SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
    "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}


# 5x5 glyphs for the unit suffix and the TOK label
LETTERS = {
    "%": ["11001", "11010", "00100", "01011", "10011"],
    "K": ["101", "110", "100", "110", "101"],
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "T": ["111", "010", "010", "010", "010"],
    "O": ["111", "101", "101", "101", "111"],
}


def _letter(d, ch, x, y, color):
    rows = LETTERS[ch]
    for row, bits in enumerate(rows):
        for col, bit in enumerate(bits):
            if bit == "1":
                d.point([(x + col, y + row)], fill=color)
    return len(rows[0])


def _severity(pct: int):
    if pct >= 90:
        return SEVERITY_ALARM
    if pct >= 70:
        return SEVERITY_WARN
    return SEVERITY_CALM


def _seven_segment(d, ch, x, y, w, h, color, t=2):
    segs = SEGMENTS[ch]
    mid = y + h // 2
    if "a" in segs:
        d.rectangle([x + 1, y, x + w - 2, y + t - 1], fill=color)
    if "g" in segs:
        d.rectangle([x + 1, mid - t // 2, x + w - 2, mid - t // 2 + t - 1], fill=color)
    if "d" in segs:
        d.rectangle([x + 1, y + h - t, x + w - 2, y + h - 1], fill=color)
    if "f" in segs:
        d.rectangle([x, y + 1, x + t - 1, mid - 1], fill=color)
    if "b" in segs:
        d.rectangle([x + w - t, y + 1, x + w - 1, mid - 1], fill=color)
    if "e" in segs:
        d.rectangle([x, mid + 1, x + t - 1, y + h - 2], fill=color)
    if "c" in segs:
        d.rectangle([x + w - t, mid + 1, x + w - 1, y + h - 2], fill=color)


def _big_number(d, text, cx, y, h, color, w=None, gap=None):
    # three digits (100%) only fit if each one narrows
    if w is None:
        w, gap = (11, 3) if len(text) <= 2 else (9, 1)
    x = cx - (len(text) * w + (len(text) - 1) * gap) // 2
    for ch in text:
        _seven_segment(d, ch, x, y, w, h, color)
        x += w + gap


def render_usage(five_hour: int, seven_day: int) -> Image.Image:
    """Usage Screen: five-hour percentage large, both windows as bars."""
    img = Image.new("RGB", (32, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)
    c5 = _severity(five_hour)
    # the bare number read as an unlabelled quantity; the % names the unit,
    # and the digits narrow to make room for it (as the token face does)
    text = str(min(five_hour, 100))
    w, gap = (11, 3) if len(text) <= 2 else (8, 1)
    _big_number(d, text, 13, 2, 19, c5, w, gap)
    _letter(d, "%", 26, 14, c5)
    # the mascot takes the bottom-left corner and both bars start after it;
    # a shorter bar costs less legibility than a smaller numeral would
    _mascot(d, 1, 24, scale=1, level=0.8)
    d.rectangle([10, 24, 30, 27], outline=BAR_TRACK)
    fill = int(round(19 * min(five_hour, 100) / 100))
    if fill:
        d.rectangle([11, 25, 10 + fill, 26], fill=c5)
    d.rectangle([10, 29, 30, 30], fill=BAR_TRACK_DIM)
    fill7 = int(round(21 * min(seven_day, 100) / 100))
    if fill7:
        d.rectangle([10, 29, 9 + fill7, 30], fill=_severity(seven_day))
    return img


# The Claude mascot, traced from assets/claude-guy.png and baked in as a
# literal: the daemon must never fail to draw a face because a file moved.
# Near-identical source shades are collapsed to two, since the wire format is
# palette-indexed and every extra colour costs frame bytes.
MASCOT_BODY = (218, 119, 87)
MASCOT_EYE = (248, 248, 248)
MASCOT = [
    ".BBBBBB.",
    ".BEBBEB.",
    "BBBBBBBB",
    "BBBBBBBB",
    ".BBBBBB.",
    ".B....B.",
]


def _mascot(d, x, y, scale=1, level=1.0):
    """Draw the mascot with its top-left at (x, y)."""
    body = tuple(int(round(c * level)) for c in MASCOT_BODY)
    eye = tuple(int(round(c * level)) for c in MASCOT_EYE)
    for row, line in enumerate(MASCOT):
        for col, ch in enumerate(line):
            if ch == ".":
                continue
            px, py = x + col * scale, y + row * scale
            d.rectangle([px, py, px + scale - 1, py + scale - 1],
                        fill=body if ch == "B" else eye)


def render_blank() -> Image.Image:
    """All black — shown on shutdown so a dark panel means nothing is driving it."""
    return Image.new("RGB", (32, 32), (0, 0, 0))


def render(state: str, count: int, pulse: bool = False) -> Image.Image:
    """State Screen. `pulse` dims the icon for the liveness blink, which runs
    only while a session demands attention (see the staleness ticket)."""
    img = Image.new("RGB", (32, 32), COLORS[state])
    d = ImageDraw.Draw(img)
    if state == "OFF":
        # a resting mascot, not near-blackness: this face used to be almost
        # indistinguishable from the blank panel shown when the daemon has
        # stopped, which undercut "dark means nothing is driving it"
        _mascot(d, 8, 10, scale=2, level=0.75)
        return img
    icon, ink = ICONS[state]
    icon(d, ink, pulse)
    if count > 1:
        d.rectangle([26, 25, 31, 31], fill=(0, 0, 0))
        _digit(d, str(min(count, 9)), 28, 26, WHITE)
    return img


TOKEN_INK = (150, 90, 220)
LABEL_INK = (90, 60, 130)

def _number_with_dot(d, text, cx, y, h, color, w, gap):
    """Digits with an optional decimal point, centred on cx."""
    digits = [c for c in text if c != "."]
    dot_w = 3 if "." in text else 0
    total = len(digits) * w + (len(digits) - 1) * gap + dot_w
    x = cx - total // 2
    for ch in text:
        if ch == ".":
            d.rectangle([x, y + h - 2, x + 1, y + h - 1], fill=color)
            x += dot_w
            continue
        _seven_segment(d, ch, x, y, w, h, color)
        x += w + gap


def render_tokens(count: int | None) -> Image.Image:
    """Token Screen: today's input + output count, compacted (293K, 1.2M).

    The unit sits inline with the number — a separate unit letter beside the
    "TOK" label read as one nonsense word ("KTOK").
    """
    from .tokens import compact

    img = Image.new("RGB", (32, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)
    if count is None:
        # no reading yet — the label alone, never a false zero
        x = 8
        for ch in "TOK":
            x += _letter(d, ch, x, 13, LABEL_INK) + 2
        return img

    text, unit = compact(count)
    digits = [c for c in text if c != "."]
    # narrow the digits when a unit letter has to share the row
    if unit:
        w, gap = (11, 3) if len(digits) <= 2 else (8, 1)
        _number_with_dot(d, text, 13, 3, 17, TOKEN_INK, w, gap)
        _letter(d, unit, 26, 14, TOKEN_INK)
    else:
        w, gap = (11, 3) if len(digits) <= 2 else (9, 1)
        _number_with_dot(d, text, 16, 3, 17, TOKEN_INK, w, gap)

    # mascot in the corner, then "TOK" in the strip beside it
    _mascot(d, 1, 25, scale=1, level=0.8)
    x = 12
    for ch in "TOK":
        x += _letter(d, ch, x, 25, LABEL_INK) + 2
    return img
