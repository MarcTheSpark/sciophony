"""
cantor_beam_linger_scroll3.py — an endless self-similar zoom with scheduled beams.

A variant of cantor_beam_linger_scroll2.py. There the figure took a single
self-similar step: one 3x horizontal zoom onto its right-hand third, paired
with a one-row vertical scroll. Here that step simply never stops:

  - the figure stretches horizontally by 3x every HZOOM_TRIPLING_TIME seconds
    (8 by default), at a perfectly steady geometric rate, homing in on the
    right-hand end of the Cantor set (the same fixed point as scroll2's step:
    its right edge stays put on screen while everything else grows leftward);
  - the camera scrolls down SCROLL_ROWS_PER_TRIPLING rows (1) per tripling, so
    after every tripling the picture is the same as it was one tripling
    earlier, one generation deeper — an endless fractal dive.

Beams no longer come from a hand-timed list. A new full beam fires every
BEAM_INTERVAL seconds (10), each in the next colour of BEAM_COLORS (yellow,
blue, then the rest of the palette). Like the original single cantor_beam,
every full beam starts on row 0 of the whole figure and works its way down row
by row. It reaches a new row every BEAM_ROW_PERIOD seconds (4), faster than
the scroll's one row per 8 s, so a beam that starts after row 0 has scrolled
away runs unseen until it overtakes the scroll and comes in at the top. It
then descends the screen until it drops off the bottom, overlapping the beams
before and after it. Extra hand-placed beams can still be added to
EXTRA_BEAMS.

The row timing is the steady state of the Cantor tempo curve that
scantimes.py follows (row n spans beats [2·3^(n-1), 3^n] of a curve whose
tempo triples every BEAM_ROW_PERIOD): each row takes BEAM_ROW_PERIOD·log3(1.5)
seconds to sweep, accelerating so it is 1.5x faster at the end than at the
start, followed by a rest. Written in closed form, it carries on for
unboundedly many rows (scantimes' tempo curve stops after 17).

Each row is swept with the classic cantor_beam geometry (centre→out on a solid
bar, then alternating outer→inner / inner→outer, jumping the gaps), but
measured in the sub-figure that fits on screen when that row's sweep ends, so
the sweep stays in view however deep the zoom has gone. It keeps the lingering
fill of the earlier versions: a LINGER_ALPHA trail that fades over
LINGER_FADE_TIME.

Rendering an endless zoom
-------------------------
The figure triples in width every 8 seconds, so it cannot be drawn as one
full-width pattern (after 100 s it would be ~10^5 frames wide). Instead each
frame is drawn relative to the deepest sub-figure S_m = [1 - 3^-m, 1] that
still covers the frame's left edge: S_m is a complete Cantor set, row L of the
whole figure is row L - m of S_m, and rows above S_m are solid across the
frame. S_m is never more than ~3.2 pattern-widths wide, so the per-frame cost
stays constant forever and nothing loses float precision.

Every row is drawn from its exact area coverage per pixel column (the measure
of the Cantor level inside each column, from a cumulative-measure table), so
the bars are antialiased, deep rows fade naturally as their bars shrink below
a pixel ((2/3)^n of the light survives per generation), and switching from S_m
to S_m+1 is seamless. Each row is computed as a single 1-pixel line and
stretched to bar height in C, which keeps the per-frame numpy work small.

Construction mirrors the earlier versions: PygameRecorder, supersampled
rendering, --render/--no-render CLI flag, optional soundtrack.
"""

import argparse
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
import pygame

from pygame_recorder import PygameRecorder


# --- Display ---
WIDTH, HEIGHT = 1920, 1080
FPS = 60
SUPERSAMPLE = 4
INTERNAL_W = WIDTH * SUPERSAMPLE
INTERNAL_H = HEIGHT * SUPERSAMPLE


# --- Soundtrack ---
# Audio played under the animation. In interactive playback it plays live via
# pygame.mixer; in render mode it is muxed into the finished MP4 by ffmpeg. The
# path is resolved relative to the current directory and then to this script's
# own folder. Set to None (or pass --no-soundtrack) to run silently; override
# the file with --soundtrack PATH.
SOUNDTRACK = "InfinitySoundtrack.mp3"

# Time (seconds into the animation) at which the soundtrack begins. Before it
# the animation runs silently.
SOUNDTRACK_START_TIME = 3.0


