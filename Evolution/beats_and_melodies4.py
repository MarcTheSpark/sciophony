import cmath
import itertools
import math
import random
import numpy as np
from scamp import *
from scamp_extensions.pitch import Scale
from marciano.evolution import TraitInfo, Individual, Population
from marciano.utility_funcs import phase_alignment, window_fit_score, target_fit_score
from scamp_extensions.process import random_walk
from scamp_extensions.utilities import TimeVaryingParameter, rotate_sequence, remap, wrap_to_range, atan_warp
from scamp_extensions.rhythm import indispensability_array_from_expression
from functools import lru_cache
from scipy.ndimage import gaussian_filter1d
from modspread import get_mod_n_spread_array
from chord_builder import chord_from_pitch_classes

# random.seed(0)

beat_strengths = [x ** 3 for x in indispensability_array_from_expression("2*2*2*3", normalize=True)]
snare_beat_strengths = rotate_sequence(beat_strengths, 3)

# disturbances = [0, 1, 0, 0, 0.7, 0,
#                 0, 0, 0, 1, 0, 0,
#                 0, 0, 0, 0, 0.6, 0,
#                 1, 0, 0, 0, 0, 0.5]
disturbances = np.zeros(24)

# beat_strengths = [x ** 2 for x in indispensability_array_from_expression("((3 + 2) + (3 + 2) + 2) * 2", normalize=True)]
# snare_beat_strengths = rotate_sequence(beat_strengths, 2)
# print(snare_beat_strengths)
# snare_beat_strengths = [0, 0.2, 0.2,
#                         1.0, 0.2, 0.2,
#                         0, 0.2, 0.2,
#                         1.0, 0.2, 0.2] * 2

beat_strength_values = sorted(beat_strengths, reverse=True)
# playback_settings.recording_file_path = "bm4.wav"
s = Session(default_soundfont="MuseScore_General", tempo=190) #190
# s.print_default_soundfont_presets()

s.timing_policy = "relative" #0.7

kit = s.new_part("STANDARD")
piano = s.new_part("Piano")
orch_hit = s.new_part("Orchestra hit")


@lru_cache
def get_perfectly_even_distance_sum(num_onsets):
    return abs(cmath.exp(2j * math.pi / num_onsets) - 1) * num_onsets


@lru_cache
def get_perfectly_uneven_distance_sum(cycle_length, num_onsets):
    return abs(cmath.exp(2j * math.pi / cycle_length) - 1) * (num_onsets - 1) + abs(cmath.exp(2j * math.pi * (num_onsets - 1) / cycle_length) - 1)


def calculate_evenness(on_offs):
    cycle_length = len(on_offs)
    onsets = [cmath.exp(2j * math.pi * i / cycle_length) for i, on_off in enumerate(on_offs) if on_off]
    if len(onsets) == 0:
        # degenerate case of silent beat; return 0
        return 0
    distances = [abs(b - a) for a, b in zip(onsets[1:] + [onsets[0]], onsets)]
    distance_sum = sum(distances)
    return distance_sum / get_perfectly_even_distance_sum(len(onsets))
    # perfectly_even_distance_sum = get_perfectly_even_distance_sum(len(onsets))
    # perfectly_uneven_distance_sum = get_perfectly_uneven_distance_sum(cycle_length, len(onsets))
    # return (distance_sum - perfectly_uneven_distance_sum) / (perfectly_even_distance_sum - perfectly_uneven_distance_sum)


