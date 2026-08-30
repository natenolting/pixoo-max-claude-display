"""Hardware smoke test: push one 32x32 frame to a Divoom Pixoo Max over
macOS's Bluetooth SPP serial bridge (/dev/cu.*).

Protocol ported from virtualabs/pixoo-client (PixooMax class), transport
swapped from Linux AF_BLUETOOTH sockets to pyserial so it runs on macOS.

Usage:
    python pixoo_smoke.py [port]

Without an argument the script picks the first /dev/cu.* port whose name
contains "pixoo" (case-insensitive).
"""

import sys
import glob
import time
from math import ceil, log2

import serial
from PIL import Image, ImageDraw

CMD_SET_SYSTEM_BRIGHTNESS = 0x74
CMD_DRAW_PIC = 0x44

# The device drops bytes written immediately after connect.
POST_CONNECT_SETTLE_S = 1.0


def spp_frame(cmd: int, args: list[int]) -> bytes:
    """Divoom SPP framing: 0x01, LE16 size, cmd, args, LE16 checksum, 0x02.

    Checksum sums every byte after the 0x01 start marker, including the
    size field and command.
    """
    payload_size = len(args) + 3
    frame = [1, payload_size & 0xFF, (payload_size >> 8) & 0xFF, cmd] + args
    cs = sum(frame[1:]) & 0xFFFF
    return bytes(frame + [cs & 0xFF, (cs >> 8) & 0xFF, 2])


def encode_image_32(img: Image.Image) -> tuple[int, list[int], list[int]]:
    """Encode a 32x32 RGB image as (color_count, palette, packed_pixels).

    Pixels are palette indices packed little-endian at ceil(log2(n_colors))
    bits per pixel, matching the reverse-engineered Pixoo Max format.
    """
    img = img.convert(mode="P", palette=Image.ADAPTIVE, colors=256).convert("RGB")
    if img.size != (32, 32):
        img = img.resize((32, 32))

    pixels: list[int] = []
    palette: list[tuple[int, int, int]] = []
    lookup: dict[tuple[int, int, int], int] = {}
    for y in range(32):
        for x in range(32):
            rgb = img.getpixel((x, y))[:3]
            idx = lookup.get(rgb)
            if idx is None:
                idx = len(palette)
                palette.append(rgb)
                lookup[rgb] = idx
            pixels.append(idx)

    bitwidth = max(1, ceil(log2(len(palette))))
    bitstream = ""
    for i in pixels:
        bitstream = bin(i)[2:].rjust(bitwidth, "0") + bitstream

    encoded: list[int] = []
    while len(bitstream) >= 8:
        encoded.append(int(bitstream[-8:], 2))
        bitstream = bitstream[:-8]
    if bitstream:
        encoded.append(int(bitstream.rjust(bitwidth, "0"), 2))

    flat_palette = [c for rgb in palette for c in rgb]
    return len(palette), flat_palette, encoded


def draw_pic_frame(img: Image.Image) -> bytes:
    """Build the full 0x44 static-image command for a 32x32 image.

    Pixoo Max uses an 8-byte inner frame header with a 16-bit color count
    (the 16x16 models use 7 bytes with an 8-bit count).
    """
    nb_colors, palette, pixel_data = encode_image_32(img)
    frame_size = 8 + len(pixel_data) + len(palette)
    header = [
        0xAA,
        frame_size & 0xFF,
        (frame_size >> 8) & 0xFF,
        0, 0, 3,
        nb_colors & 0xFF,
        (nb_colors >> 8) & 0xFF,
    ]
    prefix = [0x0, 0x0A, 0x0A, 0x04]
    return spp_frame(CMD_DRAW_PIC, prefix + header + palette + pixel_data)


def test_image() -> Image.Image:
    """Green border, magenta diagonal, white 'OK' block — obvious at a glance."""
    img = Image.new("RGB", (32, 32), (0, 0, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 31], outline=(0, 255, 0))
    d.line([2, 29, 29, 2], fill=(255, 0, 255))
    # O
    d.rectangle([7, 12, 13, 20], outline=(255, 255, 255))
    # K
    d.line([18, 12, 18, 20], fill=(255, 255, 255))
    d.line([18, 16, 23, 12], fill=(255, 255, 255))
    d.line([18, 16, 23, 20], fill=(255, 255, 255))
    return img


def find_port() -> str:
    candidates = [p for p in glob.glob("/dev/cu.*") if "pixoo" in p.lower()]
    if not candidates:
        sys.exit(
            "No /dev/cu.*pixoo* port found. Pair the Pixoo-max in "
            "System Settings > Bluetooth first, then re-run. "
            f"Ports present: {glob.glob('/dev/cu.*')}"
        )
    return candidates[0]


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    print(f"Opening {port} ...")
    t0 = time.monotonic()
    with serial.Serial(port, timeout=5, write_timeout=15) as ser:
        print(f"Opened in {time.monotonic() - t0:.2f}s; settling...")
        time.sleep(POST_CONNECT_SETTLE_S)

        frame = draw_pic_frame(test_image())
        print(f"Pushing test frame ({len(frame)} bytes)...")
        t1 = time.monotonic()
        ser.write(frame)
        ser.flush()
        print(f"Frame written in {time.monotonic() - t1:.2f}s.")

        time.sleep(0.3)
        print("Setting brightness to 80...")
        ser.write(spp_frame(CMD_SET_SYSTEM_BRIGHTNESS, [80]))
        ser.flush()

        time.sleep(0.5)
        waiting = ser.in_waiting
        if waiting:
            print(f"Device replied {waiting} bytes: {ser.read(waiting).hex()}")
        else:
            print("No reply bytes (not necessarily an error).")

    print("Done. Check the display: green border, magenta diagonal, white OK.")


if __name__ == "__main__":
    main()
