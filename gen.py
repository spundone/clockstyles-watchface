#!/usr/bin/env python3
"""Generates res/raw/watchface.xml for the Clock Styles face.

Styles (picked in Customize through a ListConfiguration):
  0 Sticker   heavy rounded hours over minutes, per-digit checkerboard tones,
              digits overlap with black outlines (Pixel lock screen big clock)
  1 Cookie    pill hands on a compact 12-scallop cookie dial with an accent dot at 12
  2 Narrow    tall condensed single-line time
  3 Thin      hairline-weight large time
  4 Line      heavy single-line time, digits alternating tones
  5 Pill      medium rounded time inside a capsule
  6 Stacked   plain regular-weight hours over minutes
  7 Numeral   analog: big 12/3/6/9 around a pill hour hand and thin minute hand
  8 Outline   analog: outlined pill hour hand, thin minute hand, four quiet marks
  9 Clover    analog on a soft four-leaf tonal dial
 10 Bubble    one digit per overlapping tonal bubble, 2x2, checkerboard tones
 11 Hybrid    digital time over slim tonal analogue hands, rim hour dots
 12 Arc       digital time inside a rim track; an accent arc fills with the minutes
 13 Tile      stacked heavy time on a rounded square tile
 14 Sunny     analog: dark hands on a bright eight-point soft burst
 15 Wavy      M3E wavy progress: elapsed minutes as a wave round the rim, flat track after
 16 Morph     the time sits in one of six M3E shapes that changes every hour and turns hourly
Analog styles are minimal: no seconds hands, no centre caps.

Other options in Customize:
  Color        seven Material themes plus Mono (greyscale).
  Analog ring  off by default: low-profile analogue time behind every style
               (rim dots, an hour pip and a minute dot).
Power saver is automatic: at <= 20% battery the active face switches to the greyscale
outline always-on layer (no colour, no hands over it).
  Background   None (default) or a vector wallpaper drawn in the theme's own colours (Glow,
               Blobs, Horizon, Rings, Dither), or Photo (WFF Photos, picked on the phone).
               Hidden in always-on and power saver.
  Info         0 Minimal (default): the date under the clock; 1 date + weather;
               2 Full: date + weather on top, steps, heart rate and battery at the bottom;
               3 Full with everything at the bottom; 4 Off: time only.
The info is shared by every style and fully built in (WFF v2 weather, step count,
heart rate (BODY_SENSORS permission), battery), so no style repeats the date and there are no complication slots.
12/24 h follows the watch setting.

Always-on mirrors each style in greyscale outlines: digits are a grey ring around an unlit
body (8 offset grey copies under a black copy), dials and pill hands are 2 px strokes, and
the info stays, dimmed and grey. Thin keeps its hairline digits.

Usage: gen.py [--default N] [--only N] [--amb] [--saver N] [--ring 0|1] [--layout 0-4] [--bg N]
  --default N  make style N the default list option
  --only N     emit style N alone, without the style ListConfiguration (renderer tests)
  --amb        draw the always-on layer in active mode, so adb screenshots can show it
  --saver 0|1 (battery saver off/on), --ring 0|1, --layout 0-4  bake that in (a reinstall keeps saved choices,
               so tests pin them instead)

Samsung's WFF renderer notes (Stack face + tools/probe.py):
  - DigitalClock/TimeText draws nothing; use PartText with [HOUR_*]/[MINUTE_Z].
  - ComplicationSlot must be a direct child of Scene, not inside a Group.
  - PartImage tintColor is ignored.
  - floor(x / 10), x % 10 and subText() work in Parameter expressions (per-digit text).
  - Font <Outline> is ignored, so outlines are black copies drawn underneath.
  - TextCircular and PartText angle= both render.
  - Built-in weather (WEATHER.*) and [STEP_COUNT] work, but weather reads unavailable
    for a few seconds after install. [BATTERY_CHARGING_STATUS] works.
  - Nested ListConfiguration / BooleanConfiguration inside a ListOption render, but the
    editor crashes (ConcurrentModificationException) when an option changes, so every
    configuration appears once, at Scene level. Conditions are fine anywhere.
  - A "%" in any string resource (even an option label) breaks the face picker
    (FormatFlagsConversionMismatchException) and complication slots stop rendering.
"""
import argparse
import math
from pathlib import Path

W = 450
C = W // 2

# Per theme: primary (light tone), container (deep), soft (pale), accent, dial (dark tonal), muted
THEMES = [
    ("c_teal",   "#FF9DD9EA", "#FF00687A", "#FFE6F7FB", "#FFD8CCFF", "#FF1F3A3D", "#FF7E9EA2"),
    ("c_ocean",  "#FF6FA4FF", "#FF1B4FD1", "#FFD8E5FF", "#FFFFC94A", "#FF1B2B4D", "#FF8197C9"),
    ("c_lime",   "#FFB6F15A", "#FF2E6A12", "#FFE8FFCC", "#FF5AE0D0", "#FF22331A", "#FF8DA77A"),
    ("c_tomato", "#FFFF7452", "#FFB3261E", "#FFFFDAD2", "#FFFFC94A", "#FF3D2320", "#FFB98D86"),
    ("c_grape",  "#FFC496FF", "#FF6A2BD6", "#FFF1DEFF", "#FFFF8AC8", "#FF2E2440", "#FF9C8CBA"),
    ("c_mango",  "#FFFFB627", "#FF9A4E00", "#FFFFE8BC", "#FFFF7452", "#FF3A2E17", "#FFB9A27A"),
    ("c_pink",   "#FFFF7AB8", "#FFB0186A", "#FFFFD9EB", "#FF8AB4FF", "#FF3D2030", "#FFB98AA2"),
    ("c_mono",   "#FFD6D6D6", "#FF3A3A3A", "#FFF2F2F2", "#FFA8A8A8", "#FF1E1E1E", "#FF7A7A7A"),
]
PRIMARY, CONTAINER, SOFT, ACCENT, DIAL, MUTED = (f"[CONFIGURATION.theme.{i}]" for i in range(6))
BLACK = "#FF000000"
AMB_HI, AMB_LO = "#FFD0D0D0", "#FF8C8C8C"  # always-on greys

# res/font, cut from Google Sans Flex (OFL) by tools/cut_fonts.py
F_TEXT, F_LIGHT = "gsf_text", "gsf_digits_light"
F_HEAVY, F_NARROW, F_THIN, F_MED = "gsf_heavy", "gsf_narrow", "gsf_thin", "gsf_medium_round"

