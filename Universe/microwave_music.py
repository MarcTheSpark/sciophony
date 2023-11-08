import numpy as np
from marciano.microwave import get_value_at, get_max_value_for_sharpness
from marciano.spherical_spiral import position_on_spiral
from scamp import *
from scamp_extensions.utilities import remap, TimeVaryingParameter
from scamp_extensions.pitch import Scale
from microwave_scan_values import scan_times, scan_value_at_time, local_maxima_indices, sharpness_env, PIECE_DURATION
import random


TIME_STEP = 0.02

s = Session()

cello = s.new_part("cello")
grav_player = s.new_osc_part("gravPlayer", 57120)
bass = s.new_part("acoustic bass")

# pop_template_mix = TimeVaryingParameter([0.9, 0.1], [PIECE_DURATION], [-3])
# pop_pitch_min = TimeVaryingParameter([40, 40], [PIECE_DURATION])
# pop_pitch_max = TimeVaryingParameter([55, 100], [PIECE_DURATION])
# pop_lengths_min = TimeVaryingParameter([3, 0.1], [PIECE_DURATION])
# pop_lengths_max = TimeVaryingParameter([7, 0.5], [PIECE_DURATION])
# pop_attack_release_time = TimeVaryingParameter([2, 0.01], [PIECE_DURATION], [-3])
pop_template_mix = TimeVaryingParameter([1.0, 0.6], [PIECE_DURATION], [-3])
pop_pitch_min = TimeVaryingParameter([40, 40], [PIECE_DURATION])
pop_pitch_max = TimeVaryingParameter([55, 100], [PIECE_DURATION])
pop_lengths_min = TimeVaryingParameter([4, 1], [PIECE_DURATION])
pop_lengths_max = TimeVaryingParameter([8, 3], [PIECE_DURATION])
pop_attack_release_time = TimeVaryingParameter([4, 0.01], [PIECE_DURATION], [-3])

# volume: remap 0-300 => 0.2-1.0

chords = [[52, 57, 64], [52, 59, 67], [52, 61, 69]]
chord_handle = None
current_chord = None

pop_locations = scan_times[local_maxima_indices]


def do_pops():
    pop_schedule = []
    for t in pop_locations:
        dur = min(t, random.uniform(pop_lengths_min.value_at(t), pop_lengths_max.value_at(t)))
        pop_schedule.append((t - dur, remap(float(scan_value_at_time(t)), 0.3, 1, 0, 300), dur))
    pop_schedule.sort(key=lambda x: x[0])
    current_time = 0
    for t, volume, dur in pop_schedule:
        wait(t - current_time)
        current_time = t
        grav_player.play_note(random.uniform(pop_pitch_min(), pop_pitch_max()),
                              volume,
                              dur,
                              {"param_backupDur": dur, "param_templateMix": pop_template_mix(),
                               "param_attackTime": pop_attack_release_time(), "param_decayTime": pop_attack_release_time()},
                              blocking=False)


def do_bass_part():
    current_clock().tempo = 180
    current_clock().set_tempo_target(50, PIECE_DURATION*1.3, curve_shape=5)
    # current_clock().tempo_history.show_plot()
    bass_scale = Scale.from_pitches([39, 40, 43, 47, 55, 57], cycle=False)

    while True:
        max_value = get_max_value_for_sharpness(sharpness_env.value_at(s.time()))
        normalized_value = abs(scan_value_at_time(s.time())) / max_value * 10
        bass.play_note(bass_scale[round(normalized_value)], 1.0, 0.25)


fork(do_bass_part)
# fork(do_pops)
s.fast_forward()
s.start_transcribing()
while s.time() < PIECE_DURATION:
    try:
        value = scan_value_at_time(s.time())
    except ValueError:
        break
    max_value = get_max_value_for_sharpness(sharpness_env.value_at(s.time()))

    which_chord = 0 if value < -max_value/5 else 1 if value < max_value/5 else 2
    # print(value, which_chord)
    if which_chord != current_chord:
        if chord_handle:
            chord_handle.end()
        chord_handle = cello.start_chord(chords[which_chord], 1.0)
        current_chord = which_chord
    wait(TIME_STEP)

s.stop_transcribing().export_to_midi_file("microwave.mid")
# What's wrong with SC? Make it free
# Fast bass line pitch-wise similar to what mariano did, but following the contour. Starts very fast, but slows down, gets heavier?
# put it into logic; get free trial

# make it jump up and down octaves at the end in the wurly