# --- Colors ---
BG_COLOR = (10, 10, 10)
BAR_COLOR = (50, 50, 50)


# --- Scheduled beams ---
# Full beam n fires at BEAM_FIRST_TIME + n * BEAM_INTERVAL, in colour
# BEAM_COLORS[n % len(BEAM_COLORS)], entering row 0 of the whole figure and
# continuing down one row every BEAM_ROW_PERIOD seconds for BEAM_NUM_ROWS rows
# (None = until it drops off the bottom of the screen). Row 0 has usually
# scrolled off the top by then, so a beam runs unseen until it catches up with
# the scroll and comes in at the top of the screen.
BEAM_FIRST_TIME = 5.0
BEAM_INTERVAL = 10.0
BEAM_NUM_ROWS = None

# The first two are scroll2's yellow and blue; the rest continue the cycle.
BEAM_COLORS = [
    (255, 230, 90),     # yellow
    (20, 100, 250),     # blue
    (255, 70, 150),     # pink
    (60, 220, 120),     # green
    (255, 140, 40),     # orange
    (160, 90, 255),     # violet
    (40, 210, 230),     # cyan
    (250, 60, 60),      # red
]

# Seconds between a full beam entering one row and the next (the tripling time
# of its tempo curve). Each row's sweep takes BEAM_ROW_PERIOD * log3(1.5)
# (~37%) of it, the rest is the Cantor rest. 4 s is the project's usual
# tripling_time (scaling_factor 2.409...); scroll2's beam used ~10 s, but here
# it has to outpace the scroll (one row per HZOOM_TRIPLING_TIME / rows per
# tripling = 8 s) or the beams would slide off the top of the screen.
BEAM_ROW_PERIOD = 4.0

# Which sub-figure a row's sweep geometry is measured in. 0: the one that fits
# on screen when the sweep ends — rows get the classic mirrored pair of beams
# (or centre→out on a solid bar). 1: its parent, of which only the right third
# is on screen — a single beam crosses the row, like the late rows of scroll2.
BEAM_FRAME_OFFSET = 0

# Extra hand-placed full beams, drawn on top of the schedule. Each entry is
#   (color (r,g,b), start_time seconds, row_period seconds, start_row,
#    num_rows or None)
EXTRA_BEAMS = []


# --- Lingering fill ---
# Opacity of the trail left behind after the beam passes, as a fraction of
# full brightness (0 = no trail, 1 = trail as bright as the beam's peak).
LINGER_ALPHA = 0.5

# Seconds over which a finished row's lingering trail fades back to black,
# measured from the moment the beam finishes sweeping that row. Set to 0 (or
# None) to disable fading and leave the trail at LINGER_ALPHA.
LINGER_FADE_TIME = 2.


# --- Layout (fractions of frame) ---
# At t = 0 the figure sits where scroll2's did; the zoom keeps its right edge
# (PATTERN_LEFT_FRAC + PATTERN_WIDTH_FRAC) fixed on screen.
PATTERN_LEFT_FRAC = 0.06
PATTERN_WIDTH_FRAC = 0.88
ROW_TOP_FRAC = 0.10
ROW_SPACING_FRAC = 0.115
BAR_HEIGHT_FRAC = 0.038

# Deepest Cantor level ever evaluated (2**level segments). Rows deeper than
# this are far below a pixel and are drawn as this level.
MAX_LEVEL = 16


# --- Endless zoom + scroll ---
# Seconds for each 3x horizontal stretch. The scroll advances
# SCROLL_ROWS_PER_TRIPLING rows in the same time; 1 makes the motion exactly
# self-similar. The zoom holds still until HZOOM_START_TIME and the scroll until
# SCROLL_START_TIME. With the zoom starting later, the rows at the top of the
# screen stay (HZOOM_START_TIME - SCROLL_START_TIME) / HZOOM_TRIPLING_TIME
# generations deeper than the sub-figure filling the screen; set the two equal
# to keep the top row a solid bar.
HZOOM_TRIPLING_TIME = 8.0
SCROLL_ROWS_PER_TRIPLING = 1.0
HZOOM_START_TIME = 20.0
SCROLL_START_TIME = 0.0


