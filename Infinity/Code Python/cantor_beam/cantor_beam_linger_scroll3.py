"""
cantor_beam_linger_scroll3.py — cantor_beam_linger_scroll with changing
colours and an endless self-similar zoom.

This is cantor_beam_linger_scroll.py with two changes:

  - every new beam comes in a new colour (yellow, blue, pink, green, orange,
    violet, cyan, red, then round again);
  - the figure zooms: it stretches horizontally by 3x for every row the camera
    scrolls down, homing in on the right-hand end of the Cantor set (its right
    edge stays put on screen while everything else grows leftward). After each
    tripling the picture is the same as before, one generation deeper.

Everything else is the original: the same beam schedule (a new beam every 5 s,
each starting on row 0 and accelerating down the figure row by row with the
scantimes Cantor tempo curve), the same constant-speed downward scroll, and the
same lingering fill (LINGER_ALPHA, fading over LINGER_FADE_TIME).

Each row is swept with the classic cantor_beam geometry (centre→out on a solid
bar, then alternating outer→inner / inner→outer), but measured in the deepest
sub-figure whose left end is on screen when that row's sweep ends, so the sweep
stays in view however far the zoom has gone.

Rendering the zoom
------------------
Each frame is drawn relative to the deepest sub-figure S_m = [1 - 3^-m, 1]
that still covers the frame's left edge: S_m is a complete Cantor set, row L of
the whole figure is row L - m of S_m, and rows above S_m are solid across the
frame. Every row is drawn from its exact area coverage per pixel column, so the
bars are antialiased and deep rows fade naturally as their bars shrink below a
pixel. Each row is computed as a single 1-pixel line and stretched to bar
height in C.

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
from cantor_utils.scantimes import row_start_and_end_beats
from cantor_utils.tempo import cantor_accel_curve


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

# Time (seconds into the animation) at which the soundtrack begins.
SOUNDTRACK_START_TIME = 0.0


# --- Colors ---
BG_COLOR = (10, 10, 10)
BAR_COLOR = (50, 50, 50)

# Each beam instance is a tuple:
#   (color (r,g,b), start_time seconds, time_scaling_factor[, start_row, num_rows])
# The scaling factor is passed to the scantimes Cantor tempo curve — larger =
# slower beam. The two optional trailing fields restrict which rows the beam
# sweeps (omit them to sweep the whole figure from row 0):
#   start_row  (default 0)    — the Cantor row the beam enters at start_time.
#   num_rows   (default None) — how many rows to sweep before stopping
#                               (None = continue to the bottom of the figure).
# Same schedule as cantor_beam_linger_scroll.py, with a new colour each time.
BEAMS = [
    ((255, 230, 90),  1.0, 3.0),    # yellow
    ((20, 100, 250),  6.0, 3.0),    # blue
    ((255, 70, 150), 11.0, 3.0),    # pink
    ((60, 220, 120), 16.0, 3.0),    # green
    ((255, 140, 40), 21.0, 3.0),    # orange
    ((160, 90, 255), 26.0, 3.0),    # violet
    ((40, 210, 230), 31.0, 3.0),    # cyan
    ((250, 60, 60),  36.0, 3.0),    # red
    ((255, 230, 90), 41.0, 3.0),    # yellow
]

# Which sub-figure a row's sweep geometry is measured in. 0: the one that fits
# on screen when the sweep ends — rows get the classic mirrored pair of beams
# (or centre→out on a solid bar). 1: its parent, of which only the right third
# is on screen — a single beam crosses the row.
BEAM_FRAME_OFFSET = 0


# --- Lingering fill ---
# Opacity of the trail left behind after the beam passes, as a fraction of
# full brightness (0 = no trail, 1 = trail as bright as the beam's peak).
LINGER_ALPHA = 0.5

# Seconds over which a finished row's lingering trail fades back to black,
# measured from the moment the beam finishes sweeping that row. Set to 0 (or
# None) to disable fading and leave the trail at LINGER_ALPHA.
LINGER_FADE_TIME = 1.


# --- Layout (fractions of frame) ---
# The base seven Cantor generations plus EXTRA_GENERATIONS more drawn below,
# revealed by the scroll. Override with --extra-generations.
EXTRA_GENERATIONS = 8
NUM_LEVELS = 7 + EXTRA_GENERATIONS
PATTERN_LEFT_FRAC = 0.06
PATTERN_WIDTH_FRAC = 0.88
ROW_TOP_FRAC = 0.10
ROW_SPACING_FRAC = 0.115
BAR_HEIGHT_FRAC = 0.038

# Deepest Cantor level ever evaluated (2**level segments). Rows deeper than
# this are far below a pixel and are drawn as this level.
MAX_LEVEL = 16


# --- Gradient look ---
# Wide diffuse glow: how far (in [0,1] pattern coords) the alpha falls to 0.
WIDE_RADIUS = 0.3           # one cantor half at level 1; halves per level
WIDE_MAX_ALPHA = 110        # peak alpha of the diffuse glow (out of 255)
WIDE_FALLOFF_EXP = 1.5      # higher = sharper falloff

# Tight focused core: a narrow bright peak right at the beam.
TIGHT_RADIUS = 0.15
TIGHT_MAX_ALPHA = 255
TIGHT_FALLOFF_EXP = 2.0


# --- Animation timing ---
# TAIL holds the final frame after the last row finishes.
TAIL = 1.5

# How far past progress = 1 (in row-progress units) the beam takes to fade fully.
FADE_LENGTH = 0.5

# How long the beam takes to bloom in at the start of a row (row-progress units).
BLOOM_LENGTH = 0.08


# --- Camera scroll ---
# Constant downward pan speed, in rows per second, held for the whole piece.
# None = chosen so the last generation ends the piece at SCROLL_END_FRAC of the
# screen (as in cantor_beam_linger_scroll.py); an explicit number overrides it
# (0 = no pan, and so no zoom). Override with --scroll-speed.
SCROLL_SPEED = None
SCROLL_START_TIME = 0.0
SCROLL_END_FRAC = 0.5
START_CAMERA_POSITION = -0.4


# --- Zoom ---
# The zoom is locked to the scroll: ZOOM_TRIPLINGS_PER_ROW 3x horizontal
# stretches per row scrolled (1 makes the motion exactly self-similar). It
# holds still until HZOOM_START_TIME.
ZOOM_TRIPLINGS_PER_ROW = 1.0
HZOOM_START_TIME = 0.0


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


# ── Beam timing ──────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _row_beats(num_rows: int):
    """(start_beat, end_beat) of the first num_rows Cantor rows."""
    out = []
    for row, beats in enumerate(row_start_and_end_beats()):
        if row >= num_rows:
            break
        out.append(beats)
    return tuple(out)


def _beam_time_offset(scaling_factor: float, start_row: int) -> float:
    """Seconds to add to a beam's local clock so it enters `start_row` at t=0."""
    return scaling_factor * cantor_accel_curve.time_at_beat(_row_beats(start_row + 1)[start_row][0])