class DrumLoop(Individual):

    drum_pitch: int = NotImplemented
    melody_inst: ScampInstrument = NotImplemented
    pulse_length: float = 0.5
    cycle_length = len(beat_strengths)
    bar_duration = pulse_length * cycle_length

    # melody_stuff
    root_pitches = [39 + (5 * i) % 12 for i in range(24)]
    # intervals above root (cycled through)
    chord_configurations = [
        [4, 10, 15],  # 7 sharp 9
        [4, 9, 14],  # major (6, 9)
    ]

    genotype_info = (
        *(
            TraitInfo("beat_switch{position}", (0, 1), mutation_width=1,
                      quantization=1, mutation_probability=0.2)
            for position in range(cycle_length)
        ),
        *(
            TraitInfo("volume{position}", (0.1, 1.0), mutation_width=0.2, mutation_probability=0.3)
            for position in range(cycle_length)
        ),
    )

    def beats(self):
        return self.genotype_array[:self.cycle_length]

    def volumes(self):
        return self.genotype_array[self.cycle_length:]

    def play_bar(self, volume_mul=1):
        for on_off, volume in zip(self.beats(), self.volumes()):
            kit.play_note(self.drum_pitch if on_off else None, volume * volume_mul, self.pulse_length)

    def evenness(self):
        return calculate_evenness(self.beats())

    def beat_strength_alignment(self, beat_strengths):
        try:
            return sum(beat_strength * volume * on_off
                       for beat_strength, volume, on_off in zip(beat_strengths, self.volumes(), self.beats())) / \
                sum(beat_strength_values[:sum(self.beats())])
        except ZeroDivisionError:
            return 0

    def busyness(self):
        return sum(self.beats()) / self.cycle_length

    def activity_array(self, on_off_vs_volume_weighted: float = 1):
        """
        A volume-weighted (to an adjustable extend) array of activity for each beat.

        :param on_off_vs_volume_weighted: if 1, it's completely weighted by volume; if 0 it's just on/off
        """
        return np.array([on_off * ((1 - on_off_vs_volume_weighted) + on_off_vs_volume_weighted * volume)
                         for on_off, volume in zip(self.beats(), self.volumes())])