STYLES = ["s_sticker", "s_cookie", "s_narrow", "s_thin", "s_line", "s_pill",
          "s_stacked", "s_numeral", "s_day", "s_clover", "s_bubble", "s_hybrid",
          "s_arc", "s_tile", "s_sunny", "s_wavy", "s_morph"]

# Hour as a number that follows the 12/24 h setting, for per-digit arithmetic
HOUR = "([IS_24HOUR_MODE] * [HOUR_0_23] + (1 - [IS_24HOUR_MODE]) * [HOUR_1_12])"
HOUR_T, HOUR_O = f"floor({HOUR} / 10)", f"{HOUR} % 10"
MIN_T, MIN_O = "floor([MINUTE] / 10)", "[MINUTE] % 10"


# ---------- building blocks ----------

def text(x, y, w, h, tmpl, exprs, size, color, family=F_TEXT, align="CENTER"):
    params = "".join(f'<Parameter expression="{e}" />' for e in exprs)
    return f'''<PartText x="{x}" y="{y}" width="{w}" height="{h}">
  <Text align="{align}">
    <Font family="{family}" size="{size}" color="{color}"><Template>{tmpl}{params}</Template></Font>
  </Text>
</PartText>'''


def digits(cy, size, expr, color, family, x=0, w=W, align="CENTER"):
    """Digits whose cap height is centred on cy (the box is 1.3 em tall)."""
    h = round(size * 1.3)
    return text(x, round(cy - h / 2), w, h, "%s", [expr], size, color, family, align)


def hour_cond(make, zero12=False):
    """make(expr) -> xml; picks the 24 h or 12 h hour from the watch setting."""
    h12 = "[HOUR_1_12_Z]" if zero12 else "[HOUR_1_12]"
    return f'''<Condition>
  <Expressions><Expression name="is24"><![CDATA[[IS_24HOUR_MODE] == 1]]></Expression></Expressions>
  <Compare expression="is24">{make("[HOUR_0_23_Z]")}</Compare>
  <Default>{make(h12)}</Default>
</Condition>'''


def time_line(cy, size, family, hour_color, colon_color, minute_color, colon_w, zero12=True, dig=None):
    """Single-line HH:MM split around a fixed colon so it never shifts (zero-padded keeps it centred).
    dig: digit maker with digits()'s signature (ghost for always-on outlines)."""
    digits_ = dig or digits
    half = colon_w // 2
    hours = hour_cond(lambda e: digits_(cy, size, e, hour_color, family, 0, C - half, "END"), zero12)
    h = round(size * 1.3)
    colon = text(C - half, round(cy - h / 2), colon_w, h, ":", [], size, colon_color, family)
    minutes = digits_(cy, size, "[MINUTE_Z]", minute_color, family, C + half, C - half, "START")
    return f"{hours}\n{colon}\n{minutes}"


def date(cy, size, color, w=260):
    h = round(size * 1.4)
    return text(C - w // 2, round(cy - h / 2), w, h, "%s %s",
                ["[DAY_OF_WEEK_S]", "[DAY]"], size, color)


AMB_PREVIEW = False  # --amb: draw the always-on layer while active, for screenshots


def group(name, body, ambient=False):
    """Active-only group (hidden in always-on) or ambient-only group."""
    if AMB_PREVIEW:
        return f'<Group name="{name}" x="0" y="0" width="{W}" height="{W}" alpha="{255 if ambient else 0}">\n  {body}\n</Group>'
    if ambient:
        return f'''<Group name="{name}" x="0" y="0" width="{W}" height="{W}" alpha="0">
  <Variant mode="AMBIENT" target="alpha" value="255" />
  {body}
</Group>'''
    return f'''<Group name="{name}" x="0" y="0" width="{W}" height="{W}">
  <Variant mode="AMBIENT" target="alpha" value="0" />
  {body}
</Group>'''


LAYOUT_FIXED = None  # --layout N bakes the info layout in
EMPTY = '<Group name="none" x="0" y="0" width="1" height="1" />'
SAVER_FIXED = None  # --saver N: bake power saver choice N in (renderer tests)


def saver(normal, mono):
    """Automatic power saver: below 20% battery the active face shows the greyscale outline layer.
    A Condition, not a configuration: options nested inside options crash Samsung's editor."""
    if SAVER_FIXED is not None:
        return mono if SAVER_FIXED == 1 else normal
    return f'''<Condition>
  <Expressions><Expression name="low"><![CDATA[[BATTERY_PERCENT] <= 20]]></Expression></Expressions>
  <Compare expression="low">{mono}</Compare>
  <Default>{normal}</Default>
</Condition>'''


def choose(cid, options, fixed=None):
    """A Scene-level ListConfiguration over options (or just option `fixed` for renderer tests)."""
    if fixed is not None:
        return options[fixed]
    return f'<ListConfiguration id="{cid}">\n' + "\n".join(
        f'<ListOption id="{i}">\n{o}\n</ListOption>' for i, o in enumerate(options)) + "\n</ListConfiguration>"


def pair(name, active, amb):
    """Active group (colour, or the greyscale outline layer in power saver) plus the always-on group."""
    return group(name, saver(active, amb)) + "\n" + group(name + "_amb", amb, True)


def over_layer(name, body):
    """Analogue hands (active only); hidden in power saver and always-on."""
    return group(name, saver(body, EMPTY))


def draw(body):
    return f'<PartDraw x="0" y="0" width="{W}" height="{W}">\n  {body}\n</PartDraw>'


def hand(length, width, angle_expr, color, tail=0, cy=C, stroke=0):
    """Pill hand pivoting at (C, cy); stroke > 0 draws it as an outline of that thickness."""
    paint = f'<Stroke color="{color}" thickness="{stroke}" />' if stroke else f'<Fill color="{color}" />'
    return f'''<PartDraw x="0" y="{cy - C}" width="{W}" height="{W}" pivotX="0.5" pivotY="0.5">
  <Transform target="angle" value="{angle_expr}" />
  <RoundRectangle x="{C - width / 2}" y="{C - length}" width="{width}" height="{length + tail + width / 2}" cornerRadiusX="{width / 2}" cornerRadiusY="{width / 2}">{paint}</RoundRectangle>
</PartDraw>'''


def dot(cx, cy, r, color):
    return f'<Ellipse x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}"><Fill color="{color}" /></Ellipse>'


HOUR_ANGLE = "([HOUR_0_11] + [MINUTE] / 60) * 30"
MINUTE_ANGLE = "([MINUTE] + [SECOND] / 60) * 6"


# ---------- styles ----------

