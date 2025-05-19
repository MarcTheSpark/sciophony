from cantor_orchestration import CantorChords, CantorMelody, MetronomeSwell, default_environment
import cantor_tempo_utils
from scamp import *

# Affects all melodies/metronomes/etc. (scales duration)
default_environment.scaling_factor = 3

s = Session()

clarinet = s.new_part("Clarinet")
guitar = s.new_part("nylon guitar")
perc = s.new_part("power")


# ----- CantorMelody options -------
# intervals: Sequence[float] = (0, 3, 2, 3, 5, 3, 2, 3)
# volume_function: Callable[[int, float], float] = lambda i, dur: dur ** 0.25
# further_scaling: float = 1
# min_note_dur: float = 0.002
# max_segments: int = None
# play_condition: Callable[[int], bool] = lambda i: True

# ----- Cantor melody examples -------
# CantorMelody(clarinet, 70).play()
# CantorMelody(clarinet, 70, intervals=(0, 1, 3)).play()
# CantorMelody(clarinet, 70, intervals=(0, 1, 3), further_scaling=1/9).play()
# CantorMelody(clarinet, 70, intervals=(0, 1, 3), further_scaling=1/3, volume_function=lambda i, dur: 1 if i % 4 == 0 else 0.3).play()


# ----- CantorChords options -------
# (same as above except no intervals sequence, and instead)
# chord_sequence: Sequence[Sequence[float]]
# roll_interval: float = 0

# ----- CantorChords examples ------
# CantorChords(guitar, [[70, 75, 77], [73, 75]], roll_interval=0.03, further_scaling=0.2).play()


# ------ MetronomeSwell options -----
# instrument: ScampInstrument
# pitch: float
# swell_env: Envelope
# subdivision_depth: int =0

# ------ MetronomeSwell examples -----
#MetronomeSwell(perc, 61, Envelope([0.2, 1.0, 0], [1.2, 1.8])).play()


def swell_loop():
    swells = [
        MetronomeSwell(perc, 61, Envelope([1, 1.0, 0], [1.2, 1.8])),
        MetronomeSwell(perc, 63, Envelope([1, 1.0, 0], [1.2, 1.8])),
        MetronomeSwell(perc, 65, Envelope([1, 1.0, 0], [1.2, 1.8])),
        MetronomeSwell(perc, 67, Envelope([1, 1.0, 0], [1.2, 1.8]))
    ]

    while True:
        for swell in swells:
            fork(swell.play)
            wait(default_environment.tripling_time)



clar_chords = CantorChords(clarinet, [[70, 75, 77], [73, 75]])
guitar_chords = CantorChords(guitar, [[70, 75, 77], [73, 75]],
                             roll_interval=0.1,
                             further_scaling=1/2,
                             play_condition=lambda i: i % 3 == 0)
clar_mel = CantorMelody(clarinet, 70, further_scaling=1/3)

score = [
    (0, swell_loop),
    (0, clar_chords.play),
    (1, guitar_chords.play),
    (3, clar_mel.play),
    (4, clar_chords.play)
]


# play score
t = 0
for tripling_t, func in score:
    wait((tripling_t - t) * default_environment.tripling_time)
    fork(func)
    t = tripling_t
    
wait_for_children_to_finish()
