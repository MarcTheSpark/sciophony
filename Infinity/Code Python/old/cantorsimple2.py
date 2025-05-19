from scamp import *
from cantor_tempo_calcs import cantor_note_rest_pairs, start_spacing_interval, get_metronome_subdivisions, get_tempo_tripling_dur
import itertools
import math

s = Session()

piano = s.new_midi_part("pianoteq", "MIDI through port 0")
perc = s.new_part("power")



def met_swell(scaling_factor=1, num_triplings=1):
    for i, dur in enumerate(get_metronome_subdivisions(scaling_factor, num_triplings, 0)):
        perc.play_note(61, 1, dur)
    perc.play_note(61, 1, dur)


# while True:
#     fork(met_swell, (2, 3))
#     wait(get_tempo_tripling_dur(2))
fork(met_swell, (2, 3))
wait_for_children_to_finish()
exit()

# def met_swell(scaling_factor=1):
#     total_met_len = sum(metronome_subdivisions) * scaling_factor
#     met_curve = Envelope([0, 1, 0], [total_met_len / 2, total_met_len / 2])
#     for i, dur in enumerate(metronome_subdivisions):
#         print(met_curve.value_at(current_clock().beat()))
#         perc.play_note(61, met_curve.value_at(current_clock().beat()), dur * scaling_factor)
#         
# 
# def metronome(scaling_factor=1):
#     while True:
#         for i, dur in enumerate(metronome_subdivisions):
#             perc.play_note(61, 1, dur * scaling_factor)
            


# Have this fade in and out, and layer them.
met_swell(27)
exit()

def cantor_pitch_cycle(start_pitch):
    return itertools.cycle([start_pitch + x for x in (0, 3, 2, 3, 5, 3, 2, 3)])



def play_cantor_pitch_cycle(start_pitch, volume, scale_factor=1, note_fade_function=lambda l: min(1, l ** 0.35), min_note_dur=0.002):
    for pitch, (note_dur, rest_dur) in zip(cantor_pitch_cycle(start_pitch), cantor_note_rest_pairs):
        if note_dur < min_note_dur:
            break
        vol = volume * note_fade_function(note_dur)
        piano.play_note(pitch, vol, note_dur * scale_factor)
        wait(rest_dur * scale_factor)


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


piano.send_midi_cc(64, 0.8)

fork(metronome, (0.8,))

i = 0
while True:
    fork(play_cantor_pitch_cycle, (start_pitch(i), 0.8, 0.8))
    wait(start_spacing_interval * 0.8)
    i += 1
