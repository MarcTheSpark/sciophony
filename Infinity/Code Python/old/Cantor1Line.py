from scamp import *
from cantor_utils import infinite_cantor
import itertools 

def cantor_pitch_cycle(start_pitch):
    return itertools.cycle([start_pitch + x for x in (0, 3, 2, 3, 5, 3, 2, 3)])

    
# --------------------- START EDITABLE --------------------------

s = Session()

s.tempo = 60


piano = s.new_part("piano")
piano.send_midi_cc(64, 0.8)
clarinet = s.new_part("clarinet")
oboe = s.new_part("oboe")
bassoon = s.new_part("bassoon")
perc = s.new_part("power")



fork(infinite_cantor, (piano, cantor_pitch_cycle(78), 0.9, 3))

# ---------------  Handle Tempo Acceleration ---------------------

next_target_tempo = s.tempo * 3
next_target_time = 27
s.set_tempo_target(next_target_tempo, next_target_time, curve_shape=-2)

while len(s.children()) > 0:
    wait(next_target_time - s.beat())
    next_target_tempo = s.tempo * 3
    s.set_tempo_target(next_target_tempo, next_target_time * 2, curve_shape=-2)
    next_target_time *= 3
    
# wait_for_children_to_finish()
# s.stop_transcribing().export_to_midi_file("CantorPiano.mid", flatten_tempo_changes=True)
