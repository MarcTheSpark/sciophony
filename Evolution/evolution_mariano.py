import functools
import random
from abjad.math import weight
from scamp import *
from marciano.evolution import TraitInfo, Individual, Population
from marciano.utility_funcs import target_fit_score
from scamp_extensions.pitch import Scale

# random.seed(0)
s = Session(tempo=160)

s.timing_policy = 0.1

piano = s.new_part("piano")
piano_pedal_down = s.new_part("piano")

wiggle_drops_inst = s.new_part("Agogo2", preset=0)  # 113)
scale_worm_inst = s.new_part("clarinet")
scale_worm_2_inst = s.new_part("Echo Drops 2")
gesture_triple_inst = s.new_part("bass")
chromatic_question_inst = s.new_part("Synth Calliope 2", 82)
simple_question_inst = s.new_part("Halo Pad 2", 94)

drum = s.new_part("Power")
piano_pedal_down.send_midi_cc(64, 1)

drone_pitch_loop = [0, 7, 12]
drone_rhythm_loop = [1.0] + [0.5] * 5  # a bar duration is 7.5

being_seen_probability = 0.4  # probability that an individual is played (same for all species for now)


def percussion_loop():
    wait(0.5)

    if (r := random.random()) < 1 / 3:
        wait(1)
    elif r < 2 / 3:
        drum.play_note(63, 1, 0.5)
        drum.play_note(63, 1, 0.5)
    else:
        drum.play_note(63, 1, 1)

    wait(1)

    if (r := random.random()) < 1 / 3:
        wait(1)
    elif r < 2 / 3:
        drum.play_note(54, 1, 0.5)
        drum.play_note(54, 1, 0.5)
    else:
        drum.play_note(54, 1, 1)


def cycle(iterable):
    while iterable:
        for element in iterable:
            yield element


def major_scale_coherence(p, root):
    interval = (p - root) % 12
    if interval == 4:
        return 1
    if interval in (2, 7, 9):
        return 0.7
    elif interval in (0, 5, 11):
        return 0.5
    elif interval in (1, 3, 6, 8, 10):
        return -0.5


class WiggleDrop(Individual):
    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("dur_pow", (0, 2), mutation_width=1, quantization=0.5, mutation_probability=0.2),
        TraitInfo("start_pitch", (70, 95), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("wiggle_interval", (1, 7), mutation_width=1, quantization=1, mutation_probability=0.3),
        TraitInfo("drop_interval", (1, 10), mutation_width=2, quantization=1, mutation_probability=0.3),
    )

    def play(self, instrument: ScampInstrument):
        if random.random() > being_seen_probability:
            return
        wait(self.metric_phase)
        # instrument.play_note(70,1,0.25)
        pitches = [self.start_pitch, self.start_pitch - self.wiggle_interval,
                   self.start_pitch, self.start_pitch - self.drop_interval]
        durs = [0.25, 0.25, 0.5, 0.5]
        properties = ["length + 0.1", "length + 0.1", "staccato", None]
        dur_mul = 2 ** self.dur_pow
        for p, d, prop in zip(pitches, durs, properties):
            instrument.play_note(p, 0.3, d * dur_mul, prop)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference pitch. Range 0-1. Weights first note most.
        """
        start_weight = 3
        drop_weight = 2
        wiggle_weight = 2 if self.wiggle_interval > 2 else 1 if self.wiggle_interval == 2 else 0
        total_weight = start_weight + drop_weight + wiggle_weight
        return (major_scale_coherence(self.start_pitch, reference_pitch) * start_weight +
                major_scale_coherence(self.start_pitch - self.wiggle_interval, reference_pitch) * wiggle_weight +
                major_scale_coherence(self.start_pitch - self.drop_interval,
                                      reference_pitch) * drop_weight) / total_weight

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return max(self.wiggle_interval, self.drop_interval)

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return 2 ** self.dur_pow * 1.5


class GestureTriple(Individual):
    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("dur_pow", (0, 2), mutation_width=1, quantization=1, mutation_probability=0.2),
        TraitInfo("start_pitch", (70, 95), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("drop_interval", (1, 10), mutation_width=2, quantization=1, mutation_probability=0.3),
    )

    def play(self, instrument: ScampInstrument):
        if random.random() > being_seen_probability:
            return
        wait(self.metric_phase)
        pitches = [self.start_pitch, self.start_pitch, self.start_pitch - self.drop_interval]
        durs = [0.25, 0.25, 0.5]
        dur_mul = 2 ** self.dur_pow
        for p, d in zip(pitches, durs):
            instrument.play_note(p, 0.3, d * dur_mul)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference pitch. Range 0-1. Weights first note most.
        """
        start_weight = 3
        drop_weight = 2
        total_weight = start_weight + drop_weight
        return (major_scale_coherence(self.start_pitch, reference_pitch) * start_weight +
                major_scale_coherence(self.start_pitch - self.drop_interval,
                                      reference_pitch) * drop_weight) / total_weight

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return self.drop_interval

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return 2 ** self.dur_pow