@lru_cache(maxsize=None)
def _row_end_times(start_time: float, scaling_factor: float,
                   start_row: int = 0) -> tuple:
    """Wall-clock time at which the beam finishes each row, indexed by row."""
    offset = _beam_time_offset(scaling_factor, start_row)
    return tuple(start_time + scaling_factor * cantor_accel_curve.time_at_beat(end_beat) - offset
                 for _start_beat, end_beat in _row_beats(NUM_LEVELS))


def _beam_params(beam):
    """Unpack a BEAMS entry, filling the optional start_row / num_rows fields."""
    color, start_time, scaling_factor = beam[0], beam[1], beam[2]
    start_row = beam[3] if len(beam) > 3 else 0
    num_rows = beam[4] if len(beam) > 4 else None
    return color, start_time, scaling_factor, start_row, num_rows


def _beam_end_time(start_time: float, scaling_factor: float,
                   start_row: int, num_rows) -> float:
    """Wall-clock time at which one beam finishes its last swept row."""
    last_row = NUM_LEVELS - 1 if num_rows is None else min(NUM_LEVELS, start_row + num_rows) - 1
    last_row = max(start_row, min(last_row, NUM_LEVELS - 1))
    return _row_end_times(start_time, scaling_factor, start_row)[last_row]


def total_animation_time() -> float:
    """Wall-clock time at which the latest beam finishes its last row."""
    return max(_beam_end_time(*_beam_params(beam)[1:]) for beam in BEAMS)


