from scamp import *
from cantor_utils import infinite_cantor
from scamp_extensions.utilities import remap
import itertools
import math

s = Session()

s.tempo = 60

clarinet = s.new_part("clarinet")
oboe = s.new_part("oboe")
bassoon = s.new_part("bassoon")
perc = s.new_part("power")


def metronome(note_length):    
    i = 0
    while True:
        if i >= 54:
            note_length *= 3
            i = 0
        
        progress = i / 54
        if i % 3 == 0:
            perc.play_note(40, 1.0, note_length, blocking=False)
            perc.play_note(54, 1.0, note_length)
        else:
            perc.play_note(40, (1 - progress) ** 3, note_length, blocking=False)
            perc.play_note(54, (1 - progress) ** 2, note_length)
        i += 1


def cantor_pitch_cycle(start_pitch):
    return itertools.cycle([start_pitch + x for x in (0, 3, 2, 3, 5, 3, 2, 3)])


fork(metronome, (1/3,))        
fork(metronome, (1/9,))        
fork(infinite_cantor, args=(clarinet, cantor_pitch_cycle(80), 1.0, 1))
fork(infinite_cantor, args=(oboe, cantor_pitch_cycle(80), 1.0, 1))
fork(infinite_cantor, args=(bassoon, cantor_pitch_cycle(61), 1.0, 3))

next_target_tempo = s.tempo * 3
next_target_time = 27
s.set_tempo_target(next_target_tempo, next_target_time, curve_shape=-2)

while True:
    wait(next_target_time - s.beat())
    next_target_tempo = s.tempo * 3
    s.set_tempo_target(next_target_tempo, next_target_time * 2, curve_shape=-2)
    next_target_time *= 3
    
wait_for_children_to_finish()



# Can metronome have more layers of 3 that are present at the same time, and overlap more?
# Pitches for infinite cantor
# Use percussion instead of pitched instruments?
# Launching more and cantor sets every time after one ends? (infinitely? What happens with pitch?) Need to have them fade out. Slow enough that you hear the convergent pulsation. Fast enough that there is space in the music
# (need an infinite fading cantor)
# Might want to have an instrument list, so that there is a change in orchestration. (or pitch/instrument pairs)
# Launching them randomly as an ocean?
# Or within a particular cantor there's a stick sound that gets thinner and thinner? (A different idea perhaps...)
# FOR THURSDAY: IMPLEMENT FADING OUT AND ORCHESTRATION CHANGE. (also, is there a way to deal with the insanely big numbers here?