class SimpleQuestion(Individual):
    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("total_dur", (1, 4), mutation_width=0.5, quantization=0, mutation_probability=0.2),
        TraitInfo("start_pitch", (58, 84), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("interval_up", (1, 7), mutation_width=1, quantization=1, mutation_probability=0.3),
        TraitInfo("interval_down", (1, 10), mutation_width=2, quantization=1, mutation_probability=0.3),
    )

    def play(self, instrument: ScampInstrument):
        if random.random() > being_seen_probability:
            return

        wait(self.metric_phase)
        # instrument.play_note(70,1,0.25)
        pitches = [self.start_pitch, self.start_pitch + self.interval_up,
                   self.start_pitch + self.interval_up, self.start_pitch,
                   self.start_pitch - self.interval_down, self.start_pitch]
        durs = [0.25, 0.25, 0.5, 0.25, 0.5, 0.5]
        properties = [None, "staccato", None, None, None, None]
        dur_mul = abs(self.total_dur / 2.25)
        for p, d, prop in zip(pitches, durs, properties):
            instrument.play_note(p, 0.7, d * dur_mul, prop)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference pitch. Range 0-1. Weights first note most.
        """
        start_weight = 3
        up_weight = 2 if self.interval_up > 2 else 1 if self.interval_up == 2 else 0
        down_weight = 2 if self.interval_down > 2 else 1 if self.interval_down == 2 else 0
        total_weight = start_weight + up_weight + down_weight
        return (major_scale_coherence(self.start_pitch, reference_pitch) * start_weight +
                major_scale_coherence(self.start_pitch + self.interval_up, reference_pitch) * up_weight +
                major_scale_coherence(self.start_pitch - self.interval_down, reference_pitch) * down_weight) / total_weight

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return self.interval_up + self.interval_down

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return self.total_dur


class ChromaticQuestion(Individual):
    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("total_dur", (1, 4), mutation_width=0.5, quantization=0, mutation_probability=0.2),
        TraitInfo("start_pitch", (34, 60), mutation_width=5, quantization=1, mutation_probability=0.2),
        TraitInfo("interval_up", (3, 9), mutation_width=1, quantization=1, mutation_probability=0.3),
    )

    def play(self, instrument: ScampInstrument):
        if random.random() > being_seen_probability:
            return

        wait(self.metric_phase)
        pitches = self.get_pitches()
        durs = [0.25, 0.25, 0.25, 0.75, 0.25]

        dur_mul = abs(self.total_dur / 1.75)  # if dur_pow is 1 then total duration of gesture is 1.

        for p, d in zip(pitches, durs):
            instrument.play_note(p, 0.7, d * dur_mul)

    def get_pitches(self):
        step_size = self.interval_up / 3
        return (self.start_pitch, round(self.start_pitch + step_size), round(self.start_pitch + 2 * step_size),
                round(self.start_pitch + 3 * step_size), self.start_pitch)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference pitch. Range 0-1. Weights first note most.
        """
        note_weights = (2, 1, 1, 2, 1)
        return sum(major_scale_coherence(pitch, reference_pitch) * weight
                   for pitch, weight in zip(self.get_pitches(), note_weights)) / sum(note_weights)

    def range(self):
        """
        Range in pitches from top to bottom
        """
        return self.interval_up

    def duration(self):
        """
        Total duration of gesture in beats.
        """
        return self.total_dur