def outlined(x, w, align, cy, size, expr, color, t, line=BLACK, family=F_HEAVY):
    """One digit with an outline: 8 offset copies in `line` underneath, then the colored digit."""
    d = max(1, round(t * 0.7))
    offs = [(t, 0), (-t, 0), (0, t), (0, -t), (d, d), (d, -d), (-d, d), (-d, -d)]
    copies = [digits(cy + dy, size, expr, line, family, x + dx, w, align) for dx, dy in offs]
    return "\n".join(copies + [digits(cy, size, expr, color, family, x, w, align)])


def ghost(cy, size, expr, color, family, x=0, w=W, align="CENTER", t=2):
    """Always-on digit: a `color` outline around a black (unlit) body. Same signature as digits()."""
    return outlined(x, w, align, cy, size, expr, BLACK, t, color, family)


def ghost_hand(length, width, angle_expr, color, cy=C):
    return hand(length, width, angle_expr, color, cy=cy, stroke=2)


AMB_COLON = AMB_LO


def s_sticker():
    size, ov, t = 150, 20, 5
    cap = 0.728 * size
    cy1 = round(C - (cap - 6) / 2)   # the two rows straddle the screen centre
    cy2 = round(cy1 + cap - 6)
    lx, rx = C + ov // 2 - size, C - ov // 2   # left cells end-aligned, right cells start-aligned
    active = "\n".join([
        outlined(lx, size, "END", cy1, size, HOUR_T, SOFT, t),
        outlined(rx, size, "START", cy1, size, HOUR_O, PRIMARY, t),
        outlined(lx, size, "END", cy2, size, MIN_T, PRIMARY, t),
        outlined(rx, size, "START", cy2, size, MIN_O, SOFT, t),
    ])
    g = lambda x, a, cy, e, col: ghost(cy, size, e, col, F_HEAVY, x, size, a, 3)
    amb = "\n".join([
        g(lx, "END", cy1, HOUR_T, AMB_HI), g(rx, "START", cy1, HOUR_O, AMB_LO),
        g(lx, "END", cy2, MIN_T, AMB_LO), g(rx, "START", cy2, MIN_O, AMB_HI),
    ])
    return pair("sticker", active, amb)


def cookie_shape(color, lobes=12, rc=112, r=30, disc=128, inset=0):
    """Scalloped cookie: a disc with small lobe circles on its rim (outer radius rc + r)."""
    parts = [dot(C, C, disc - inset, color)]
    for k in range(lobes):
        a = 2 * math.pi * k / lobes
        parts.append(dot(C + rc * math.sin(a), C - rc * math.cos(a), r - inset, color))
    return "\n  ".join(parts)


def s_cookie():
    """Compact 12-scallop cookie dial that clears the info rows, an accent dot at 12 and
    rounded pill hands."""
    noon = lambda col: dot(C, C - 112, 6, col)
    over = "\n".join([
        hand(64, 22, HOUR_ANGLE, PRIMARY),
        hand(104, 14, MINUTE_ANGLE, SOFT),
    ])
    amb = "\n".join([
        draw(cookie_shape(AMB_LO) + "\n  " + cookie_shape(BLACK, inset=2) + "\n  " + noon(AMB_HI)),
        ghost_hand(64, 22, HOUR_ANGLE, AMB_LO),
        ghost_hand(104, 14, MINUTE_ANGLE, AMB_HI),
    ])
    return pair("cookie", draw(cookie_shape(DIAL) + "\n  " + noon(ACCENT)), amb), over_layer("cookie_hands", over)


def s_narrow():
    size = 236
    active = "\n".join([
        time_line(C, size, F_NARROW, SOFT, ACCENT, PRIMARY, 50),
    ])
    amb = time_line(C, size, F_NARROW, AMB_HI, AMB_COLON, AMB_LO, 50, dig=ghost)
    return pair("narrow", active, amb)


def s_thin():
    size = 150
    active = "\n".join([
        time_line(C, size, F_THIN, PRIMARY, PRIMARY, PRIMARY, 30),
    ])
    amb = time_line(C, size, F_THIN, AMB_HI, AMB_LO, AMB_HI, 30)
    return pair("thin", active, amb)


def s_line():
    """Heavy single line, digits alternate tones from the right: ones-minute PRIMARY, then SOFT, ..."""
    size, cy = 108, C
    cell, cw = round(size * 0.84), round(size * 0.36)
    def layout(n_hour, amb=False):
        mk = ghost if amb else digits
        hi, lo = (AMB_HI, AMB_LO) if amb else (PRIMARY, SOFT)
        total = (n_hour + 2) * cell + cw
        x = C - total // 2
        out = []
        hour_digits = [(HOUR_T, lo), (HOUR_O, hi)][2 - n_hour:]
        for expr, col in hour_digits:
            out.append(mk(cy, size, expr, col, F_HEAVY, x, cell)); x += cell
        out.append(text(x, round(cy - size * 0.65), cw, round(size * 1.3), ":", [], size, AMB_COLON if amb else SOFT, F_HEAVY)); x += cw
        for expr, col in ((MIN_T, lo), (MIN_O, hi)):
            out.append(mk(cy, size, expr, col, F_HEAVY, x, cell)); x += cell
        return "\n".join(out)
    time = lambda amb=False: f'''<Condition>
  <Expressions><Expression name="two"><![CDATA[{HOUR} >= 10]]></Expression></Expressions>
  <Compare expression="two">{layout(2, amb)}</Compare>
  <Default>{layout(1, amb)}</Default>
</Condition>'''
    active = time()
    amb = time(True)
    return pair("line", active, amb)


def s_pill():
    size = 108
    pw, ph = 384, 176
    pill = (f'<RoundRectangle x="{C - pw // 2}" y="{C - ph // 2}" width="{pw}" height="{ph}" '
            f'cornerRadiusX="{ph // 2}" cornerRadiusY="{ph // 2}"><Fill color="{CONTAINER}" /></RoundRectangle>')
    active = "\n".join([
        draw(pill),
        time_line(C, size, F_MED, SOFT, ACCENT, SOFT, 34),
    ])
    ring = (f'<RoundRectangle x="{C - pw // 2}" y="{C - ph // 2}" width="{pw}" height="{ph}" '
            f'cornerRadiusX="{ph // 2}" cornerRadiusY="{ph // 2}"><Stroke color="{AMB_LO}" thickness="2" /></RoundRectangle>')
    amb = draw(ring) + "\n" + time_line(C, size, F_MED, AMB_HI, AMB_COLON, AMB_HI, 34, dig=ghost)
    return pair("pill", active, amb)


