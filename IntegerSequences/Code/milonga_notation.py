"""
Ideas: out of range pitches are played by a repeated, increasing-in-volume, octaves in (violin?)
harmony?
Syncopate bass !
"""

import dataclasses
import math
from typing import Callable, Iterable
from scamp import *
from scamp_extensions.pitch import Scale
from utility_funcs import sort_by_frequency
from sequence_definitions import A319419
import itertools
playback_settings.recording_file_path = "old/binary_sequence.wav"

s = Session()

s.tempo = 120
bass = s.new_part("slap bass")
piano_treble = s.new_part("Piano", clef_preference="treble")
piano_bass = s.new_part("Piano", clef_preference="bass")
drums1 = s.new_part("Closed Hi-Hat", preset="POWER")
drums2 = s.new_part("Rim Click", preset="POWER")
drums3 = s.new_part("Wood Block", preset="POWER")
drums5 = s.new_part("", "POWER")

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
    pitch_transformation: Callable[[int, int], float] = lambda n, p: p if p < 108 else None

    def play(self):
        indices = (range(self.start_n, self.stop_n) if self.stop_n else itertools.count(self.start_n))
        for n, volume, duration in zip(indices, itertools.cycle(self.volumes), itertools.cycle(self.durations)):
            x = self.sequence_formula(n)
            if self.play_condition(n, x):
                scale_degree = self.scale_degree_function(n, x)
                pitch = self.pitch_transformation(n, self.scale[scale_degree])
                props = ["accent"] if volume > 0.8 else []
                if pitch is not None :
                    if pitch > 103:
                        pitch -= 24
                        props.append("15va")
                    elif pitch > 90:
                        pitch -= 12
                        props.append("8va")
                self.inst.play_note(pitch, volume, duration, props)
            else:
                wait(duration)


main_sequence_player = SequencePlayer(
    piano_bass, A319419, milonga_volume_loop, [1/4],
    scale=blues_scale
)
main_sequence_player_bass = SequencePlayer(
    piano_bass, A319419, milonga_volume_loop, [1/4],
    scale=blues_scale,
    play_condition=lambda n, x: x < 10
)
main_sequence_player_treble = SequencePlayer(
    piano_treble, A319419, milonga_volume_loop, [1/4],
    play_condition=lambda n, x: x >= 10,
    scale=blues_scale
)
high_beats = dataclasses.replace(
    main_sequence_player,
    inst=drums1,
    volumes=[1],
    play_condition=lambda n, x: x > 10,
    pitch_transformation=lambda n, p: 42
)
multiples_of_2 = dataclasses.replace(
    main_sequence_player,
    volumes=[1],
    inst=drums2,
    pitch_transformation=lambda n, p: 33,
    play_condition=lambda n, x: x > 0 and x % 2 == 0
)
multiples_of_5 = dataclasses.replace(
    multiples_of_2,
    inst=drums3,
    play_condition=lambda n, x: x > 0 and x % 5 == 0,
    pitch_transformation=lambda n, p: 76
)
multiples_of_7 = dataclasses.replace(
    multiples_of_5,
    inst=drums3,
    play_condition=lambda n, x: x > 0 and x % 7 == 0
)
intro = dataclasses.replace(
    main_sequence_player,
    durations=milonga_volume_loop,
    volumes=[1],
    stop_n=24
)


def play_bass_line(inst, sequence, scale):
    for i in itertools.count():
        if i % 8 == 0:
            next_8_values = [sequence(n) % 6 for n in range(i, i + 8)]
            sorted_by_freq = sort_by_frequency(next_8_values)
            first_most_common = next_8_values.index(sorted_by_freq[0])
            degree_to_play = sorted_by_freq[1] - 6
            wait(first_most_common * 0.25)
            inst.play_note(scale[degree_to_play], 1, 2 - first_most_common * 0.25)


def play_clicks(n):
    for i in range(n):
        drums1.play_note(42, 2, 1)


def introduce_new_cycles():
    for i in itertools.count():
        binary = str(bin(i)[2:])
        if binary.startswith('111') and len(binary) > 4:
            count_up = int(binary[3:], 2)
            volume = (count_up / int((len(binary) - 3) * '1', 2)) * 0.5 + 0.5
            pitch = 50 + 3 * count_up % 31 % 19 % 11 % 7 % 5
            # written_pitch = [64, 67, 71, 74, 77][count_up % 31 % 19 % 11 % 7 % 5]
            drums5.play_note(pitch, volume, 0.25)
            # drums5.play_note(written_pitch, volume, 0.25, f"pitch = {pitch}")
        elif i == 0 or i >= 16 and math.log2(i) == int(math.log2(i)):
            drums5.play_note(49, 1, 2, "accent", blocking=False)
            wait(0.25)
        else:
            wait(0.25)


s.start_transcribing()
s.fast_forward()
intro.play()
play_clicks(4)
fork(introduce_new_cycles)
# fork(multiples_of_2.play)
# fork(multiples_of_5.play)
# fork(multiples_of_7.play)
# fork(high_beats.play)
# s.start_transcribing([piano_treble, piano_bass])
# fork(main_sequence_player_bass.play)
# fork(main_sequence_player_treble.play)
fork(play_bass_line, args=(bass, A319419, blues_scale))
wait(600, units="time")
score = s.stop_transcribing().to_score(time_signature=["2/4"] * 4 + ["3/4"] + ["2/4", "2/4", "3/8", "2/4"])
score.export_music_xml("Notation/BluesSequenceMilonga3.musicxml")
# wait_for_children_to_finish()

