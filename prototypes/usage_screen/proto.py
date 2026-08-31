# PROTOTYPE — throwaway. Answers: what should the Usage Screen look like?
# Three variants x three utilization levels. Contact sheet + device push.
# Not production code.

import sys
import time
import glob
from math import ceil, log2

from PIL import Image, ImageDraw

# (five_hour_pct, seven_day_pct) samples to render
SAMPLES = [(44, 9), (78, 40), (96, 88)]

BG = (0, 0, 0)
DIM = (40, 40, 60)


def severity(pct):
    """Color by how close to the wall: calm blue -> amber -> red."""
    if pct >= 90:
        return (230, 20, 20)
    if pct >= 70:
        return (220, 140, 0)
    return (0, 130, 230)


# ---------------------------------------------------------- 7-segment digits
# segment order: a(top) b(top-right) c(bottom-right) d(bottom) e(bottom-left)
#                f(top-left) g(middle)
SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def draw_digit(d, ch, x, y, w, h, color, t=2):
    """7-segment digit in a w x h box at (x, y), stroke thickness t."""
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


def draw_number(d, text, cx, y, h, color, t=2):
    """Centered number; digits narrow automatically when 3 wide (100%)."""
    w = 11 if len(text) <= 2 else 9
    gap = 3 if len(text) <= 2 else 1
    total = len(text) * w + (len(text) - 1) * gap
    x = cx - total // 2
    for ch in text:
        draw_digit(d, ch, x, y, w, h, color, t)
        x += w + gap