class SnareLoop(DrumLoop):
    drum_pitch = 38
    inst = s.new_part("piano")
    end_inst = s.new_part("strings", num_channels=16)
    play_prob_param = TimeVaryingParameter([0, 0, 1], [20, 80], clock=s, units="time")
    harmony_volume_threshold = 0

    def play_comp_chords(self):
        volumes_np = np.array(self.volumes())
        long_note_thresh = np.percentile(volumes_np, 75)
        short_note_thresh = np.percentile(volumes_np, 50)
        held_chord = None
        for root_pitch, chord_config, volume, on_off in zip(self.root_pitches, itertools.cycle(self.chord_configurations), self.volumes(), self.beats()):
            if on_off and volume >= short_note_thresh and random.random() < SnareLoop.play_prob_param():
                if held_chord:
                    held_chord.end()
                    held_chord = None
                if volume >= long_note_thresh:
                    held_chord = self.inst.start_chord([root_pitch + 12 + interval for interval in chord_config],
                                                       remap(volume, 0.5, 1.0, 0, 1))
                    wait(self.pulse_length)
                else:
                    self.inst.play_chord([root_pitch + 12 + interval for interval in chord_config],
                                         remap(volume, 0.5, 1.0, 0, 1),
                                         self.pulse_length, "staccato")

            else:
                wait(self.pulse_length)

    # ----------------------------------- The ending: harmony ------------------------------------------

    def play_harmony(self, start_pitch=60, max_size=8):
        chord1, chord2 = self.get_chords(start_pitch, max_size)
        start_offset, dur1, dur2 = self.get_harmony_start_offset_and_durations()
        wait(start_offset * self.pulse_length)
        self.end_inst.play_chord(chord1, [0 if dur1 > 3 else 0.6, 1], dur1 * self.pulse_length)
        self.end_inst.play_chord(chord2, [1, 0 if dur2 > 3 else 0.6 if dur2 > 2 else 1], dur2 * self.pulse_length)

    def get_pc_lists(self):
        return list(np.where(self.genotype_array[:12])[0]), list(np.where(self.genotype_array[12:24])[0])

    @staticmethod
    def chord_from_pc_list(pc_list, start_pitch, max_size=math.inf, min_gap=4):
        num_notes = min(max_size, len(pc_list))
        chord = []
        pcs_used = []
        lowest_next_pitch = start_pitch
        while len(chord) < num_notes:
            for p in range(lowest_next_pitch, lowest_next_pitch + 12):
                pc = p % 12
                if pc in pc_list and pc not in pcs_used:
                    chord.append(p)
                    pcs_used.append(pc)
                    lowest_next_pitch = p + min_gap
                    break
        return chord

    def get_chords(self, start_pitch=60, max_size=8):
        return [SnareLoop.chord_from_pc_list(pc_list, start_pitch, max_size) for pc_list in self.get_pc_lists()]

    # return [chord_from_pitch_classes(pc_list, 65, 85, 6) if len(pc_list) > 0 else []
    #         for pc_list in self.get_pc_lists()]

    def _get_harmony_start_beats(self):
        return sorted(np.argsort(self.volumes())[-2:])
        # return np.argmax(self.volumes()[:12]), np.argmax(self.volumes()[12:24])

    def get_harmony_start_offset_and_durations(self):
        start_beat1, start_beat2 = self._get_harmony_start_beats()
        dur1 = (start_beat2 - start_beat1)
        dur2 = (24 - start_beat2)
        return start_beat1, dur1, dur2

    @staticmethod
    def voice_leading_distance(chord1, chord2):
        """
        Calculate the average minimum distance between each note in chord2 and the notes in chord1.

        :param chord1 : List of MIDI pitches for the first chord.
        :param chord2: List of MIDI pitches for the second chord.
        :return: Average voice leading distance between the two chords.
        """
        if len(chord1) == 0 or len(chord2) == 0:
            # we don't want this so make it very bad
            return math.inf
        total_distance = 0
        for note2 in chord2:
            nearest_distance = min([abs(note2 - note1) for note1 in chord1])
            total_distance += nearest_distance
        average_distance = total_distance / len(chord2)
        return average_distance

    @staticmethod
    def measure_consonance(chord, interval_consonance=(3, -10, 0, 1, 4, 5, -3, 5, 2, 1, 0, -10)):
        """
        Measures the consonance of a chord based on the weighted consonance of the associated intervals

        :param chord: List of MIDI pitches representing the chord.
        :param interval_consonance: consonance score (weighting) for each of the 12 intervals

        :return: Measure of consonance for the chord.
        """

        # Generate all pairs of notes in the chord
        pairs = itertools.combinations(chord, 2)

        # Count consonant intervals
        consonant_count = sum(interval_consonance[abs(max(*pair) - min(*pair)) % 12] for pair in pairs)

        return atan_warp(consonant_count, -10, 10, 0, 1)
        # # Total number of intervals
        # total_intervals = len(chord) * (len(chord) - 1) / 2
        #
        # # Calculate proportion of consonant intervals
        # return consonant_count / total_intervals if total_intervals else 0


def multi_iterator(iterator, multiple):
    for x in iterator:
        for _ in range(multiple):
            yield x


