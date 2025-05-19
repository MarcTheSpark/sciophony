from scamp import *
from cantor_utils import infinite_cantor
from scamp_extensions.utilities import remap
import itertools
import math
from dataclasses import dataclass
from typing import Iterator


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


def ideal_scale_factor(n, initial_length=1):
    return 3 ** n * initial_length


def ideal_start_time(n, initial_length=1):
    return sum(3 ** n for n in range(1, n + 1)) * initial_length


@dataclass
class OrchestrationEntry:
    inst: ScampInstrument
    pitch: float | Iterator[float]
    scale_factor: float = None
    start_time: float = None
    
    
# --------------------- START EDITABLE --------------------------

s = Session()

s.tempo = 60


piano = s.new_midi_part("pianoteq", midi_output_device="midi through port 0") #s.new_part("piano")
piano.send_midi_cc(64, 0.8)
clarinet = s.new_part("clarinet")
oboe = s.new_part("oboe")
bassoon = s.new_part("bassoon")
perc = s.new_part("power")


# ---------- manual orchestration ----------

# orchestration = [
#     OrchestrationEntry(piano, cantor_pitch_cycle(80)),
#     OrchestrationEntry(piano, cantor_pitch_cycle(73)),
#     OrchestrationEntry(piano, cantor_pitch_cycle(56)),
#     OrchestrationEntry(piano, cantor_pitch_cycle(49)),
#     OrchestrationEntry(clarinet, cantor_pitch_cycle(80)),
#     OrchestrationEntry(clarinet, cantor_pitch_cycle(73)),
#     OrchestrationEntry(oboe, cantor_pitch_cycle(56)),
#     OrchestrationEntry(bassoon, cantor_pitch_cycle(49))
# ]

# ---------- manual orchestration & timing/scale ----------

# orchestration = [
#     OrchestrationEntry(piano, cantor_pitch_cycle(80), start_time=0, scale_factor=1),
#     OrchestrationEntry(piano, cantor_pitch_cycle(73), start_time=3, scale_factor=3),
#     OrchestrationEntry(piano, cantor_pitch_cycle(56), start_time=12, scale_factor=9),
#     OrchestrationEntry(piano, cantor_pitch_cycle(49), start_time=39, scale_factor=27),
#     OrchestrationEntry(clarinet, cantor_pitch_cycle(80), start_time=120, scale_factor=81),
#     OrchestrationEntry(clarinet, cantor_pitch_cycle(73), start_time=363, scale_factor=243),
#     OrchestrationEntry(oboe, cantor_pitch_cycle(56), start_time=1092, scale_factor=729),
#     OrchestrationEntry(bassoon, cantor_pitch_cycle(49), start_time=3279, scale_factor=2187)
# ]

# --------------- all piano; automatic pitches -----------------


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


orchestration = [
    OrchestrationEntry(piano, cantor_pitch_cycle(start_pitch(i))) for i in range(22)
]


fork(metronome, (1/3,))

# s.start_transcribing()
# s.fast_forward()
# ---------------------- END EDITABLE --------------------------


for i, orch_entry in enumerate(orchestration):
    if orch_entry.scale_factor is None:
        orch_entry.scale_factor = ideal_scale_factor(i)
    if orch_entry.start_time is None:
        orch_entry.start_time = ideal_start_time(i)
        


for orch_entry in orchestration:
    fork(infinite_cantor, args=(orch_entry.inst, orch_entry.pitch, 1.0, orch_entry.scale_factor), schedule_at=orch_entry.start_time)

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



# Can metronome have more layers of 3 that are present at the same time, and overlap more?
# Pitches for infinite cantor
# Use percussion instead of pitched instruments?
# Launching more and cantor sets every time after one ends? (infinitely? What happens with pitch?) Need to have them fade out. Slow enough that you hear the convergent pulsation. Fast enough that there is space in the music
# (need an infinite fading cantor)
# Might want to have an instrument list, so that there is a change in orchestration. (or pitch/instrument pairs)
# Launching them randomly as an ocean?
# Or within a particular cantor there's a stick sound that gets thinner and thinner? (A different idea perhaps...)
# FOR THURSDAY: IMPLEMENT FADING OUT AND ORCHESTRATION CHANGE. (also, is there a way to deal with the insanely big numbers here?

