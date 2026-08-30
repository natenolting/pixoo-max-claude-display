"""Pixoo Max transport: direct IOBluetooth RFCOMM, per ADR 0001.

The device must stay UNPAIRED; async channel open (sync fails where async
works); MTU-chunked writes; keep-open connection with 5→60 s backoff
reconnect on failure. Requires the Bluetooth TCC grant on the host process.
"""

import time
from math import ceil, log2

CMD_SET_BRIGHTNESS = 0x74
CMD_DRAW_PIC = 0x44
RFCOMM_CHANNEL = 1
SETTLE_S = 1.0  # device drops bytes written immediately after connect
BACKOFF_MIN_S = 5
BACKOFF_MAX_S = 60


def spp_frame(cmd: int, args: list[int]) -> bytes:
    payload_size = len(args) + 3
    frame = [1, payload_size & 0xFF, (payload_size >> 8) & 0xFF, cmd] + args
    cs = sum(frame[1:]) & 0xFFFF
    return bytes(frame + [cs & 0xFF, (cs >> 8) & 0xFF, 2])


def encode_image_32(img) -> tuple[int, list[int], list[int]]:
    """Palette-indexed encoding: indices packed little-endian at
    ceil(log2(n_colors)) bits per pixel (reverse-engineered format)."""
    from PIL import Image

    img = img.convert("P", palette=Image.ADAPTIVE, colors=256).convert("RGB")
    if img.size != (32, 32):
        img = img.resize((32, 32))
    pixels, palette, lookup = [], [], {}
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


def draw_pic_frame(img) -> bytes:
    # Pixoo Max inner header is 8 bytes with a 16-bit color count
    # (the 16x16 models use 7 bytes / 8-bit count)
    n, pal, pix = encode_image_32(img)
    size = 8 + len(pix) + len(pal)
    header = [0xAA, size & 0xFF, (size >> 8) & 0xFF, 0, 0, 3, n & 0xFF, (n >> 8) & 0xFF]
    return spp_frame(CMD_DRAW_PIC, [0x0, 0x0A, 0x0A, 0x04] + header + pal + pix)


def _delegate_class():
    """Build the RFCOMM delegate class once.

    An Objective-C class name may only be registered with the runtime once
    per process, so this must never run inside the connect path — a second
    registration raises and every reconnect would fail.
    """
    import objc
    from Foundation import NSObject

    class _RFCOMMDelegate(NSObject):
        def init(self):
            self = objc.super(_RFCOMMDelegate, self).init()
            self.open_status = None
            self.owner = None
            return self

        def rfcommChannelOpenComplete_status_(self, channel, status):
            self.open_status = status

        def rfcommChannelClosed_(self, channel):
            if self.owner is not None:
                self.owner._channel = None

        def rfcommChannelData_data_length_(self, channel, data, length):
            pass  # device ACKs; nothing to do with them yet

    return _RFCOMMDelegate


_DELEGATE_CLASS = None


def _get_delegate_class():
    global _DELEGATE_CLASS
    if _DELEGATE_CLASS is None:
        _DELEGATE_CLASS = _delegate_class()
    return _DELEGATE_CLASS


class PixooTransport:
    def __init__(self, address: str):
        self.address = address
        self._channel = None
        self._device = None
        self._delegate = None
        self._backoff = BACKOFF_MIN_S
        self._next_attempt = 0.0

    def _pump(self, seconds: float) -> None:
        from Foundation import NSDate, NSRunLoop

        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(seconds)
        )

    def _connect(self) -> None:
        import IOBluetooth

        dev = IOBluetooth.IOBluetoothDevice.deviceWithAddressString_(self.address)
        if not dev.isConnected():
            err = dev.openConnection()
            if err != 0:
                raise ConnectionError(f"baseband connect failed: {err}")
        delegate = _get_delegate_class().alloc().init()
        delegate.owner = self
        result, channel = dev.openRFCOMMChannelAsync_withChannelID_delegate_(
            None, RFCOMM_CHANNEL, delegate
        )
        if result != 0:
            raise ConnectionError(f"RFCOMM open call failed: {result}")
        for _ in range(20):
            self._pump(0.5)
            if delegate.open_status is not None:
                break
        if delegate.open_status != 0:
            raise ConnectionError(f"RFCOMM open status: {delegate.open_status}")
        self._device, self._delegate, self._channel = dev, delegate, channel
        self._pump(SETTLE_S)

    def _ensure_connected(self) -> bool:
        if self._channel is not None:
            return True
        now = time.monotonic()
        if now < self._next_attempt:
            return False
        try:
            self._connect()
            self._backoff = BACKOFF_MIN_S
            return True
        except Exception as e:
            print(f"[transport] connect failed: {e}; retry in {self._backoff}s")
            self._next_attempt = now + self._backoff
            self._backoff = min(self._backoff * 2, BACKOFF_MAX_S)
            self.close()
            return False

    def _write(self, data: bytes) -> None:
        mtu = self._channel.getMTU() or 666
        for i in range(0, len(data), mtu):
            chunk = data[i:i + mtu]
            err = self._channel.writeSync_length_(chunk, len(chunk))
            if err != 0:
                raise ConnectionError(f"write error {err}")

    def _send(self, data: bytes) -> bool:
        if not self._ensure_connected():
            return False
        try:
            self._write(data)
            self._pump(0.05)
            return True
        except Exception as e:
            print(f"[transport] write failed: {e}; will reconnect")
            self.close()
            self._next_attempt = time.monotonic() + self._backoff
            return False

    def push(self, img) -> bool:
        return self._send(draw_pic_frame(img))

    def set_brightness(self, value: int) -> bool:
        return self._send(spp_frame(CMD_SET_BRIGHTNESS, [max(0, min(100, value))]))

    def close(self) -> None:
        # clean close matters: the device firmware wedges on dead sessions
        if self._channel is not None:
            try:
                self._channel.closeChannel()
            except Exception:
                pass
        self._channel = None
