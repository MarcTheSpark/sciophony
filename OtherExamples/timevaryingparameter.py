from scamp import *
from scamp_extensions.utilities import TimeVaryingParameter
import random

s = Session(tempo=120)

piano = s.new_part("piano")

min_pitch = TimeVaryingParameter([40, 80, 60], [20, 20])
max_pitch = TimeVaryingParameter([80, 90], [40])

while True:
    piano.play_note(int(random.uniform(min_pitch(), max_pitch())), 0.7, 0.2)

