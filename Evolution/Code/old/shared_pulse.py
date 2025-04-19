import random

from scamp import *
from marciano.evolution import TraitInfo, Individual, Population
from scamp_extensions.pitch import Scale

random.seed(0)
s = Session(tempo=160)

s.timing_policy = 0.8

piano_pedal_down = s.new_part("piano")
piano = s.new_part("piano")
piano_pedal_down.send_midi_cc(64, 1)

drone_pitch_loop = [34, 41, 46]
drone_rhythm_loop = [1.0] + [0.5] * 5

def cycle(iterable):
    while iterable:
        for element in iterable:
            yield element


# TODO: Don't conflate consonance with richness/complexity
# 3 different categories: dissonance, imperfect consonance, perfect consonance
def major_scale_coherence(p, root):
    interval = (p - root) % 12
    if interval == 4:
        return 1
    if interval in (2, 7, 9):
        return 0.7
    elif interval in (0, 5, 11):
        return 0.5
    elif interval in (1, 3, 6, 8, 10):
        return 0



class WiggleDrop(Individual):

    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("dur_pow", (0, 2), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("start_pitch", (70, 95), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("wiggle_interval", (1, 7), mutation_width=1, quantization=1, mutation_probability=0.3),
        TraitInfo("drop_interval", (1, 10), mutation_width=2, quantization=1, mutation_probability=0.3),
    )

    def play(self, instrument: ScampInstrument):
        wait(self.metric_phase)
        pitches = [self.start_pitch, self.start_pitch - self.wiggle_interval,
                   self.start_pitch, self.start_pitch - self.drop_interval]
        durs = [0.25, 0.25, 0.5, 0.5]
        properties = ["length + 0.1", "length + 0.1",  "staccato", None]
        dur_mul = 2 ** self.dur_pow
        for p , d, prop in zip(pitches, durs, properties):
            instrument.play_note(p, 0.7, d * dur_mul, prop)


    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference drum_pitch. Range 0-1. Weights first note most.
        """
        start_weight = 3
        drop_weight = 2
        wiggle_weight = 2 if self.wiggle_interval > 2 else 1 if self.wiggle_interval == 2 else 0
        total_weight = start_weight + drop_weight + wiggle_weight
        return (major_scale_coherence(self.start_pitch, reference_pitch) * start_weight +
                major_scale_coherence(self.start_pitch - self.wiggle_interval, reference_pitch) * wiggle_weight +
                major_scale_coherence(self.start_pitch - self.drop_interval, reference_pitch) * drop_weight) / total_weight

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return max(self.wiggle_interval, self.drop_interval)

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return 2 ** self.dur_pow* 1.5


class ScaleWorm(Individual):
    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("length", (3, 10), mutation_width=2, quantization=1, mutation_probability=0.4),
        TraitInfo("scale_switch1", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch2", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch3", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch4", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch5", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch6", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch7", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch8", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch9", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch10", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch11", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("scale_switch12", (0, 1), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("start_degree", (-10, 8), mutation_width=2, quantization=1, mutation_probability=0.4),
        TraitInfo("up_probability", (0, 1), mutation_probability=0.5),
        TraitInfo("random_seed", mutation_probability=0.1)
    )

    def __init__(self, *genotype: float):
        super().__init__(*genotype)
        self._recalculate()

    def _recalculate(self):
        self.scale = self._get_scale()
        self.pitches = self._get_pitches()

    @classmethod
    def new_random(cls):
        new_rand = super().new_random()
        while sum(new_rand.genotype_array[2:14]) < 6:
            new_rand = super().new_random()
        return new_rand

    def mutated(self):
        new_mutated = super().mutated()
        while sum(new_mutated.genotype_array[2:14]) < 6:
            new_mutated = super().mutated()
        return new_mutated

    def _get_scale(self):
        pitches = []
        for pitch, switch in zip(range(60, 72), self.genotype_array[2:14]):
            if switch:
                pitches.append(pitch)
        if len(pitches) < 2:
            pitches = [60, 62]
        return Scale.from_pitches(pitches)

    def _get_pitches(self):
        pitches = []
        scale = self._get_scale()
        degree = self.start_degree
        random_number_generator = random.Random(self.random_seed)
        for _ in range(self.length):
            pitches.append(scale[degree])
            degree += 1 if random_number_generator.random() < self.up_probability else -1
        return pitches

    def play(self, instrument: ScampInstrument):
        wait(self.metric_phase)
        for pitch in self._get_pitches():
            instrument.play_note(pitch, 0.6, 1/3)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference drum_pitch. Range 0-1. Weights first note most.
        """
        return (3 * major_scale_coherence(self.pitches[0], reference_pitch) +
                sum(major_scale_coherence(p, reference_pitch) for p in self.pitches[1:])) / (len(self.pitches) + 2)

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return max(self.pitches) - min(self.pitches)

    def upwardness(self):
        return sum(b > a for a, b in zip(self.pitches[:-1], self.pitches[1:])) / (len(self.pitches) - 1)

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return self.length / 3


def drone():
    for p, d in zip(cycle(drone_pitch_loop), cycle(drone_rhythm_loop)):
        piano_pedal_down.play_note(p, 0.3, d)


def wiggle_drop_fitness_func(wiggle_drop) -> float:
    return 20 * wiggle_drop.major_scale_coherence(58) \
        - wiggle_drop.duration()  \
        - 3 * (wiggle_drop.metric_phase - 2) % 7 ** 1.5


def scale_worm_fitness_func(scale_worm) -> float:
    return 40 * scale_worm.major_scale_coherence(58) \
        + 5 * scale_worm.upwardness() * scale_worm.duration() \
        - 3 * (scale_worm.metric_phase - 3.5) % 7 ** 1.5

fork(drone)

wiggle_drops = Population.generate(WiggleDrop, 100, fitness_function=wiggle_drop_fitness_func, reproduction_curve=Envelope.from_levels([1, 5]))
scale_worms = Population.generate(ScaleWorm, 100, fitness_function=scale_worm_fitness_func, reproduction_curve=Envelope.from_levels([1, 5]))

wiggle_drops.evolve_continuously(40)
scale_worms.evolve_continuously(40)

while True:
    fork(wiggle_drops.get_individual(0.3).play, args=(piano, ))
    fork(scale_worms.get_individual(0.3).play, args=(piano, ))
    wait(7)



"""
Notes:
- Long bar, so that the metric phase is more easily heard.
- Consider an evolutionary model of generating beats in which each part (kick, snare, hihat) is trying to find its niche.
    * Perhaps pressure for kick and snare to be far apart, hihat to be at other locations
    * perhaps pressure for a certain kind of symmetry or asymmetry?
    * Pressure for a certain proportion of overlap.
- Split consonance into Perfect, imperfect, dissonant, and weight each separately.
"""