def s_stacked():
    size = 150
    active = "\n".join([
        hour_cond(lambda e: digits(C - 65, size, e, PRIMARY, F_TEXT), zero12=True),
        digits(C + 65, size, "[MINUTE_Z]", PRIMARY, F_TEXT),
    ])
    amb = "\n".join([
        hour_cond(lambda e: ghost(C - 65, size, e, AMB_HI, F_TEXT), zero12=True),
        ghost(C + 65, size, "[MINUTE_Z]", AMB_HI, F_TEXT),
    ])
    return pair("stacked", active, amb)


def s_numeral():
    cy, r, size = C, 112, 88
    nums = "\n".join([
        digits(cy - r, size, "12", PRIMARY, F_HEAVY),
        digits(cy + r, size, "6", PRIMARY, F_HEAVY),
        digits(cy, size, "3", SOFT, F_HEAVY, C + r - 80, 160),
        digits(cy, size, "9", SOFT, F_HEAVY, C - r - 80, 160),
    ])
    over = "\n".join([
        hand(74, 24, HOUR_ANGLE, PRIMARY, cy=cy),
        hand(142, 6, MINUTE_ANGLE, SOFT, cy=cy),
    ])
    amb = "\n".join([
        ghost(cy - r, size, "12", AMB_LO, F_HEAVY), ghost(cy + r, size, "6", AMB_LO, F_HEAVY),
        ghost(cy, size, "3", AMB_LO, F_HEAVY, C + r - 80, 160), ghost(cy, size, "9", AMB_LO, F_HEAVY, C - r - 80, 160),
        ghost_hand(74, 24, HOUR_ANGLE, AMB_HI, cy),
        hand(142, 4, MINUTE_ANGLE, AMB_HI, cy=cy),
    ])
    return pair("numeral", nums, amb), over_layer("numeral_hands", over)


def s_day():
    """Outline: outlined pill hour hand and a thin minute hand, four quiet marks at 12/3/6/9.
    (Was 'Day'; its date chip went because the shared info line already shows the date.)"""
    marks = lambda col: draw("\n  ".join(dot(C + 192 * dx, C + 192 * dy, 3, col)
                                          for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))))
    over = "\n".join([
        hand(100, 22, HOUR_ANGLE, DIAL),
        hand(100, 22, HOUR_ANGLE, PRIMARY, stroke=4),
        hand(178, 6, MINUTE_ANGLE, SOFT),
    ])
    amb = "\n".join([
        marks(AMB_LO),
        ghost_hand(100, 22, HOUR_ANGLE, AMB_HI),
        hand(178, 4, MINUTE_ANGLE, AMB_HI),
    ])
    return pair("day", marks(MUTED), amb), over_layer("day_hands", over)


def s_clover():
    """Soft four-leaf clover dial: four lobes on 12/3/6/9 over a disc that fills the notches,
    sized to clear the info rows; four quiet marks and slim hands."""
    def clover(color, inset=0):
        return "\n  ".join([dot(C, C, 100 - inset, color)] + [
            dot(C + 56 * dx, C + 56 * dy, 74 - inset, color) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))])
    marks = lambda col: "\n  ".join(dot(C + 106 * dx, C + 106 * dy, 4, col)
                                    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)))
    over = "\n".join([
        hand(62, 18, HOUR_ANGLE, PRIMARY),
        hand(100, 7, MINUTE_ANGLE, SOFT),
    ])
    amb = "\n".join([
        draw("\n  ".join([clover(AMB_LO), clover(BLACK, 2), marks(AMB_LO)])),
        ghost_hand(62, 18, HOUR_ANGLE, AMB_HI),
        hand(100, 4, MINUTE_ANGLE, AMB_HI),
    ])
    return pair("clover", draw(clover(DIAL) + "\n  " + marks(MUTED)), amb), over_layer("clover_hands", over)


def s_bubble():
    """Four overlapping tonal bubbles in a 2x2 grid, one digit in each (hours on top),
    checkerboard tones, sized to clear the info rows."""
    r, d, size = 70, 62, 96
    cells = [(-1, -1, HOUR_T), (1, -1, HOUR_O), (-1, 1, MIN_T), (1, 1, MIN_O)]
    tone = [(CONTAINER, SOFT), (PRIMARY, DIAL), (PRIMARY, DIAL), (CONTAINER, SOFT)]
    bubble = lambda k, col, inset=0: dot(C + d * cells[k][0], C + d * cells[k][1], r - inset, col)
    num = lambda k, col, mk=digits: mk(C + d * cells[k][1], size, cells[k][2], col, F_HEAVY,
                                        C + d * cells[k][0] - r, 2 * r)
    active = "\n".join([draw("\n  ".join(bubble(k, tone[k][0]) for k in range(4)))] +
                       [num(k, tone[k][1]) for k in range(4)])
    amb = "\n".join([draw("\n  ".join(bubble(k, AMB_LO) + "\n  " + bubble(k, BLACK, 2) for k in range(4)))] +
                    [num(k, AMB_HI if k in (1, 2) else AMB_LO,
                         lambda cy, sz, e, col, fam, x, w: ghost(cy, sz, e, col, fam, x, w, "CENTER", 2))
                     for k in range(4)])
    return pair("bubble", active, amb)


def s_arc():
    """Digital time inside a rim track; an accent arc fills with the minutes and a dot rides its tip."""
    r, t = 196, 10
    box = f'x="{C - r}" y="{C - r}" width="{2 * r}" height="{2 * r}"'
    track = lambda col: f'<Ellipse {box}><Stroke color="{col}" thickness="{t}" /></Ellipse>'
    arc = lambda col, th: (f'<Arc centerX="{C}" centerY="{C}" width="{2 * r}" height="{2 * r}" startAngle="0" endAngle="0">'
                          f'<Transform target="endAngle" value="([MINUTE] + [SECOND] / 60) * 6" />'
                          f'<Stroke color="{col}" thickness="{th}" cap="ROUND" /></Arc>')
    tip = lambda col, rr: f'''<PartDraw x="0" y="0" width="{W}" height="{W}" pivotX="0.5" pivotY="0.5">
  <Transform target="angle" value="([MINUTE] + [SECOND] / 60) * 6" />
  {dot(C, C - r, rr, col)}
</PartDraw>'''
    active = "\n".join([draw(track(DIAL) + "\n  " + arc(ACCENT, t)), tip(SOFT, 9),
                        time_line(C, 100, F_MED, PRIMARY, MUTED, SOFT, 32)])
    amb = "\n".join([draw(arc(AMB_LO, 2)), tip(AMB_HI, 5),
                     time_line(C, 100, F_MED, AMB_HI, AMB_COLON, AMB_HI, 32, dig=ghost)])
    return pair("arc", active, amb)


