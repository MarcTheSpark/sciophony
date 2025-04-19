import cmath
import math
import random
from scamp import *
from scamp_extensions.pitch import Scale
from marciano.evolution import TraitInfo, Individual, Population
from scamp_extensions.process import random_walk
from scamp_extensions.utilities import TimeVaryingParameter, rotate_sequence
from scamp_extensions.rhythm import indispensability_array_from_expression
from functools import lru_cache


# random.seed(0)

beat_strengths = [x ** 2 for x in indispensability_array_from_expression("2*2*2*3", normalize=True)]
snare_beat_strengths = [0, 0.2, 0.2,
                        1.0, 0.2, 0.2,
                        0, 0.2, 0.2,
                        1.0, 0.2, 0.2] * 2


beat_strengths = [x ** 2 for x in indispensability_array_from_expression("((3 + 2) + (3 + 2) + 2) * 2", normalize=True)]
snare_beat_strengths = rotate_sequence(beat_strengths, 2)
print(snare_beat_strengths)
# snare_beat_strengths = [0, 0.2, 0.2,
#                         1.0, 0.2, 0.2,
#                         0, 0.2, 0.2,
#                         1.0, 0.2, 0.2] * 2
5 + 5 + 2

beat_strength_values = sorted(beat_strengths, reverse=True)

s = Session(default_soundfont="MuseScore_General", tempo=190)
# s.print_default_soundfont_presets()

s.timing_policy = 0.7

kit = s.new_part("STANDARD")


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


class SnareLoop(DrumLoop):
    drum_pitch = 38
    melody_inst = s.new_part("Trumpet")
    min_pitch, max_pitch = 55, 70

    def get_scale(self):
        return Scale.from_pitches(
            [72 + i for i, on_off in zip(range(self.cycle_length), self.beats()) if on_off] +
            [72 + self.cycle_length]
        )

    def play_melody(self, threshold, volume_mul=1):
        scale = self.get_scale()

        min_degree, max_degree = round(scale.pitch_to_degree(self.min_pitch)), \
            round(scale.pitch_to_degree(self.max_pitch))
        walk = random_walk(
            sum(self.beats()) % (max_degree - min_degree) // 2 + min_degree,
            step=2,
            clamp_min=min_degree,
            clamp_max=max_degree
        )
        note_handle = None
        for volume, on_off in zip(self.volumes(), self.beats()):
            if (not note_handle) and on_off and volume > threshold:
                note_handle = self.melody_inst.start_note(scale[next(walk)], volume * volume_mul)
            elif note_handle and on_off:
                note_handle.end()
                if volume + random.uniform(-0.3, 0.3) > threshold:
                    pitch = scale[next(walk)]
                    print(pitch)
                    note_handle = self.melody_inst.start_note(pitch, volume * volume_mul)
                else:
                    note_handle = None
            wait(self.pulse_length)
        if note_handle:
            note_handle.end()


def multi_iterator(iterator, multiple):
    for x in iterator:
        for _ in range(multiple):
            yield x


class HiHatLoop(DrumLoop):
    drum_pitch = 42
    melody_inst = s.new_part("Saxophone")
    min_degree, max_degree = -7, 7

    def get_scale(self):
        return Scale.from_pitches(
            [72 + i for i, on_off in zip(range(self.cycle_length), self.beats()) if on_off] +
            [72 + self.cycle_length]
        )

    def play_melody(self, threshold, volume_mul=1):
        walk = random_walk(
            sum(self.beats()) % (self.max_degree - self.min_degree) // 2 + self.min_degree,
            clamp_min=self.min_degree,
            clamp_max=self.max_degree
        )
        playing = False
        scale = self.get_scale()

        for volume, on_off in multi_iterator(zip(self.volumes(), self.beats()), 2):
            if on_off and volume > threshold and not playing:
                playing = True
            elif not on_off or volume < threshold and playing:
                playing = False
            if playing:
                self.melody_inst.play_note(scale[next(walk)], volume * volume_mul, self.pulse_length / 2)
            else:
                wait(self.pulse_length / 2)