class HiHatLoop(DrumLoop):
    drum_pitch = 42
    inst = s.new_part("Saxophone")
    arpeggio_inst = s.new_part("marimba")
    min_pitch, max_pitch = 54, 78
    play_prob_param = TimeVaryingParameter([0, 0, 1], [50, 50], clock=s, units="time")

    def get_scale(self):
        return Scale.from_pitches(
            [72 + i for i, on_off in zip(range(self.cycle_length), self.beats()) if on_off] +
            [72 + self.cycle_length]
        )

    def play_melody(self):
        pitch = self.root_pitches[0] + 15
        interval_pattern = itertools.cycle([-2, -1, -3, 4])
        for root_pitch, volume, on_off in zip(self.root_pitches, self.volumes(), self.beats()):
            pitch = wrap_to_range(pitch, self.min_pitch, self.max_pitch)
            if on_off and random.random() < HiHatLoop.play_prob_param():
                for _ in range(2):
                    self.inst.play_note(pitch,
                                        remap(volume, 0.2, 1.0, 0, 1),
                                        self.pulse_length / 2)
                    pitch += next(interval_pattern)
            else:
                for _ in range(2):
                    next(interval_pattern)
                wait(self.pulse_length)

    def get_pc_lists(self):
        return list(np.where(self.genotype_array[:12])[0]), list(np.where(self.genotype_array[12:24])[0])

    def _get_arpeggio_pitches(self, pc_octave=72):
        pitches = []

        volume_lists = [self.volumes()[:12], self.volumes()[12:]]
        last_volume = -1
        for pc_list, volume_list in zip(self.get_pc_lists(), volume_lists):
            pc_iter = itertools.cycle(pc_list[::-1])
            for volume in volume_list:
                try:
                    pc = next(pc_iter)
                except StopIteration:
                    pc = 0
                if len(pitches) == 0:
                    pitches.append(pc_octave + pc)
                elif volume > last_volume:
                    pitches.append(pc_octave + pc if pc_octave + pc > pitches[-1] else pc_octave + 12 + pc)
                else:
                    pitches.append(pc_octave + pc if pc_octave + pc < pitches[-1] else pc_octave - 12 + pc)
                last_volume = volume
        return pitches

    def play_arpeggios(self, pc_octave=72):
        # Cycle through pcs (in reverse), going down to next closest pc each time
        # Jump up an octave (new hi volume) with every large volume value
        for pitch, volume in zip(self._get_arpeggio_pitches(pc_octave), self.volumes()):
            self.arpeggio_inst.play_note(pitch, volume ** 0.5, self.pulse_length)


class KickLoop(DrumLoop):
    drum_pitch = 36
    inst = s.new_part("Fingered Bass")

    def play_bassline(self):
        for root_pitch, volume, on_off in zip(self.root_pitches, self.volumes(), self.beats()):
            if on_off:
                self.inst.play_note(root_pitch, remap(volume, 0.5, 1.0, 0, 1),
                                    self.pulse_length)
            else:
                wait(self.pulse_length)


def do_metro():
    while True:
        for j in range(4):
            for i in range(3):
                if j == i == 0:
                    kit.play_note(36, 1.0, 0.5)
                elif i == 0:
                    kit.play_note(45, 1.0, 0.5)
                else:
                    kit.play_note(63, 1.0, 0.5)


# fork(do_metro)

def snare_fitness_func(snare_loop: SnareLoop) -> float:
    return (target_fit_score(snare_loop.busyness(), 0.4, 0.1) +
            2 * snare_loop.beat_strength_alignment(snare_beat_strengths))


def hihat_fitness_func(hihat_loop: HiHatLoop) -> float:
    return target_fit_score(hihat_loop.busyness(), 0.9, 0.2) + 2 * hihat_loop.evenness() + hihat_loop.beat_strength_alignment(beat_strengths)


def kick_fitness_func(kick_loop: KickLoop) -> float:
    return target_fit_score(kick_loop.busyness(), 0.2, 0.1) + kick_loop.beat_strength_alignment(beat_strengths)



# snare_pop = Population.generate(SnareLoop, 100, snare_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))
# hihat_pop = Population.generate(HiHatLoop, 100, hihat_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))
# kick_pop = Population.generate(KickLoop, 100, kick_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))

# quiet_genome = [0] * DrumLoop.cycle_length + [random.uniform(0.1, 1) for _ in range(DrumLoop.cycle_length)]
quiet_genome = [0 for _ in range(DrumLoop.cycle_length)] + [0.1 for _ in range(DrumLoop.cycle_length)]
# quiet_genome = [1 for _ in range(DrumLoop.cycle_length)] + [1.0 for _ in range(DrumLoop.cycle_length)]