# ── Scroll and zoom ──────────────────────────────────────────────────
#
# Both are closed-form in wall-clock time, so every frame is deterministic.

def _scroll_speed() -> float:
    """Pan speed in rows/second: the override, or an end-centred auto speed."""
    if SCROLL_SPEED is not None:
        return max(0.0, SCROLL_SPEED)
    span = total_animation_time() - SCROLL_START_TIME
    if span <= 0:
        return 0.0
    # Camera offset that puts the last generation at SCROLL_END_FRAC.
    end_camera = ((NUM_LEVELS - 1)
                  - (SCROLL_END_FRAC - ROW_TOP_FRAC) / ROW_SPACING_FRAC)
    return max(0.0, end_camera / span)


def camera_position(t: float) -> float:
    """Downward pan offset at time t, in rows: row k sits at ROW_TOP_FRAC when
    the camera is at k."""
    return START_CAMERA_POSITION + _scroll_speed() * max(0.0, t - SCROLL_START_TIME)


def zoom_exponent(t: float) -> float:
    """Number of 3x stretches completed at time t (fractional)."""
    if t <= HZOOM_START_TIME:
        return 0.0
    return ZOOM_TRIPLINGS_PER_ROW * (camera_position(t) - camera_position(HZOOM_START_TIME))


def _right_frac() -> float:
    """Screen fraction of the figure's right end, which the zoom holds fixed."""
    return PATTERN_LEFT_FRAC + PATTERN_WIDTH_FRAC


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
    """Range of figure rows that may intersect the frame (callers still cull)."""
    reach = (ROW_TOP_FRAC + BAR_HEIGHT_FRAC) / ROW_SPACING_FRAC
    first = max(0, math.floor(_camera_rows - reach))
    last = math.ceil(_camera_rows + (1.0 + BAR_HEIGHT_FRAC) / ROW_SPACING_FRAC)
    return range(first, min(NUM_LEVELS - 1, last) + 1)


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


def _linger_fade(t: float, row_end_time: float) -> float:
    """Fraction (0..1) of LINGER_ALPHA still showing for a finished row."""
    if not LINGER_FADE_TIME or LINGER_FADE_TIME <= 0:
        return 1.0
    return max(0.0, 1.0 - (t - row_end_time) / LINGER_FADE_TIME)


def beam_generation(row: int, end_time: float) -> int:
    """Sub-figure a row sweep's geometry is measured in.

    The deepest generation (at most the row's own) whose sub-figure has its
    left end on screen when the sweep finishes, so the whole sweep stays in
    view, then BEAM_FRAME_OFFSET generations up from there.
    """
    fit = max(0, math.ceil(zoom_exponent(end_time) - _fit_exponent()))
    return max(0, min(row, fit) - BEAM_FRAME_OFFSET)


def draw_row_sweep(surface, t: float, color, row: int, progress: float,
                   end_time: float):
    """One row of a beam: the moving glow plus its lingering fill."""
    fill_fade = _linger_fade(t, end_time)
    if progress > 1.0 + FADE_LENGTH and fill_fade <= 0.0:
        return

    # Sweep geometry lives in sub-figure S_g, where this row is level row - g.
    # Map the frame's S_m column coordinates into S_g's.
    gen = beam_generation(row, end_time)
    level = row - gen
    x_fracs = 1.0 - (1.0 - _column_fracs()) * 3.0 ** (gen - _frame_gen)

    # Lingering fill up to the swept extent, with the bright moving beam
    # composited on top (max → beam always brighter than trail).
    fill = np.where(swept_mask(level, progress, x_fracs),
                    LINGER_ALPHA * 255.0 * fill_fade, 0.0).astype(np.float32)
    glow = _beam_glow_alpha(level, progress, x_fracs)
    _blit_row_light(surface, row, color, np.maximum(fill, glow))


