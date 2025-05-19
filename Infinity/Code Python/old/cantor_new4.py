from cantor_orchestration import CantorChords, CantorMelody, MetronomeSwell, default_environment
import cantor_tempo_utils
from scamp import *

# Affects all melodies/metronomes/etc. (scales duration)
default_environment.scaling_factor = 3

s = Session()


piano = s.new_midi_part("piano","IAC driver BUS 1")
piano.send_midi_cc(64,1)
perc = s.new_midi_part("power","IAC driver BUS 2")
guitar = s.new_midi_part("nylon guitar","IAC driver BUS 3")
flute = s.new_midi_part("flute","IAC driver BUS 4")
bass = s.new_midi_part("bass","IAC driver BUS 5")

#perc = s.new_part("power")

swell_envelope= Envelope([0.2, 1.0, 0], [1.5, 2.5],[-1, -3])

def swell_loop():
    swells = [
        MetronomeSwell(perc, 70, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 71, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 54, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 79, swell_envelope/2, subdivision_depth=0, play_condition=lambda i: i % 3 !=0)
    ]

    while True:
        for swell in swells:
            fork(swell.play)
            wait(default_environment.tripling_time)


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)

guitar_cords =[(58,63,68),(61,63,64)]


score = [
    (0, swell_loop),
    (0, CantorMelody(bass, 37,intervals= [0], further_scaling=9).play),
    (7, CantorMelody(flute, start_pitch(0),further_scaling=3).play),
    (11, CantorChords(guitar, guitar_cords,further_scaling=1,volume_function = lambda i, dur: 0.6 * dur ** 0.25, roll_interval=0.1).play),
    (22, CantorChords(guitar, guitar_cords,further_scaling=1,volume_function = lambda i, dur: 0.6 * dur ** 0.25, roll_interval=0.1).play)


]

start_t = 0
for num_cascades in range(3, 11, 2):
    for i in range(num_cascades):
        score.append((start_t + i, CantorMelody(piano, start_pitch(i)).play))
    start_t += num_cascades + 10

""" for i in range(8):
    score.append((i, CantorMelody(piano, start_pitch(i)).play))

for i in range(8):
    score.append((i+12, CantorMelody(piano, start_pitch(i)).play))

for i in range(8):
    score.append((i+24, CantorMelody(piano, start_pitch(i)).play)) """


score.sort(key=lambda e: e[0])


# play score
t = 0
for tripling_t, func in score:
    wait((tripling_t - t) * default_environment.tripling_time)
    fork(func)
    t = tripling_t
    
wait_for_children_to_finish()