# --- Gradient look ---
# Wide diffuse glow: how far (in [0,1] pattern coords) the alpha falls to 0.
WIDE_RADIUS = 0.3           # one cantor half at level 1; halves per level
WIDE_MAX_ALPHA = 110        # peak alpha of the diffuse glow (out of 255)
WIDE_FALLOFF_EXP = 1.5      # higher = sharper falloff

# Tight focused core: a narrow bright peak right at the beam.
TIGHT_RADIUS = 0.15
TIGHT_MAX_ALPHA = 255
TIGHT_FALLOFF_EXP = 2.0


# --- Beam envelope ---
# How far past progress = 1 (in row-progress units) the beam takes to fade fully.
FADE_LENGTH = 0.5

# How long the beam takes to bloom in at the start of a row (row-progress units).
BLOOM_LENGTH = 0.08


# ── Cantor geometry ──────────────────────────────────────────────────

@lru_cache(maxsize=None)
def cantor_measure_table(level: int):
    """(endpoints, cumulative measure) of the Cantor level, for np.interp.

    The level's segments are [s, s + 3**-level] for each start s. Interpolating
    the cumulative measure over the sorted endpoints gives F(x), the length of
    the level inside [0, x]; the coverage of a pixel column is then a difference
    of F at its two edges.
    """
    starts = np.zeros(1)
    seg = 1.0
    for _ in range(level):
        seg /= 3.0
        starts = np.stack([starts, starts + 2.0 * seg], axis=1).ravel()
    ends = starts + seg
    k = np.arange(starts.size, dtype=np.float64)
    endpoints = np.stack([starts, ends], axis=1).ravel()
    measure = np.stack([k * seg, (k + 1.0) * seg], axis=1).ravel()
    return endpoints, measure


def beam_positions(level: int, progress: float):
    """Active beam x-positions for this row at the given progress.

    Progress in [0, 1] sweeps across the row; progress > 1 lets the beam
    continue past the row's edge (during the rest after the row) so it can
    fade out gracefully rather than freeze.
    """
    p = max(0.0, progress)
    if level == 0:
        return [0.5 - 0.5 * p, 0.5 + 0.5 * p]
    if level % 2 == 1:
        # Outer → inner: 0 → 1/3 (left), 1 → 2/3 (right)
        return [p / 3.0, 1.0 - p / 3.0]
    else:
        # Inner → outer: 1/3 → 0 (left), 2/3 → 1 (right)
        return [1/3 - p / 3.0, 2/3 + p / 3.0]


def swept_mask(level: int, progress: float, x_fracs: np.ndarray) -> np.ndarray:
    """Boolean mask of pattern columns the beam has already swept on this row.

    Mirrors beam_positions: the swept region is everything between each
    beam's start position and its current position. Progress is clamped to
    [0, 1] so that during the rest after the row (progress > 1) the whole
    row reads as fully swept.
    """
    p = float(np.clip(progress, 0.0, 1.0))
    if level == 0:
        # center → out
        return np.abs(x_fracs - 0.5) <= 0.5 * p
    if level % 2 == 1:
        # outer → inner: swept from the edges toward 1/3 and 2/3
        return (x_fracs <= p / 3.0) | (x_fracs >= 1.0 - p / 3.0)
    else:
        # inner → outer: swept from 1/3, 2/3 toward the edges
        left = (x_fracs >= 1/3 - p / 3.0) & (x_fracs <= 1/3)
        right = (x_fracs >= 2/3) & (x_fracs <= 2/3 + p / 3.0)
        return left | right


def bar_h_px() -> int:
    return max(2, int(BAR_HEIGHT_FRAC * INTERNAL_H))


# ── Zoom and scroll ──────────────────────────────────────────────────
#
# Both are closed-form in wall-clock time, so every frame is deterministic.

def _right_frac() -> float:
    """Screen fraction of the figure's right end, which the zoom holds fixed."""
    return PATTERN_LEFT_FRAC + PATTERN_WIDTH_FRAC


def zoom_exponent(t: float) -> float:
    """Number of 3x stretches completed at time t (fractional)."""
    return max(0.0, t - HZOOM_START_TIME) / HZOOM_TRIPLING_TIME


def camera_position(t: float) -> float:
    """Downward pan offset at time t, in rows: row k sits at ROW_TOP_FRAC when
    the camera is at k."""
    return (SCROLL_ROWS_PER_TRIPLING * max(0.0, t - SCROLL_START_TIME)
            / HZOOM_TRIPLING_TIME)


