"""
This plays the recording of snapshots of which individuals are active, made by evolution_on_thread.py.
"""
from bisect import bisect_left
from evolution_species import *
import threading


class EvolutionMusicRecordingPlayer(threading.Thread):

    def __init__(self, pickled_snapshots_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import pickle
        with open(pickled_snapshots_file, "rb") as f:
            self.snapshots = pickle.load(f)

        self._recalc()
        self.b = self.snapshots[0][0]
        self.t = self.snapshots[0][1]
        self.snapshot_index = 0

    def _recalc(self):
        """Recalculates self._beats and self._times."""
        self._beats = [ss[0] for ss in self.snapshots]
        self._times = [ss[1] for ss in self.snapshots]

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

    def normalize(self, db=None, dt=None, remove_fast_forward=False):
        if db is None:
            db = self.mean_delta_beat()
        if dt is None:
            dt = self.mean_delta_time()

        self.snapshots = [
            (i * db, i * dt, *snapshot[2:])
            for i, snapshot in enumerate(
                snapshot for snapshot in self.snapshots if not remove_fast_forward or not snapshot[4]
            )
        ]
        self.b = self.t = self.snapshot_index = 0
        self._recalc()
        return self

    def mean_delta_beat(self):
        dbs = [b[0] - a[0] for a, b in zip(self.snapshots[:-1], self.snapshots[1:])]
        return sum(dbs) / len(dbs)

    def mean_delta_time(self):
        dts = [b[1] - a[1] for a, b in zip(self.snapshots[:-1], self.snapshots[1:])]
        return sum(dts) / len(dts)

    def delete_beat_range(self, start_beat, end_beat, normalize=False):
        db_avg, dt_avg = self.mean_delta_beat(), self.mean_delta_time()
        self.snapshots = [ss for ss in self.snapshots if not start_beat <= ss[0] < end_beat]
        if normalize:
            # need to get the average db and dt first, since otherwise the big gap will distort it
            self.normalize(db_avg, dt_avg)

    def delete_time_range(self, start_time, end_time, normalize=False):
        db_avg, dt_avg = self.mean_delta_beat(), self.mean_delta_time()
        self.snapshots = [ss for ss in self.snapshots if not start_time <= ss[1] < end_time]
        if normalize:
            # need to get the average db and dt first, since otherwise the big gap will distort it
            self.normalize(db_avg, dt_avg)

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