class KickLoop(DrumLoop):
    drum_pitch = 36
    melody_inst = s.new_part("Trombone")
    min_pitch, max_pitch = 36, 55

    def get_scale(self):
        return Scale.from_pitches(
            [72 + i for i, on_off in zip(range(self.cycle_length), self.beats()) if on_off] +
            [72 + self.cycle_length]
        )

    def play_melody(self, threshold, volume_mul=1):
        scale = self.get_scale()

        min_degree, max_degree = scale.pitch_to_degree(self.min_pitch), scale.pitch_to_degree(self.max_pitch)
        walk = random_walk(
            sum(self.beats()) % (max_degree - min_degree) // 2 + min_degree,
            step=2,
            clamp_min=min_degree,
            clamp_max=max_degree
        )

        note_handle = None
        for volume, on_off in zip(self.volumes(), self.beats()):
            if (not note_handle) and on_off and volume > threshold:
                note_handle = self.melody_inst.start_note(scale[next(walk)], volume * volume_mul)
            elif note_handle and on_off:
                note_handle.end()
                if volume + random.uniform(-0.3, 0.3) > threshold:
                    note_handle = self.melody_inst.start_note(scale[next(walk)], volume * volume_mul)
                else:
                    note_handle = None
            wait(self.pulse_length)
        if note_handle:
            note_handle.end()


def snare_fitness_func(snare_loop: SnareLoop) -> float:
    return target_fit_score(snare_loop.busyness(), 0.4, 0.1) + snare_loop.beat_strength_alignment(snare_beat_strengths)


def hihat_fitness_func(hihat_loop: HiHatLoop) -> float:
    return target_fit_score(hihat_loop.busyness(), 0.9, 0.2) + 2 * hihat_loop.evenness() + hihat_loop.beat_strength_alignment(beat_strengths)


def kick_fitness_func(kick_loop: KickLoop) -> float:
    return target_fit_score(kick_loop.busyness(), 0.2, 0.1) + kick_loop.beat_strength_alignment(beat_strengths)


# snare_pop = Population.generate(SnareLoop, 100, snare_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))
# hihat_pop = Population.generate(HiHatLoop, 100, hihat_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))
# kick_pop = Population.generate(KickLoop, 100, kick_fitness_func, reproduction_curve=Envelope.from_levels([0, 5]))

# quiet_genome = [0] * DrumLoop.cycle_length + [random.uniform(0.1, 1) for _ in range(DrumLoop.cycle_length)]
quiet_genome = [0 for _ in range(DrumLoop.cycle_length)] + [0.1 for _ in range(DrumLoop.cycle_length)]

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


snare_pop.evolve_continuously(9, sex_prob=0.6, clock=s)
hihat_pop.evolve_continuously(8, sex_prob=0.6, clock=s)
kick_pop.evolve_continuously(7, sex_prob=0.6, clock=s)


kick_play_thresh = TimeVaryingParameter([1, 1,  0], [50, 150], units="time")
snare_play_thresh = TimeVaryingParameter([1, 1,  0], [100, 200], units="time")
hihat_play_thresh = TimeVaryingParameter([1, 1,  0], [150, 250], units="time")


while s.time() < 200:
    kit.play_note(81, 1, 1, blocking=False)
    snare_individual = snare_pop.get_individual(0.7)
    hihat_individual = hihat_pop.get_individual(0.5)
    kick_individual = kick_pop.get_individual(0.5)
    fork(kick_individual.play_bar)
    if kick_fitness_func(kick_individual) * random.random() > 0.5:
        fork(kick_individual.play_melody, args=(kick_play_thresh(), ))
    fork(snare_individual.play_bar)
    if snare_fitness_func(snare_individual) * random.random() > 0.5:
        fork(snare_individual.play_melody, args=(snare_play_thresh() ** 0.5, ))
    fork(hihat_individual.play_bar, args=(0.6, ))
    if hihat_fitness_func(hihat_individual) * random.random() > 0.5:
        fork(hihat_individual.play_melody, args=(hihat_play_thresh() ** 0.5, ))

    print(f"Population average: {kick_pop.mean_fitness()}, Individual: {kick_fitness_func(kick_individual)}")
    wait(DrumLoop.bar_duration)


"""
How to get melody out of the SAME GENOTYPE as the rhythm_loop.
Use different phenotypic expression, selection criterion.
Use the scales from these binary on/off switches?
Maybe dormant/useless genes that then find a niche?
"""