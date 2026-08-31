# PROTOTYPE — throwaway. Direct IOBluetooth RFCOMM push to Pixoo Max,
# bypassing the flaky /dev/cu serial bridge. Run from Terminal.app (which
# holds the Bluetooth TCC grant):
#
#   .venv/bin/python prototypes/state_screen/direct_push.py          # probe only
#   .venv/bin/python prototypes/state_screen/direct_push.py all      # all variants
#   .venv/bin/python prototypes/state_screen/direct_push.py A        # one variant

import sys
import time

import objc  # noqa: F401  (pyobjc runtime)
import IOBluetooth
from Foundation import NSObject, NSRunLoop, NSDate

sys.path.insert(0, "prototypes/state_screen")
from proto import VARIANTS, STATES, DEMO_COUNT, encode_image_32, spp_frame

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", ".."))
from claude_display.config import PIXOO_ADDRESS as _ADDR
if not _ADDR:
    _sys.exit("set PIXOO_ADDRESS in .env first")
PIXOO_ADDR = _ADDR
RFCOMM_CHANNEL = 1


class ChannelDelegate(NSObject):
    def init(self):
        self = objc.super(ChannelDelegate, self).init()
        self.received = b""
        self.open_status = None
        return self

    def rfcommChannelData_data_length_(self, channel, data, length):
        self.received += bytes(data)
        print(f"  <- device: {bytes(data).hex()}")

    def rfcommChannelOpenComplete_status_(self, channel, status):
        self.open_status = status
        print(f"  async open complete, status={status}")


def pump(seconds):
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(seconds)
    )


def build_frame(img):
    n, pal, pix = encode_image_32(img)
    size = 8 + len(pix) + len(pal)
    header = [0xAA, size & 0xFF, (size >> 8) & 0xFF, 0, 0, 3, n & 0xFF, (n >> 8) & 0xFF]
    return spp_frame(0x44, [0x0, 0x0A, 0x0A, 0x04] + header + pal + pix)


def write_chunked(channel, data, mtu):
    for i in range(0, len(data), mtu):
        chunk = bytes(data[i:i + mtu])
        err = channel.writeSync_length_(chunk, len(chunk))
        if err != 0:
            print(f"  write error {err} at offset {i}")
            return False
    return True


def main():
    which = sys.argv[1].upper() if len(sys.argv) > 1 else "PROBE"

    dev = IOBluetooth.IOBluetoothDevice.deviceWithAddressString_(PIXOO_ADDR)
    print(f"device: {dev.name()} paired={bool(dev.isPaired())} connected={bool(dev.isConnected())}")

    if not dev.isConnected():
        print("opening baseband connection...")
        err = dev.openConnection()
        print(f"openConnection -> {err}")
        if err != 0:
            sys.exit("baseband connect failed — is the Pixoo on and in range?")

    print("SDP query...")
    dev.performSDPQuery_(None)
    pump(2.0)
    spp_channel = RFCOMM_CHANNEL
    services = dev.services() or []
    for svc in services:
        name = svc.getServiceName()
        res, chan = svc.getRFCOMMChannelID_(None)
        print(f"  service: {name!r} rfcomm_channel={chan if res == 0 else '-'}")
        if res == 0 and name and ("serial" in str(name).lower() or "spp" in str(name).lower()):
            spp_channel = chan
    print(f"using RFCOMM channel {spp_channel}")

    delegate = ChannelDelegate.alloc().init()
    result, channel = dev.openRFCOMMChannelSync_withChannelID_delegate_(
        None, spp_channel, delegate
    )
    if result != 0 or channel is None:
        print(f"sync open failed ({result}); trying async...")
        result, channel = dev.openRFCOMMChannelAsync_withChannelID_delegate_(
            None, spp_channel, delegate
        )
        print(f"async open call -> {result}")
        for _ in range(20):
            pump(0.5)
            if delegate.open_status is not None:
                break
        if delegate.open_status != 0:
            print(f"async status: {delegate.open_status}")
            channel = None
    if channel is None:
        sys.exit("RFCOMM open failed on both paths")
    mtu = channel.getMTU()
    print(f"RFCOMM channel {RFCOMM_CHANNEL} open, MTU={mtu}")
    pump(1.0)  # settle — device drops bytes sent immediately after connect

    print("probe: brightness 80")
    write_chunked(channel, spp_frame(0x74, [80]), mtu)
    pump(1.5)

    if which != "PROBE":
        names = list(VARIANTS) if which == "ALL" else [which]
        for name in names:
            for s in STATES:
                print(f"variant {name} state {s}")
                write_chunked(channel, build_frame(VARIANTS[name](s, DEMO_COUNT)), mtu)
                pump(2.5)

    channel.closeChannel()
    print("done (connection left up)")


if __name__ == "__main__":
    main()