def draw_beam_instance(surface, t: float, color, start_time: float,
                       scaling_factor: float, start_row: int = 0,
                       num_rows=None):
    if t < start_time:
        return
    end_row = NUM_LEVELS if num_rows is None else min(NUM_LEVELS, start_row + num_rows)
    # Beat position on the beam's own (shifted) Cantor tempo curve; each row's
    # progress is where that beat falls within the row's [start, end] beats.
    offset = _beam_time_offset(scaling_factor, start_row)
    beat = cantor_accel_curve.beat_at_time(((t - start_time) + offset) / scaling_factor)
    end_times = _row_end_times(start_time, scaling_factor, start_row)
    h = bar_h_px()
    beats = _row_beats(NUM_LEVELS)
    for row in visible_rows():
        if row < start_row or row >= end_row:
            continue
        start_beat, end_beat = beats[row]
        if beat < start_beat or not _visible(_row_top_px(row, h), h):
            continue
        progress = (beat - start_beat) / (end_beat - start_beat)
        draw_row_sweep(surface, t, color, row, progress, end_times[row])


def draw_scene(surface, t: float):
    _set_frame(t)
    surface.fill(BG_COLOR)
    draw_static_bars(surface)
    for beam in BEAMS:
        draw_beam_instance(surface, t, *_beam_params(beam))


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
STOP_TIME = None           # None → computed from animation length
FRAMES_DIR = ".frames_beam_linger_scroll3"
OUTPUT_PATH = "cantor_beam_linger_scroll3.mp4"
KEEP_FRAMES = False


def main():
    global LINGER_ALPHA, LINGER_FADE_TIME
    global NUM_LEVELS, SCROLL_SPEED, SCROLL_START_TIME
    global ZOOM_TRIPLINGS_PER_ROW, HZOOM_START_TIME

    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action=argparse.BooleanOptionalAction,
                        default=RENDER,
                        help="Render to mp4 (use --no-render for interactive playback)")
    parser.add_argument("--start", type=float, default=START_TIME,
                        help="Start saving frames at this time (seconds)")
    parser.add_argument("--stop", type=float, default=STOP_TIME,
                        help="Stop time in seconds (render mode only; "
                             "default: computed animation length)")
    parser.add_argument("--linger-alpha", type=float, default=LINGER_ALPHA,
                        help="Opacity of the lingering fill, 0..1 (0 = no trail)")
    parser.add_argument("--linger-fade-time", type=float, default=LINGER_FADE_TIME,
                        help="Seconds for a finished row's trail to fade out "
                             "(larger = slower; 0 = never fade)")
    parser.add_argument("--extra-generations", type=int, default=EXTRA_GENERATIONS,
                        help="Extra Cantor generations drawn below the base seven "
                             "(revealed by the downward camera scroll)")
    parser.add_argument("--scroll-speed", type=float, default=SCROLL_SPEED,
                        help="Constant downward pan speed in rows/second. Omit "
                             "to end with the last row mid-screen (0 = no pan)")
    parser.add_argument("--scroll-start", type=float, default=SCROLL_START_TIME,
                        help="Time in seconds at which the constant scroll begins")
    parser.add_argument("--triplings-per-row", type=float,
                        default=ZOOM_TRIPLINGS_PER_ROW,
                        help="3x horizontal zooms per row scrolled "
                             "(1 = self-similar, 0 = no zoom)")
    parser.add_argument("--zoom-start", type=float, default=HZOOM_START_TIME,
                        help="Time in seconds at which the horizontal zoom begins")
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
    NUM_LEVELS = 7 + args.extra_generations
    SCROLL_SPEED = args.scroll_speed
    SCROLL_START_TIME = args.scroll_start
    ZOOM_TRIPLINGS_PER_ROW = args.triplings_per_row
    HZOOM_START_TIME = args.zoom_start

    if args.stop is None:
        args.stop = total_animation_time() + TAIL

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cantor Beam (lingering fill, scroll + zoom)")

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