def _fit_exponent() -> float:
    """Zoom exponent above a generation's start at which its sub-figure's left
    end reaches the left edge of the frame."""
    return math.log(_right_frac() / PATTERN_WIDTH_FRAC, 3)


def frame_generation(z: float) -> int:
    """Deepest m whose sub-figure S_m = [1 - 3^-m, 1] covers the whole frame
    left of the figure's right end, at zoom exponent z."""
    return max(0, math.floor(z - _fit_exponent()))


# Per-frame placement, set by _set_frame(t):
#   _camera_rows  — camera_position(t)
#   _frame_gen    — m: the frame is drawn in the coordinates of S_m
#   _x0, _w       — S_m's left end and width on the internal surface (float px)
#   _c0, _c1      — the internal-surface columns the figure occupies
_camera_rows = 0.0
_frame_gen = 0
_x0 = 0.0
_w = 1.0
_c0 = 0
_c1 = 1
_coverage_cache: dict = {}


def _set_frame(t: float):
    global _camera_rows, _frame_gen, _x0, _w, _c0, _c1
    z = zoom_exponent(t)
    _camera_rows = camera_position(t)
    _frame_gen = frame_generation(z)
    _w = PATTERN_WIDTH_FRAC * 3.0 ** (z - _frame_gen) * INTERNAL_W
    right_px = int(round(_right_frac() * INTERNAL_W))
    _x0 = right_px - _w
    _c0 = max(0, math.floor(_x0))
    _c1 = max(_c0 + 1, min(INTERNAL_W, right_px))
    _coverage_cache.clear()


def _column_fracs() -> np.ndarray:
    """S_m coordinate of the centre of each figure column, _c0.._c1."""
    return (np.arange(_c0, _c1, dtype=np.float64) + 0.5 - _x0) / _w


def _local_level(row: int) -> int:
    """Level of `row` within the frame's sub-figure S_m (rows above it are
    solid across the frame, the same as level 0)."""
    return min(MAX_LEVEL, max(0, row - _frame_gen))


def _row_coverage(row: int) -> np.ndarray:
    """Fraction (0..1) of each figure column covered by this row's bars."""
    level = _local_level(row)
    cov = _coverage_cache.get(level)
    if cov is None:
        endpoints, measure = cantor_measure_table(level)
        edges = (np.arange(_c0, _c1 + 1, dtype=np.float64) - _x0) / _w
        F = np.interp(edges, endpoints, measure)
        cov = np.clip(np.diff(F) * _w, 0.0, 1.0).astype(np.float32)
        _coverage_cache[level] = cov
    return cov


def _row_top_px(row: int, height_px: int) -> int:
    y = ROW_TOP_FRAC + ROW_SPACING_FRAC * (row - _camera_rows)
    return int(round(y * INTERNAL_H)) - height_px // 2


def _visible(y_top: int, height_px: int) -> bool:
    return y_top + height_px > 0 and y_top < INTERNAL_H


def visible_rows():
    """Range of rows that may intersect the frame (callers still cull)."""
    reach = (ROW_TOP_FRAC + BAR_HEIGHT_FRAC) / ROW_SPACING_FRAC
    first = max(0, math.floor(_camera_rows - reach))
    last = math.ceil(_camera_rows + (1.0 + BAR_HEIGHT_FRAC) / ROW_SPACING_FRAC)
    return range(first, last + 1)


# ── Drawing ──────────────────────────────────────────────────────────

# Reused scratch surfaces: a 1-pixel line per width, and the bar-height band it
# is stretched into.
_line_scratch: dict = {}
_band_scratch: dict = {}


def _blit_row_line(surface, row: int, rgb: np.ndarray, special_flags=0):
    """Stretch one line of per-column colours (n x 3, uint8) to bar height and
    blit it onto the row."""
    h = bar_h_px()
    y_top = _row_top_px(row, h)
    if not _visible(y_top, h):
        return
    n = rgb.shape[0]
    line = _line_scratch.get(n)
    if line is None:
        line = _line_scratch[n] = pygame.Surface((n, 1))
    pixels = pygame.surfarray.pixels3d(line)
    pixels[:, 0, :] = rgb
    del pixels
    band = _band_scratch.get((n, h))
    if band is None:
        band = _band_scratch[(n, h)] = pygame.Surface((n, h))
    pygame.transform.scale(line, (n, h), band)
    surface.blit(band, (_c0, y_top), special_flags=special_flags)


