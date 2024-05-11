from scamp import *
from cantor_utils import infinite_cantor


s = Session()

clarinet = s.new_part("clarinet")
perc = s.new_part("power")

def metronome():
    while True:
        perc.play_note(54, 1, 0.25)
        
        
fork(metronome)
fork(infinite_cantor, args=(clarinet, 70, 1.0, 0.25))

s.set_rate_target(100, 40, curve_shape=-50, duration_units="time")
# s.tempo_history.show_plot()
wait_for_children_to_finish()