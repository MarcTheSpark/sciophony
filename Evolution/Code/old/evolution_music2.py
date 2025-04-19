import random
from marciano.evolution import Individual, Population, TraitInfo
from scamp import *
from itertools import cycle
import functools

s = Session(tempo=90)

clarinet = s.new_part("clarinet")
oboe = s.new_part("oboe")
flute = s.new_part("flute")
bassoon = s.new_part("bassoon")

instrument_cycler = cycle([clarinet, oboe, flute])


def consonance(p1, p2):
    interval = (p2 - p1) % 12
    if interval in (3, 4, 8, 9):
        return 3
    elif interval in (0, 5, 7):
        return 1
    elif interval in (2, 10):
        return 0
    elif interval in (3, 6):
        return -3
    else:
        return -5


def major_scale_coherence(p, root):
    interval = (p - root) % 12
    if interval == 4:
        return 4
    if interval in (2, 7, 9):
        return 2
    elif interval in (0, 5, 11):
        return 1
    elif interval in (1, 3, 6, 8, 10):
        return -8


class SixNoteMelody(Individual):
    genotype_info = (
        TraitInfo("p1", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d1", (0.25, 0.5), mutation_width=0.5, quantization=0.25),
        TraitInfo("p2", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d2", (0.25, 0.5), mutation_width=0.5, quantization=0.25),
        TraitInfo("p3", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d3", (0.25, 1.5), mutation_width=0.5, quantization=0.25),
        TraitInfo("p4", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d4", (0.25, 2), mutation_width=0.5, quantization=0.25),
        TraitInfo("p5", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d5", (0.25, 0.5), mutation_width=0.5, quantization=0.25),
        TraitInfo("p6", (60, 80), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("d6", (0.25, 0.5), mutation_width = 0.5, quantization = 0.25),
    )

    def play(self, instrument, transposition=0):
        for pitch, dur in zip(self.genotype_array[::2], self.genotype_array[1::2]):
            instrument.play_note(pitch + transposition, 0.6, dur, "staccato" if dur == 0.25 else None)

    @property
    def pitches(self):
        return self.genotype_array[::2]

    @property
    def durations(self):
        return self.genotype_array[1::2]

    def consonance_with(self, drones):
        return sum(
            sum(consonance(drone_pitch, pitch) for drone_pitch in drones) * dur
            for pitch, dur in zip(self.pitches, self.durations)
        )

    def coherence_with_major_scale(self, root):
        return sum(major_scale_coherence(pitch, root) > 0
                   for pitch, dur in zip(self.pitches, self.durations)) ** 2

    def jumpiness(self):
        return sum((b - a) ** 2 for a, b in zip(self.pitches[:-1], self.pitches[1:])) ** 0.5

    def total_duration(self):
        return sum(self.durations)

    def pitch_variety(self):
        return len(set(self.pitches))


def fitness_func(melody: SixNoteMelody, root):
    # total duration being a nice multiple of 4?
    return melody.coherence_with_major_scale(root) * 4 \
        - melody.total_duration() \
        + 4 * melody.pitch_variety() \
        - melody.jumpiness()


drone_chord = bassoon.start_chord([40, 47], 0.5)

melody_population = Population.generate(SixNoteMelody, 100, fitness_function=functools.partial(fitness_func, root=40))


melody_population.evolve_continuously(60)


def change_fitness_func():
    global drone_chord
    print("Changing fitness func")
    drone_chord.end()
    drone_chord = bassoon.start_chord([46, 53], 0.5)
    melody_population.fitness_function = functools.partial(fitness_func, root=46)


s.fork(change_fitness_func, schedule_at=40)


while True:
    random_individual = melody_population.get_individual(0.7)
    # print(random_individual)
    print(f"This individual: {melody_population.fitness_function(random_individual)}, "
          f"Population average: {melody_population.mean_fitness()}")
    inst = next(instrument_cycler)
    transpose = -12 if inst is clarinet else 0 if inst is oboe else 12
    fork(random_individual.play, args=(inst, transpose))
    wait(random.uniform(1, 3))


# Turning down mutation rate for drum_pitch?
# Changing the harshness of the reproduction curve?
# How to judge the consonance of a melody as a gestalt
# Simpler gestures where there are only a few main points to force to be consonant
# Have them all have the same rhythmic context! Maybe simple loops with an isochronous pulse.
# - evolutionary pressure on rhythmic phase?
# - Could use prime cycles?