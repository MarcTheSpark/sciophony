"""
Makes an uneven cantor-like rhythm, which was kind of interesting with the rest of the music.
"""

from dataclasses import dataclass, field
from scamp import *
from scamp_extensions.utilities import TimeVaryingParameter
import itertools
from typing import Iterable, Callable
import random


s = Session(tempo=48.18582690793219)

drum_kit = s.new_midi_part("drum kit", "IAC driver BUS 6")


drum_loop = {
    "kick": ((0, 1.0), (2.75, 0.7)),
    "hihat": ((0.5, 0.6), (0.75, 0.65), (1.0, 0.7), (1.25, 0.75), (1.5, 0.8), (1.75, 0.85), (2.5, 0.6), (3.25, 0.55),
              (3.5, 0.6), (3.75, 0.65), (4.0, 0.7), (4.25, 0.75), (4.5, 0.8), (4.75, 0.85), (5.5, 0.6), (6.25, 0.85)),
    "snare": ((1.25, 0.6), (2.0, 0.8), (5, 0.7), (5.75, 0.9)),
}


@dataclass
class DrumLine:
    inst: ScampInstrument
    pitch: float
    durs: list[float]
    volumes: Iterable[float]
    double_stroke_prob: TimeVaryingParameter = field(default=TimeVaryingParameter(0))
    double_stroke_length: float = 0.14
    play_prob: TimeVaryingParameter = field(default=TimeVaryingParameter(1))
    rest_play_prob: TimeVaryingParameter = field(default=TimeVaryingParameter(0 ))


@dataclass
class DrumLoop:
    lines: list[DrumLine]
    rate_mul: float = 1
    
    def play(self, loop=True):
        while True:
            for i in range(len(self.lines)):
                fork(self.play_line, (i,), initial_rate=self.rate_mul)
            wait_for_children_to_finish()
            if not loop:
                break
        
    def play_line(self, index):
        line = self.lines[index]
        volume_iter = itertools.cycle(line.volumes)
        for dur in line.durs:
            if (dur < 0 and random.random() < line.rest_play_prob()) or (dur > 0 and random.random() > line.play_prob()):
                dur = -dur
                
            if dur > 0:
                vol = next(volume_iter)
                if random.random() < line.double_stroke_prob():
                    note_durs = min(line.double_stroke_length,  dur / 2), dur - min(line.double_stroke_length,  dur / 2)
                    line.inst.play_note(line.pitch, vol, note_durs[0])
                    line.inst.play_note(line.pitch, vol * 0.7, note_durs[1])
                else:
                    line.inst.play_note(line.pitch, vol, dur)
            else:
                wait(abs(dur))
        

kick_line = DrumLine(drum_kit, 36, (0.5, -2.25, 0.5, -3.25), (1.0, 0.7), double_stroke_prob=TimeVaryingParameter([0, 0.5], [90]))

hihat_line = DrumLine(
    drum_kit, 42,
    (-0.5, ) + (0.25, ) * 6  + (-0.5, 0.25) + (-0.5, ) + (0.25, ) * 7 + (-0.5, 0.25) * 2,
    [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.6, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.6, 0.85],
    double_stroke_prob=TimeVaryingParameter([0, 1  ], [90])
)

snare_line = DrumLine(drum_kit, 38, (-1.25, 0.75, 0.75, -2.25, 0.75, 0.75),
                      (0.6, 0.8, 0.7, 0.9), double_stroke_prob=TimeVaryingParameter([0, 0.8], [90]))

main_loop = DrumLoop([kick_line, hihat_line, snare_line], rate_mul=6.5/4)

main_loop.play(True)


# probability of playing a note
# doubling strokes (1 -> 0.25, 0.25, -0.5
# shifting parts forward or back, randomly

    