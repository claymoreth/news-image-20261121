#!/usr/bin/env python3
"""news-image-20261121 — main.py
Program generates one editorial news infographic for Saturday 21 November 2026:
"The World in One Day" — 40 stories, 8 regions. Writes /output/entry.png
(1024x1024 PNG, deterministic, stdlib only: math, os, struct, zlib, base64).
Glyph bitmaps (Liberation fonts, rasterised at build-prep time with PIL) live
in fontdata.bin next to this file; this program reads that binary at runtime
and rebuilds FONTDATA in memory. No third-party library is used here.
All stories, figures and dates were verified against news sources on 21 Nov 2026.
"""
import base64
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette ---
PAPER = (247, 242, 231)   # warm newsprint
CARD = (255, 253, 248)    # card white
INK = (26, 26, 26)        # headline ink
MUTED = (96, 90, 78)      # secondary text
RED = (179, 39, 30)       # accent / pins
LINE = (214, 208, 190)    # hairlines
OCEAN = (233, 239, 241)   # map sea
LAND = (186, 196, 168)    # map land
LANDLINE = (140, 148, 120)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
REGION_COLORS = [
    (158, 43, 37),    # 1 Middle East & Conflict
    (31, 78, 121),    # 2 Europe
    (30, 122, 110),   # 3 Asia-Pacific
    (183, 121, 31),   # 4 Americas
    (91, 74, 138),    # 5 Africa
    (46, 125, 50),    # 6 Climate & Environment
    (173, 20, 87),    # 7 Science, Tech & Health
    (93, 64, 55),     # 8 Sport & Culture
]
REGION_NAMES = ["MIDEAST", "EUROPE", "ASIA-PACIFIC", "AMERICAS",
                "AFRICA", "CLIMATE", "SCIENCE", "SPORT"]

