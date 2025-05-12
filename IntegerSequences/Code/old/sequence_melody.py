import dataclasses
import itertools
from typing import Callable, Sequence
from scamp import ScampInstrument, wait
from scamp_extensions.pitch import Scale
from scamp_extensions.utilities import wrap_to_range


class IntCondition:

    def __init__(self, test_func: Callable[[int], bool]):
        self.test_func = test_func

    def __call__(self, x):
        return self.test_func(x)

    def __and__(self, other):
        return IntCondition(lambda x: self(x) and other(x))

    def __or__(self, other):
        return IntCondition(lambda x: self(x) or other(x))

    def __invert__(self):
        return IntCondition(lambda x: not self(x))


class ModCondition(IntCondition):

    def __init__(self, mod, remainder):
        super().__init__(lambda x: x % mod == remainder)


@dataclasses.dataclass
class MelodySequencePlayer:
    inst: ScampInstrument
    sequence_formula: Callable[[int], int]
    scale_step_range: tuple[int, int]
    play_condition: Callable[[int], bool]
    new_note_condition: Callable[[int], bool]
    interval_choices: Sequence[float] = None
    scale: Scale = Scale.chromatic(0)
    rounding_scale: Scale = Scale.chromatic(0)
    start_n: int = 0
    stop_n: int = None
    dur_subdivision = 1/4

    def play(self):
        indices = (range(self.start_n, self.stop_n) if self.stop_n else itertools.count(self.start_n))
        current_note, current_step = None, None

        def _start_new_note(x):
            nonlocal current_note, current_step
            if self.interval_choices and current_step is not None:
                current_step += self.interval_choices[x % len(self.interval_choices)]
            else:
                current_step = wrap_to_range(x, *self.scale_step_range, True)
            current_step = wrap_to_range(current_step, *self.scale_step_range, True)
            current_note = self.inst.start_note(self.rounding_scale.round(self.scale[current_step]), 1.0)

        def _end_active_note():
            nonlocal current_note
            if current_note is not None:
                current_note.end()
            current_note = None

        for n in indices:
            x = self.sequence_formula(n)
            if self.play_condition(x):
                # Play this beat
                if current_note is not None:
                    # was playing last beat
                    if self.new_note_condition(x):
                        # rearticulate and change note
                        _end_active_note()
                        _start_new_note(x)
                    else:
                        # hold old note, so no need to do anything
                        pass
                else:
                    # was not playing last beat
                    # so start a new note
                    _start_new_note(x)
            else:
                # Off this beat; end any active note, and reset the current step
                _end_active_note()
                current_step = None

            wait(self.dur_subdivision)
