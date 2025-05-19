from cantor_orchestration import CantorChords, CantorMelody, MetronomeSwell, default_environment
import cantor_tempo_utils
from scamp import *

# Affects all melodies/metronomes/etc. (scales duration)
default_environment.scaling_factor = 3

s = Session()

guitar = s.new_part("nylon guitar")
piano = s.new_midi_part("piano", "midi through port 0")
piano.send_midi_cc(64, 1)
perc = s.new_part("power")


def swell_loop():
    swells = [
        MetronomeSwell(perc, 61, Envelope([1, 1.0, 0], [1.2, 1.8]), subdivision_depth=1, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 63, Envelope([1, 1.0, 0], [1.2, 1.8]), subdivision_depth=1, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 65, Envelope([1, 1.0, 0], [1.2, 1.8]), subdivision_depth=1, play_condition=lambda i: i % 3 !=0),
        MetronomeSwell(perc, 67, Envelope([1, 1.0, 0], [1.2, 1.8]), subdivision_depth=1, play_condition=lambda i: i % 3 !=0)
    ]

    while True:
        for swell in swells:
            fork(swell.play)
            wait(default_environment.tripling_time)


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


score = [
    (0, swell_loop)
]


start_t = 0
for num_cascades in range(2, 11, 3):
    for i in range(num_cascades):
        score.append((start_t + i, CantorMelody(piano, start_pitch(i), volume_function=lambda i, dur: 0.8* dur ** 0.25).play))
    start_t += num_cascades + 10


score.sort(key=lambda e: e[0])


# play score
t = 0
for tripling_t, func in score:
    wait((tripling_t - t) * default_environment.tripling_time)
    fork(func)
    t = tripling_t
    
wait_for_children_to_finish()
