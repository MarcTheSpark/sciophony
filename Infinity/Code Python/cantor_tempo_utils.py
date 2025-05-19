import json
from scamp import TempoEnvelope


def cantor_rest_pattern(dur):
    pattern_so_far = (dur,)
    longest_rest = dur
    yield dur
    while True:
        longest_rest *= 3
        yield from (longest_rest,) + pattern_so_far
        pattern_so_far = pattern_so_far + (longest_rest,) + pattern_so_far
        

cantor_accel_curve = TempoEnvelope([3 ** (-n) for n in range(17)], [3 ** n for n in range(1, 17)], ["exp * 2"] * 16, "beatlength")


RECALC = False

if RECALC:
    _cantor_times = []

    b = 0
    for rest_dur in cantor_rest_pattern(1):
        _cantor_times.append((cantor_accel_curve.time_at_beat(b), cantor_accel_curve.time_at_beat(b + 1)))
        b += 1 + rest_dur
        print(f"Calculating... on beat {b} of {cantor_accel_curve.length()}")
        if b > cantor_accel_curve.length():
            break

    _cantor_times_flat = [x for entry in _cantor_times for x in entry]
    _cantor_durs = [(-1) ** i * (b - a) for i, (a, b) in enumerate(zip(_cantor_times_flat, _cantor_times_flat[1:]))]

    with open("cantordurs.json", "w") as f:
        json.dump(_cantor_durs, f, indent=4)
else:
    with open("cantordurs.json", "r") as f:
        _cantor_durs = json.load(f)
    
# _cantor_durs alternates positive (note duration) and negative (rest duration)
# probably easiest to pair them as (note duration, rest duration) so we make...


def get_cantor_note_rest_pairs(scaling_factor=3, min_note_dur=0.001):
    """
    Generates alternating note and rest durations for an additive cantor set rhythm that is accelerating.
    
    :param scaling_factor: The note duration in seconds at the starting tempo. Note that the tempo is accelerating throughout the first
        note, so the first not is actually shorter than initial_dur.
    """
    pairs = []
    for a, b in zip(_cantor_durs[::2], _cantor_durs[1::2]):
        if a * scaling_factor < min_note_dur:
            break
        pairs.append((a * scaling_factor, abs(b) * scaling_factor))
    
    return pairs


def get_metronome_subdivisions(num_tripling_cycles, subdivision_depth, scaling_factor=3):
    # times three because we dilated the other one that way too
    subdivision_size = 3 ** (-subdivision_depth)
    total_beats_to_accelerate = sum(3 ** (n + 1) for n in range(num_tripling_cycles))
    _metronome_beats = [x * subdivision_size for x in range(total_beats_to_accelerate * 3 ** subdivision_depth + 1)]
    _metronome_times = [cantor_accel_curve.time_at_beat(b) * scaling_factor for b in _metronome_beats]
    metronome_subdivisions = [b - a for a, b in zip(_metronome_times, _metronome_times[1:])]
    return metronome_subdivisions


_first_dur = _cantor_durs[0]
_tripling_dur = sum(abs(x) for x in _cantor_durs[:3])


def get_tempo_tripling_dur(scaling_factor=3):
    return _tripling_dur * scaling_factor


def get_first_dur(scaling_factor=3):
    return _first_dur * scaling_factor