class ScaleWorm(Individual):
    """
    A worm that wiggles up and down a scale, defined by pitch class sw  itches.
    """

    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("length", (3, 8), mutation_width=2, quantization=1, mutation_probability=0.4),
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
        TraitInfo("up_probability", (0.5, 1), mutation_probability=0.5),
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
            instrument.play_note(pitch, 0.6, 1 / 3)

    def major_scale_coherence(self, reference_pitch):
        """
        Coherence with major scale from reference pitch. Range 0-1. Weights first note most.
        """
        weights = [3 if i % 3 == 0 else 1 for i in range(len(self.pitches))]
        return sum(w * major_scale_coherence(p, reference_pitch) for p, w in zip(self.pitches, weights)) / sum(weights)

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


class ScaleWorm2(ScaleWorm):
    """
    Same as ScaleWorm, except it tends to be longer and more downward.
    """

    genotype_info = (
        TraitInfo("metric_phase", (0, 6.5), mutation_width=0.5, quantization=0.5, mutation_probability=0.5),
        TraitInfo("length", (8, 18), mutation_width=2, quantization=1, mutation_probability=0.4),
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
        TraitInfo("up_probability", (0, 0.5), mutation_probability=0.2),  # tends to go down
        TraitInfo("random_seed", mutation_probability=0.1)
    )


# ---------------------------------- FITNESS FUNCTIONS -----------------------------------------------

scale_root = 34

def mod_distance(x, y, modulo):
    dist = abs(x - y) % modulo
    return min(dist, modulo - dist)


def wiggle_drop_fitness_func(wiggle_drop: WiggleDrop, print_factors=False) -> float:
    scale_coherence_fitness = wiggle_drop.major_scale_coherence(scale_root)
    duration_fitness = target_fit_score(wiggle_drop.duration(), 3, 0.5)
    phase_fitness = target_fit_score(mod_distance(wiggle_drop.metric_phase, 4, 7), 0, 0.8) #-3 * abs((wiggle_drop.metric_phase - 4) % 7)
    if print_factors:
        print(f"Scale Coherence: {scale_coherence_fitness:.2f}, "
              f"Duration: {duration_fitness:.2f}, "
              f"Phase: {phase_fitness:.2f}")
    return 3 * scale_coherence_fitness + duration_fitness + phase_fitness


def simple_question_fitness_func(simple_question: SimpleQuestion, phase_target=0, print_factors=False) -> float:
    scale_coherence_fitness = simple_question.major_scale_coherence(scale_root)
    duration_fitness = target_fit_score(simple_question.duration(), 2.25, 0.3)
    phase_fitness = target_fit_score(mod_distance(simple_question.metric_phase, phase_target, 7), 0, 0.5)
    if print_factors:
        print(f"Scale Coherence: {scale_coherence_fitness:.2f}, "
              f"Duration: {duration_fitness:.2f}, "
              f"Phase: {phase_fitness:.2f}")
    return 3 * scale_coherence_fitness + duration_fitness + phase_fitness


chromatic_question_fitness_func = functools.partial(simple_question_fitness_func, phase_target=2)


def scale_worm_fitness_func(scale_worm: ScaleWorm, duration_target=1.5, phase_target=1, print_factors=False) -> float:
    scale_coherence_fitness = scale_worm.major_scale_coherence(scale_root)
    duration_fitness = target_fit_score(scale_worm.duration(), duration_target, 0.3)
    phase_fitness = target_fit_score(mod_distance(scale_worm.metric_phase, phase_target, 7), 0, 0.5)
    if print_factors:
        print(f"Scale Coherence: {scale_coherence_fitness:.2f}, "
              f"Duration: {duration_fitness:.2f}, "
              f"Phase: {phase_fitness:.2f}")
    return 3 * scale_coherence_fitness + duration_fitness + phase_fitness


scale_worm_2_fitness_func = functools.partial(scale_worm_fitness_func, duration_target=10, phase_target=5)



def gesture_triple_fitness_func(gesture_triple: GestureTriple, phase_target=0.5, print_factors=False) -> float:
    scale_coherence_fitness = gesture_triple.major_scale_coherence(scale_root)
    duration_fitness = target_fit_score(gesture_triple.duration(), 1.0, 0.3)
    phase_fitness = target_fit_score(mod_distance(gesture_triple.metric_phase, phase_target, 7), 0, 0.5)
    if print_factors:
        print(f"Scale Coherence: {scale_coherence_fitness:.2f}, "
              f"Duration: {duration_fitness:.2f}, "
              f"Phase: {phase_fitness:.2f}")
    return 3 * scale_coherence_fitness + duration_fitness + phase_fitness


# s.start_transcribing()
# s.fast_forward_in_beats(1000)