snare_pop = Population(
    [SnareLoop(*quiet_genome) for _ in range(100)],
    snare_fitness_func,
    reproduction_curve=Envelope.from_levels([0, 5])
)
hihat_pop = Population(
    [HiHatLoop(*quiet_genome) for _ in range(100)],
    hihat_fitness_func,
    reproduction_curve=Envelope.from_levels([0, 5])
)
kick_pop = Population(
    [KickLoop(*quiet_genome) for _ in range(100)],
    kick_fitness_func,
    reproduction_curve=Envelope.from_levels([0, 5])
)


# for _ in range(1):
#     # skip a generations!
#     snare_pop.next_generation(0.6)
#     hihat_pop.next_generation(0.6)
#     kick_pop.next_generation(0.6)

snare_pop.evolve_continuously(7, sex_prob=0.6, clock=s)
hihat_pop.evolve_continuously(8, sex_prob=0.6, clock=s)
kick_pop.evolve_continuously(9, sex_prob=0.6, clock=s)


kick_play_thresh = TimeVaryingParameter([1, 1,  0], [50, 150], units="time")
snare_play_thresh = TimeVaryingParameter([1, 1,  0], [100, 200], units="time")
hihat_play_thresh = TimeVaryingParameter([1, 1,  0], [150, 250], units="time")


def evolve_and_play_disturbances():
    global disturbances

    beats = [sl.beats() for sl in snare_pop.individuals]
    print(beats)
    print(np.mean(np.array(beats), axis=0))
    print(disturbances)
    for a, b in zip(np.mean(np.array(beats), axis=0), snare_beat_strengths):
        print(a, b)
    print("---------------------")

    def get_disturbances_collision_amount(activity_array):
        # blurred_disturbances = gaussian_filter1d(disturbances, 3, mode="wrap")
        return np.dot(activity_array, disturbances) / len(activity_array)

    def snare_avoidance_fitness_func(snare_loop: SnareLoop) -> float:
        disturbance_alignment = get_disturbances_collision_amount(snare_loop.beats())
        beat_strength_alignment = snare_loop.beat_strength_alignment(snare_beat_strengths)
        return 2 - 5 * disturbance_alignment #- beat_strength_alignment  # + target_fit_score(snare_loop.busyness(), 0.4, 0.1) * 0.5

    def kick_avoidance_fitness_func(kick_loop: KickLoop) -> float:
        disturbance_alignment = get_disturbances_collision_amount(kick_loop.activity_array(0.5))
        beat_strength_alignment = kick_loop.beat_strength_alignment(beat_strengths)
        return 2 - 5 * disturbance_alignment - beat_strength_alignment  # + target_fit_score(kick_loop.busyness(), 0.2, 0.1) * 0.5

    def hihat_avoidance_fitness_func(hihat_loop: HiHatLoop) -> float:
        disturbance_alignment = get_disturbances_collision_amount(hihat_loop.activity_array(0.5))
        return 2 - 5 * disturbance_alignment  # + target_fit_score(hihat_loop.busyness(), 0.9, 0.2) * 0.5

    snare_pop.fitness_function = snare_avoidance_fitness_func
    kick_pop.fitness_function = kick_avoidance_fitness_func
    hihat_pop.fitness_function = hihat_avoidance_fitness_func
    snare_pop.evolve_continuously(17, sex_prob=0.4, clock=s)
    hihat_pop.evolve_continuously(18, sex_prob=0.4, clock=s)
    kick_pop.evolve_continuously(19, sex_prob=0.4, clock=s)

    while True:
        # disturbances = np.ones(24)
        disturbances = np.roll(get_mod_n_spread_array(length=24, n=17, spread=((current_clock().beat()) / 30) ** 1.4 + 1), 2)
        for x in disturbances:
            lh = [int(50-10*x), int(55-10*x), int(60-10*x)]
            rh = [int(67+10*x), int(72+10*x), int(77+10*x)]
            orch_hit.play_chord(lh + rh if x else None, 0.4 + 0.6 * x, 0.5)
        if sum(disturbances) > 13:
            # disturbances[:] = 0
            break

    snare_pop.stop_evolving()
    hihat_pop.stop_evolving()
    kick_pop.stop_evolving()