def draw_static_bars(surface):
    h = bar_h_px()
    bg = np.array(BG_COLOR, dtype=np.float32)
    bar = np.array(BAR_COLOR, dtype=np.float32)
    for row in visible_rows():
        if not _visible(_row_top_px(row, h), h):
            continue
        cov = _row_coverage(row)[:, np.newaxis]
        _blit_row_line(surface, row, (bg + (bar - bg) * cov).astype(np.uint8))


def _blit_row_light(surface, row: int, color, alpha: np.ndarray):
    """Additively composite a per-column light intensity (0..255) onto one
    row, masked to the row's bars."""
    a = np.clip(alpha, 0.0, 255.0).astype(np.float32) / 255.0
    a *= _row_coverage(row)
    if not a.any():
        return
    rgb = np.array(color, dtype=np.float32) * a[:, np.newaxis]
    _blit_row_line(surface, row, rgb.astype(np.uint8),
                   special_flags=pygame.BLEND_RGB_ADD)


def _beam_glow_alpha(level: int, progress: float, x_fracs: np.ndarray) -> np.ndarray:
    """Per-column alpha (0..255+) of the live, moving beam on its current row."""
    beams = beam_positions(level, progress)
    wide_radius = WIDE_RADIUS / (2 ** level)
    tight_radius = TIGHT_RADIUS / (1.5 ** level)
    alpha = np.zeros(x_fracs.shape[0], dtype=np.float32)
    for bx in beams:
        d_wide = np.abs(x_fracs - bx) / wide_radius
        wide = np.clip(1 - d_wide, 0, 1) ** WIDE_FALLOFF_EXP * WIDE_MAX_ALPHA
        d_tight = np.abs(x_fracs - bx) / tight_radius
        tight = np.clip(1 - d_tight, 0, 1) ** TIGHT_FALLOFF_EXP * TIGHT_MAX_ALPHA
        alpha = np.maximum(alpha, wide + tight)

    if progress < BLOOM_LENGTH:
        alpha *= progress / BLOOM_LENGTH
    elif progress > 1.0:
        alpha *= max(0.0, 1.0 - (progress - 1.0) / FADE_LENGTH)
    return alpha


def _sweep_progress(t: float, start_time: float, sweep_time: float) -> float:
    """Progress through a row, accelerating like a row of the Cantor tempo curve.

    A Cantor row spans beats [2b, 3b] of a curve whose tempo triples at a steady
    rate, so progress = 2 * (1.5 ** (elapsed / sweep_time) - 1): 0 at the start,
    1 after sweep_time, and still climbing afterwards so the beam can fade out
    past the row's edge.
    """
    return 2.0 * (1.5 ** ((t - start_time) / sweep_time) - 1.0)


def _linger_fade(t: float, row_end_time: float) -> float:
    """Fraction (0..1) of LINGER_ALPHA still showing for a finished row."""
    if not LINGER_FADE_TIME or LINGER_FADE_TIME <= 0:
        return 1.0
    return max(0.0, 1.0 - (t - row_end_time) / LINGER_FADE_TIME)


def beam_generation(start_time: float, sweep_time: float, row: int) -> int:
    """Sub-figure a row sweep's geometry is measured in.

    The deepest generation (at most the row's own) whose sub-figure has its
    left end on screen when the sweep finishes, so the whole sweep stays in
    view, then BEAM_FRAME_OFFSET generations up from there.
    """
    z_end = zoom_exponent(start_time + sweep_time)
    fit = max(0, math.ceil(z_end - _fit_exponent()))
    return max(0, min(row, fit) - BEAM_FRAME_OFFSET)


