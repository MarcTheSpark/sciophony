"""
This plays the recording of snapshots of which individuals are active, made by evolution_on_thread.py.
"""
from bisect import bisect_left
from itertools import zip_longest
from scamp.utilities import floor_to_multiple
from evolution_species import *
import threading


class EvolutionMusicRecordingPlayer(threading.Thread):

    def __init__(self, pickled_snapshots_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import pickle
        with open(pickled_snapshots_file, "rb") as f:
            self.snapshots = pickle.load(f)

        self._recalc()
        self._reset()

    def reset_to_start(self):
        self._recalc()
        self._reset()

    def _recalc(self):
        """Recalculates self._beats and self._times."""
        self._beats = [ss[0] for ss in self.snapshots]
        self._times = [ss[1] for ss in self.snapshots]

    def _reset(self):
        self.b = self.snapshots[0][0]
        self.t = self.snapshots[0][1]
        self.snapshot_index = 0

    def current_snapshot(self):
        return self.snapshots[self.snapshot_index]

    def index_at_beat(self, b):
        return bisect_left(self._beats, b)

    def index_at_time(self, t):
        return bisect_left(self._times, t)

    def snapshot_at_beat(self, b):
        return self.snapshots[self.index_at_beat(b)]

    def snapshot_at_time(self, t):
        return self.snapshots[self.index_at_time(t)]

    def advance_time(self, dt):
        self.t += dt
        while self.time() < self.t:
            self.snapshot_index += 1
        self.b = self.beat()

    def advance_beat(self, db):
        self.b += db
        while self.beat() < self.b:
            # advance forward until we are at the given beat
            self.snapshot_index += 1
        self.t = self.time()

    def go_to_beat(self, b):
        self.snapshot_index = self.index_at_beat(b)

    def go_to_time(self, t):
        self.snapshot_index = self.index_at_time(t)

    def beat(self):
        return self.current_snapshot()[0]

    def time(self):
        return self.current_snapshot()[1]

    @property
    def playing_individuals(self):
        return self.current_snapshot()[2]

    @property
    def disturbances(self):
        return self.current_snapshot()[3]

    def delete_fast_forwards(self, ripple_delete=True, shift_to_zero=False):
        return self.delete_conditional(
            lambda ss: ss[4],
            ripple_delete=ripple_delete, shift_to_zero=shift_to_zero
        )

    def delete_beat_ranges(self, *beat_ranges, ripple_delete=True, shift_to_zero=False):
        return self.delete_conditional(
            lambda ss: any(start_beat <= ss[0] < end_beat for start_beat, end_beat in beat_ranges),
            ripple_delete=ripple_delete, shift_to_zero=shift_to_zero
        )

    def delete_conditional(self, delete_condition_function, ripple_delete=True, shift_to_zero=False):
        new_snapshots = []
        start_beat, start_time = self.snapshots[0][:2]
        beat_shift = -start_beat if shift_to_zero else 0
        time_shift = -start_time if shift_to_zero else 0
        for ss, next_ss in zip_longest(self.snapshots, self.snapshots[1:]):
            if delete_condition_function(ss):
                # delete_snapshot
                if next_ss is not None and ripple_delete:
                    beat_shift -= next_ss[0] - ss[0]
                    time_shift -= next_ss[1] - ss[1]

            else:
                if beat_shift == time_shift == 0:
                    new_snapshots.append(ss)
                else:
                    new_snapshots.append((
                        ss[0] + beat_shift,
                        ss[1] + time_shift,
                        *ss[2:]
                    ))
        self.snapshots = new_snapshots
        self.reset_to_start()
        return self

    def print_snapshot_report(self, end_beat=None):
        cycle_start = floor_to_multiple(self.snapshots[0][0], 12)
        for ss in self.snapshots:
            if end_beat is not None and ss[0] >= end_beat:
                break
            if ss[0] >= cycle_start:
                print(f"BEATS {cycle_start}-{cycle_start + 12}:")
                cycle_start += 12
            ss_string = f"    Snapshot at (b:{ss[0]}, t:{ss[1]}): {tuple(ss[2].keys())}"
            if sum(ss[3]) > 0:
                ss_string += f", disturbances={tuple(ss[3])}"
            if ss[4]:
                ss_string += " [FAST FORWARD]"
            print(ss_string)

    def is_fast_forwarding(self):
        return self.current_snapshot()[4]

    def run(self):
        threading.current_thread().__clock__ = s
        s.timing_policy = "relative"  # 0.7

        def play_disturbances(disturbances):
            for x in disturbances:
                lh = [int(50 - 10 * x), int(55 - 10 * x), int(60 - 10 * x)]
                rh = [int(67 + 10 * x), int(72 + 10 * x), int(77 + 10 * x)]
                orch_hit.play_chord(lh + rh if x else None, 0.4 + 0.6 * x, 0.5)

        while True:
            for species, loop_object in self.playing_individuals.items():
                if species in ('kick', 'snare', 'hihat'):
                    fork(loop_object.play_bar)
                elif species == 'kick_bass':
                    fork(loop_object.play_bassline)
                elif species == 'snare_piano':
                    fork(loop_object.play_comp_chords)
                elif species == 'hihat_sax':
                    fork(loop_object.play_melody)
                elif species == 'kick_end':
                    fork(loop_object.play_bassline_end)
                elif species == 'snare_harmony':
                    fork(loop_object.play_harmony)
                elif species == 'hihat_marimba':
                    fork(loop_object.play_arpeggios)
            if not np.all(self.disturbances == 0):
                fork(play_disturbances, (self.disturbances,))

            wait(12)
            try:
                self.advance_beat(12)
            except IndexError:
                # at end of recording
                break


if __name__ == '__main__':
    import pathlib
    evolution_recording = EvolutionMusicRecordingPlayer(pathlib.Path(__file__).parent.joinpath("recorded_snapshots.pk"))
    evolution_recording.normalize(remove_fast_forward=True)
    evolution_recording.start()