disturbances_clock: Clock = None
# s.start_transcribing()
s.fast_forward()
while s.time() < 260:
    if disturbances_clock is not None and not disturbances_clock.alive:
        break

    # kit.play_note(81, 1, 1, blocking=False)
    fork(kick_pop.get_individual(0.5).play_bar)
    if s.time() >= 18:
        fork(kick_pop.get_individual(0.25, 0.75).play_bassline)
    fork(snare_pop.get_individual(0.5).play_bar)
    if s.time() >= 38:
        fork(snare_pop.get_individual(0.25, 0.75).play_comp_chords)
    fork(hihat_pop.get_individual(0.5).play_bar, args=(0.6, ))
    if s.time() >= 60:
        fork(hihat_pop.get_individual(0.25, 0.75).play_melody)

    snare_pop.fitness_function(snare_pop.get_individual(0.25, 0.75))

    if s.time() > 120 and not disturbances_clock:
        disturbances_clock = fork(evolve_and_play_disturbances)
    # print(f"Population average: {kick_pop.mean_fitness()}, Individual: {kick_pop.fitness_function(kick_individual)}")
    wait(DrumLoop.bar_duration)

s.fast_forward(False)


# I THINK THIS WORKS REALLY WELL AS AN EVOLUTION!
# From here, just tweak it based on
# - how long the consonance_env takes to evolve
# - speed of evolution
# - sex prop affects convergence, since there's no mutation there for some reason. (seems a mistake)
# WE WANT THE HI-HAT to do repeated arpeggios
# MAYBE Bass has two notes per bar only?

_consonance_targets = [
    np.array((3, -1, 0, 1, 4, 5, -3, 5, 2, 1, 0, -1)),
    np.array((3, -15, 0, 1, 4, 5, -3, 5, 2, 1, 0, -15))
]
consonance_env = TimeVaryingParameter.from_levels(_consonance_targets, 400)


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
    # have the min consonance approach zero
    consonance_sum = (SnareLoop.measure_consonance(chord1, consonance_env()) + SnareLoop.measure_consonance(chord2, consonance_env())) / 2
    offset, dur1, dur2 = sl.get_harmony_start_offset_and_durations()
    chord_dur_fitness = (target_fit_score(offset, 3, 2) +
                         target_fit_score(dur1, 10, 2) +
                         target_fit_score(dur2, 10, 2))
    return (chord_size_fitness, chord_size_variation_fitness, voice_leading_dist_fitness,
            consonance_sum, chord_dur_fitness)


def snare_loop_harmony_fitness_func(sl: SnareLoop):
    (chord_size_fitness, chord_size_variation_fitness, voice_leading_dist_fitness,
     consonance_sum, chord_dur_fitness) = _snare_loop_harmony_fitness_metrics(sl)

    return chord_size_fitness + consonance_sum * 3 + chord_dur_fitness

    # return (chord_size_fitness + chord_size_variation_fitness +
    #         voice_leading_dist_fitness + 4 * consonance_sum + chord_dur_fitness)


@lru_cache(maxsize=2)
def get_snare_harmonies_average(t):
    return snare_pop.mean_of_func(lambda individual: np.array(individual.genotype_array[:24]))


def hihat_loop_arpeggios_fitness_func(hh: HiHatLoop):
    total_active_pcs = sum(hh.genotype_array[:24])
    if total_active_pcs == 0:
        return 0
    return np.dot(get_snare_harmonies_average(s.time()), hh.genotype_array[:24]) / total_active_pcs ** 0.5


