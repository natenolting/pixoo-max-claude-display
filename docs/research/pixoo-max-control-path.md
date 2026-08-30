# Pixoo Max control from Mac — research report

Resolves [.wayfinder/tickets/001-pixoo-max-control-path.md](../../.wayfinder/tickets/001-pixoo-max-control-path.md).

## 1. WiFi / LAN HTTP API? — No. Bluetooth Classic only. (Confidence: HIGH)

- FCC filing [A8I-PIXOO-MAX](https://fccid.io/A8I-PIXOO-MAX) titled "Pixoo-max with Bluetooth". Sole radio test report: **Bluetooth BR/EDR** (2402–2480 MHz, Part 15C). No 802.11 test report, no BLE report. Compare Pixoo-64: [A8IPIXOO64](https://fccid.io/A8IPIXOO64) "Pixoo 64 with WiFi".
- So no `http://<ip>/post` LAN API. All Pixoo-64 tooling (pixoo-rest, r12f/divoom, PyPI `pixoo`, doc.divoom-gz.com REST docs) inapplicable to Pixoo Max.
- Retail listings claiming "Bluetooth and WiFi" are marketing noise; FCC cert contradicts them.
- Divoom cloud API (redphx/apixoo) is a server-side gallery/social API, not local device control.

## 2. Bluetooth protocol + libraries — BT Classic SPP/RFCOMM, reverse-engineered, Pixoo Max supported (Confidence: HIGH)

Protocol: RFCOMM (SPP), channel 1. Classic Divoom framing (documented in
[node-divoom-timebox-evo PROTOCOL.md](https://github.com/RomRider/node-divoom-timebox-evo/blob/master/PROTOCOL.md)):
`0x01` start, 2-byte LE length, payload, 2-byte LE sum checksum, `0x02` end.
Image draw = cmd `0x44` (static), `0x49` (animation frames, chunked).
Palette-based: N RGB palette entries then pixel indices packed at
`ceil(log2(N))` bits/pixel, bit-reversed packing.

Repos with verified Pixoo Max (32x32) support:

- **[virtualabs/pixoo-client](https://github.com/virtualabs/pixoo-client)** (Python) — explicit `PixooMax(Pixoo)` class. Connects `socket.AF_BLUETOOTH / BTPROTO_RFCOMM`, port 1. 32x32 draw via `draw_pic()`, brightness via `set_system_brightness`. Animation `NotYetImplemented` for Max. Key 32x32 difference: 8-byte frame header with **16-bit color count** (`[0xAA, size&0xff, size>>8, 0, 0, 0, nb_colors...]`) vs 7-byte header on 16x16; image pre-quantized to 256-color adaptive palette. Caveat: `AF_BLUETOOTH` is Linux-only — won't run natively on macOS (absent from CPython macOS builds through 3.14).
- **[d03n3rfr1tz3/hass-divoom](https://github.com/d03n3rfr1tz3/hass-divoom)** (Python, Home Assistant) — explicitly lists `pixoomax` device type with dedicated examples. `pixoomax.py`: `screensize = 32`, `chunksize = 200`; supports image/GIF, brightness 0–100, scrolling text w/ fonts, clock/scoreboard modes. README: Bluetooth Classic RFCOMM, NOT BLE; BLE proxies won't work. Most complete/maintained Max implementation found.
- **[jakobwesthoff/divoom-pixoo-max-nodejs](https://github.com/jakobwesthoff/divoom-pixoo-max-nodejs)** (Node/TS) — reverse-engineering aimed at Pixoo Max specifically. Static images working; animation code exists but commented out (200-byte chunks). Uses `node-bluetooth-serial-port` (macOS support via IOBluetooth). Practical detail: **must wait ~100 ms after connect before sending** or commands get dropped.

Not Max-capable: RomRider/node-divoom-timebox-evo (16x16 encoder only, no BT transport), MattIPv4/divoom-control (Pixoo 16x16), PyPI `pixoo` (Pixoo-64 HTTP), redphx/apixoo (cloud).

## 3. USB: data or power? — Power only, per all evidence. (Confidence: MEDIUM-HIGH)

- USB-C documented (manuals, reviews) solely as power/charging (5000 mAh battery).
- Zero evidence of USB CDC/serial/HID control on Pixoo Max or any Divoom device.
- Hands-on check cheap: `system_profiler SPUSBDataType` / `ls /dev/cu.usb*` with device plugged in. Expect nothing.

## 4. macOS BT Classic SPP feasibility — Yes, two workable routes. (Confidence: MEDIUM)

- **Route A — `/dev/cu.*` + pyserial**: macOS exposes paired SPP peripherals as `/dev/cu.<DeviceName>` (IOBluetooth RFCOMM bridge, same as HC-05 modules). Pair "Pixoo-max" in System Settings > Bluetooth, look for `/dev/cu.Pixoo*`, open with pyserial (baud irrelevant), write raw Divoom frames. Port the ~150 lines of `PixooMax` encoding from virtualabs/pixoo-client onto pyserial.
- **Route B — Node `node-bluetooth-serial-port`**: native macOS (IOBluetooth binding); exactly what the jakobwesthoff Max repo uses. Connect by MAC + RFCOMM channel 1.
- PyBluez on macOS: known broken/limited RFCOMM ([pybluez#174](https://github.com/pybluez/pybluez/issues/174)) — avoid.
- Quirks: (a) device is also an A2DP speaker — macOS may grab it as audio output on pair/connect; (b) 100 ms post-connect settle delay; (c) no macOS-specific Divoom pairing horror stories found — but few documented macOS successes, so `/dev/cu` appearance is **unverified for this exact device** (needs SPP SDP record; likely, but confirm on hardware).

## 5. Frame push mechanics (Confidence: MEDIUM on encoding, LOW on achievable fps)

- Encoding: palette-indexed (see §2). 32x32 vs 16x16: 1024 px vs 256 px; 8-byte header w/ 16-bit palette-count vs 7-byte; worst-case frame ≈ 768 B palette + 1024 B indices ≈ ~1.8 KB + framing, split into ~200-byte chunks.
- Two push modes: one-shot static image (`0x44`) per update, or upload multi-frame animation (`0x49`, per-frame time field, device plays standalone).
- No published fps benchmarks for Pixoo Max. RFCOMM/EDR throughput (~100+ kB/s) theoretically allows tens of fps at ~2 KB/frame, but Divoom firmware processing is the real bottleneck; Divoom's own animation guidance centers on 8–12 fps. For a stats display (redraw every 1–10 s), throughput is a non-issue.

## Recommended control path (Mac-hosted stats display)

1. Pair Pixoo Max via System Settings (Bluetooth Classic).
2. First try **pyserial → `/dev/cu.Pixoo*`**, sending frames built with virtualabs' `PixooMax` encoder (swap its socket for the serial port). Fallback: **Node + `node-bluetooth-serial-port`** (proven macOS path, MAC + channel 1).
3. Render 32x32 stats offscreen (PIL/canvas), quantize to ≤256-color adaptive palette, push as static image (`0x44`) each refresh tick; 100 ms settle after connect; keep connection open between pushes.
4. Steal command tables (brightness, text, clock modes) from hass-divoom's `divoom.py`/`pixoomax.py`.

## Open unknowns — need hands-on testing (feeds Hardware smoke test)

- Does macOS actually spawn `/dev/cu.Pixoo*` after pairing (SPP SDP record present?). If not, Route B.
- Does macOS's A2DP auto-connect interfere with RFCOMM channel 1?
- Real sustained fps for repeated `0x44` static pushes at 32x32.
- Animation upload (`0x49`) at 32x32: virtualabs left it unimplemented; hass-divoom claims it — verify on hardware; Pixoo-64 lore says >~40 frames crashes device (may not apply).
- USB port: confirm no device enumerates (expected power-only).
- Whether current firmware still matches 2020-era reverse-engineered protocol.

Prompt-injection check: fetched pages contained no instruction-like content; treated as data. One conflict: retail/blog pages claiming WiFi — overridden by FCC primary source.