def s_tile():
    """A rounded square tile in the deep tone holding stacked hours and minutes."""
    side, rad, size = 236, 76, 100
    tile = lambda paint: (f'<RoundRectangle x="{C - side // 2}" y="{C - side // 2}" width="{side}" height="{side}" '
                          f'cornerRadiusX="{rad}" cornerRadiusY="{rad}">{paint}</RoundRectangle>')
    active = "\n".join([
        draw(tile(f'<Fill color="{CONTAINER}" />')),
        hour_cond(lambda e: digits(C - 50, size, e, PRIMARY, F_HEAVY), zero12=True),
        digits(C + 50, size, "[MINUTE_Z]", SOFT, F_HEAVY),
    ])
    amb = "\n".join([
        draw(tile(f'<Stroke color="{AMB_LO}" thickness="2" />')),
        hour_cond(lambda e: ghost(C - 50, size, e, AMB_HI, F_HEAVY), zero12=True),
        ghost(C + 50, size, "[MINUTE_Z]", AMB_LO, F_HEAVY),
    ])
    return pair("tile", active, amb)


def s_sunny():
    """Analog on a bright eight-point soft burst, with dark hands: the light-dial sibling of Cookie and Clover."""
    def burst(color, inset=0):
        return "\n  ".join([dot(C, C, 116 - inset, color)] + [
            dot(C + 100 * math.sin(k * math.pi / 4), C - 100 * math.cos(k * math.pi / 4), 38 - inset, color)
            for k in range(8)])
    over = "\n".join([
        hand(62, 18, HOUR_ANGLE, CONTAINER),
        hand(102, 8, MINUTE_ANGLE, DIAL),
    ])
    amb = "\n".join([
        draw(burst(AMB_LO) + "\n  " + burst(BLACK, 2)),
        ghost_hand(62, 18, HOUR_ANGLE, AMB_HI),
        hand(102, 4, MINUTE_ANGLE, AMB_HI),
    ])
    return pair("sunny", draw(burst(PRIMARY)), amb), over_layer("sunny_hands", over)


MIN_FRAC = "([MINUTE] + [SECOND] / 60) * 6"


def wave_ring(R, amp, waves, color, stroke, steps=240):
    """A closed wavy ring (M3E wavy progress) as short round-capped line segments."""
    pts = []
    for i in range(steps + 1):
        a = 2 * math.pi * i / steps
        r = R + amp * math.sin(waves * a)
        pts.append((C + r * math.sin(a), C - r * math.cos(a)))
    return "\n  ".join(
        f'<Line startX="{x1:.1f}" startY="{y1:.1f}" endX="{x2:.1f}" endY="{y2:.1f}">'
        f'<Stroke color="{color}" thickness="{stroke}" cap="ROUND" /></Line>'
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]))


def arc_from(R, start_expr, color, thickness, gap=0):
    """Arc from an expression angle round to 12 o'clock (the not-yet-elapsed part)."""
    start = f"{start_expr} + {gap}" if gap else start_expr
    return (f'<Arc centerX="{C}" centerY="{C}" width="{2 * R}" height="{2 * R}" startAngle="0" endAngle="360">'
            f'<Transform target="startAngle" value="{start}" />'
            f'<Stroke color="{color}" thickness="{thickness}" cap="ROUND" /></Arc>')


def s_wavy():
    """M3E wavy progress round the rim: the elapsed minutes are a wave, the rest a flat track
    after a small gap; heavy rounded time in the middle."""
    R, amp, n = 194, 5, 20
    def ring(wave_col, wave_w, track_col):
        body = [wave_ring(R, amp, n, wave_col, wave_w), arc_from(R, MIN_FRAC, BLACK, 2 * amp + wave_w + 8)]
        if track_col:
            body.append(arc_from(R, MIN_FRAC, track_col, 4, gap=8))
        return draw("\n  ".join(body))
    active = "\n".join([ring(ACCENT, 6, DIAL), time_line(C, 84, F_HEAVY, PRIMARY, MUTED, SOFT, 28)])
    amb = "\n".join([ring(AMB_LO, 2, None),
                     time_line(C, 84, F_HEAVY, AMB_HI, AMB_COLON, AMB_HI, 28, dig=ghost)])
    return pair("wavy", active, amb)


def m3_shapes(color, inset=0):
    """Six M3 Expressive shapes (each within r 135 so it clears the info rows)."""
    def blob(disc, lobes, rc, r, phase=0.0):
        return ([dot(C, C, disc - inset, color)] if disc else []) + [
            dot(C + rc * math.sin(phase + 2 * math.pi * k / lobes), C - rc * math.cos(phase + 2 * math.pi * k / lobes),
                r - inset, color) for k in range(lobes)]
    pill = (f'<RoundRectangle x="{C - 128 + inset}" y="{C - 86 + inset}" width="{256 - 2 * inset}" height="{172 - 2 * inset}" '
            f'cornerRadiusX="{86 - inset}" cornerRadiusY="{86 - inset}"><Fill color="{color}" /></RoundRectangle>')
    return [
        [dot(C, C, 122 - inset, color)],              # circle
        blob(100, 4, 44, 88, math.pi / 4),            # soft square (4-leaf cookie)
        blob(108, 8, 98, 34),                         # sunny
        [pill],                                       # pill
        blob(104, 6, 92, 42),                         # 6-sided cookie
        blob(0, 4, 54, 78),                           # clover
    ]


def s_morph():
    """M3E shape morph: the hour sits in one of six expressive shapes that changes every hour
    and turns once an hour; stacked heavy time on top."""
    def shapes(make):
        sets = [make(k) for k in range(6)]
        exprs = "".join(f'<Expression name="m{k}"><![CDATA[[HOUR_0_11] % 6 == {k}]]></Expression>' for k in range(1, 6))
        compares = "".join(f'<Compare expression="m{k}">{sets[k]}</Compare>' for k in range(1, 6))
        return f"<Condition>\n  <Expressions>{exprs}</Expressions>\n  {compares}\n  <Default>{sets[0]}</Default>\n</Condition>"
    def spin(body):
        return (f'<PartDraw x="0" y="0" width="{W}" height="{W}" pivotX="0.5" pivotY="0.5">\n'
                f'  <Transform target="angle" value="[MINUTE] * 6" />\n  {body}\n</PartDraw>')
    on = shapes(lambda k: spin("\n  ".join(m3_shapes(PRIMARY)[k])))
    off = shapes(lambda k: spin("\n  ".join(m3_shapes(AMB_LO)[k] + m3_shapes(BLACK, 2)[k])))
    size = 84
    active = "\n".join([on,
        hour_cond(lambda e: digits(C - 44, size, e, CONTAINER, F_HEAVY), zero12=True),
        digits(C + 44, size, "[MINUTE_Z]", DIAL, F_HEAVY)])
    amb = "\n".join([off,
        hour_cond(lambda e: ghost(C - 44, size, e, AMB_HI, F_HEAVY), zero12=True),
        ghost(C + 44, size, "[MINUTE_Z]", AMB_LO, F_HEAVY)])
    return pair("morph", active, amb)