def draw_row_sweep(surface, t: float, color, start_time: float,
                   sweep_time: float, row: int):
    """One row of a full beam: the moving glow plus its lingering fill."""
    if t < start_time:
        return
    h = bar_h_px()
    if not _visible(_row_top_px(row, h), h):
        return
    progress = _sweep_progress(t, start_time, sweep_time)
    end_time = start_time + sweep_time
    fill_fade = _linger_fade(t, end_time)
    if progress > 1.0 + FADE_LENGTH and fill_fade <= 0.0:
        return

    # Sweep geometry lives in sub-figure S_g, where this row is level g' = row - g.
    # Map the frame's S_m column coordinates into S_g's.
    gen = beam_generation(start_time, sweep_time, row)
    level = row - gen
    x_fracs = 1.0 - (1.0 - _column_fracs()) * 3.0 ** (gen - _frame_gen)

    # Lingering fill up to the swept extent, with the bright moving beam
    # composited on top (max → beam always brighter than trail).
    fill = np.where(swept_mask(level, progress, x_fracs),
                    LINGER_ALPHA * 255.0 * fill_fade, 0.0).astype(np.float32)
    glow = _beam_glow_alpha(level, progress, x_fracs)
    _blit_row_light(surface, row, color, np.maximum(fill, glow))


def _row_lifetime(sweep_time: float) -> float:
    """Seconds from a row sweep's start until both its glow and trail are gone
    (infinite if trails never fade)."""
    if not LINGER_FADE_TIME or LINGER_FADE_TIME <= 0:
        return math.inf
    glow_end = sweep_time * math.log(1.0 + (1.0 + FADE_LENGTH) / 2.0, 1.5)
    return max(glow_end, sweep_time + LINGER_FADE_TIME)


def _sweep_time(row_period: float) -> float:
    """Sweep length of one row of a full beam: the Cantor row [2b, 3b] takes
    log3(1.5) of the tempo curve's tripling time."""
    return row_period * math.log(1.5, 3)


def draw_beam_instance(surface, t: float, color, start_time: float,
                       row_period: float, start_row: int, num_rows=None):
    """A full beam: enters start_row at start_time, then each following row
    every row_period seconds, for num_rows rows (None = without end; rows off
    screen are skipped)."""
    if t < start_time or (num_rows is not None and num_rows <= 0):
        return
    sweep_time = _sweep_time(row_period)
    for k in _live_beam_rows(t - start_time, row_period, num_rows):
        draw_row_sweep(surface, t, color, start_time + k * row_period,
                       sweep_time, start_row + k)


def _live_beam_rows(elapsed: float, row_period: float, num_rows) -> range:
    """Indices (within the beam) of the rows still glowing or lingering."""
    newest = math.floor(elapsed / row_period)
    if num_rows is not None:
        newest = min(num_rows - 1, newest)
    life = _row_lifetime(_sweep_time(row_period))
    oldest = 0 if math.isinf(life) else max(0, math.floor((elapsed - life) / row_period))
    return range(oldest, newest + 1)


def _beam_finished(t: float, start_time: float, row_period: float,
                   start_row: int, num_rows) -> bool:
    """True once a full beam can never show again: its last row has faded, or
    (with no row limit) every row it still lights is below the screen and it
    outpaces the scroll, so it will stay there."""
    if t < start_time:
        return False
    rows = _live_beam_rows(t - start_time, row_period, num_rows)
    if len(rows) == 0:
        return True
    scroll_rate = SCROLL_ROWS_PER_TRIPLING / HZOOM_TRIPLING_TIME
    h = bar_h_px()
    return (1.0 / row_period > scroll_rate
            and _row_top_px(start_row + rows.start, h) >= INTERNAL_H)


def scheduled_beam(n: int):
    """(color, start_time, row_period, start_row, num_rows) of the n-th
    scheduled full beam. Every one starts on row 0 of the whole figure."""
    start = BEAM_FIRST_TIME + n * BEAM_INTERVAL
    color = BEAM_COLORS[n % len(BEAM_COLORS)]
    return color, start, BEAM_ROW_PERIOD, 0, BEAM_NUM_ROWS


def active_beams(t: float):
    """Scheduled full beams (oldest first) that may still be visible at time t,
    followed by EXTRA_BEAMS. Call after _set_frame(t).

    Every scheduled beam runs the same course, so an older one is always
    further along: walk back from the newest and stop at the first that has
    finished.
    """
    if BEAM_INTERVAL > 0 and t >= BEAM_FIRST_TIME:
        live = []
        for n in range(math.floor((t - BEAM_FIRST_TIME) / BEAM_INTERVAL), -1, -1):
            beam = scheduled_beam(n)
            if _beam_finished(t, *beam[1:]):
                break
            live.append(beam)
        yield from reversed(live)
    for beam in EXTRA_BEAMS:
        if not _beam_finished(t, *beam[1:]):
            yield beam


