"""The display faces.

State Screen: a coloured field with a white icon and a corner count badge
(.wayfinder/tickets/006-state-screen-prototype.md) — except IDLE, which is
a whole sleeping-Claude scene, and OFF, which rests the mascot on black.
Usage Screen: big 7-segment five-hour percentage with two bars
(.wayfinder/tickets/011-usage-screen-prototype.md).
Token Screen: today's input + output count, compacted.
"""

from PIL import Image, ImageDraw

COLORS = {
    "NEEDS_PERMISSION": (200, 0, 0),
    "WAITING": (210, 130, 0),
    "WORKING": (0, 0, 0),
    "OFF": (0, 0, 0),
}

WHITE = (255, 255, 255)

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


def _bang(d, color, phase=0):
    ink = _dim(color) if phase % 2 else color
    d.rectangle([14, 6, 17, 18], fill=ink)
    d.rectangle([14, 22, 17, 25], fill=ink)


def _caret(d, color, phase=0):
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
    if not phase % 2:
        d.rectangle([18, 9, 23, 23], fill=color)


# The Claude burst, breathing: arms reach out and draw back. Rotation was
# tried first, but an eight-fold symmetric shape rotating at 32 pixels lands
# on nearly the same pixels each step and reads as jitter. A changing
# silhouette survives the low frame rate the Bluetooth link allows.
BREATHE_RADII = (9, 10, 11, 12, 13, 12, 11, 10)


def _burst(d, color, r_out, arms=8, r_in=2, thick=1.6, taper=1.1):
    import math

    for i in range(arms):
        a = math.radians(i * 360 / arms)
        for t in range(r_in, r_out + 1):
            x, y = 15.5 + math.cos(a) * t, 15.5 - math.sin(a) * t
            w = thick - taper * ((t - r_in) / max(1, r_out - r_in))
            if w > 0:
                d.ellipse([x - w, y - w, x + w, y + w], fill=color)


def _working(d, color, phase=0):
    _burst(d, color, BREATHE_RADII[phase % len(BREATHE_RADII)])


# IDLE has no icon entry: it renders a whole scene, not a glyph on a field
ICONS = {
    "NEEDS_PERMISSION": (_bang, WHITE),
    "WAITING": (_caret, WHITE),
    "WORKING": (_working, (217, 119, 87)),
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
    _mascot(d, *MASCOT_CORNER, scale=1, level=0.8)
    d.rectangle([10, 24, 30, 27], outline=BAR_TRACK)
    fill = int(round(19 * min(five_hour, 100) / 100))
    if fill:
        d.rectangle([11, 25, 10 + fill, 26], fill=c5)
    d.rectangle([10, 29, 30, 30], fill=BAR_TRACK_DIM)
    fill7 = int(round(21 * min(seven_day, 100) / 100))
    if fill7:
        d.rectangle([10, 29, 9 + fill7, 30], fill=_severity(seven_day))
    return img


# One corner shared by every face: the faces swap in place, so a pixel of
# drift between them reads as the mascot jumping.
MASCOT_CORNER = (1, 25)

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


# The sleeping-Claude idle scene, traced from assets/claude-guy-sleeping.png.
# Three colours: '.' backdrop, '#' the sleeping figure, 'o' the drifting Zs.
SLEEP_BACK = (91, 96, 155)
SLEEP_FIGURE = (51, 54, 87)
SLEEP_ZS = (153, 153, 204)
SLEEP_COLOURS = {".": SLEEP_BACK, "#": SLEEP_FIGURE, "o": SLEEP_ZS}
SLEEPING = [
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "............ooo..ooo............",
    "..............o....o............",
    ".......ooo...o....o...ooo.......",
    ".........o..o....o......o.......",
    "........o...ooo..ooo...o........",
    "..ooo..o..............o....ooo..",
    "....o..ooo............ooo....o..",
    "...o........................o...",
    "..o........................o....",
    "..ooo......................ooo..",
    "........################........",
    "........################........",
    "........##.##.####.##.##........",
    "........##.##.####.##.##........",
    "........##.##.####.##.##........",
    ".....######..######..######.....",
    ".....######################.....",
    ".....######################.....",
    "........################........",
    "........################........",
    ".........##.##....##.##.........",
    ".........##.##....##.##.........",
    ".........##.##....##.##.........",
    "................................",
    "................................",
    "................................",
    "................................",
]


def _sleeping_face() -> Image.Image:
    img = Image.new("RGB", (32, 32), SLEEP_BACK)
    px = img.load()
    for y, line in enumerate(SLEEPING):
        for x, ch in enumerate(line):
            px[x, y] = SLEEP_COLOURS[ch]
    return img


def render_blank() -> Image.Image:
    """All black — shown on shutdown so a dark panel means nothing is driving it."""
    return Image.new("RGB", (32, 32), (0, 0, 0))


def _count_badge(d, count: int) -> None:
    """Bottom-right digit, shown only when more than one session shares a state."""
    if count > 1:
        d.rectangle([26, 25, 31, 31], fill=(0, 0, 0))
        _digit(d, str(min(count, 9)), 28, 26, WHITE)


def render(state: str, count: int, phase: int = 0) -> Image.Image:
    """State Screen. `phase` advances over time and each icon decides what it
    means: the permission mark dims on alternate phases, the waiting cursor
    blinks, and the working burst breathes through its frames."""
    if state == "IDLE":
        # a whole scene rather than a glyph on a field
        img = _sleeping_face()
        d = ImageDraw.Draw(img)
        _count_badge(d, count)
        return img
    img = Image.new("RGB", (32, 32), COLORS[state])
    d = ImageDraw.Draw(img)
    if state == "OFF":
        # a resting mascot, not near-blackness: this face used to be almost
        # indistinguishable from the blank panel shown when the daemon has
        # stopped, which undercut "dark means nothing is driving it"
        _mascot(d, 8, 10, scale=2, level=0.75)
        return img
    icon, ink = ICONS[state]
    icon(d, ink, phase)
    _count_badge(d, count)
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
    _mascot(d, *MASCOT_CORNER, scale=1, level=0.8)
    x = 12
    for ch in "TOK":
        x += _letter(d, ch, x, 25, LABEL_INK) + 2
    return img
