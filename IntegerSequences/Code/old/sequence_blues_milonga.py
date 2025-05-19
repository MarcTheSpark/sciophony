"""
Ideas: out of range pitches are played by a repeated, increasing-in-volume, octaves in (violin?)
harmony?
Syncopate bass
"""

import dataclasses
from typing import Callable, Iterable

from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
from utility_funcs import sort_by_frequency
from sequence_definitions import A319419
import itertools

s = Session()

s.tempo = 120
bass = s.new_part("slap bass")
piano = s.new_part("Piano")
drums = s.new_part("POWER")

#piano=s.new_midi_part("Piano","IAC Driver Bus 1")
#bass=s.new_midi_part("slap bass","IAC Driver Bus 2")
#drums = s.new_midi_part("POWER","IAC Driver Bus 3")


blues_scale = Scale.blues(42)

milonga_volume_loop = [1, 0.5, 0.5, 1, 0.5, 0.5, 1, 0.5]


@dataclasses.dataclass
class SequencePlayer:
    inst: ScampInstrument
    sequence_formula: Callable[[int], int]
    volumes: Iterable[float]
    durations: Iterable[float]
    start_n: int = 0
    stop_n: int = None
    scale: Scale = Scale.chromatic(60)
    play_condition: Callable[[int, int], bool] = lambda n, x: True
    scale_degree_function: Callable[[int, int], float] = lambda n, x: x
    pitch_transformation: Callable[[int, int], float] = lambda n, x: x

    def play(self):
        indices = (range(self.start_n, self.stop_n) if self.stop_n else itertools.count(self.start_n))
        for n, volume, duration in zip(indices, itertools.cycle(self.volumes), itertools.cycle(self.durations)):
            x = self.sequence_formula(n)
            if self.play_condition(n, x):
                scale_degree = self.scale_degree_function(n, x)
                pitch = self.pitch_transformation(n, self.scale[scale_degree])
                self.inst.play_note(pitch, volume, duration)
            else:
                wait(duration)


main_sequence_player = SequencePlayer(
    piano, A319419, milonga_volume_loop, [1/4],
    scale=blues_scale
)
high_beats = dataclasses.replace(
    main_sequence_player,
    inst=drums,
    volumes=[1],
    play_condition=lambda n, x: x > 10,
    pitch_transformation=lambda n, x: 42
)
multiples_of_2 = dataclasses.replace(
    main_sequence_player,
    volumes=itertools.repeat(1),
    inst=drums,
    pitch_transformation=lambda n, x: 33,
    play_condition=lambda n, x: x > 0 and x % 2 == 0
)
multiples_of_5 = dataclasses.replace(
    multiples_of_2,
    play_condition=lambda n, x: x > 0 and x % 5 == 0,
    pitch_transformation=lambda n, x: 71
)
multiples_of_7 = dataclasses.replace(
    multiples_of_5,
    play_condition=lambda n, x: x > 0 and x % 7 == 0
)


def play_bass_line(inst, sequence, scale):
    for i in itertools.count():
        if i % 8 == 0:
            next_8_values = [sequence(n) % 6 for n in range(i, i + 8)]
            degree_to_play = sort_by_frequency(next_8_values)[0] - 6
            inst.play_note(scale[degree_to_play], 1, 2)


fork(multiples_of_2.play)
fork(multiples_of_5.play)
fork(multiples_of_7.play)
fork(high_beats.play)
fork(main_sequence_player.play)
fork(play_bass_line, args=(bass, A319419, blues_scale))
wait_for_children_to_finish()

# def play_sequence_reverse(inst, start_n, stop_n):
#     for i in range(nsteps):
#         inst.play_note(my_scale[A319419(i)], rhythm_loop[i], volume[i])


# def play_high_beats(inst,nsteps,thresh):
#     for i in range(nsteps):
#         if A319419(i) > thresh:
#             inst.play_note(42, 2, rhythm_loop[i])
#         else:
#             wait(rhythm_loop[i])

# def play_multiple_N(inst,nsteps,N,drumnote,vol):
#     for i in range(nsteps):
#         if A319419(i) > 0 and A319419(i) % N == 0:
#             inst.play_note(drumnote, vol, rhythm_loop[i])
#             print(A319419(i))
#         else:
#             wait(rhythm_loop[i])
#

