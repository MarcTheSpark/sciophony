from scamp import *
from cantor_tempo_calcs import get_cantor_note_rest_pairs, get_tempo_tripling_dur
import itertools


s = Session()

piano = s.new_midi_part("pianoteq", "MIDI through port 0")



def cantor_pitch_cycle(start_pitch):
    return itertools.cycle([start_pitch + x for x in (0, 3, 2, 3, 5, 3, 2, 3)])



def play_cantor_pitch_cycle(start_pitch, volume, scaling_factor=3, note_fade_function=lambda l: min(1, l ** 0.25), min_note_dur=0.002):
    for pitch, (note_dur, rest_dur) in zip(cantor_pitch_cycle(start_pitch), get_cantor_note_rest_pairs(scaling_factor)):
        if note_dur < min_note_dur:
            break
        vol = volume * note_fade_function(note_dur)
        piano.play_note(pitch, vol, note_dur)
        wait(rest_dur)


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


piano.send_midi_cc(64, 0.8)

i = 0
start_spacing_interval = get_tempo_tripling_dur()
while True:
    fork(play_cantor_pitch_cycle, (start_pitch(i), 0.8))
    wait(start_spacing_interval)
    i += 1
