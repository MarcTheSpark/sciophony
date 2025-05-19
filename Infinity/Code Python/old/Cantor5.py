from scamp import *
from cantor_utils import infinite_cantor
from scamp_extensions.utilities import remap

s = Session()

s.tempo = 30

clarinet = s.new_part("clarinet")

perc = s.new_part("power")

def metronome(note_length):
    initial_note_length_seconds = note_length * 60 / s.tempo
    while True:
        note_length_seconds = note_length * 60 / s.tempo
        print(note_length_seconds)
        perc.play_note(54, 1, note_length)
        note_length_seconds = note_length * 60 / s.tempo
        perc.play_note(54, remap(note_length_seconds, 1, 0, initial_note_length_seconds, initial_note_length_seconds / 2), note_length)
        if note_length_seconds < initial_note_length_seconds / 2:
            note_length *= 2
        
fork(metronome, (0.5,))
        
fork(infinite_cantor, args=(clarinet, 80, 1.0, 3))

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

