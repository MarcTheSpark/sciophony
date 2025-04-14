"""
Okay, so here's where it got really messy. The first step of putting the music on a separate thread was done to
facilitate having an animation run alongside. But the issue was that the animation sometimes needed to peek into the
future in order to show the grid that was about to be played by a part as it was fading in, and this was an issue
because sometimes parts were governed by random probabilities of playing or not playing a note. Calculating those
probabilities early would mess up the evolution process (by changing the random state), but we need to know them early
in order to visualize.

This led me to create the SaveVals class, which I used to save the random values from a play-though so that they could
be known in advance when played again with visualization.

This worked...until we started wanting to mess with the visualization in Reaper --- removing measures here and there
for pacing. This led to difficulties, since it's hard to skip a measure in an evolutionary process. So that's why I
created the Recorder and EvolutionMusicRecording classes to just record exactly what individuals (i.e. the specific
genomes) were active at a given time. This made it easy to just skip a few measures.

So when you give EvolutionMusic a snapshots_recording_file, it saves and pickles a recording of a bunch of snapshots
of which individuals and disturbances are active at agny given time, and this can be read and played by
evolution_play_recorded.

The whole thing was a mess. I think, if I had this to do again, I would precalculate the entire evolutionary process
ahead of time, instead of having it run live.
"""


import threading
from marciano.utility_funcs import target_fit_score
from modspread import get_mod_n_spread_array
from evolution_species import *

random.seed(10)


def do_metro():
    """In case we need a metronome to figure out where we are."""
    while True:
        for j in range(4):
            for i in range(3):
                if j == i == 0:
                    metro_kit.play_note(67, 1.0, 0.5)
                else:
                    wait(0.5)


# Populations are initialized with a quiet genome consisting of all off switches, and all low volumes
quiet_genome = [0 for _ in range(DrumLoop.cycle_length)] + [0.1 for _ in range(DrumLoop.cycle_length)]


