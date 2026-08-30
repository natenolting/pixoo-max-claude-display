# PROTOTYPE — throwaway. Answers: what should the 32x32 State Screen look like?
# Three variants x five states, pushed to the real Pixoo Max and composed into
# a contact sheet. Not production code.

import sys
import time
import glob
from math import ceil, log2

from PIL import Image, ImageDraw

STATES = ["PERM", "WAIT", "WORK", "IDLE", "OFF"]
DEMO_COUNT = 2  # count badge value used in all mocks

# state -> primary color
COLORS = {
    "PERM": (200, 0, 0),
    "WAIT": (210, 130, 0),
    "WORK": (0, 70, 200),
    "IDLE": (12, 12, 24),
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


def draw_digit(d, ch, ox, oy, color, scale=1):
    for row, bits in enumerate(DIGITS_3X5[ch]):
        for col, bit in enumerate(bits):
            if bit == "1":
                d.rectangle(
                    [ox + col * scale, oy + row * scale,
                     ox + col * scale + scale - 1, oy + row * scale + scale - 1],
                    fill=color,
                )


def icon_bang(d, color):
    d.rectangle([14, 6, 17, 18], fill=color)
    d.rectangle([14, 22, 17, 25], fill=color)


def icon_hourglass(d, color):
    d.line([10, 7, 21, 7], fill=color)
    d.line([10, 24, 21, 24], fill=color)
    d.line([10, 8, 15, 15], fill=color)
    d.line([21, 8, 16, 15], fill=color)
    d.line([10, 23, 15, 16], fill=color)
    d.line([21, 23, 16, 16], fill=color)
    d.polygon([(13, 21), (18, 21), (15, 18)], fill=color)


def icon_play(d, color):
    d.polygon([(11, 8), (11, 24), (23, 16)], fill=color)


def icon_zzz(d, color):
    for ox, oy, s in [(8, 8, 2), (16, 14, 2), (12, 21, 1)]:
        w = 3 * s
        d.line([ox, oy, ox + w, oy], fill=color)
        d.line([ox + w, oy, ox, oy + w], fill=color)
        d.line([ox, oy + w, ox + w, oy + w], fill=color)


# ---------------------------------------------------------------- variant A
def variant_a(state, count):
    """Full-field color + white icon + count digit bottom-right."""
    img = Image.new("RGB", (32, 32), COLORS[state])
    d = ImageDraw.Draw(img)
    icon_color = WHITE if state != "IDLE" else (90, 90, 140)
    if state == "PERM":
        icon_bang(d, icon_color)
    elif state == "WAIT":
        icon_hourglass(d, icon_color)
    elif state == "WORK":
        icon_play(d, icon_color)
    elif state == "IDLE":
        icon_zzz(d, icon_color)
    elif state == "OFF":
        d.point([31, 31], fill=(30, 30, 30))
        return img
    if count > 1:
        d.rectangle([26, 25, 31, 31], fill=(0, 0, 0))
        draw_digit(d, str(count), 28, 26, WHITE)
    return img


# ---------------------------------------------------------------- variant B
def variant_b(state, count):
    """Black field, big spark glyph colored by state, count as dot row."""
    img = Image.new("RGB", (32, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)
    if state == "OFF":
        return img
    c = COLORS[state] if state != "IDLE" else (60, 60, 90)
    cx, cy, r = 15, 14, 10
    d.line([cx - r, cy, cx + r, cy], fill=c, width=2)
    d.line([cx, cy - r, cx, cy + r], fill=c, width=2)
    k = int(r * 0.7)
    d.line([cx - k, cy - k, cx + k, cy + k], fill=c, width=2)
    d.line([cx - k, cy + k, cx + k, cy - k], fill=c, width=2)
    d.ellipse([cx - 2, cy - 2, cx + 3, cy + 3], fill=c)
    for i in range(min(count, 6)):
        x = 4 + i * 5
        d.rectangle([x, 29, x + 2, 31], fill=c)
    return img


# ---------------------------------------------------------------- variant C
def variant_c(state, count):
    """Split: state color block w/ icon on top, big count digits below."""
    img = Image.new("RGB", (32, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)
    if state == "OFF":
        return img
    d.rectangle([0, 0, 31, 22], fill=COLORS[state])
    icon_color = (0, 0, 0) if state in ("WAIT",) else WHITE
    if state == "IDLE":
        icon_color = (90, 90, 140)
    # smaller icons squeezed into 23 rows
    if state == "PERM":
        d.rectangle([14, 3, 17, 13], fill=icon_color)
        d.rectangle([14, 17, 17, 20], fill=icon_color)
    elif state == "WAIT":
        d.ellipse([10, 4, 21, 15], outline=icon_color)
        d.line([15, 7, 15, 10], fill=icon_color)
        d.line([15, 10, 19, 12], fill=icon_color)
    elif state == "WORK":
        d.polygon([(12, 4), (12, 18), (22, 11)], fill=icon_color)
    elif state == "IDLE":
        icon_zzz(d, icon_color)
    draw_digit(d, str(count), 12, 25, WHITE, scale=1)
    d.text((17, 24), "", fill=WHITE)
    return img


VARIANTS = {"A": variant_a, "B": variant_b, "C": variant_c}


# ------------------------------------------------------------ device pusher
def spp_frame(cmd, args):
    payload_size = len(args) + 3
    frame = [1, payload_size & 0xFF, (payload_size >> 8) & 0xFF, cmd] + args
    cs = sum(frame[1:]) & 0xFFFF
    return bytes(frame + [cs & 0xFF, (cs >> 8) & 0xFF, 2])


def encode_image_32(img):
    img = img.convert("P", palette=Image.ADAPTIVE, colors=256).convert("RGB")
    pixels, palette, lookup = [], [], {}
    for y in range(32):
        for x in range(32):
            rgb = img.getpixel((x, y))[:3]
            if rgb not in lookup:
                lookup[rgb] = len(palette)
                palette.append(rgb)
            pixels.append(lookup[rgb])
    bitwidth = max(1, ceil(log2(len(palette))))
    bits = ""
    for i in pixels:
        bits = bin(i)[2:].rjust(bitwidth, "0") + bits
    out = []
    while len(bits) >= 8:
        out.append(int(bits[-8:], 2))
        bits = bits[:-8]
    if bits:
        out.append(int(bits.rjust(bitwidth, "0"), 2))
    return len(palette), [c for rgb in palette for c in rgb], out


def push(ser, img):
    n, pal, pix = encode_image_32(img)
    size = 8 + len(pix) + len(pal)
    header = [0xAA, size & 0xFF, (size >> 8) & 0xFF, 0, 0, 3, n & 0xFF, (n >> 8) & 0xFF]
    ser.write(spp_frame(0x44, [0x0, 0x0A, 0x0A, 0x04] + header + pal + pix))
    ser.flush()


# ------------------------------------------------------------ contact sheet
def contact_sheet(path, scale=7, pad=10):
    cell = 32 * scale
    w = pad + len(STATES) * (cell + pad)
    h = 24 + pad + len(VARIANTS) * (cell + pad + 16)
    sheet = Image.new("RGB", (w, h), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for col, s in enumerate(STATES):
        d.text((pad + col * (cell + pad) + cell // 2 - 12, 6), s, fill=WHITE)
    for row, (name, fn) in enumerate(VARIANTS.items()):
        y = 24 + pad + row * (cell + pad + 16)
        d.text((pad, y + cell // 2), name, fill=WHITE)
        for col, s in enumerate(STATES):
            img = fn(s, DEMO_COUNT).resize((cell, cell), Image.NEAREST)
            sheet.paste(img, (pad + col * (cell + pad), y))
    sheet.save(path)
    print(f"contact sheet -> {path}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    if mode == "sheet":
        contact_sheet("prototypes/state_screen/contact_sheet.png")
        return
    # device mode: push sequence, e.g. `proto.py device A` or `device all`
    import serial

    port = next(p for p in glob.glob("/dev/cu.*") if "pixoo" in p.lower())
    which = sys.argv[2].upper() if len(sys.argv) > 2 else "ALL"
    names = list(VARIANTS) if which == "ALL" else [which]
    with serial.Serial(port, timeout=5, write_timeout=15) as ser:
        time.sleep(1.0)
        for name in names:
            for s in STATES:
                print(f"variant {name} state {s}")
                push(ser, VARIANTS[name](s, DEMO_COUNT))
                time.sleep(2.5)


if __name__ == "__main__":
    main()
