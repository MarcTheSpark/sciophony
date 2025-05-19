from dataclasses import dataclass, field
from cantor_tempo_utils import (get_tempo_tripling_dur, get_first_dur, get_metronome_subdivisions,
                                get_cantor_note_rest_pairs)
from abc import ABC, abstractmethod
from typing import Sequence, Callable
from scamp import ScampInstrument, wait_for_children_to_finish, wait, Envelope
import math


@dataclass
class Environment:
    
    scaling_factor: float = 3
    
    @property
    def tripling_time(self):
        return get_tempo_tripling_dur(self.scaling_factor)
    
    @property
    def first_dur(self):
        return get_first_dur(self.scaling_factor)
    
    def get_metronome_durs(self, num_tripling_cycles, subdivision_depth):
        return get_metronome_subdivisions(num_tripling_cycles, subdivision_depth, self.scaling_factor)
    
    def get_cantor_note_rest_pairs(self, min_note_dur=0.002):
        return get_cantor_note_rest_pairs(self.scaling_factor, min_note_dur=min_note_dur)


default_environment = Environment()


def _get_default_environment():
    return default_environment


@dataclass(kw_only=True)
class CantorOrchestration:
    further_scaling: float = 1
    min_note_dur: float = 0.002
    environment: Environment = field(default_factory=_get_default_environment)
    max_segments: int = None
    play_condition: Callable[[int], bool] = lambda i: True
    
    def start_play(self):
        """Override if action is needed at the start of playing this orchestration"""
        pass
        
    @abstractmethod
    def play_segment(self, i, dur):
        """
        Required abstractmethod determining how to play a single segment of this cantor orchestration.
        
        :param i: the number of the segment
        :param dur: the length of the segment
        """
        pass
    
    def end_play(self):
        """Override if action is needed at the end of playing this orchestration"""
        pass

    def note_rest_pairs(self):
        return get_cantor_note_rest_pairs(
            scaling_factor=self.environment.scaling_factor * self.further_scaling,
            min_note_dur=self.min_note_dur
        )
    
    def play(self):
        self.start_play()
        for i, (note_dur, rest_dur) in enumerate(self.note_rest_pairs()):
            if self.max_segments and i >= self.max_segments:
                break
            if self.play_condition(i):
                self.play_segment(i, note_dur)
            else:
                wait(note_dur)
            wait(rest_dur)
        self.end_play()
            

@dataclass(init=False)
class CantorMelody(CantorOrchestration):
    instrument: ScampInstrument
    start_pitch: float
    intervals: Sequence[float] = (0, 3, 2, 3, 5, 3, 2, 3)
    volume_function: Callable[[int, float], float] = lambda i, dur: dur ** 0.25
    
    def __init__(self, instrument: ScampInstrument, start_pitch: float,
                 intervals: Sequence[float] = (0, 3, 2, 3, 5, 3, 2, 3),
                 volume_function: Callable[[int, float], float] = lambda i, dur: dur ** 0.25, **kwargs):
        self.instrument = instrument
        self.start_pitch = start_pitch
        self.intervals = intervals
        self.volume_function = volume_function
        super().__init__(**kwargs)

    def play_segment(self, i, dur):
        pitch = self.start_pitch + self.intervals[i % len(self.intervals)]
        volume = self.volume_function(i, dur / (self.environment.first_dur * self.further_scaling))
        self.instrument.play_note(pitch, volume, dur)
        

@dataclass(init=False)
class CantorChords(CantorOrchestration):
    instrument: ScampInstrument
    chord_sequence: Sequence[Sequence[float]]
    roll_start_volume: float = 0.4
    roll_end_volume: float = 0.7
    volume_function: Callable[[int, float], float] = lambda i, dur: dur ** 0.25
    roll_interval: float = 0.08
    
    def __init__(self, instrument, chord_sequence,
                 volume_function: Callable[[int, float], float] = lambda i, dur: dur ** 0.25,
                 roll_interval: float = 0.08, **kwargs):
        self.instrument = instrument
        self.chord_sequence = chord_sequence
        self.volume_function = volume_function
        self.roll_interval = roll_interval
        super().__init__(**kwargs)

    @staticmethod
    def _roll_chord(inst, pitches, min_volume, max_volume, dur, roll_interval):
        roll_interval = min(roll_interval, dur / len(pitches))
        for i, pitch in enumerate(pitches):
            volume = max_volume if len(pitches) <= 1 else \
                     i / (len(pitches) - 1) * (max_volume - min_volume) + min_volume
            inst.play_note(pitch, volume, dur, blocking=False)
            dur -= roll_interval
            wait(roll_interval)
        wait_for_children_to_finish()

    def play_segment(self, i, dur):
        pitches = self.chord_sequence[i % len(self.chord_sequence)]
        volume = self.volume_function(i, dur / (self.environment.first_dur * self.further_scaling))
        if self.roll_interval:
            CantorChords._roll_chord(self.instrument, pitches, volume * self.roll_start_volume, volume * self.roll_end_volume,
                                     dur, self.roll_interval)
        else:
            self.instrument.play_chord(pitches, volume, dur)


@dataclass
class MetronomeOrchestration:
    num_tripling_cycles: int
    subdivision_depth: int
    further_scaling: float = 1
    environment: Environment = field(default_factory=_get_default_environment)
    play_condition: Callable[[int], bool] = lambda i: True
    
    def start_play(self):
        """Override if action is needed at the start of playing this orchestration"""
        pass
        
    @abstractmethod
    def play_tick(self, i, tripling_progress, dur):
        """
        Required abstractmethod determining how to play a single tick of this metronome.
        
        :param i: the number of the segment
        :param tripling_progress: how many triplings we have gone through (fractional)
        :param dur: the length of the segment
        """
        pass
    
    def end_play(self):
        """Override if action is needed at the end of playing this orchestration"""
        pass

    def tick_durs(self):
        return get_metronome_subdivisions(self.num_tripling_cycles, self.subdivision_depth,
                                          self.environment.scaling_factor * self.further_scaling)
    
    def play(self):
        t = 0
        for i, dur in enumerate(self.tick_durs()):
            if self.play_condition(i):
                self.play_tick(i, t / self.environment.tripling_time, dur)
            else:
                wait(dur)
            t += dur


@dataclass(init=False)
class MetronomeSwell(MetronomeOrchestration):
    instrument: ScampInstrument = None
    pitch: float = None
    swell_env: Envelope = None
    subdivision_depth: int = 0
    
    def __init__(self, instrument, pitch, swell_env, subdivision_depth=0, **kwargs):
        self.instrument = instrument
        self.pitch = pitch
        self.swell_env = swell_env
        self.subdivision_depth = subdivision_depth
        super().__init__(math.ceil(swell_env.length()), subdivision_depth, **kwargs)

    def play_tick(self, i, tripling_progress, dur):
        self.instrument.play_note(self.pitch, self.swell_env.value_at(tripling_progress), dur)