snare_pop.fitness_function = snare_loop_harmony_fitness_func
snare_pop.evolve_continuously(13, sex_prob=0.7, clock=s)
hihat_pop.fitness_function = hihat_loop_arpeggios_fitness_func
hihat_pop.evolve_continuously(13, sex_prob=0.4, clock=s)



# Next step:
# - Hi-hat arpeggiates on chords from each half. Some sort of bell sound. Measured on its consonance with the
# snare population (i.e. the consonance of it's first half / first snare cord, it's second half w second snare chord)
# as well as its activity, which is the volumes array thresholded.
# Kick is on bassline. Aims for evenness of distribution.

# # PLOTS THE HARMONY OVER TIME
# harms = []
# hihat_fits = []
# s.fast_forward()
# for _ in range(50):
#     snare_loop = snare_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
#     harms.append(snare_pop.mean_of_func(lambda sl: (SnareLoop.measure_consonance(sl.get_chords()[0]) +
#                                                     SnareLoop.measure_consonance(sl.get_chords()[1])) / 2))
#     hihat_fits.append(hihat_pop.mean_fitness())
#     print(consonance_env())
#     wait(DrumLoop.bar_duration)
#
# from matplotlib import pyplot as plt
# plt.plot(harms, label="consonance")
# plt.plot(hihat_fits, label="hihat fits")
# plt.legend()
# plt.show()
# for _ in range(5):
#     print(snare_pop.get_individual(min_percentile=0.7, max_percentile=1.0).get_chords())
# s.fast_forward(False)



# Maybe the volumes control the timing completely
s.start_transcribing()
while True:
    kick_loop = kick_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
    snare_loop = snare_pop.get_individual(min_percentile=0.7, max_percentile=1.0)
    hihat_loop = hihat_pop.get_individual(min_percentile=0.7, max_percentile=1.0)

    chord_pc_flags = np.array(hihat_loop.genotype_array[:24])
    chord_pc_flags = np.where(chord_pc_flags == 0, -1, chord_pc_flags)
    fork(kick_loop.play_bar)
    fork(snare_loop.play_bar)
    fork(hihat_loop.play_bar)
    fork(snare_loop.play_harmony)
    # fork(hihat_loop.play_arpeggios)
    wait(DrumLoop.bar_duration)
    print(_snare_loop_harmony_fitness_metrics(snare_loop)[-2], snare_loop_harmony_fitness_func(snare_loop))
    chords = snare_loop.get_chords()
    print(snare_loop.get_chords())
    print(SnareLoop.measure_consonance(chords[0]), SnareLoop.measure_consonance(chords[1]))
    print("---")
s.stop_transcribing().to_score(time_signature="12/8").show()
exit()
while True:
    fork(kick_pop.get_individual(0.5).play_bar)
    fork(kick_pop.get_individual(0.25, 0.75).play_bassline)
    fork(snare_pop.get_individual(0.5).play_bar)
    fork(snare_pop.get_individual(0.25, 0.75).play_comp_chords)
    fork(hihat_pop.get_individual(0.5).play_bar, args=(0.6,))
    fork(hihat_pop.get_individual(0.25, 0.75).play_melody)
    wait(DrumLoop.bar_duration)

# import pickle as pk
# with open("end_texture_start.pk", "wb") as f:
#     pk.dump([kick_pop, snare_pop, hihat_pop], f)
# chords_to_approach = [[62, 69, 61, 78], [63, 68, 72, 79], [60, 70, 74, (76), 81]]

# s.stop_transcribing().export_to_midi_file("bm4.mid")
# add bassline (kick)
# add comping chords (snare)

"""
Evolution ending:
- Use the same machinery to compute pitch instead of time? Bring up the pitch scales from the on/off switches. Niches in frequency bands.
- Evolutionary pressure is now towards a particular chord! Since it's being repurposed, the fitness is in a new domain!
- Seems to come out of the blue but doesn't.

Would like it to float off to pitch land?
"""