"""
The main player of the "blues milonga" music using OEIS sequence A319419.
"""

import dataclasses
import math
import random
from typing import Callable, Iterable
from scamp import *
from scamp_extensions.pitch import Scale
from scamp_extensions.rhythm import indispensability_array_from_expression
from utility_funcs import sort_by_frequency
from sequence_definitions import A319419
import itertools
from freshness_tracker import FreshnessTracker

# playback_settings.recording_file_path = "binary_sequence_slow.wav"


NUM_POWERS_OF_2 = 10


blues_scale = Scale.blues(42)


def loop_with_jitter(sequence, jit):
    while True:
        for x in sequence:
            yield x + random.uniform(-jit, jit)


milonga_volume_loop = loop_with_jitter([0.9, 0.65, 0.65, 0.8, 0.65, 0.65, 0.85, 0.65], 0.03)


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
    pitch_transformation: Callable[[int, int], float] = lambda n, p: p if p < 108 else p - 12 if p < 120 else None

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


def pow2_reverse_indices(pow2):
    yield 0
    for k in range(pow2):
        yield from range(2 ** k, 2 ** (k + 1))
    for k in reversed(range(pow2 - 1)):
        yield from range(2 ** k, 2 ** (k + 1))
    yield 0


reversed_indices = list(pow2_reverse_indices(NUM_POWERS_OF_2))


def A319419_symmetry(n):
    return A319419(reversed_indices[n])


def play_bass_line(inst, sequence, scale, transpose=0):
    indispensabilities = indispensability_array_from_expression("3 + 3 + 2", normalize=True)
    freshness_tracker = FreshnessTracker(current_clock().master.time, half_life=0.5)
    for i in reversed_indices:
        if i % 8 == 0:
            next_8_values = [sequence(n) % 6 for n in range(i, i + 8)]
            sorted_by_freq = sort_by_frequency(next_8_values)
            first_most_common = next_8_values.index(sorted_by_freq[0])
            degree_to_play = sorted_by_freq[1] - 6
            wait(first_most_common * 0.25)
            vol = 1 - indispensabilities[first_most_common % 8] / 4
            inst.play_note(scale[degree_to_play] + transpose, vol * freshness_tracker.freshness(degree_to_play),
                           2 - first_most_common * 0.25)


def play_clicks(drum_inst, n):
    for i in range(n):
        drum_inst.play_note(42, 2, 1)


def introduce_new_cycles(drum_inst):
    for i in pow2_reverse_indices(NUM_POWERS_OF_2):
        binary = str(bin(i)[2:])
        if binary.startswith('111') and len(binary) > 4:
            count_up = int(binary[3:], 2)
            volume = (count_up / int((len(binary) - 3) * '1', 2)) * 0.5 + 0.5
            drum_inst.play_note(50 + count_up % 31 % 19 % 11 % 7 % 5, volume, 0.25)
        elif i == 0 or i >= 16 and math.log2(i) == int(math.log2(i)):
            drum_inst.play_note(49, 1, 2, blocking=False)
            wait(0.25)
        else:
            wait(0.25)


current_num = None


def main(use_midi=False):
    global current_num

    s = Session()
    s.timing_policy = "absolute"
    s.tempo = 120

    if use_midi:
        piano = s.new_midi_part("Piano","IAC Driver Bus 1")
        bass =s.new_midi_part("slap bass","IAC Driver Bus 2")
        drums = s.new_midi_part("POWER","IAC Driver Bus 3")
    else:
        piano = s.new_part("Piano")
        bass = s.new_part("slap bass")
        drums = s.new_part("POWER")

    # s.start_transcribing()
    # s.fast_forward()

    main_sequence_player = SequencePlayer(
        piano, A319419_symmetry, milonga_volume_loop, [1 / 4],
        scale=blues_scale,
        stop_n=len(reversed_indices)
    )
    high_beats = dataclasses.replace(
        main_sequence_player,
        inst=drums,
        volumes=[1],
        play_condition=lambda n, x: x > 10,
        pitch_transformation=lambda n, p: 42
    )
    multiples_of_2 = dataclasses.replace(
        main_sequence_player,
        volumes=[1],
        inst=drums,
        pitch_transformation=lambda n, p: 33,
        play_condition=lambda n, x: x > 0 and x % 2 == 0
    )
    multiples_of_5 = dataclasses.replace(
        multiples_of_2,
        play_condition=lambda n, x: x > 0 and x % 5 == 0,
        pitch_transformation=lambda n, p: 76
    )
    multiples_of_7 = dataclasses.replace(
        multiples_of_5,
        play_condition=lambda n, x: x > 0 and x % 7 == 0
    )
    intro = dataclasses.replace(
        main_sequence_player,
        durations= [1, 0.5, 0.5, 1, 0.5, 0.5, 1, 0.5],
        volumes=[1],
        stop_n=24
    )

    intro.play()
    play_clicks(drums, 4)
    fork(introduce_new_cycles, args=(drums, ))
    fork(multiples_of_2.play)
    fork(multiples_of_5.play)
    fork(multiples_of_7.play)
    fork(high_beats.play)
    fork(main_sequence_player.play)
    fork(play_bass_line, args=(bass, A319419_symmetry, blues_scale, 12 if use_midi else 0))

    for x in reversed_indices:
        current_num = x
        wait(0.25)

    # s.stop_transcribing().export_to_midi_file("milongaMidiFull.mid")


if __name__ == '__main__':
    main(use_midi=False)

# Try the opening loop of pitches, but with duration defined by the bassline thing?
# Iso-rhythm style?
# Play with chunks of the opening melody!
# Could be echoing the sequence in the piano
# Operations of translation and stretching
# Could try filtered parts of the piano melody according to pitch.
