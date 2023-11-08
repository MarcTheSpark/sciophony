import cmath
import itertools
import math
import random

import numpy as np
from scamp import *
from scamp_extensions.pitch import Scale
from marciano.evolution import TraitInfo, Individual, Population
from marciano.utility_funcs import phase_alignment
from scamp_extensions.process import random_walk
from scamp_extensions.utilities import TimeVaryingParameter, rotate_sequence, remap, wrap_to_range
from scamp_extensions.rhythm import indispensability_array_from_expression
from functools import lru_cache

from scipy.ndimage import gaussian_filter1d

from modspread import get_mod_n_spread_array


# random.seed(0)

beat_strengths = [x ** 2 for x in indispensability_array_from_expression("2*2*2*3", normalize=True)]
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
playback_settings.recording_file_path = "bm4.wav"
s = Session(default_soundfont="MuseScore_General", tempo=190) #190
# s.print_default_soundfont_presets()

s.timing_policy = 0.7

kit = s.new_part("STANDARD")
piano = s.new_part("Piano")
orch_hit = s.new_part("Orchestra hit")


def window_fit_score(x, window_min, window_max, half_life=0.5):
    if window_min <= x <= window_max:
        return 1
    elif x < window_min:
        return 0.5 ** ((window_min - x) / half_life)
    else:
        return 0.5 ** ((x - window_max) / half_life)


def target_fit_score(x, target, half_life=0.5):
    return window_fit_score(x, target, target, half_life)


@lru_cache
def get_perfectly_even_distance_sum(num_onsets):
    return abs(cmath.exp(2j * math.pi / num_onsets) - 1) * num_onsets


@lru_cache
def get_perfectly_uneven_distance_sum(cycle_length, num_onsets):
    return  abs(cmath.exp(2j * math.pi / cycle_length) - 1) * (num_onsets - 1) + abs(cmath.exp(2j * math.pi * (num_onsets - 1) / cycle_length) - 1)


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
                      quantization=1, mutation_probability=0.1)
            for position in range(cycle_length)
        ),
        *(
            TraitInfo("volume{position}", (0.1, 1.0), mutation_width=0.2, mutation_probability=0.2)
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

    def activity_array(self):
        return [on_off * volume for on_off, volume in zip(self.beats(), self.volumes())]


class SnareLoop(DrumLoop):
    drum_pitch = 38
    inst = s.new_part("piano")
    play_prob_param = TimeVaryingParameter([0, 0, 1], [20, 80], clock=s, units="time")

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


def multi_iterator(iterator, multiple):
    for x in iterator:
        for _ in range(multiple):
            yield x


class HiHatLoop(DrumLoop):
    drum_pitch = 42
    inst = s.new_part("Saxophone")
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


def snare_fitness_func(snare_loop: SnareLoop) -> float:
    kick_alignment = phase_alignment(snare_loop.activity_array(), disturbances, 2)
    return target_fit_score(snare_loop.busyness(), 0.4, 0.1) + snare_loop.beat_strength_alignment(snare_beat_strengths) - kick_alignment


def hihat_fitness_func(hihat_loop: HiHatLoop) -> float:
    return target_fit_score(hihat_loop.busyness(), 0.9, 0.2) + 2 * hihat_loop.evenness() + hihat_loop.beat_strength_alignment(beat_strengths)


def kick_fitness_func(kick_loop: KickLoop) -> float:
    return target_fit_score(kick_loop.busyness(), 0.2, 0.1) + kick_loop.beat_strength_alignment(beat_strengths)


def get_disturbances_collision_amount(activity_array):
    blurred_disturbances = gaussian_filter1d(disturbances, 3, mode="wrap")
    return np.dot(activity_array, blurred_disturbances) / len(activity_array)


def snare_avoidance_fitness_func(snare_loop: SnareLoop) -> float:
    disturbance_alignment = get_disturbances_collision_amount(snare_loop.activity_array())
    kick_alignment = phase_alignment(snare_loop.activity_array(), disturbances, 2)
    return 2 - disturbance_alignment - kick_alignment  # + target_fit_score(snare_loop.busyness(), 0.4, 0.1) * 0.5


def kick_avoidance_fitness_func(kick_loop: KickLoop) -> float:
    disturbance_alignment = get_disturbances_collision_amount(kick_loop.activity_array())
    snare_alignment = phase_alignment(kick_loop.activity_array(), disturbances, 2)
    return 2 - disturbance_alignment - snare_alignment  # + target_fit_score(kick_loop.busyness(), 0.2, 0.1) * 0.5


def hihat_avoidance_fitness_func(hihat_loop: HiHatLoop) -> float:
    disturbance_alignment = get_disturbances_collision_amount(hihat_loop.activity_array())
    return 2 - disturbance_alignment  # + target_fit_score(hihat_loop.busyness(), 0.9, 0.2) * 0.5

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


for _ in range(1):
    # skip a generations!
    snare_pop.next_generation(0.6)
    hihat_pop.next_generation(0.6)
    kick_pop.next_generation(0.6)

snare_pop.evolve_continuously(7, sex_prob=0.6, clock=s)
hihat_pop.evolve_continuously(8, sex_prob=0.6, clock=s)
kick_pop.evolve_continuously(9, sex_prob=0.6, clock=s)


kick_play_thresh = TimeVaryingParameter([1, 1,  0], [50, 150], units="time")
snare_play_thresh = TimeVaryingParameter([1, 1,  0], [100, 200], units="time")
hihat_play_thresh = TimeVaryingParameter([1, 1,  0], [150, 250], units="time")


def piano_part():
    global disturbances
    snare_pop.fitness_function = snare_avoidance_fitness_func
    kick_pop.fitness_function = kick_avoidance_fitness_func
    hihat_pop.fitness_function = hihat_avoidance_fitness_func
    snare_pop.evolve_continuously(19, sex_prob=0.4, clock=s)
    hihat_pop.evolve_continuously(18, sex_prob=0.4, clock=s)
    kick_pop.evolve_continuously(17, sex_prob=0.4, clock=s)

    while True:
        # disturbances = np.ones(24)
        disturbances = np.roll(get_mod_n_spread_array(length=24, n=17, spread=(current_clock().beat()) / 50 + 1), 2)
        for x in disturbances:
            lh = [int(50-10*x), int(55-10*x), int(60-10*x)]
            rh = [int(67+10*x), int(72+10*x), int(77+10*x)]
            orch_hit.play_chord(lh + rh if x else None, 0.4 + 0.6 * x, 0.5)
        if sum(disturbances) > 7:
            disturbances[:] = 0
            break


piano_clock = None
s.start_transcribing()
while s.time() < 260:
    print(s.time())
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

    if s.time() > 120 and not piano_clock:
        piano_clock = fork(piano_part)
    # print(f"Population average: {kick_pop.mean_fitness()}, Individual: {kick_pop.fitness_function(kick_individual)}")
    wait(DrumLoop.bar_duration)

s.stop_transcribing().export_to_midi_file("bm4.mid")
# add bassline (kick)
# add comping chords (snare)

"""
How to get melody out of the SAME GENOTYPE as the rhythm_loop.
Use different phenotypic expression, selection criterion.
Use the scales from these binary on/off switches?
Maybe dormant/useless genes that then find a niche?
"""