class EvolutionMusic(threading.Thread):

    def __init__(self, snapshots_recording_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fitness functions focus on alignment with the beat strength arrays, and on targeting the right busyness for
        # the respective parts (high for hihat, medium for snare, low for kick)

        def snare_fitness_func(snare_loop: SnareLoop) -> float:
            return (target_fit_score(snare_loop.busyness(), 0.4, 0.1) +
                    2 * snare_loop.beat_strength_alignment(snare_beat_strengths))

        def hihat_fitness_func(hihat_loop: HiHatLoop) -> float:
            return target_fit_score(hihat_loop.busyness(), 0.9,
                                    0.2) + 2 * hihat_loop.evenness() + hihat_loop.beat_strength_alignment(
                beat_strengths)

        def kick_fitness_func(kick_loop: KickLoop) -> float:
            return target_fit_score(kick_loop.busyness(), 0.2, 0.1) + kick_loop.beat_strength_alignment(beat_strengths)

        self.snare_pop = Population(
            [SnareLoop(*quiet_genome) for _ in range(100)],
            snare_fitness_func,
            reproduction_curve=Envelope.from_levels([0, 5])
        )
        self.hihat_pop = Population(
            [HiHatLoop(*quiet_genome) for _ in range(100)],
            hihat_fitness_func,
            reproduction_curve=Envelope.from_levels([0, 5])
        )
        self.kick_pop = Population(
            [KickLoop(*quiet_genome) for _ in range(100)],
            kick_fitness_func,
            reproduction_curve=Envelope.from_levels([0, 5])
        )

        self.playing_individuals = {}
        self.disturbances = np.zeros(24)
        self.snapshots_recording_file = snapshots_recording_file

    def run(self):
        global end_play_prob
        threading.current_thread().__clock__ = s
        recorder = Recorder(self)
        if self.snapshots_recording_file is None:
            recorder.on = False

        # BEGIN INTRO
        rand_state = random.getstate()
        s.tempo_history.go_to_beat(-3 * DrumLoop.bar_duration)
        self.playing_individuals["kick"] = KickLoop(*quiet_genome)
        fork(recorder.take_snapshots, [DrumLoop.bar_duration])
        wait(DrumLoop.bar_duration)

        self.playing_individuals["kick"] = KickLoop(*quiet_genome).mutate()
        self.playing_individuals["snare"] = SnareLoop(*quiet_genome)
        self.playing_individuals["hihat"] = HiHatLoop(*quiet_genome)
        fork(recorder.take_snapshots, [DrumLoop.bar_duration])
        self.playing_individuals["kick"].play_bar()

        self.playing_individuals["kick"] = KickLoop(*quiet_genome).mutate().mutate()
        self.playing_individuals["snare"] = SnareLoop(*quiet_genome).mutate()
        self.playing_individuals["hihat"] = HiHatLoop(*quiet_genome)
        fork(recorder.take_snapshots, [DrumLoop.bar_duration])
        fork(self.playing_individuals["kick"].play_bar)
        fork(self.playing_individuals["snare"].play_bar)
        wait(DrumLoop.bar_duration)


        # RESET TO TIME 0 AND RANDOMNESS
        random.setstate(rand_state)

        # TRUE BEGINNING
        s.fast_forward_to_beat(DrumLoop.bar_duration)   # skip the first bar, because it wasn't needed
        # Evolution is slow
        self.snare_pop.evolve_continuously(7, sex_prob=0.6, clock=s)
        self.hihat_pop.evolve_continuously(8, sex_prob=0.6, clock=s)
        self.kick_pop.evolve_continuously(9, sex_prob=0.6, clock=s)

        while s.time() * SPEED_FACTOR < 120:
            if s.beat() == 312:
                s.fast_forward_in_beats(DrumLoop.bar_duration * 6)
            # Play the beats
            self.playing_individuals["kick"] = self.kick_pop.get_individual(0.5)
            self.playing_individuals["snare"] = self.snare_pop.get_individual(0.5)
            self.playing_individuals["hihat"] = self.hihat_pop.get_individual(0.5)
            fork(self.playing_individuals["kick"].play_bar)
            fork(self.playing_individuals["snare"].play_bar)
            fork(self.playing_individuals["hihat"].play_bar, args=(0.6,))

            # Gradually introduce melodic aspects
            if s.time() * SPEED_FACTOR >= 18:
                self.playing_individuals["kick_bass"] = self.kick_pop.get_individual(0.25, 0.75)
                if "kick_bass_preimage" not in saver.values_by_situation:
                    saver.save(self.playing_individuals["kick_bass"].genotype_array, "kick_bass_preimage" )

                fork(self.playing_individuals["kick_bass"].play_bassline)
            if s.time() * SPEED_FACTOR >= 38:
                self.playing_individuals["snare_piano"] = self.snare_pop.get_individual(0.25, 0.75)
                if "snare_piano_preimage" not in saver.values_by_situation:
                    saver.save(self.playing_individuals["snare_piano"].genotype_array, "snare_piano_preimage")
                fork(self.playing_individuals["snare_piano"].play_comp_chords)
            if s.time() * SPEED_FACTOR >= 60:
                self.playing_individuals["hihat_sax"] = self.hihat_pop.get_individual(0.25, 0.75)
                if "hihat_sax_preimage" not in saver.values_by_situation:
                    saver.save(self.playing_individuals["hihat_sax"].genotype_array, "hihat_sax_preimage")
                fork(self.playing_individuals["hihat_sax"].play_melody)

            fork(recorder.take_snapshots, [DrumLoop.bar_duration])

            wait(DrumLoop.bar_duration)

        # -------------------------------------------- SECOND PART -------------------------------------------
        # Introduce disturbances, and have all of the parts try to avoid them metrically

        def play_disturbances():
            while True:
                # disturbances = np.ones(24)
                self.disturbances = np.roll(
                    get_mod_n_spread_array(length=24, n=17, spread=((current_clock().beat()) / 30) ** 1.4 + 1), 2)
                for x in self.disturbances:
                    lh = [int(50 - 10 * x), int(55 - 10 * x), int(60 - 10 * x)]
                    rh = [int(67 + 10 * x), int(72 + 10 * x), int(77 + 10 * x)]

                    orch_hit.play_chord(lh + rh if x else None, 0.4 + 0.6 * x, 0.5)
                if sum(self.disturbances) > 13:
                    self.disturbances[:] = 0
                    break

        def get_disturbances_collision_amount(activity_array):
            """Measures how much a given activity array is colliding with the disturbances"""
            return np.dot(activity_array, self.disturbances) / len(activity_array)

        # Fitness functions now focus on avoiding disturbances
        def snare_avoidance_fitness_func(snare_loop: SnareLoop) -> float:
            return -get_disturbances_collision_amount(snare_loop.beats())

        def kick_avoidance_fitness_func(kick_loop: KickLoop) -> float:
            return -get_disturbances_collision_amount(kick_loop.activity_array(0.5))

        def hihat_avoidance_fitness_func(hihat_loop: HiHatLoop) -> float:
            return -get_disturbances_collision_amount(hihat_loop.activity_array(0.5))

        self.snare_pop.stop_evolving()
        self.kick_pop.stop_evolving()
        self.hihat_pop.stop_evolving()
        self.snare_pop.fitness_function = snare_avoidance_fitness_func
        self.kick_pop.fitness_function = kick_avoidance_fitness_func
        self.hihat_pop.fitness_function = hihat_avoidance_fitness_func
        self.snare_pop.evolve_continuously(27, sex_prob=0.4, clock=s)
        self.hihat_pop.evolve_continuously(28, sex_prob=0.4, clock=s)
        self.kick_pop.evolve_continuously(29, sex_prob=0.4, clock=s)

        disturbances_clock = fork(play_disturbances)

        while disturbances_clock.alive:
            # Play the beats
            self.playing_individuals["kick"] = self.kick_pop.get_individual(0.5)
            self.playing_individuals["snare"] = self.snare_pop.get_individual(0.5)
            self.playing_individuals["hihat"] = self.hihat_pop.get_individual(0.5)
            fork(self.playing_individuals["kick"].play_bar)
            fork(self.playing_individuals["snare"].play_bar)
            fork(self.playing_individuals["hihat"].play_bar, args=(0.6,))

            # Play the melodic parts
            self.playing_individuals["kick_bass"] = self.kick_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["kick_bass"].play_bassline)
            self.playing_individuals["snare_piano"] = self.snare_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["snare_piano"].play_comp_chords)
            self.playing_individuals["hihat_sax"] = self.hihat_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["hihat_sax"].play_melody)
            fork(recorder.take_snapshots, [DrumLoop.bar_duration])

            wait(DrumLoop.bar_duration)

        # -------------------------------------------- THIRD (AND FINAL) PART ------------------------------------------
        # The populations are left reeling from the disturbances, and now start to find a new niche in harmony

        # These are the consonance scores used in evaluating different intervals; over time we penalize minor seconds
        # and major sevenths more and more to try to push them out of the harmonic landscape
        interval_consonance_env = TimeVaryingParameter.from_levels([
            np.array((3, -1, 0, 1, 4, 5, -3, 5, 2, 1, 0, -1)),
            np.array((3, -15, 0, 1, 4, 5, -3, 5, 2, 1, 0, -15))
        ], 200)

        def _snare_loop_harmony_fitness_metrics(sl: SnareLoop):
            chord1, chord2 = sl.get_chords()
            # Have it approach chords of average size 5 for each chord
            chord_size_fitness = (target_fit_score(len(chord1), 5, 1) +
                                  target_fit_score(len(chord2), 5, 1)) / 2
            # Have the chords approach the same size
            chord_size_variation_fitness = target_fit_score((len(chord1) - len(chord2)), 0, 1)
            # Have the chords approach an average voice leading distance of 1
            # (each note is about a half-step from a note of the other chord)
            voice_leading_dist_fitness = target_fit_score(SnareLoop.voice_leading_distance(chord1, chord2), 1, 2)

            consonance_sum = (SnareLoop.measure_consonance(chord1, interval_consonance_env()) +
                              SnareLoop.measure_consonance(chord2, interval_consonance_env())) / 2

            return (chord_size_fitness, chord_size_variation_fitness, voice_leading_dist_fitness,
                    consonance_sum, sl.timing_coherence())

        def snare_loop_harmony_fitness_func(sl: SnareLoop):
            """Snare (string chords) fitness is based on chord size, consonance, and timing coherence"""
            (chord_size_fitness, chord_size_variation_fitness, voice_leading_dist_fitness,
             consonance_sum, timing_coherence) = _snare_loop_harmony_fitness_metrics(sl)

            return chord_size_fitness + consonance_sum * 3 + timing_coherence

        @lru_cache(maxsize=2)
        def get_snare_harmonies_average(t):
            """Since the snare (now string chords) are driving the harmony at the end, the other parts' fitness is based
            on how much they fit into them. This function returns the mean pitch class arrays for the two snare chords.
            Although the parameter `t` is not used, it's playing a role in caching, so that this is only recalculated
            when t changes."""
            return self.snare_pop.mean_of_func(lambda individual: np.array(individual.genotype_array[:24]))

        def hihat_loop_arpeggios_fitness_func(hh: HiHatLoop):
            """Hihat fitness is based on how well the hihat harmony aligns with the snare harmony, as measured by
            dot product of their vectors. We divide by the total number active pitch classes, since otherwise more active
            pitch classes will just lead to a bigger number even if they aren't particularly aligned. But we use the square
            root of the number because otherwise just a single well aligned pitch class will be the best we can do.
            """
            total_active_pcs = sum(hh.genotype_array[:24])
            if total_active_pcs == 0:
                return 0
            return np.dot(get_snare_harmonies_average(s.time() * SPEED_FACTOR), hh.genotype_array[:24]) / total_active_pcs ** 0.5

        def kick_loop_bass_fitness_func(kl: KickLoop):
            """See hihat_loop_arpeggios_fitness_func"""
            total_active_pcs = sum(kl.genotype_array[:24])
            if total_active_pcs == 0:
                return 0
            return np.dot(get_snare_harmonies_average(s.time() * SPEED_FACTOR), kl.activity_array(0.5)) / total_active_pcs ** 0.5

        self.snare_pop.stop_evolving()
        self.hihat_pop.stop_evolving()
        self.kick_pop.stop_evolving()
        self.snare_pop.fitness_function = snare_loop_harmony_fitness_func
        self.hihat_pop.fitness_function = hihat_loop_arpeggios_fitness_func
        self.kick_pop.fitness_function = kick_loop_bass_fitness_func
        self.snare_pop.evolve_continuously(21, sex_prob=0.6, clock=s)
        self.hihat_pop.evolve_continuously(23, sex_prob=0.4, clock=s)
        self.kick_pop.evolve_continuously(22, sex_prob=0.4, clock=s)

        # Fade out the melodic parts
        SnareLoop.play_prob_param = TimeVaryingParameter([1, 0], [20 / SPEED_FACTOR], clock=s, units="time")
        KickLoop.play_prob_param = TimeVaryingParameter([1, 0], [10 / SPEED_FACTOR], clock=s, units="time")
        HiHatLoop.play_prob_param = TimeVaryingParameter([1, 0], [20 / SPEED_FACTOR], clock=s, units="time")

        end_play_prob_curve = TimeVaryingParameter([0, 0, 1], [10 / SPEED_FACTOR, 60 / SPEED_FACTOR], clock=s, units="time")

        # Maybe the volumes control the timing completely

        while s.time() * SPEED_FACTOR < 360:
            end_play_prob = end_play_prob_curve()
            # kick_loop = self.kick_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
            # snare_loop = self.snare_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
            # hihat_loop = self.hihat_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
            #
            # fork(kick_loop.play_bar)
            # fork(snare_loop.play_bar)
            # fork(hihat_loop.play_bar)
            #
            # # Play the melodic parts (these will fade out)
            # fork(self.kick_pop.get_individual(0.25, 0.75).play_bassline)
            # fork(self.snare_pop.get_individual(0.25, 0.75).play_comp_chords)
            # fork(self.hihat_pop.get_individual(0.25, 0.75).play_melody)


            # Play the beats
            self.playing_individuals["kick_end"] = self.playing_individuals["kick"] = self.kick_pop.get_individual(0.7, 1.0)
            self.playing_individuals["snare_harmony"] = self.playing_individuals["snare"] = self.snare_pop.get_individual(0.7, 1.0)
            self.playing_individuals["hihat_marimba"] = self.playing_individuals["hihat"] = self.hihat_pop.get_individual(0.7, 1.0)
            fork(self.playing_individuals["kick"].play_bar)
            fork(self.playing_individuals["snare"].play_bar)
            fork(self.playing_individuals["hihat"].play_bar, args=(0.6,))

            # Play the melodic parts
            self.playing_individuals["kick_bass"] = self.kick_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["kick_bass"].play_bassline)
            self.playing_individuals["snare_piano"] = self.snare_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["snare_piano"].play_comp_chords)
            self.playing_individuals["hihat_sax"] = self.hihat_pop.get_individual(0.25, 0.75)
            fork(self.playing_individuals["hihat_sax"].play_melody)

            # play end music (these will fade in)
            fork(self.playing_individuals["snare_harmony"].play_harmony)
            fork(self.playing_individuals["hihat_marimba"].play_arpeggios)
            fork(self.playing_individuals["kick_end"].play_bassline_end)
            fork(recorder.take_snapshots, [DrumLoop.bar_duration])

            wait(DrumLoop.bar_duration)
        if self.snapshots_recording_file:
            recorder.save_to_pickle(self.snapshots_recording_file)


class Recorder:
    def __init__(self, evolution_music: EvolutionMusic, frame_rate=60):
        self.snap_shots = []
        self.em: EvolutionMusic = evolution_music
        self.frame_rate = frame_rate
        self.on = True

    def take_snapshot(self):
        this_snap_shot = (
            s.beat(),
            s.time(),
            self.em.playing_individuals.copy(),
            self.em.disturbances.copy(),
            s.is_fast_forwarding()
        )
        self.snap_shots.append(this_snap_shot)

    def take_snapshots(self, how_long):
        if not self.on:
            return
        i = 0
        start = current_clock().beat()
        while current_clock().beat() - start < how_long:
            if i % 10 == 0:
                print(f"{len(self.snap_shots)} frames saved; {s.beat()=}, {s.time()=}")
            self.take_snapshot()
            wait(1/self.frame_rate * s.tempo / 60)
            i += 1

    def save_to_pickle(self, file_name):
        if not self.on:
            return
        import pickle
        with open(file_name, 'wb') as f:
            pickle.dump(self.snap_shots, f)



# s.fast_forward()
EvolutionMusic("recorded_snapshots.pk").run()  # Runs and saves recorded_snapshots.pk
# saver.save_to_json("saved_vals.json")