# tiny 3x5 digits for secondary readings
SMALL = {
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


def draw_small(d, text, x, y, color):
    for ch in text:
        for row, bits in enumerate(SMALL[ch]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    d.point([(x + col, y + row)], fill=color)
        x += 4


# ------------------------------------------------------------------ variants
def variant_a(five, seven):
    """Big 7-seg number up top, 5h bar under it, thin 7d bar at the bottom."""
    img = Image.new("RGB", (32, 32), BG)
    d = ImageDraw.Draw(img)
    c = severity(five)
    draw_number(d, str(five), 16, 2, 19, c)
    # 5-hour bar
    d.rectangle([1, 24, 30, 27], outline=DIM)
    fill = int(round(28 * min(five, 100) / 100))
    if fill:
        d.rectangle([2, 25, 1 + fill, 26], fill=c)
    # 7-day bar, thinner and dimmer
    d.rectangle([1, 29, 30, 30], outline=None, fill=(20, 20, 30))
    fill7 = int(round(30 * min(seven, 100) / 100))
    if fill7:
        d.rectangle([1, 29, fill7, 30], fill=severity(seven))
    return img


def variant_b(five, seven):
    """Two vertical columns: 5h on the left (tall), 7d on the right (narrow)."""
    img = Image.new("RGB", (32, 32), BG)
    d = ImageDraw.Draw(img)
    c5, c7 = severity(five), severity(seven)
    # 5h column
    d.rectangle([2, 2, 12, 29], outline=DIM)
    h5 = int(round(26 * min(five, 100) / 100))
    if h5:
        d.rectangle([3, 29 - h5, 11, 28], fill=c5)
    # 7d column
    d.rectangle([15, 2, 21, 29], outline=DIM)
    h7 = int(round(26 * min(seven, 100) / 100))
    if h7:
        d.rectangle([16, 29 - h7, 20, 28], fill=c7)
    # numbers stacked at the right
    draw_small(d, str(five), 23, 4, c5)
    draw_small(d, str(seven), 23, 22, c7)
    return img


def variant_c(five, seven):
    """Perimeter ring fills clockwise with the 5h figure; number in the middle."""
    img = Image.new("RGB", (32, 32), BG)
    d = ImageDraw.Draw(img)
    c = severity(five)
    # walk the perimeter clockwise from top-left
    ring = []
    for x in range(0, 32):
        ring.append((x, 0))
    for y in range(1, 32):
        ring.append((31, y))
    for x in range(30, -1, -1):
        ring.append((x, 31))
    for y in range(30, 0, -1):
        ring.append((0, y))
    lit = int(round(len(ring) * min(five, 100) / 100))
    for i, p in enumerate(ring):
        d.point([p], fill=c if i < lit else (18, 18, 26))
    draw_number(d, str(five), 16, 7, 14, c)
    # 7d as a short underline beneath the number
    w7 = int(round(18 * min(seven, 100) / 100))
    if w7:
        d.rectangle([7, 24, 6 + w7, 25], fill=severity(seven))
    return img


VARIANTS = {"A": variant_a, "B": variant_b, "C": variant_c}


# ------------------------------------------------------------ device pushing
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


def build_frame(img):
    n, pal, pix = encode_image_32(img)
    size = 8 + len(pix) + len(pal)
    header = [0xAA, size & 0xFF, (size >> 8) & 0xFF, 0, 0, 3, n & 0xFF, (n >> 8) & 0xFF]
    return spp_frame(0x44, [0x0, 0x0A, 0x0A, 0x04] + header + pal + pix)


def push_to_device(which):
    """Direct IOBluetooth push, same recipe as ADR 0001. Terminal only."""
    import objc
    import IOBluetooth
    from Foundation import NSObject, NSRunLoop, NSDate

    class D(NSObject):
        def init(self):
            self = objc.super(D, self).init()
            self.open_status = None
            return self

        def rfcommChannelOpenComplete_status_(self, ch, status):
            self.open_status = status

        def rfcommChannelData_data_length_(self, ch, data, length):
            pass

    def pump(s):
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(s))

    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", ".."))
    from claude_display.config import PIXOO_ADDRESS as _ADDR
    if not _ADDR:
        _sys.exit("set PIXOO_ADDRESS in .env first")
    dev = IOBluetooth.IOBluetoothDevice.deviceWithAddressString_(_ADDR)
    if not dev.isConnected():
        err = dev.openConnection()
        if err != 0:
            sys.exit(f"baseband connect failed: {err}")
    delegate = D.alloc().init()
    result, channel = dev.openRFCOMMChannelAsync_withChannelID_delegate_(None, 1, delegate)
    if result != 0:
        sys.exit(f"RFCOMM open call failed: {result}")
    for _ in range(20):
        pump(0.5)
        if delegate.open_status is not None:
            break
    if delegate.open_status != 0 or channel is None:
        sys.exit(f"RFCOMM open failed: {delegate.open_status}")
    print(f"channel open, MTU={channel.getMTU()}")
    pump(1.0)

    names = list(VARIANTS) if which == "ALL" else [which]
    for name in names:
        for five, seven in SAMPLES:
            print(f"variant {name}: 5h={five}% 7d={seven}%")
            data = build_frame(VARIANTS[name](five, seven))
            mtu = channel.getMTU() or 666
            for i in range(0, len(data), mtu):
                chunk = data[i:i + mtu]
                channel.writeSync_length_(chunk, len(chunk))
            pump(3.0)
    channel.closeChannel()
    print("done")


def contact_sheet(path, scale=7, pad=10):
    cell = 32 * scale
    w = pad + len(SAMPLES) * (cell + pad)
    h = 24 + pad + len(VARIANTS) * (cell + pad + 16)
    sheet = Image.new("RGB", (w, h), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for col, (five, seven) in enumerate(SAMPLES):
        d.text((pad + col * (cell + pad) + cell // 2 - 30, 6),
               f"5h {five}%  7d {seven}%", fill=(255, 255, 255))
    for row, (name, fn) in enumerate(VARIANTS.items()):
        y = 24 + pad + row * (cell + pad + 16)
        d.text((pad, y + cell // 2), name, fill=(255, 255, 255))
        for col, (five, seven) in enumerate(SAMPLES):
            img = fn(five, seven).resize((cell, cell), Image.NEAREST)
            sheet.paste(img, (pad + col * (cell + pad), y))
    sheet.save(path)
    print(f"contact sheet -> {path}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    if mode == "sheet":
        contact_sheet("prototypes/usage_screen/contact_sheet.png")
    else:
        push_to_device(sys.argv[2].upper() if len(sys.argv) > 2 else "ALL")
