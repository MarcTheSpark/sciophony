from scamp import *
from cantor_tempo_calcs import get_cantor_note_rest_pairs, get_tempo_tripling_dur, get_metronome_subdivisions
import itertools


s = Session()

piano = s.new_midi_part("pianoteq", "MIDI through port 0")
perc = s.new_part("power")

tripling_dur = get_tempo_tripling_dur()

metronome_subdivisions = get_metronome_subdivisions(3, 1, scaling_factor=3)


def metronome_swell(pitch):
    swell_env = Envelope([0.2, 0.8, 0], [1.2, 1.8])
    for dur in metronome_subdivisions:
        perc.play_note(pitch, swell_env.value_at(current_clock().time() / tripling_dur), dur)


def metronome_forker(pitch_cycle=itertools.cycle([61, 65, 67, 69, 73])):
    while True:
        fork(metronome_swell, (next(pitch_cycle), ))
        wait(tripling_dur)


fork(metronome_forker)


def cantor_pitch_cycle(start_pitch):
    return itertools.cycle([start_pitch + x for x in (0, 3, 2, 3, 5, 3, 2, 3)])



def play_cantor_pitch_cycle(start_pitch, volume, scaling_factor=3, note_fade_function=lambda l: min(1, l ** 0.25), min_note_dur=0.002):
    for pitch, (note_dur, rest_dur) in zip(cantor_pitch_cycle(start_pitch),
                                           get_cantor_note_rest_pairs(scaling_factor=scaling_factor, min_note_dur=min_note_dur)):
        vol = volume * note_fade_function(note_dur)
        piano.play_note(pitch, vol, note_dur)
        wait(rest_dur)


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


piano.send_midi_cc(64, 0.8)


i = 0
while True:
    fork(play_cantor_pitch_cycle, (start_pitch(i), 0.8))
    wait(tripling_dur)
    i += 1


"""
Work on orchestration tools.

- What would an object oriented version of this look like? Like CantorSetPlayer
objects or something plus a scheduler that places them in time? Different subclasses
of CantorSetPlayer that play it in different ways (e.g. strum, percussion, different
melodic patterns), or only play parts of the set, or whatever?
"""