def draw_scene(surface, t: float):
    _set_frame(t)
    surface.fill(BG_COLOR)
    draw_static_bars(surface)
    for beam in active_beams(t):
        draw_beam_instance(surface, t, *beam)


# ── Soundtrack ───────────────────────────────────────────────────────

def _resolve_soundtrack(path):
    """Return a usable path to the soundtrack, or None if it can't be found.

    Tries the path as given (absolute or relative to the current directory),
    then relative to this script's own folder.
    """
    if not path:
        return None
    if os.path.exists(path):
        return path
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if os.path.exists(here):
        return here
    print(f"[soundtrack] file not found: {path!r} — continuing without audio.",
          file=sys.stderr)
    return None


def _start_soundtrack_playback(path, start_offset):
    """Begin live audio playback for interactive mode (best-effort)."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        # start_offset lets the audio line up when previewing from --start.
        pygame.mixer.music.play(start=max(0.0, start_offset))
        print(f"[soundtrack] playing {path}", file=sys.stderr)
    except Exception as exc:  # mixer/codec issues shouldn't kill the animation
        print(f"[soundtrack] could not play audio ({exc}); continuing silently.",
              file=sys.stderr)


def _mux_soundtrack_into_video(video_path, audio_path, audio_start,
                               ffmpeg_path="ffmpeg"):
    """Mux the soundtrack into an already-rendered MP4, in place.

    `audio_start` is the soundtrack position that belongs under the first video
    frame. Positive: the audio is seeked to that point. Negative (the video
    opens before SOUNDTRACK_START_TIME): the audio is delayed by that much
    silence. The result is trimmed to the shorter of the two streams.
    """
    if not os.path.exists(video_path):
        print(f"[soundtrack] rendered video not found at {video_path}; "
              "skipping audio mux.", file=sys.stderr)
        return
    tmp_path = str(video_path) + ".muxed.mp4"
    cmd = [ffmpeg_path, "-y", "-i", str(video_path)]
    if audio_start >= 0:
        cmd += ["-ss", str(audio_start), "-i", str(audio_path)]
    else:
        delay_ms = int(round(-audio_start * 1000))
        cmd += ["-i", str(audio_path), "-af", f"adelay={delay_ms}:all=1"]
    cmd += [
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        tmp_path,
    ]
    print("[soundtrack] muxing audio: " + " ".join(cmd), file=sys.stderr)
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        os.replace(tmp_path, video_path)
        print(f"[soundtrack] wrote {video_path} with audio.", file=sys.stderr)
    except FileNotFoundError:
        print(f"[soundtrack] ffmpeg not found at {ffmpeg_path!r}; "
              "the MP4 has no audio.", file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        print(f"[soundtrack] ffmpeg mux failed:\n{stderr}", file=sys.stderr)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Main ─────────────────────────────────────────────────────────────

# Defaults for running from Thonny (just edit these and hit Run).
# CLI flags override them if you launch from a terminal.
RENDER = False
START_TIME = 0.0
STOP_TIME = 100.0          # render length; interactive playback runs until quit
FRAMES_DIR = ".frames_beam_linger_scroll3"
OUTPUT_PATH = "cantor_beam_linger_scroll3.mp4"
KEEP_FRAMES = False


def main():
    global LINGER_ALPHA, LINGER_FADE_TIME
    global HZOOM_TRIPLING_TIME, SCROLL_ROWS_PER_TRIPLING
    global HZOOM_START_TIME, SCROLL_START_TIME
    global BEAM_INTERVAL, BEAM_ROW_PERIOD, BEAM_NUM_ROWS

    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action=argparse.BooleanOptionalAction,
                        default=RENDER,
                        help="Render to mp4 (use --no-render for interactive playback)")
    parser.add_argument("--start", type=float, default=START_TIME,
                        help="Start saving frames at this time (seconds)")
    parser.add_argument("--stop", type=float, default=STOP_TIME,
                        help="Stop time in seconds (render mode only)")
    parser.add_argument("--linger-alpha", type=float, default=LINGER_ALPHA,
                        help="Opacity of the lingering fill, 0..1 (0 = no trail)")
    parser.add_argument("--linger-fade-time", type=float, default=LINGER_FADE_TIME,
                        help="Seconds for a finished row's trail to fade out "
                             "(larger = slower; 0 = never fade)")
    parser.add_argument("--tripling-time", type=float, default=HZOOM_TRIPLING_TIME,
                        help="Seconds for each 3x horizontal zoom")
    parser.add_argument("--rows-per-tripling", type=float,
                        default=SCROLL_ROWS_PER_TRIPLING,
                        help="Rows scrolled per 3x zoom (1 = self-similar)")
    parser.add_argument("--zoom-start", type=float, default=HZOOM_START_TIME,
                        help="Time in seconds at which the horizontal zoom begins")
    parser.add_argument("--scroll-start", type=float, default=SCROLL_START_TIME,
                        help="Time in seconds at which the vertical scroll begins")
    parser.add_argument("--beam-interval", type=float, default=BEAM_INTERVAL,
                        help="Seconds between scheduled full beams")
    parser.add_argument("--beam-row-period", type=float, default=BEAM_ROW_PERIOD,
                        help="Seconds for a full beam to advance one row")
    parser.add_argument("--beam-rows", type=int, default=BEAM_NUM_ROWS,
                        help="Rows each full beam sweeps before stopping "
                             "(default: until it drops off the screen)")
    parser.add_argument("--soundtrack", default=SOUNDTRACK,
                        help="Audio track under the animation (default: "
                             "InfinitySoundtrack.mp3). Plays live in interactive "
                             "mode and is muxed into the MP4 when rendering.")
    parser.add_argument("--no-soundtrack", dest="soundtrack",
                        action="store_const", const=None,
                        help="Run silently (no soundtrack)")
    parser.add_argument("--frames-dir", default=FRAMES_DIR)
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument("--keep-frames", action=argparse.BooleanOptionalAction,
                        default=KEEP_FRAMES,
                        help="Keep the frames directory after rendering")
    args = parser.parse_args()

    LINGER_ALPHA = args.linger_alpha
    LINGER_FADE_TIME = args.linger_fade_time
    HZOOM_TRIPLING_TIME = args.tripling_time
    SCROLL_ROWS_PER_TRIPLING = args.rows_per_tripling
    HZOOM_START_TIME = args.zoom_start
    SCROLL_START_TIME = args.scroll_start
    BEAM_INTERVAL = args.beam_interval
    BEAM_ROW_PERIOD = args.beam_row_period
    BEAM_NUM_ROWS = args.beam_rows

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cantor Beam (endless zoom + scroll)")

    global INTERNAL_W, INTERNAL_H
    if args.render:
        INTERNAL_W = WIDTH * SUPERSAMPLE
        INTERNAL_H = HEIGHT * SUPERSAMPLE
        render_target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    else:
        INTERNAL_W = WIDTH
        INTERNAL_H = HEIGHT
        render_target = screen

    mode = "render" if args.render else "playback"
    stop_time = args.stop if args.render else None

    soundtrack = _resolve_soundtrack(args.soundtrack)
    # In interactive mode the audio plays live, starting at SOUNDTRACK_START_TIME
    # (see the loop below). In render mode it is muxed in after the frames are
    # written.
    music_pending = bool(soundtrack) and not args.render

    with PygameRecorder(
        size=(WIDTH, HEIGHT),
        fps=FPS,
        mode=mode,
        start_time=args.start,
        stop_time=stop_time,
        frames_dir=args.frames_dir,
        output_path=args.output,
        delete_frames=not args.keep_frames,
    ) as rec:
        while rec.should_continue():
            t, dt, should_save = rec.tick()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    rec.request_stop()
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_q
                ):
                    rec.request_stop()

            if music_pending and t >= SOUNDTRACK_START_TIME:
                _start_soundtrack_playback(soundtrack, start_offset=0.0)
                music_pending = False

            draw_scene(render_target, t)

            if args.render:
                pygame.transform.smoothscale(render_target, (WIDTH, HEIGHT), screen)

            if should_save:
                rec.submit(screen)

            pygame.display.flip()

    # The recorder has finished writing the MP4 on exit from the `with` block;
    # now fold the soundtrack in. The rendered video begins at args.start and
    # the music at SOUNDTRACK_START_TIME, so the audio is seeked (or delayed) by
    # the difference.
    if soundtrack and args.render:
        _mux_soundtrack_into_video(args.output, soundtrack,
                                   audio_start=args.start - SOUNDTRACK_START_TIME)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
