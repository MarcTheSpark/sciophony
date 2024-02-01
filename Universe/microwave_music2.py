from scamp import *
from scamp_extensions.utilities import remap, TimeVaryingParameter
from scamp_extensions.pitch import Scale
from microwave_music import get_max_value_for_sharpness
from microwave_scan_values import scan_times, scan_values, scan_value_at_time, chord_zone_at_time, local_maxima_indices, local_extrema_indices, sharpness_env, PIECE_DURATION
import random


TIME_STEP = 0.02

s = Session()
# s.fast_forward()
# s.fast_forward_in_time(PIECE_DURATION * 0.6)

cello = s.new_part("cello")
timpani = s.new_part("timpani")
grav_player = s.new_osc_part("gravPlayer", 57120)

bass = s.new_part("acoustic bass")

pop_template_mix = TimeVaryingParameter([1.0, 0.2], [PIECE_DURATION], [2])
pop_pitch_min = TimeVaryingParameter([40, 40], [PIECE_DURATION])
pop_pitch_max = TimeVaryingParameter([55, 100], [PIECE_DURATION])
pop_lengths = TimeVaryingParameter([8, 2], [PIECE_DURATION])
pop_lengths_min = TimeVaryingParameter([4, 1], [PIECE_DURATION])
pop_lengths_max = TimeVaryingParameter([8, 3], [PIECE_DURATION])
pop_attack_release_time = TimeVaryingParameter([4, 0.01], [PIECE_DURATION], [-3])
chord_jitter = TimeVaryingParameter([0, 1], [PIECE_DURATION])
grav_player_scale = Scale.from_pitches([64, 67, 69, 71, 73, 75])

# volume: remap 0-300 => 0.2-1.0

chords = [[52, 59, 67], [52, 61, 69], [64, 69, 76]]


def get_chord_from_zone(zone):
    octave_displacement, index = divmod(int(zone), 3)
    return [x + 12 * octave_displacement for x in chords[index]]


pop_locations = scan_times[local_maxima_indices]
pop_value_range = min(scan_values[local_maxima_indices]), max(scan_values[local_maxima_indices])
# Map from range of maxima overall to pop_pitch_min(), pop_pitch_max()
# add a pop timeout?


def do_pops():
    pop_schedule = []
    polarity = 1  # switch that flips between high and low pops
    for t in pop_locations:
        if t < pop_lengths_min.value_at(t):
            continue
        dur = min(t, random.uniform(pop_lengths_min.value_at(t), pop_lengths_max.value_at(t)))
        volume = remap(float(scan_value_at_time(t)), 0.3, 1, pop_value_range[0], pop_value_range[1])
        pitch = (pop_pitch_max() + pop_pitch_min()) / 2 + polarity * remap(float(scan_value_at_time(t)), 0, (pop_pitch_max() - pop_pitch_min()) / 2, pop_value_range[0], pop_value_range[1])
        pop_schedule.append((t - dur, pitch, volume, dur))
        polarity *= -1
    pop_schedule.sort(key=lambda x: x[0])
    current_time = 0
    for t, pitch, volume, dur in pop_schedule:
        wait(t - current_time)
        current_time = t
        grav_player.play_note(pitch,  #random.uniform(pop_pitch_min(), pop_pitch_max()),
                              volume,
                              dur,
                              {"param_backupDur": dur, "param_templateMix": pop_template_mix(),
                               "param_attackTime": pop_attack_release_time(), "param_decayTime": pop_attack_release_time()},
                              blocking=False)


def do_timpani():
    current_time = 0
    for t in sorted(pop_locations):
        wait(t - current_time)
        current_time = t
        volume = remap(float(scan_value_at_time(t)), 0.3, 1, pop_value_range[0], pop_value_range[1])
        pitch = 60 - remap(float(scan_value_at_time(t)), 0, 25, pop_value_range[0], pop_value_range[1])
        timpani.play_note(pitch, volume, 1.0, blocking=False)


bass_pitches = [40, 40, 40, 40, 43, 40, 47, 40, 40, 40, 40, 40, 43, 40, 47, 40, 40, 40, 40, 40, 43, 40, 47, 40, 43, 40,
                47, 40, 55, 40, 57, 39]


def bass_line():
    current_clock().tempo = 160
    current_clock().set_tempo_target(40, PIECE_DURATION, curve_shape=5, duration_units="time")
    last_pitch = None
    while True:
        for pitch in bass_pitches:
            # current_clock().tempo -= 0.05
            bass.play_note(pitch, 0.9 if pitch != last_pitch else 0.7, 0.1)
            last_pitch = pitch


def do_cello_part():
    chord_handle = None
    current_chord_zone = None
    while s.time() < PIECE_DURATION:
        try:
            which_chord = int(chord_zone_at_time(s.time()))
        except ValueError:
            break

        # print(value, which_chord)
        if which_chord != current_chord_zone:
            # jittered_chord_choice = which_chord + int((random.random() * chord_jitter() * 3)) * 2
            # while jittered_chord_choice > 7:
            #     jittered_chord_choice -= 2
            # while jittered_chord_choice < -7:
            #     jittered_chord_choice += 2
            # chord = get_chord_from_zone(jittered_chord_choice)

            chord = get_chord_from_zone(which_chord)

            if chord_handle:
                chord_handle.end()
            chord_handle = cello.start_chord(chord, 0.6)
            current_chord_zone = which_chord
        wait(TIME_STEP)


# fork(bass_line)
fork(do_pops)
fork(do_cello_part)
fork(do_timpani)
# s.fast_forward()
s.start_transcribing()

wait(PIECE_DURATION)
s.stop_transcribing().export_to_midi_file("microwave.mid")