wiggle_drops = Population.generate(WiggleDrop, 2000, fitness_function=wiggle_drop_fitness_func,
                                   reproduction_curve=Envelope.from_levels([1, 2]))
wiggle_drops.individuals = wiggle_drops.individuals[:100]

scale_worms = Population.generate(ScaleWorm, 2000, fitness_function=scale_worm_fitness_func,
                                  reproduction_curve=Envelope.from_levels([1, 2]))
scale_worms.individuals = scale_worms.individuals[:100]

scale_worms_2 = Population.generate(ScaleWorm2, 2000, fitness_function=scale_worm_2_fitness_func,
                                    reproduction_curve=Envelope.from_levels([1, 2]))
scale_worms_2.individuals = scale_worms_2.individuals[:100]

simple_questions = Population.generate(SimpleQuestion, 2000, fitness_function=simple_question_fitness_func,
                                       reproduction_curve=Envelope.from_levels([1, 2]))
simple_questions.individuals = simple_questions.individuals[:100]

chromatic_questions = Population.generate(ChromaticQuestion, 2000, fitness_function=chromatic_question_fitness_func,
                                          reproduction_curve=Envelope.from_levels([1, 5]))
chromatic_questions.individuals = chromatic_questions.individuals[:100]

gesture_triples = Population.generate(GestureTriple, 200, fitness_function=gesture_triple_fitness_func,
                                      reproduction_curve=Envelope.from_levels([1, 5]))
gesture_triples.individuals = gesture_triples.individuals[:100]


wiggle_drops.evolve_continuously(6, sex_prob=0.6, clock=s, amortize=True)
scale_worms.evolve_continuously(6, clock=s, amortize=True)
scale_worms_2.evolve_continuously(6, clock=s, amortize=True)
simple_questions.evolve_continuously(6, sex_prob=0.6, clock=s, amortize=True)
chromatic_questions.evolve_continuously(6, sex_prob=0.4, clock=s, amortize=True)
gesture_triples.evolve_continuously(6, clock=s, amortize=True)



def drone():
    for p, d in zip(cycle(drone_pitch_loop), cycle(drone_rhythm_loop)):
        piano_pedal_down.play_note(scale_root + p, 0.3, d)


fork(drone)


def change_pedal():
    piano_pedal_down.send_midi_cc(64, 0)
    wait(0.2)
    piano_pedal_down.send_midi_cc(64, 1)


def play_one_loop_of_the_jungle():
    wiggle_drop_individual = wiggle_drops.get_individual(0.4, 0.7)
    # wiggle_drop_fitness_func(wiggle_drop_individual, print_factors=True)
    fork(wiggle_drop_individual.play, args=(wiggle_drops_inst,))

    simple_question_individual = simple_questions.get_individual(0.4, 0.7)
    # simple_question_fitness_func(simple_question_individual, print_factors=True)
    fork(simple_question_individual.play, args=(simple_question_inst,))

    chromatic_question_individual = chromatic_questions.get_individual(0.4, 0.7)
    # chromatic_question_fitness_func(chromatic_question_individual, print_factors=True)
    fork(chromatic_question_individual.play, args=(chromatic_question_inst,))

    scale_worm_individual = scale_worms.get_individual(0.4, 0.7)
    # scale_worm_fitness_func(scale_worm_individual, print_factors=True)
    fork(scale_worm_individual.play, args=(scale_worm_inst,))

    scale_worm_2_individual = scale_worms_2.get_individual(0.4, 0.7)
    # scale_worm_2_fitness_func(scale_worm_2_individual, print_factors=True)
    fork(scale_worm_2_individual.play, args=(scale_worm_2_inst,))

    gesture_triple_individual = gesture_triples.get_individual(0.4, 0.7)
    # gesture_triple_fitness_func(gesture_triple_individual, print_factors=True)
    fork(gesture_triple_individual.play, args=(gesture_triple_inst,))

    fork(percussion_loop)
    wait(7)


while s.time() < 60:
    play_one_loop_of_the_jungle()


scale_root = 40
fork(change_pedal)


while True:
    play_one_loop_of_the_jungle()

# prf = s.stop_transcribing()
# prf.export_to_midi_file("Evolution_2.mid")


"""
Ideas:

- Include swelling chords in the texture.
- Make the "measure" longer, so that we can really give them temporal niches.
- Clarify ranges, etc.
"""