def play_sequence(inst, sequence_formula, volumes=itertools.repeat(1), durations=itertools.repeat(1/4),
                  start_n=0, stop_n=None, scale=blues_scale, play_condition=lambda n, x: True,
                  scale_degree_function=lambda n, x: x, pitch_transformation=lambda n, x: x):
    indices = (range(start_n, stop_n) if stop_n else itertools.count(start_n))
    for n, volume, duration in zip(indices, volumes, durations):
        x = sequence_formula(n)
        if play_condition(n, x):
            scale_degree = scale_degree_function(n, x)
            pitch = pitch_transformation(n, scale[scale_degree])
            inst.play_note(pitch, volume, duration)
        else:
            wait(duration)


def play_clicks(n):
    for i in range(n):
        drums.play_note(42, 2, 1)


def play_multiples_of_N(N, drum_note, volume):
    play_sequence(drums, A319419, itertools.repeat(volume), milonga_rhythm_loop,
                  play_condition=lambda n, x: x > 0 and x % N == 0, pitch_transformation=lambda  n, x: drum_note)


# note: weird that the volume loop was being used for the durations, but it works
# play_sequence(piano, A319419, durations=milonga_volume_loop, stop_n=24)
# play_clicks(4)

fork(play_multiples_of_N, args=(2, 33, 1))
fork(play_multiples_of_N, args=(7, 71, 1))
fork(play_multiples_of_N, args=(5, 71, 1))
play_sequence(drums, A319419, milonga_volume_loop, milonga_rhythm_loop, play_condition=lambda n, x: x > 10,
              pitch_transformation=lambda n, x: 42)
play_sequence(piano, A319419, milonga_volume_loop, milonga_rhythm_loop)


def play_bass_line(inst,nsteps):
    for i in range(nsteps):
        if (i%8)==0:
            t=[A319419(n) for n in range(i, i + 8)]
            cha=sort_by_frequency(t)
            ch = np.array(cha)
            #ch = [cha % 6 for x in cha]
            ch = ch % 6 - 12
            print(i)
            print(ch)
            inst.play_note(my_scale[ch[1]+6],1,2)


# def play_high_beats(inst,nsteps,thresh):
#     for i in range(nsteps):
#         if A319419(i) > thresh:
#             inst.play_note(42, 2, rhythm_loop[i])
#         else:
#             wait(rhythm_loop[i])


# def play_odd_even(inst,nsteps):
#     for i in range(nsteps):
#         if A319419(i) % 2 == 0:
#             inst.play_note(33, 2, rhythm_loop[i])
#         else:
#             wait(rhythm_loop[i])
#
# def play_multiple_N(inst,nsteps,N,drumnote,vol):
#     for i in range(nsteps):
#         if A319419(i) > 0 and A319419(i) % N == 0:
#             inst.play_note(drumnote, vol, rhythm_loop[i])
#             print(A319419(i))
#         else:
#             wait(rhythm_loop[i])
#
# def play_bass_line(inst,nsteps):
#     for i in range(nsteps):
#         if (i%8)==0:
#             t=[A319419(n) for n in range(i, i + 8)]
#             cha=sort_by_frequency(t)
#             ch = np.array(cha)
#             #ch = [cha % 6 for x in cha]
#             ch = ch % 6 - 12
#             print(i)
#             print(ch)
#             inst.play_note(my_scale[ch[1]+6],1,2)
#             #wait(2)
# """             if len(ch) < 5:
#                 for j in range(len(ch)):
#                     inst.play_note(my_scale[ch[j]],1,0.5)
#                 wait(4-len(ch))
#             else:
#                 for j in range(4):
#                     inst.play_note(my_scale[ch[j]],1,0.5)
#                     print("long chord") """
            
    

        


# def play_interlude():
#     for i in range(4):
#         drums.play_note(42,2,1)

    

# NSTEPS_intro = 24
# NSTEPS_main = 2**10
# play_sequence_reverse(piano,NSTEPS_intro)
#
# play_interlude()
# s.fork(play_sequence, args = (piano, NSTEPS_main))
# s.fork(play_bass_line, args = (bass,NSTEPS_main))
# s.fork(play_high_beats, args = (drums,NSTEPS_main,10))
# s.fork(play_multiple_N, args = (drums,NSTEPS_main,2,33,1))
# s.fork(play_multiple_N, args = (drums,NSTEPS_main,7,71,1))
# s.fork(play_multiple_N, args = (drums,NSTEPS_main,5,71,1))
# s.wait_for_children_to_finish()

#perf=s.stop_transcribing()
#perf.export_to_midi_file("Blues_Milonga_1.mid")

#play_interlude()
#play_sequence_reverse(inst2,16)






