# -*- coding: utf-8 -*-
"""Erzeugt assets/cockpit.ico - App-Icon im RaceRoom-Stil (Lenkrad, Anthrazit,
roter Akzent #e8212b, weisse Speichen). Rein in Python (zlib/struct), damit es
in der CI ohne zusaetzliche Pakete laeuft. Groessen: 256/48/32/16."""
import os
import struct
import zlib

BG = (12, 12, 14)        # #0c0c0e RaceRoom-Anthrazit
RED = (232, 33, 43)      # #e8212b RR_RED
WHITE = (241, 241, 243)  # #f1f1f3
LINE = (38, 38, 44)      # #26262c Rahmen

SIZES = (256, 48, 32, 16)


def _wheel_pixel(x, y, s):
    """Farbe eines Pixels im s x s-Icon (Ursprung Mitte, y nach unten)."""
    cx = cy = (s - 1) / 2.0
    dx = x - cx
    dy = y - cy
    r = (dx * dx + dy * dy) ** 0.5
    maxr = s * 0.42
    ring_out = maxr
    ring_in = maxr * 0.78
    hub_out = maxr * 0.30
    hub_in = maxr * 0.14
    if r > ring_out:
        return BG
    # aeusserer roter Ring
    if ring_in <= r <= ring_out:
        return RED
    # Nabe
    if r <= hub_in:
        return RED
    if r <= hub_out:
        return BG
    # drei Speichen (Winkel 90 Grad, 210 Grad, 330 Grad)
    import math
    ang = math.atan2(dy, dx)
    for spoke in (math.pi / 2, math.pi / 2 + 2 * math.pi / 3, math.pi / 2 + 4 * math.pi / 3):
        d = abs(((ang - spoke + math.pi) % (2 * math.pi)) - math.pi)
        if d < 0.16 and r <= ring_in:
            return WHITE
    return BG


def _render(size, ss=4):
    """Anti-Aliasing per Supersampling: ss x ss Unterpixel pro Pixel."""
    big = size * ss
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            rs = gs = bs = cnt = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = _wheel_pixel(x * ss + sx + 0.5, y * ss + sy + 0.5, big)
                    rs += c[0]; gs += c[1]; bs += c[2]; cnt += 1
            row += bytes((rs // cnt, gs // cnt, bs // cnt, 255))
        rows.append(bytes(row))
    return rows


def _png(size, rows):
    """RGBA-PNG (Filter 0 je Zeile) aus Pixeldaten bauen."""
    def chunk(tag, data):
        raw = tag + data
        return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xffffffff)
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def make_ico(path):
    entries = []
    offset = 6 + 16 * len(SIZES)
    for s in SIZES:
        data = _png(s, _render(s))
        entries.append((s, offset, data))
        offset += len(data)
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, len(SIZES))
    for s, off, data in entries:
        w = 0 if s >= 256 else s
        out += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), off)
    for _s, _off, data in entries:
        out += data
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(bytes(out))
    return os.path.getsize(path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "assets", "cockpit.ico")
    n = make_ico(dest)
    print("Icon geschrieben: %s (%d Bytes, Groessen %s)" % (os.path.normpath(dest), n, "/".join(str(s) for s in SIZES)))