def ticks(r, color, big=4, small=0, rs=None):
    """12 hour dots on radius r (and optionally 48 minute dots on rs)."""
    out = []
    for k in range(60):
        a = 2 * math.pi * k / 60
        if k % 5 == 0:
            out.append(dot(C + r * math.sin(a), C - r * math.cos(a), big, color))
        elif small:
            out.append(dot(C + (rs or r) * math.sin(a), C - (rs or r) * math.cos(a), small, color))
    return "\n  ".join(out)


def s_hybrid():
    """Slim tonal hands behind a bright digital time, hour dots on the rim."""
    active = "\n".join([
        draw(ticks(204, MUTED, 3)),
        hand(112, 30, HOUR_ANGLE, MUTED),
        hand(192, 16, MINUTE_ANGLE, CONTAINER),
        time_line(C, 104, F_MED, SOFT, ACCENT, SOFT, 34),
    ])
    amb = "\n".join([
        draw(ticks(204, AMB_LO, 3)),
        ghost_hand(112, 30, HOUR_ANGLE, AMB_LO),
        ghost_hand(192, 16, MINUTE_ANGLE, AMB_LO),
        time_line(C, 104, F_MED, AMB_HI, AMB_COLON, AMB_HI, 34, dig=ghost),
    ])
    return pair("hybrid", active, amb)


BUILDERS = [s_sticker, s_cookie, s_narrow, s_thin, s_line, s_pill,
            s_stacked, s_numeral, s_day, s_clover, s_bubble, s_hybrid,
            s_arc, s_tile, s_sunny, s_wavy, s_morph]


def ring():
    """Optional low-profile analogue time behind every style: rim hour dots, an hour pip and a minute dot."""
    def pip(r, length, width, angle, color):
        return f'''<PartDraw x="0" y="0" width="{W}" height="{W}" pivotX="0.5" pivotY="0.5">
  <Transform target="angle" value="{angle}" />
  <RoundRectangle x="{C - width / 2}" y="{C - r - length / 2}" width="{width}" height="{length}" cornerRadiusX="{width / 2}" cornerRadiusY="{width / 2}"><Fill color="{color}" /></RoundRectangle>
</PartDraw>'''
    def body(tick, hour, minute):
        return "\n".join([draw(ticks(216, tick, 2)), pip(216, 22, 6, HOUR_ANGLE, hour), pip(216, 10, 10, MINUTE_ANGLE, minute)])
    return pair("ring", body(MUTED, MUTED, PRIMARY), body("#FF4A4A4A", AMB_LO, AMB_HI))


def layers(b):
    """(under the chips, over the chips) for a style."""
    r = b()
    return r if isinstance(r, tuple) else (r, "")


# ---------- complications ----------

DATE_TOP_CY, STATS_CY = 66, 384            # layout 0: date + weather on top, steps + battery at the bottom
INFO_CY, LINE2_CY = 372, 400                # layout 1: date + weather, then steps + battery
DATE_END = C + 22                           # layout 1: date END-aligned here, weather follows


def battery(x, cy, tone, fill, charge):
    """Small drawn battery at x (fill follows the level, `charge` colour while charging), then the percentage."""
    bw, bh = 22, 12
    y = cy - bh // 2
    fill_rect = lambda col: (f'<RoundRectangle x="{x + 2}" y="{y + 2}" width="{bw - 4}" height="{bh - 4}" cornerRadiusX="1.5" cornerRadiusY="1.5">'
                             f'<Transform target="width" value="{bw - 4} * [BATTERY_PERCENT] / 100" /><Fill color="{col}" /></RoundRectangle>')
    body = (f'<RoundRectangle x="{x}" y="{y}" width="{bw}" height="{bh}" cornerRadiusX="3" cornerRadiusY="3"><Stroke color="{tone}" thickness="1.5" /></RoundRectangle>\n  '
            f'<RoundRectangle x="{x + bw + 1}" y="{cy - 2.5}" width="2.5" height="5" cornerRadiusX="1" cornerRadiusY="1"><Fill color="{tone}" /></RoundRectangle>')
    level = f'''<Condition>
  <Expressions><Expression name="chg"><![CDATA[[BATTERY_CHARGING_STATUS]]]></Expression></Expressions>
  <Compare expression="chg">{draw(fill_rect(charge))}</Compare>
  <Default>{draw(fill_rect(fill))}</Default>
</Condition>'''
    pct = text(x + bw + 8, cy - 13, 70, 26, "%s%%", ["[BATTERY_PERCENT]"], 20, tone, align="START")
    return "\n".join([draw(body), level, pct])


def steps(x, cy, tone, icon):
    """Two little footprints, then the built-in step count."""
    def foot(fx, fy):
        return (f'<Ellipse x="{fx}" y="{fy}" width="6" height="8.5"><Fill color="{icon}" /></Ellipse>'
                + dot(fx + 3, fy + 11.5, 2.4, icon))
    feet = foot(x + 1, cy - 11) + foot(x + 9, cy - 6)
    return draw(feet) + "\n" + text(x + 20, cy - 13, 80, 26, "%s", ["[STEP_COUNT]"], 20, tone, align="START")


SUN = "#FFFFC94A"
HEART = "#FFFF6F7D"


def heart(x, cy, tone, icon):
    """Drawn heart (two lobes and a V), then the built-in heart rate; '--' until there is a reading.
    Needs BODY_SENSORS, which the watch asks the user to allow."""
    v = lambda x1: (f'<Line startX="{x1}" startY="{cy - 1.5}" endX="{x + 7.5}" endY="{cy + 5}">'
                    f'<Stroke color="{icon}" thickness="4.5" cap="ROUND" /></Line>')
    shape = dot(x + 4.5, cy - 3, 3.4, icon) + dot(x + 10.5, cy - 3, 3.4, icon) + v(x + 2.4) + v(x + 12.6) + dot(x + 7.5, cy - 0.5, 3, icon)
    return draw(shape) + f'''
<Condition>
  <Expressions><Expression name="hr"><![CDATA[[HEART_RATE] > 0]]></Expression></Expressions>
  <Compare expression="hr">{text(x + 20, cy - 13, 60, 26, "%s", ["[HEART_RATE]"], 20, tone, align="START")}</Compare>
  <Default>{text(x + 20, cy - 13, 60, 26, "--", [], 20, tone, align="START")}</Default>
</Condition>'''


