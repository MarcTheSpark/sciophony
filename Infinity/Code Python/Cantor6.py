from scamp import *
from cantor_utils import infinite_cantor
from scamp_extensions.utilities import remap
import math

s = Session()

s.tempo = 60

clarinet = s.new_part("clarinet")

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
        
fork(metronome, (1/3,))
        
# fork(infinite_cantor, args=(clarinet, 80, 1.0, 3))

next_target_tempo = s.tempo * 3
next_target_time = 27
s.set_tempo_target(next_target_tempo, next_target_time, curve_shape=-2)

while True:
    wait(next_target_time - s.beat())
    next_target_tempo = s.tempo * 3
    s.set_tempo_target(next_target_tempo, next_target_time * 2, curve_shape=-2)
    next_target_time *= 3
    
wait_for_children_to_finish()



# needs to include more layers of subdivision top layer goes to half volume as middle layer goes to null?
# needs to be triple subdivision obviously!