# ---------------------------------------------------------------- canvas ----
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c):
        self.fill_rect(x, y, w, 1, c)
        self.fill_rect(x, y + h - 1, w, 1, c)
        self.fill_rect(x, y, 1, h, c)
        self.fill_rect(x + w - 1, y, 1, h, c)

    def hline(self, x0, x1, y, c):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        self.px[i:i + (x1 - x0 + 1) * 3] = bytes(c) * (x1 - x0 + 1)

    def vline(self, x, y0, y1, c):
        if x < 0 or x >= self.w:
            return
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def line(self, x0, y0, x1, y1, c, width=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        r = max(0, width // 2)
        for s in range(steps + 1):
            t = s / steps
            cx = int(round(x0 + dx * t))
            cy = int(round(y0 + dy * t))
            if width <= 1:
                self.set(cx, cy, c)
            else:
                self.circle(cx, cy, r, c)

    def circle(self, cx, cy, r, c):
        if r <= 0:
            self.set(cx, cy, c)
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            self.hline(cx - dx, cx + dx, cy + dy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        if rx <= 0 or ry <= 0:
            return
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            self.hline(cx - dx, cx + dx, cy + dy, c)

    def ring(self, cx, cy, r, c, thick=2):
        for dy in range(-r, r + 1):
            dxo = int(math.sqrt(r * r - dy * dy))
            dxi = int(math.sqrt(max(0, (r - thick) * (r - thick) - dy * dy))) if r - thick > 0 else 0
            self.hline(cx - dxo, cx - dxi, cy + dy, c)
            self.hline(cx + dxi, cx + dxo, cy + dy, c)

    def poly(self, pts, c):
        """Scanline fill of a polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, yy1 = pts[i]
                x2, yy2 = pts[(i + 1) % n]
                if (yy1 <= y < yy2) or (yy2 <= y < yy1):
                    if yy2 != yy1:
                        xs.append(x1 + (y - yy1) * (x2 - x1) / (yy2 - yy1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(math.ceil(xs[k])), int(math.floor(xs[k + 1])), y, c)

# ------------------------------------------------------------------- font ---
# FONTDATA is built at runtime from fontdata.bin (see _load_fonts below).
# Each entry:
#   FONTDATA["face+size"][char] = (advance, w, h, yoff, rawbits)
# yoff = top of bitmap relative to the text baseline (negative = above).

def _glyph_bits(g):
    adv, w, h, yoff, raw = g
    if isinstance(raw, str):
        raw = base64.b64decode(raw) if raw else b""
    return adv, w, h, yoff, raw

def text_width(key, s):
    f = FONTDATA[key]
    total = 0
    for ch in s:
        g = f.get(ch)
        if g is None:
            g = f.get(" ")
        total += g[0]
    return total

def draw_text(cv, x, y_base, key, s, color):
    """Draw text with baseline at y_base; returns width drawn."""
    f = FONTDATA[key]
    cx = x
    for ch in s:
        g = f.get(ch)
        if g is None:
            g = f.get(" ")
        adv, w, h, yoff, raw = _glyph_bits(g)
        if w and h:
            top = y_base + yoff
            for row in range(h):
                for col in range(w):
                    bit = (row * w + col)
                    if raw[bit >> 3] & (0x80 >> (bit & 7)):
                        cv.set(cx + col, top + row, color)
        cx += adv
    return cx - x

def draw_text_c(cv, cx, y_base, key, s, color):
    draw_text(cv, cx - text_width(key, s) // 2, y_base, key, s, color)

def wrap_text(key, s, maxw):
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(key, trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

def draw_para(cv, x, y_top, w, key, s, color, leading):
    """Draw wrapped paragraph; y_top is the ascender-top of the first line
    (draw_text's y is the ascender top, not the baseline).
    Returns y position just below the last line."""
    lines = wrap_text(key, s, w)
    y = y_top
    for ln in lines:
        draw_text(cv, x, y, key, ln, color)
        y += leading
    return y

def _ascent(key):
    # approx ascent = size * 0.78 for these fonts; size = trailing digits
    i = len(key)
    while i > 0 and key[i - 1].isdigit():
        i -= 1
    size = int(key[i:])
    return int(size * 0.78)

# ---------------------------------------------------------------- font data --
# NOTE on coordinates: PIL renders text with the anchor at the ASCENDER TOP,
# so draw_text's y argument is the ascender-top line, NOT the baseline.
# draw_para therefore passes y straight through (no +ascent).
#
# Glyph bitmaps live in fontdata.bin (packed by prep/pack_font.py from the
# system Liberation fonts at build-prep time; the pack script verified all
# 16 faces x 100 glyphs and the round-trip). The binary is generated fresh,
# never copied from another entry. main.py stays stdlib-only: it reads the
# binary at runtime and rebuilds FONTDATA in memory.
# Format: magic "FNT1", u16 num_fonts; per font: u8 name_len, name, u16
# num_glyphs; per glyph: u32 codepoint, i16 advance, u16 w, u16 h, i16 yoff,
# u16 nbytes, nbytes raw bitmap bytes (1 bit/px, MSB first, row-major).

def _load_fonts():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "fontdata.bin"), "rb") as fh:
        data = fh.read()
    if data[:4] != b"FNT1":
        raise ValueError("bad fontdata.bin magic")
    pos = 4
    nfonts = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    fonts = {}
    for _ in range(nfonts):
        nlen = data[pos]
        pos += 1
        name = data[pos:pos + nlen].decode("ascii")
        pos += nlen
        ng = struct.unpack_from(">H", data, pos)[0]
        pos += 2
        glyphs = {}
        for _ in range(ng):
            cp, adv, w, h, yoff, nb = struct.unpack_from(">IhHHhH", data, pos)
            pos += struct.calcsize(">IhHHhH")
            raw = data[pos:pos + nb]
            pos += nb
            glyphs[chr(cp)] = (adv, w, h, yoff, raw)
        fonts[name] = glyphs
    return fonts


FONTDATA = _load_fonts()

# ------------------------------------------------------------------ stories --
# The 40 stories, exactly as selected in DESIGN-BRIEF.md (verified 21 Nov 2026).
# Regions: 1 Mideast, 2 Europe, 3 Asia-Pacific, 4 Americas, 5 Africa,
# 6 Climate, 7 Science, 8 Sport. lat/lon are the map-pin positions.
# Leads: num, region, place, topic, source, headline, desc, label, lat, lon
LEADS = [
    (1, 1, "RIYADH, SAUDI ARABIA", "CONFLICT", "Reuters, AFP",
     "Coalition downs three Houthi missiles over Riyadh",
     "Saudi-led coalition intercepts three ballistic missiles fired at the "
     "capital in the early hours; second attack in days after the PIF Tower "
     "was struck Thursday. No casualties reported.",
     "3 MISSILES DOWNED", 24.6, 46.7),
    (2, 7, "MERCURY", "SPACE", "ESA",
     "BepiColombo reaches Mercury after eight years",
     "ESA-JAXA craft fires its thrusters for 37 minutes at 19:24 CET for "
     "weak gravity capture. Launched October 2018; nine flybys; 9.9 billion "
     "km. Only the second craft to orbit Mercury.",
     "8 YEARS \u00b7 9.9BN KM", 49.87, 8.65),
    (3, 6, "ANTALYA, TURKIYE", "CLIMATE", "AP, Reuters, AFP",
     "COP31 runs into overtime with no deal",
     "Talks slip past Friday's deadline; a third draft is promised Saturday "
     "morning. Thursday's draft cut 144 paragraphs to 80 and dropped any "
     "mention of coal, oil and gas.",
     "3RD DRAFT DUE SAT AM", 36.9, 30.7),
]

# Secondary: num, region, place, topic, source, headline, sub, lat, lon
SECONDARY = [
    (4, 2, "WARSAW", "NATO", "AP, Reuters",
     "Rutte in Warsaw as Poland seeks more",
     "NATO chief visits Saturday", 52.2, 21.0),
    (5, 3, "WELLINGTON", "CRICKET", "IANS",
     "Rahul's century puts India on top",
     "KL Rahul 100 off 207 balls, Day 3", -41.3, 174.8),
    (6, 4, "LAS VEGAS", "F1", "Formula 1",
     "Russell fastest in final practice",
     "Russell 1:34.041 in FP3", 36.2, -115.1),
    (7, 8, "TURIN", "TENNIS", "ATP",
     "ATP Finals semis today",
     "Alcaraz-Shelton; Zverev-Medvedev", 45.1, 7.7),
    (8, 2, "PARIS", "PROTEST", "Le Parisien",
     "Cost-of-living march shuts Paris metro",
     "~70,000 police; 16 metro stops shut", 48.85, 2.35),
    (9, 3, "BRUSSELS", "TRADE", "ANTARA",
     "Indonesia and EU sign trade deal today",
     "IEU-CEPA after a decade of talks", 50.85, 4.35),
    (10, 4, "PERU", "QUAKE", "Reuters, USGS",
     "M6.8 quake shakes Lima",
     "00:09 UTC; no major casualties", -11.2, -75.8),
    (11, 5, "DRC", "EBOLA", "Outbreak Watch, ECDC",
     "Ebola staff strike as cases pass 11,000",
     "11,376 cases, 5,568 deaths", 2.77, 27.62),
    (12, 5, "BAYELSA, NIGERIA", "DISASTER", "THISDAY, AFP",
     "Boat with 300+ capsizes; 50+ feared dead",
     "~100 missing; four bodies found", 4.9, 6.3),
    (13, 8, "MELBOURNE", "CRICKET", "cricket.com.au",
     "Australia host England in first T20I tonight",
     "First of five T20Is, MCG 19:15", -37.8, 145.0),
]

# Index items 14-40: num, region, place, one-line text, lat, lon
INDEX = [
    (14, 1, "KRYVYI RIH", "Russian strike kills 2, hurts 42", 47.9, 33.4),
    (15, 1, "HODEIDAH", "Coalition strikes Yemen port; UN warns", 14.8, 42.95),
    (16, 7, "BEIJING", "US cleared ~900,000 AI chips for China", 39.9, 116.4),
    (17, 4, "NEW YORK", "Banks disclose vendor cyberattacks", 40.7, -74.0),
    (18, 2, "COPENHAGEN", "Denmark expels Russian defence attache", 55.7, 12.6),
    (19, 2, "BRUSSELS", "EU disburses EUR 7.9bn to Ukraine", 50.85, 4.35),
    (20, 6, "ODISHA", "Cyclone Akvan aftermath; rain continues", 19.8, 85.5),
    (21, 4, "LOS ANGELES", "Jury convicts Palisades fire starter", 34.05, -118.25),
    (22, 7, "KENYA", "US-led group wins $60bn+ rare-earth deal", -4.5, 39.2),
    (23, 7, "BARCELONA", "Cancer pill shrinks tumours in 44%", 41.4, 2.17),
    (24, 6, "BRASILIA", "Lula recognises 362,000 ha of Raoni land", -8.0, -55.0),
    (25, 5, "SENEGAL", "Dozens missing after migrant boat sinks", 14.6, -17.1),
    (26, 5, "JOHANNESBURG", "581 women killed in three months", -26.2, 28.0),
    (27, 5, "ABUJA", "All 36 states back state police", 9.06, 7.5),
    (28, 1, "WASHINGTON", "Pentagon: Iran war cost $48.3bn", 38.9, -77.0),
    (29, 3, "TOKYO", "Takaichi returns; Nikkei falls 5.06%", 35.7, 139.7),
    (30, 2, "ROME", "General strike rolls into Saturday", 41.9, 12.5),
    (31, 4, "WASHINGTON", "Trump 'too busy' to meet Kim Jong Un", 38.9, -77.0),
    (32, 5, "MOGADISHU", "Somalia expels UAE ambassador", 2.05, 45.3),
    (33, 1, "HORMUZ", "Tanker hit; traffic down 65%", 26.5, 56.3),
    (34, 2, "BIRMINGHAM", "52 years since pub bombings", 52.5, -1.9),
    (35, 3, "NEW SOUTH WALES", "Coal output up 32% to 2032", -32.6, 150.9),
    (36, 4, "ATLANTA", "Rubio: US did not help Bolsonaro flee", 33.75, -84.4),
    (37, 5, "KINSHASA", "DRC condemns EU-Rwanda migration pact", -4.3, 15.3),
    (38, 4, "US EAST COAST", "Storm brings flooding to coast", 34.5, -77.5),
    (39, 4, "CANADA", "Asbestos found in squishy toys", 45.4, -75.7),
    (40, 8, "HELSINKI", "Mao Shimada leads Finlandia Trophy", 60.2, 25.0),
]

# Stats strip: (big, label)
STATS = [
    ("3", "missiles downed over Riyadh"),
    ("8 yrs", "BepiColombo's voyage to Mercury"),
    ("92,934", "people registered at COP31"),
    ("42", "hurt in the Kryvyi Rih strike"),
    ("~900,000", "AI chips cleared for China"),
    ("M6.8", "quake shakes Peru"),
]

# DATE CHECK — stories that are NOT Saturday's news (one line each).
DATECHECK = [
    "Russian missiles land in Poland (20 Nov)",
    "Kyiv's bridges hit (20 Nov)",
    "UK-EU summit deals (20 Nov)",
    "Trump-Xi-Putin Shenzhen summit (19 Nov)",
    "ICJ Myanmar genocide ruling (19 Nov)",
    "Mongolia's president quits (20 Nov)",
    "LA quake 4.2 (20 Nov)",
    "US-China military-AI pact (20 Nov)",
    "Pete Rose pardon (20 Nov)",
    "Wall Street's AI sell-off (20 Nov)",
    "EU-Canada Alliance for the Future (30 Oct)",
    "UN Climate Yearbook 44 of 96 (9 Nov)",
    "Spain general strike (11 Nov)",
    "'Storm Xavier in Athens' \u2014 wrong; Xavier is in the South Pacific",
]

# Map-pin offsets (dx, dy in px) for crowded clusters. A leader line is drawn
# from the true location to the offset pin. Fan is wide enough that no two
# pin centres are closer than ~20 px.
PIN_OFF = {
    2: (-38, -22), 4: (18, -16), 7: (0, -24), 8: (-30, 8),
    9: (-22, 22), 18: (12, -16), 19: (28, 22), 23: (-26, 36),
    28: (-16, -10), 30: (6, 28), 31: (22, 14), 34: (-48, -6),
    40: (34, -4), 3: (44, 26), 14: (48, -2), 15: (-20, -6), 33: (12, -8),
    12: (14, 8), 27: (-14, -10), 37: (12, 10), 32: (16, 8),
    38: (4, 20), 39: (-6, -18), 17: (16, -6), 36: (-20, 8), 35: (14, -12),
    6: (14, -12), 21: (-14, 10), 25: (-16, -12),
}

# ------------------------------------------------------------- layout helpers
WARN = []


def trim_to(key, s, maxw):
    """Shorten s (dropping whole words) until it fits maxw at font key."""
    if text_width(key, s) <= maxw:
        return s
    words = s.split(" ")
    while len(words) > 1 and text_width(key, " ".join(words)) > maxw:
        words.pop()
    return " ".join(words)


def chip(cv, x, y, w, h, text, bg, fg, font):
    """Solid chip with vertically centred text (draw_text y = ascender top)."""
    cv.fill_rect(x, y, w, h, bg)
    top = y + max(0, (h - _ascent(font)) // 2)
    draw_text_c(cv, x + w // 2, top, font, text, fg)


def draw_masthead(cv):
    # Top row, Rank #1 style: small red serif title left, story count right,
    # boxed by thin rules. (Was: big centered title + centered count line.)
    cv.hline(16, 1008, 4, INK)
    draw_text(cv, 16, 10, "serifB19", "THE WORLD IN ONE DAY", RED)
    _count = "40 STORIES \u00b7 8 REGIONS \u00b7 EVERY ONE DATED"
    draw_text(cv, 1008 - text_width("sansB13", _count), 10, "sansB13",
              _count, INK)
    cv.hline(16, 1008, 28, INK)
    draw_text_c(cv, 512, 38, "serifB40", "Saturday 21 November 2026", INK)
    draw_text_c(cv, 512, 84, "serifI16",
                "Riyadh intercepts three missiles \u00b7 COP31 into overtime "
                "\u00b7 BepiColombo at Mercury \u00b7 Rutte in Warsaw", MUTED)
    cv.hline(16, 1008, 129, INK)


def draw_region_strip(cv):
    y, h, w = 132, 14, 128
    for i, name in enumerate(REGION_NAMES):
        x = i * w
        cv.fill_rect(x, y, w, h, REGION_COLORS[i])
        draw_text_c(cv, x + w // 2, y + 3, "sansB9", name, WHITE)


def draw_stats(cv):
    y0 = 152
    for i, (big, label) in enumerate(STATS):
        x = 16 + i * 152
        if i:
            cv.vline(x - 8, y0 + 2, y0 + 42, LINE)
        draw_text(cv, x, y0, "serifB22", big, RED)
        lines = wrap_text("sans9", label, 140)
        yy = y0 + 25
        for ln in lines[:2]:
            draw_text(cv, x, yy, "sans9", ln, MUTED)
            yy += 11
    # thermometer: 1.5C limit passed
    tx = 940
    cv.fill_rect(tx + 8, y0 + 4, 6, 26, (220, 220, 220))
    cv.fill_rect(tx + 8, y0 + 16, 6, 14, RED)
    cv.circle(tx + 11, y0 + 34, 7, RED)
    cv.circle(tx + 11, y0 + 34, 4, (255, 255, 255))
    cv.circle(tx + 11, y0 + 34, 3, RED)
    draw_text(cv, tx + 24, y0, "serifB19", "1.5C", INK)
    draw_text(cv, tx + 24, y0 + 23, "sans9", "LIMIT", MUTED)
    draw_text(cv, tx + 24, y0 + 34, "sans9", "PASSED", MUTED)
    cv.hline(16, 1008, 197, LINE)

# --------------------------------------------------------------- illustrations
# Every illustration depicts its actual event (no generic flags, landmarks
# or decorative icons). Boxes are (x, y, w, h) on the canvas.

def burst(cv, cx, cy, r, c):
    for k in range(8):
        ang = k * math.pi / 4.0
        cv.line(cx, cy, int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang)), c, 2)
    cv.circle(cx, cy, max(2, r // 3), c)


def ellipse_ring(cv, cx, cy, rx, ry, c):
    n = 48
    prev = None
    for i in range(n + 1):
        ang = 2 * math.pi * i / n
        px = int(round(cx + rx * math.cos(ang)))
        py = int(round(cy + ry * math.sin(ang)))
        if prev is not None:
            cv.line(prev[0], prev[1], px, py, c, 1)
        prev = (px, py)


def ill_riyadh(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (16, 24, 48))
    for sx, sy in [(20, 12), (90, 20), (160, 8), (230, 16), (290, 10)]:
        cv.hline(x + sx - 1, x + sx + 1, y + sy, (255, 255, 255))
        cv.vline(x + sx, y + sy - 1, y + sy + 1, (255, 255, 255))
    # skyline silhouette + PIF Tower
    cv.fill_rect(x, y + h - 26, w, 26, (8, 12, 26))
    for bx, bw, bh in [(8, 30, 18), (48, 22, 12), (84, 26, 20), (200, 30, 14),
                       (238, 24, 18), (272, 30, 12)]:
        cv.fill_rect(x + bx, y + h - 26 - bh, bw, bh + 26, (8, 12, 26))
    cv.fill_rect(x + 140, y + h - 70, 26, 70, (8, 12, 26))
    cv.fill_rect(x + 140, y + h - 74, 26, 4, (255, 214, 90))
    for wx in (146, 154):
        cv.fill_rect(x + wx, y + h - 68, 3, 4, (255, 214, 90))
    # three missile trails + intercept bursts
    for (tx0, ty0, tx1, ty1) in [(60, 6, 95, 44), (180, 2, 205, 40), (268, 8, 250, 46)]:
        cv.line(x + tx0, y + ty0, x + tx1, y + ty1, (200, 200, 200), 2)
        cv.line(x + tx0, y + ty0, x + tx1, y + ty1, (255, 255, 255), 1)
    burst(cv, x + 95, y + 44, 12, (255, 176, 32))
    burst(cv, x + 205, y + 40, 11, (255, 120, 40))
    burst(cv, x + 250, y + 46, 10, (255, 176, 32))


def ill_mercury(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (10, 12, 22))
    for sx, sy in [(16, 10), (60, 18), (120, 8), (200, 14), (260, 22), (300, 8)]:
        cv.set(x + sx, y + sy, (255, 255, 255))
    cx, cy, r = x + w // 2 - 40, y + h // 2 + 6, 34
    cv.circle(cx, cy, r, (168, 164, 152))
    cv.circle(cx - 8, cy - 6, r - 6, (150, 146, 134))
    for (ox, oy, orr) in [(-14, -10, 6), (6, -14, 5), (12, 4, 7), (-4, 10, 5),
                          (16, -2, 4), (-18, 6, 4), (2, -2, 3)]:
        cv.circle(cx + ox, cy + oy, orr, (128, 124, 112))
    cv.circle(cx + 12, cy + 4, 3, (110, 106, 94))
    # orbit ellipse around the planet (stays inside the illustration box)
    ellipse_ring(cv, cx, cy, 72, 26, (120, 140, 160))
    sx, sy = x + w - 78, y + 16
    cv.fill_rect(sx, sy, 16, 10, (220, 224, 228))
    cv.fill_rect(sx - 14, sy + 2, 14, 6, (40, 90, 160))
    cv.fill_rect(sx + 16, sy + 2, 14, 6, (40, 90, 160))
    cv.line(sx + 8, sy, sx + 8, sy - 8, (220, 224, 228), 1)
    cv.circle(sx + 8, sy - 9, 2, (255, 214, 90))


def ill_cop(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (18, 60, 46))
    cx, cy, r = x + 62, y + h // 2, 32
    cv.circle(cx, cy, r, (46, 125, 80))
    cv.circle(cx - 6, cy - 4, 20, (30, 90, 55))
    cv.poly([(cx - 18, cy - 8), (cx - 6, cy - 14), (cx + 2, cy - 4),
             (cx - 8, cy + 2), (cx - 20, cy + 2)], (30, 110, 60))
    cv.poly([(cx + 6, cy + 8), (cx + 18, cy + 2), (cx + 20, cy + 12),
             (cx + 8, cy + 16)], (30, 110, 60))
    # thermometer at right
    tx = x + w - 74
    cv.fill_rect(tx, y + 10, 14, h - 26, (240, 240, 240))
    cv.fill_rect(tx + 2, y + 26, 10, h - 42, RED)
    cv.circle(tx + 7, y + h - 14, 11, RED)
    cv.circle(tx + 7, y + h - 14, 6, (255, 255, 255))
    cv.circle(tx + 7, y + h - 14, 4, RED)
    draw_text(cv, tx + 22, y + 12, "sansB13", "1.5C", WHITE)
    draw_text(cv, tx + 22, y + 30, "sans9", "LIMIT", (255, 255, 255))
    draw_text(cv, tx + 22, y + 41, "sans9", "PASSED", (255, 255, 255))
    # negotiation table
    cv.fill_rect(x + 150, y + h - 22, 90, 4, (120, 90, 50))
    for px in (160, 200, 228):
        cv.circle(x + px, y + h - 30, 5, (230, 200, 160))
        cv.fill_rect(x + px - 5, y + h - 26, 10, 5, (230, 200, 160))


def ill_warsaw(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (31, 78, 121))
    cv.fill_rect(x + 10, y + h - 24, 70, 24, (230, 230, 225))
    for cx in (22, 38, 54, 68):
        cv.fill_rect(x + cx, y + h - 22, 4, 16, (31, 78, 121))
    cv.fill_rect(x + 8, y + h - 28, 74, 4, (230, 230, 225))
    # AWACS plane
    px, py = x + 110, y + 12
    cv.fill_rect(px, py + 4, 62, 6, (255, 255, 255))
    cv.line(px + 62, py + 7, px + 72, py + 7, (255, 255, 255), 2)
    cv.fill_rect(px + 22, py, 30, 3, (200, 200, 200))
    cv.circle(px + 37, py - 2, 5, (200, 200, 200))
    cv.poly([(px + 8, py + 10), (px + 20, py + 10), (px + 12, py + 18)], (255, 255, 255))
    cv.poly([(px + 44, py + 10), (px + 56, py + 10), (px + 52, py + 18)], (255, 255, 255))
    # NATO four-point star
    sx, sy = x + w - 26, y + h - 22
    cv.poly([(sx, sy - 10), (sx + 3, sy - 3), (sx + 10, sy), (sx + 3, sy + 3),
             (sx, sy + 10), (sx - 3, sy + 3), (sx - 10, sy), (sx - 3, sy - 3)],
            (255, 255, 255))


def ill_cricket(cv, x, y, w, h, score):
    cv.fill_rect(x, y, w, h, (30, 90, 55))
    cv.fill_rect(x, y + h - 8, w, 8, (120, 90, 50))
    # stumps + bails
    sx = x + 14
    for dx in (0, 6, 12):
        cv.fill_rect(sx + dx, y + 8, 3, 18, (240, 220, 160))
    cv.fill_rect(sx, y + 6, 15, 2, (240, 220, 160))
    # bat + red ball
    cv.line(x + 52, y + 8, x + 66, y + 28, (220, 190, 140), 4)
    cv.fill_rect(x + 62, y + 26, 12, 5, (220, 190, 140))
    cv.circle(x + 96, y + 14, 5, RED)
    cv.circle(x + 96, y + 14, 2, (255, 255, 255))
    draw_text(cv, x + 118, y + 8, "sansB13", score, WHITE)


def ill_f1(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (12, 12, 20))
    cv.fill_rect(x, y + h - 12, w, 12, (40, 40, 48))
    cv.hline(x, x + w, y + h - 12, (255, 214, 90))
    # light streaks
    for ly in (6, 12, 18):
        cv.hline(x + 8, x + 70, y + ly, (255, 60, 60))
        cv.hline(x + w - 70, x + w - 8, y + ly + 4, (60, 140, 255))
    # F1 car
    cx, cy = x + w // 2 - 10, y + h - 22
    cv.fill_rect(cx, cy, 44, 5, (200, 30, 30))
    cv.fill_rect(cx + 12, cy - 5, 16, 5, (200, 30, 30))
    cv.fill_rect(cx - 4, cy - 2, 4, 9, (200, 30, 30))
    cv.circle(cx + 8, cy + 6, 4, BLACK)
    cv.circle(cx + 8, cy + 6, 2, (180, 180, 180))
    cv.circle(cx + 34, cy + 6, 4, BLACK)
    cv.circle(cx + 34, cy + 6, 2, (180, 180, 180))


def ill_tennis(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (30, 110, 70))
    cv.fill_rect(x + 8, y + 6, w - 16, h - 12, (60, 140, 90))
    cv.hline(x + 8, x + w - 8, y + h // 2, WHITE)
    cv.vline(x + w // 2, y + 6, y + h - 6, WHITE)
    cv.rect(x + 14, y + 9, w - 28, h - 18, WHITE)
    cv.fill_rect(x + w // 2 - 1, y + 6, 2, h - 12, (40, 40, 40))
    cv.circle(x + w - 30, y + 10, 4, (200, 230, 60))
    # racket
    cv.ellipse(x + 34, y + 12, 8, 11, (230, 230, 230))
    cv.ellipse(x + 34, y + 12, 5, 8, (30, 110, 70))
    cv.line(x + 34, y + 23, x + 30, y + 33, (230, 230, 230), 2)


def ill_paris(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (200, 170, 120))
    cv.fill_rect(x, y + h - 10, w, 10, (120, 90, 60))
    # crowd: heads + shoulders
    for i, px in enumerate(range(6, w - 6, 18)):
        sh = (40, 60, 120) if i % 3 == 0 else ((120, 40, 40) if i % 3 == 1 else (60, 90, 50))
        cv.circle(x + px, y + h - 20, 5, (230, 200, 160))
        cv.fill_rect(x + px - 7, y + h - 15, 14, 6, sh)
    # placards on sticks
    for px, ph in [(30, 14), (86, 18), (140, 14)]:
        cv.vline(x + px, y + 4, y + h - 16, (80, 60, 40))
        cv.fill_rect(x + px - 12, y + 4, 24, ph, WHITE)
        cv.hline(x + px - 8, x + px + 8, y + 8, RED)
        cv.hline(x + px - 8, x + px + 8, y + 12, INK)


def ill_signing(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (31, 78, 121))
    # EU stars circle
    sx, sy = x + w - 30, y + 12
    for k in range(8):
        ang = k * math.pi / 4.0
        cv.circle(int(sx + 9 * math.cos(ang)), int(sy + 9 * math.sin(ang)), 1, (255, 214, 90))
    cv.circle(sx, sy, 2, (255, 214, 90))
    # table + document + two signatories
    cv.fill_rect(x + 10, y + h - 14, w - 20, 5, (120, 90, 50))
    cv.fill_rect(x + w // 2 - 22, y + h - 26, 44, 12, WHITE)
    cv.hline(x + w // 2 - 18, x + w // 2 + 18, y + h - 22, INK)
    cv.hline(x + w // 2 - 18, x + w // 2 + 2, y + h - 18, MUTED)
    for px in (34, w - 44):
        cv.circle(x + px, y + h - 34, 6, (230, 200, 160))
        cv.fill_rect(x + px - 8, y + h - 28, 16, 14, (40, 40, 40) if px < w // 2 else (90, 40, 40))


def ill_quake(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (240, 235, 220))
    # building with a crack
    cv.fill_rect(x + 12, y + 8, 34, h - 16, (180, 170, 150))
    for wy in (14, 24):
        cv.fill_rect(x + 18, y + wy, 8, 6, (60, 60, 60))
        cv.fill_rect(x + 32, y + wy, 8, 6, (60, 60, 60))
    cv.line(x + 28, y + 8, x + 24, y + 18, (120, 30, 20), 2)
    cv.line(x + 24, y + 18, x + 30, y + 28, (120, 30, 20), 2)
    cv.line(x + 30, y + 28, x + 26, y + h - 8, (120, 30, 20), 2)
    # seismograph trace
    pts = []
    for i in range(0, 110):
        xx = x + 60 + i
        yy = y + h // 2 + (6 if i % 7 == 0 else (-8 if i % 5 == 0 else (3 if i % 3 == 0 else 0)))
        pts.append((xx, yy))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 1)
    draw_text(cv, x + 62, y + 6, "sansB13", "M6.8", RED)


def ill_ebola(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (245, 240, 230))
    # medical cross
    cv.fill_rect(x + 12, y + 8, 22, 8, RED)
    cv.fill_rect(x + 19, y + 1, 8, 22, RED)
    # rising bar chart of cases
    base = y + h - 6
    for i, bh in enumerate((6, 10, 14, 20)):
        cv.fill_rect(x + 52 + i * 16, base - bh, 11, bh, (91, 74, 138))
    draw_text(cv, x + 52, y + 4, "sansB9", "11,376", INK)
    # masked medic
    cv.circle(x + w - 24, y + 12, 6, (230, 200, 160))
    cv.fill_rect(x + w - 32, y + 18, 16, 14, (240, 240, 240))
    cv.fill_rect(x + w - 28, y + 13, 8, 3, (120, 180, 220))


def ill_boat(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (140, 180, 210))
    cv.fill_rect(x, y + h - 12, w, 12, (40, 110, 160))
    for i in range(4):
        cv.line(x + i * 46, y + h - 8, x + i * 46 + 22, y + h - 8, (255, 255, 255), 1)
    # boat hull + canopy + passengers
    bx, by = x + w // 2 - 40, y + h - 26
    cv.poly([(bx, by), (bx + 80, by), (bx + 70, by + 12), (bx + 10, by + 12)], (120, 70, 30))
    cv.fill_rect(bx + 18, by - 12, 44, 12, (240, 220, 160))
    for px in (bx + 24, bx + 40, bx + 56):
        cv.circle(px, by - 16, 4, (230, 200, 160))
    # rescue ring
    cv.ring(x + w - 26, y + 12, 7, (255, 120, 40), 3)


def ill_stadium(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (14, 20, 40))
    # floodlight towers
    for lx in (14, w - 22):
        cv.fill_rect(x + lx, y + 4, 3, 16, (200, 200, 200))
        cv.circle(x + lx + 1, y + 4, 4, (255, 240, 160))
        cv.line(x + lx + 1, y + 6, x + w // 2 - 10, y + h - 8, (255, 240, 160), 1)
    # stadium bowl + pitch
    cv.ellipse(x + w // 2, y + h - 4, w // 2 - 6, 12, (60, 60, 70))
    cv.ellipse(x + w // 2, y + h - 4, w // 2 - 14, 8, (40, 110, 60))
    cv.fill_rect(x + w // 2 - 24, y + h - 12, 48, 4, (200, 170, 110))
    # bat + ball
    cv.line(x + 30, y + h - 16, x + 40, y + h - 26, (220, 190, 140), 3)
    cv.circle(x + w - 40, y + 12, 4, RED)

# -------------------------------------------------------------------- cards --
def draw_lead(cv, lead, x, y, ill):
    num, region, place, topic, source, headline, desc, label = lead[:8]
    w, h = 324, 196
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, LINE)
    ill(cv, x + 1, y + 1, w - 2, 84)
    lw = text_width("sansB9", label) + 12
    chip(cv, x + 8, y + 8, lw, 14, label, RED, WHITE, "sansB9")
    ky = y + 92
    draw_text(cv, x + 8, ky, "sansB10",
              "%d \u00b7 %s \u00b7 %s" % (num, place, topic), REGION_COLORS[region - 1])
    sw = text_width("sans9", source)
    draw_text(cv, x + w - 8 - sw, ky + 1, "sans9", source, MUTED)
    lines = wrap_text("serifB19", headline, w - 16)
    yy = y + 108
    for ln in lines[:2]:
        draw_text(cv, x + 8, yy, "serifB19", ln, INK)
        yy += 23
    dlines = wrap_text("sans11", desc, w - 16)
    yy = y + 154
    for ln in dlines[:3]:
        draw_text(cv, x + 8, yy, "sans11", ln, MUTED)
        yy += 14


def draw_secondary(cv, sec, x, y, ill):
    num, region, place, topic, source, headline, sub = sec[:7]
    w, h = 192, 94
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, LINE)
    ill(cv, x + 1, y + 1, w - 2, 36)
    ky = y + 41
    kicker = "%d \u00b7 %s \u00b7 %s" % (num, place, topic)
    draw_text(cv, x + 6, ky, "sansB9", trim_to("sansB9", kicker, w - 12),
              REGION_COLORS[region - 1])
    lines = wrap_text("sansB12", headline, w - 12)
    yy = y + 53
    for ln in lines[:2]:
        draw_text(cv, x + 6, yy, "sansB12", ln, INK)
        yy += 14
    draw_text(cv, x + 6, y + 81, "sans9", trim_to("sans9", sub, w - 12), MUTED)


LEAD_ILLS = [ill_riyadh, ill_mercury, ill_cop]


def draw_leads(cv):
    for i, lead in enumerate(LEADS):
        draw_lead(cv, lead, 16 + i * 334, 198, LEAD_ILLS[i])


def draw_secondary_rows(cv):
    ills = [ill_warsaw, lambda c, x, y, w, h: ill_cricket(c, x, y, w, h, "322-2"),
            ill_f1, ill_tennis, ill_paris, ill_signing, ill_quake, ill_ebola,
            ill_boat, ill_stadium]
    for row in range(2):
        for col in range(5):
            i = row * 5 + col
            draw_secondary(cv, SECONDARY[i], 16 + col * 200, 400 + row * 96, ills[i])

# ------------------------------------------------------------------- map -----
# Coarse equirectangular continent outlines (lon, lat). Readable at map scale;
# pins are the precise part.
CONTINENTS = [
    [(-168, 66), (-155, 71), (-140, 70), (-125, 70), (-110, 68), (-95, 69),
     (-85, 66), (-78, 62), (-70, 62), (-65, 60), (-60, 55), (-55, 47),
     (-60, 46), (-65, 44), (-70, 42), (-74, 40), (-76, 35), (-80, 32),
     (-81, 25), (-84, 30), (-89, 30), (-93, 30), (-97, 26), (-96, 19),
     (-90, 21), (-87, 13), (-83, 9), (-79, 9), (-82, 13), (-86, 15),
     (-90, 14), (-94, 17), (-97, 16), (-105, 20), (-110, 24), (-114, 29),
     (-120, 34), (-124, 42), (-125, 49), (-130, 54), (-135, 58), (-140, 60),
     (-152, 60), (-158, 58), (-165, 60)],
    [(-58, 64), (-52, 60), (-44, 60), (-40, 64), (-32, 68), (-22, 70),
     (-20, 74), (-25, 76), (-35, 76), (-45, 75), (-55, 72), (-58, 68)],
    [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
     (-70, -23), (-70, -30), (-72, -37), (-73, -44), (-70, -50), (-66, -55),
     (-68, -52), (-65, -45), (-62, -40), (-58, -34), (-52, -32), (-48, -28),
     (-40, -22), (-38, -15), (-35, -9), (-35, -6), (-40, -3), (-44, -2),
     (-50, 0), (-53, 4), (-58, 6), (-62, 9), (-68, 11), (-72, 12),
     (-75, 11), (-77, 8)],
    [(-17, 15), (-17, 20), (-15, 25), (-10, 30), (-6, 33), (-1, 35), (5, 37),
     (10, 37), (11, 34), (15, 32), (20, 32), (25, 32), (30, 31), (32, 31),
     (34, 28), (35, 24), (37, 20), (39, 18), (40, 15), (43, 12), (48, 11),
     (51, 10), (51, 12), (46, 5), (41, 0), (40, -5), (39, -10), (35, -18),
     (32, -25), (28, -32), (25, -34), (20, -35), (17, -32), (15, -27),
     (12, -18), (12, -10), (13, -5), (9, -1), (9, 4), (4, 6), (-2, 5),
     (-8, 5), (-13, 8), (-17, 12)],
    [(-10, 36), (-9, 38), (-9, 43), (-2, 44), (-1, 46), (-4, 48), (-2, 50),
     (0, 51), (2, 51), (5, 53), (8, 55), (8, 57), (10, 59), (6, 58), (5, 60),
     (10, 62), (12, 64), (18, 66), (25, 68), (30, 70), (40, 68), (50, 69),
     (60, 69), (70, 72), (80, 73), (90, 75), (100, 76), (110, 74), (120, 73),
     (130, 72), (140, 72), (150, 70), (160, 69), (170, 67), (178, 65),
     (178, 64), (170, 62), (162, 60), (158, 55), (155, 50), (150, 45),
     (142, 42), (140, 38), (135, 35), (130, 33), (127, 35), (126, 38),
     (129, 42), (132, 43), (135, 44), (138, 46), (141, 50), (142, 55),
     (140, 60), (135, 65), (130, 68), (125, 68), (120, 70), (115, 72),
     (110, 74), (105, 75), (100, 76), (100, 68), (100, 60), (100, 50),
     (100, 40), (100, 30), (100, 20), (98, 16), (96, 13), (94, 16), (92, 20),
     (90, 22), (88, 22), (86, 19), (84, 17), (82, 14), (80, 11), (78, 8),
     (76, 10), (74, 14), (72, 19), (70, 21), (68, 23), (66, 25), (64, 26),
     (62, 26), (60, 25), (58, 25), (56, 26), (54, 26), (52, 27), (50, 29),
     (52, 26), (54, 24), (56, 22), (58, 19), (56, 16), (53, 14), (49, 13),
     (45, 12), (43, 14), (41, 18), (39, 22), (37, 26), (35, 29), (36, 32),
     (34, 36), (30, 36), (26, 38), (22, 37), (18, 38), (14, 38), (10, 37),
     (6, 37), (2, 36), (-2, 36), (-6, 36), (-8, 37)],
    [(113, -22), (114, -30), (115, -34), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
     (137, -12), (135, -15), (132, -12), (130, -13), (126, -14), (122, -17),
     (118, -20), (114, -22)],
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51), (-2, 50)],
    [(130, 31), (132, 33), (134, 34), (136, 35), (138, 35), (140, 36),
     (141, 38), (141, 41), (140, 44), (142, 44), (144, 43), (141, 40),
     (139, 38), (137, 37), (135, 34), (133, 34), (131, 33)],
    [(109, 1), (111, 3), (114, 4), (117, 6), (119, 1), (117, -2), (114, -3),
     (110, -3), (109, 0)],
    [(95, 5), (98, 3), (100, 0), (103, -3), (105, -5), (104, -4), (101, -1),
     (98, 2)],
    [(131, -1), (134, -3), (137, -4), (140, -6), (143, -8), (146, -8),
     (148, -9), (146, -7), (143, -5), (140, -3), (137, -2), (134, -1)],
    [(105, -6), (108, -7), (111, -7), (114, -8), (112, -7), (109, -6)],
    [(120, 18), (122, 16), (122, 14), (121, 13), (122, 11), (124, 10),
     (122, 9), (120, 10), (119, 13), (120, 16)],
    [(44, -16), (47, -15), (50, -16), (49, -20), (47, -24), (45, -25),
     (43, -22), (43, -18)],
    [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38), (175, -40),
     (173, -42), (170, -44), (167, -46)],
    [(-22, 64), (-18, 63), (-14, 64), (-15, 66), (-20, 66), (-24, 65)],
]

MAP_X0, MAP_X1, MAP_Y0, MAP_Y1 = 16, 640, 618, 786


def project(lon, lat):
    px = MAP_X0 + (lon + 168.0) / 360.0 * (MAP_X1 - MAP_X0)
    py = MAP_Y0 + (78.0 - lat) / 136.0 * (MAP_Y1 - MAP_Y0)
    return int(round(px)), int(round(py))


def all_pins():
    pins = []
    for lead in LEADS:
        pins.append((lead[0], lead[8], lead[9]))
    for sec in SECONDARY:
        pins.append((sec[0], sec[7], sec[8]))
    for item in INDEX:
        pins.append((item[0], item[4], item[5]))
    return pins


def draw_map(cv):
    draw_text(cv, MAP_X0, 600, "sansB13", "WHERE IT HAPPENED", INK)
    cv.fill_rect(MAP_X0, MAP_Y0, MAP_X1 - MAP_X0, MAP_Y1 - MAP_Y0, OCEAN)
    cv.rect(MAP_X0, MAP_Y0, MAP_X1 - MAP_X0, MAP_Y1 - MAP_Y0, LINE)
    for poly_ll in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly_ll]
        cv.poly(pts, LAND)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            cv.line(x0, y0, x1, y1, LANDLINE, 1)
    # leader lines first, then pins on top
    for num, lat, lon in all_pins():
        if num in PIN_OFF:
            tx, ty = project(lon, lat)
            dx, dy = PIN_OFF[num]
            cv.line(tx, ty, tx + dx, ty + dy, MUTED, 1)
            cv.ring(tx, ty, 3, RED, 1)
    for num, lat, lon in all_pins():
        tx, ty = project(lon, lat)
        dx, dy = PIN_OFF.get(num, (0, 0))
        cx, cy = tx + dx, ty + dy
        cv.circle(cx, cy, 7, RED)
        cv.circle(cx, cy, 6, (255, 255, 255))
        cv.circle(cx, cy, 5, RED)
        draw_text_c(cv, cx, cy - 4, "sansB9", str(num), WHITE)


def draw_datecheck(cv):
    x0 = 648
    draw_text(cv, x0, 600, "sansB13", "DATE CHECK \u2014 NOT SATURDAY'S NEWS", RED)
    draw_text(cv, x0, 616, "sans9", "Left out as Friday 20 November news:", MUTED)
    yy = 632
    for item in DATECHECK:
        cv.fill_rect(x0, yy + 3, 3, 3, RED)
        draw_text(cv, x0 + 8, yy, "sans10", trim_to("sans10", item, 344), INK)
        yy += 11


def draw_index(cv):
    draw_text(cv, 16, 792, "sansB12",
              "ALSO ON SATURDAY 21 NOVEMBER \u2014 27 MORE STORIES", INK)
    for i, item in enumerate(INDEX):
        col = i // 9
        row = i % 9
        x = 16 + col * 330
        y = 810 + row * 18
        draw_text(cv, x, y, "sansB10", "%d." % item[0], RED)
        line = "%s \u2014 %s" % (item[2], item[3])
        draw_text(cv, x + 22, y, "sans10", trim_to("sans10", line, 300), INK)


def draw_footer(cv):
    cv.hline(16, 1008, 976, LINE)
    draw_text_c(cv, 512, 982, "sans9",
                "Every story here happened, or was first reported, on Saturday "
                "21 November 2026 in at least one time zone.", MUTED)
    draw_text_c(cv, 512, 993, "sans9",
                "Claims are attributed. Forecasts are flagged. Original drawings.",
                MUTED)

# ------------------------------------------------------------------- output --
def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: None
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        return out + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def main():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_region_strip(cv)
    draw_stats(cv)
    draw_leads(cv)
    draw_secondary_rows(cv)
    draw_map(cv)
    draw_datecheck(cv)
    draw_index(cv)
    draw_footer(cv)
    os.makedirs("/output", exist_ok=True)
    n = write_png(cv, "/output/entry.png")
    print("wrote /output/entry.png %d bytes" % n)
    if WARN:
        print("warnings:")
        for w in WARN:
            print(" -", w)


if __name__ == "__main__":
    main()