def weather_icon(ox, cy, cloud, sun, drop):
    """18 px drawn weather glyph picked by [WEATHER.CONDITION] (WFF codes: 1 clear, 2 cloudy,
    3 fog, 4 heavy rain, 5 heavy snow, 6 rain, 7 snow, 8 sunny, 9 storm, 10 sleet, 11 light snow,
    12 light rain, 13 mist, 14 partly cloudy)."""
    oy = cy - 9
    def cl(dy=0, col=cloud):
        return (dot(ox + 6, oy + 11 + dy, 4.5, col) + dot(ox + 11, oy + 8 + dy, 6, col)
                + f'<RoundRectangle x="{ox + 2}" y="{oy + 10 + dy}" width="15" height="6" cornerRadiusX="3" cornerRadiusY="3"><Fill color="{col}" /></RoundRectangle>')
    def drops(n=3):
        return "".join(f'<RoundRectangle x="{ox + 4 + 4.5 * k}" y="{oy + 14}" width="1.8" height="4.5" cornerRadiusX="0.9" cornerRadiusY="0.9"><Fill color="{drop}" /></RoundRectangle>' for k in range(n))
    def flakes():
        return "".join(dot(ox + 4.5 + 4.5 * k, oy + 16, 1.4, drop) for k in range(3))
    bolt = (f'<Line startX="{ox + 10}" startY="{oy + 12}" endX="{ox + 7.5}" endY="{oy + 16}"><Stroke color="{sun}" thickness="1.8" cap="ROUND" /></Line>'
            f'<Line startX="{ox + 7.5}" startY="{oy + 16}" endX="{ox + 11}" endY="{oy + 16}"><Stroke color="{sun}" thickness="1.8" cap="ROUND" /></Line>'
            f'<Line startX="{ox + 11}" startY="{oy + 16}" endX="{ox + 8.5}" endY="{oy + 19}"><Stroke color="{sun}" thickness="1.8" cap="ROUND" /></Line>')
    glyphs = [
        ("[WEATHER.CONDITION] == 1 || [WEATHER.CONDITION] == 8", dot(ox + 9, cy, 6.5, sun)),
        ("[WEATHER.CONDITION] == 14", dot(ox + 7, oy + 6, 5, sun) + cl(1)),
        ("[WEATHER.CONDITION] == 4 || [WEATHER.CONDITION] == 6 || [WEATHER.CONDITION] == 10 || [WEATHER.CONDITION] == 12", cl(-4) + drops()),
        ("[WEATHER.CONDITION] == 5 || [WEATHER.CONDITION] == 7 || [WEATHER.CONDITION] == 11", cl(-4) + flakes()),
        ("[WEATHER.CONDITION] == 9", cl(-4) + bolt),
    ]
    exprs = "".join(f'<Expression name="w{i}"><![CDATA[{e}]]></Expression>' for i, (e, _) in enumerate(glyphs))
    compares = "".join(f'<Compare expression="w{i}">{draw(g)}</Compare>' for i, (_, g) in enumerate(glyphs))
    return f'''<Condition>
  <Expressions>{exprs}</Expressions>
  {compares}
  <Default>{draw(cl())}</Default>
</Condition>'''


def weather(x, cy, tone, cloud, sun, drop):
    """Drawn condition icon at x and the temperature; '--' until the watch has weather."""
    return f'''<Condition>
  <Expressions><Expression name="wx"><![CDATA[[WEATHER.IS_AVAILABLE]]]></Expression></Expressions>
  <Compare expression="wx">{weather_icon(x, cy, cloud, sun, drop)}
{text(x + 22, cy - 13, 70, 26, "%s°", ["[WEATHER.TEMPERATURE]"], 20, tone, align="START")}</Compare>
  <Default>{text(x + 22, cy - 13, 70, 26, "--", [], 20, tone, align="START")}</Default>
</Condition>'''


def info():
    """Shared by every style, picked by the single Scene-level "Info" option:
      0 Minimal (default)  'Tue, 17 Nov' under the clock
      1 Date + weather     'Tue, 17 Nov (weather) 30°' under the clock
      2 Full               date + weather on top, 'steps  heart rate  battery' at the bottom
      3 Full, bottom       date + weather, then steps / heart rate / battery, both at the bottom
      4 Off                time only
    Weather always sits right after the date. Everything is built in (WFF v2 weather, step count,
    heart rate), so nothing here is a complication slot."""
    def body(tone, cloud, sun, drop, fill, charge, foot, hr):
        date_txt = lambda cy, x, w, align: text(x, cy - 13, w, 26, "%s, %s %s",
                                               ["[DAY_OF_WEEK_S]", "[DAY]", "[MONTH_S]"], 20, tone, align=align)
        top = "\n".join([
            date_txt(DATE_TOP_CY, DATE_END - 200, 200, "END"),
            weather(DATE_END + 8, DATE_TOP_CY, tone, cloud, sun, drop),
            steps(C - 118, STATS_CY, tone, foot),
            heart(C - 36, STATS_CY, tone, hr),
            battery(C + 40, STATS_CY, tone, fill, charge),
        ])
        bottom = "\n".join([
            date_txt(INFO_CY, DATE_END - 200, 200, "END"),
            weather(DATE_END + 8, INFO_CY, tone, cloud, sun, drop),
            steps(C - 118, LINE2_CY, tone, foot),
            heart(C - 36, LINE2_CY, tone, hr),
            battery(C + 40, LINE2_CY, tone, fill, charge),
        ])
        minimal = date_txt(STATS_CY, C - 150, 300, "CENTER")
        date_wx = "\n".join([
            date_txt(STATS_CY, DATE_END - 200, 200, "END"),
            weather(DATE_END + 8, STATS_CY, tone, cloud, sun, drop),
        ])
        return minimal, date_wx, top, bottom
    active = body(SOFT, SOFT, SUN, PRIMARY, PRIMARY, ACCENT, PRIMARY, HEART)
    amb = body(AMB_LO, AMB_LO, AMB_HI, AMB_LO, AMB_LO, AMB_HI, AMB_LO, AMB_LO)
    opts = [pair(f"info{i}", active[i], amb[i]) for i in range(4)] + [EMPTY]
    return choose("info", opts, LAYOUT_FIXED)


# ---------- backgrounds ----------

def layer_draw(body, alpha=255):
    return f'<PartDraw x="0" y="0" width="{W}" height="{W}" alpha="{alpha}">\n  {body}\n</PartDraw>'


def backgrounds(dark, deep):
    """Vector wallpapers drawn in the current theme's colours, so the time and hands always match.
    dark = the theme's dark tonal colour, deep = its saturated container colour."""
    glow = "\n".join(layer_draw(dot(C, C, r, deep), 11) for r in range(228, 20, -11))
    blobs = "\n".join([
        layer_draw(dot(C - 120, C - 130, 170, dark)),
        layer_draw(dot(C + 140, C + 110, 185, deep), 110),
        layer_draw(dot(C - 70, C + 200, 120, dark), 200),
    ])
    horizon = "\n".join([
        layer_draw(dot(C, C + 360, 320, dark)),
        layer_draw(dot(C, C + 420, 320, deep), 130),
    ])
    rings = layer_draw("\n  ".join(
        f'<Arc centerX="{C}" centerY="{C}" width="{2 * r}" height="{2 * r}" startAngle="0" endAngle="360">'
        f'<Stroke color="{dark}" thickness="10" /></Arc>' for r in range(70, 230, 34)), 150)
    dots = []
    for row in range(26):
        y = 9 + row * 18
        r = 3.6 * max(0.0, (y - 150) / 300)
        if r < 0.7:
            continue
        for col in range(26):
            x = 9 + col * 18 + (9 if row % 2 else 0)
            if (x - C) ** 2 + (y - C) ** 2 < (C + 6) ** 2:
                dots.append(dot(x, y, round(r, 1), deep))
    dither = layer_draw("\n  ".join(dots), 200)
    return [glow, blobs, horizon, rings, dither]


BACKGROUNDS = ["bg_none", "bg_glow", "bg_blobs", "bg_horizon", "bg_rings", "bg_dither", "bg_photo"]
BG_FIXED = None  # --bg N bakes background N in (screenshots)


def photo_bg():
    """WFF Photos element: a photo picked in the companion app's customise screen."""
    return (f'<PartImage x="0" y="0" width="{W}" height="{W}">\n'
            f'  <Photos source="[CONFIGURATION.photo]" defaultImageResource="photo_default" change="TAP" />\n'
            f'</PartImage>\n'
            + layer_draw(f'<Rectangle x="0" y="0" width="{W}" height="{W}"><Fill color="#FF000000" /></Rectangle>', 90))


def background():
    """Scene-level Background option, behind everything; hidden in always-on and power saver."""
    opts = [EMPTY] + [group(f"bg{i + 1}", saver(b, EMPTY)) for i, b in enumerate(backgrounds(DIAL, CONTAINER))]
    opts.append(group("bg_photo", saver(photo_bg(), EMPTY)))
    if BG_FIXED is not None:
        return opts[BG_FIXED]
    return choose("background", opts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--default", type=int, default=0)
    ap.add_argument("--only", type=int)
    ap.add_argument("--amb", action="store_true", help="show the always-on layer while active (screenshots)")
    ap.add_argument("--saver", type=int, help="bake power saver option N in (0 off, 1 on)")
    ap.add_argument("--ring", type=int, choices=[0, 1], help="bake the analog ring on/off in")
    ap.add_argument("--layout", type=int, choices=range(5), help="bake Info option N in")
    ap.add_argument("--bg", type=int, choices=range(len(BACKGROUNDS)), help="bake background N in")
    a = ap.parse_args()
    global AMB_PREVIEW, SAVER_FIXED, LAYOUT_FIXED, BG_FIXED
    BG_FIXED = a.bg
    LAYOUT_FIXED = a.layout
    AMB_PREVIEW = a.amb
    SAVER_FIXED = a.saver

    colors = "\n".join(
        f'<ColorOption id="{i}" displayName="{n}" colors="{" ".join(cs)}" />'
        for i, (n, *cs) in enumerate(THEMES))
    # Declaring a PhotosConfiguration with no <Photos> element in the scene makes Samsung's runtime
    # fail to build the face (NullPointerException in WatchFaceDocument), so declare it only when used.
    photo_cfg = ('<PhotosConfiguration id="photo" configType="SINGLE" />\n'
                 if a.bg is None or a.bg == len(BACKGROUNDS) - 1 else "")
    bg_opts = "\n".join(f'<ListOption id="{i}" displayName="{n}" />' for i, n in enumerate(BACKGROUNDS))
    list_opts = "\n".join(f'<ListOption id="{i}" displayName="{n}" />' for i, n in enumerate(STYLES))
    if a.only is not None:
        styles = "\n".join(layers(BUILDERS[a.only]))
    else:
        styles = choose("style", ["\n".join(layers(bld)) for bld in BUILDERS])
    if a.ring is not None:
        bg = ring() if a.ring else ""
    else:
        bg = (f'<BooleanConfiguration id="ring">\n<BooleanOption id="TRUE">\n{ring()}\n</BooleanOption>\n'
              f'<BooleanOption id="FALSE">{EMPTY}</BooleanOption>\n</BooleanConfiguration>')
    # Each configuration appears exactly once and none sits inside another (Samsung's editor
    # throws ConcurrentModificationException when an option change touches nested ones).
    scene = f"{background()}\n{bg}\n{styles}\n{info()}"

    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by gen.py; edit that instead. -->
<WatchFace width="{W}" height="{W}">
<Metadata key="CLOCK_TYPE" value="DIGITAL" />
<Metadata key="PREVIEW_TIME" value="10:08:32" />
<UserConfigurations>
<ListConfiguration id="style" displayName="style_label" defaultValue="{a.default}">
{list_opts}
</ListConfiguration>
<ColorConfiguration id="theme" displayName="theme_label">
{colors}
</ColorConfiguration>
<BooleanConfiguration id="ring" displayName="ring_label" defaultValue="FALSE" />
<ListConfiguration id="background" displayName="bg_label" defaultValue="0">
{bg_opts}
</ListConfiguration>
{photo_cfg}<ListConfiguration id="info" displayName="info_label" defaultValue="0">
<ListOption id="0" displayName="info_min" />
<ListOption id="1" displayName="info_wx" />
<ListOption id="2" displayName="info_full" />
<ListOption id="3" displayName="info_bottom" />
<ListOption id="4" displayName="info_off" />
</ListConfiguration>
</UserConfigurations>
<Scene backgroundColor="#FF000000">
{scene}
</Scene>
</WatchFace>
'''
    out = Path(__file__).parent / "res/raw/watchface.xml"
    out.write_text(xml)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
