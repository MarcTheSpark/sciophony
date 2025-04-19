"""
Definition of all of the evolution species (imports evolution_ensemble.py, and imported by evolution_on_thread.py,
evolution_recording_player.py and evolution_animation.py).
"""

from marciano.evolution import TraitInfo, Individual, Population
import cmath
import itertools
import math
from evolution_ensemble import *
from scamp_extensions.rhythm import indispensability_array_from_expression
from scamp_extensions.utilities import TimeVaryingParameter, rotate_sequence, remap, wrap_to_range, atan_warp
from functools import lru_cache
import numpy as np
from scamp import *
import random


# ------------------------------------- GLOBAL VARIABLES --------------------------------------------

# 12/8 meter, raised to the power of 3 to be extra emphasized
beat_strengths = [x ** 3 for x in indispensability_array_from_expression("2*2*2*3", normalize=True)]
# Snare is rotated by three 8ths so that it hits on the off beats.
snare_beat_strengths = rotate_sequence(beat_strengths, 3)

# We use the first however many of this sorted beat strengths
# later as a denominator when calculating beat strength alignment
beat_strength_values = sorted(beat_strengths, reverse=True)

# Used at the end when the pitchy stuff comes back; controls the probability of playing things towards the end
# ramps up to 1 slowly.
end_play_prob = 0


# ------------------------------------- UTILITY FUNCTIONS --------------------------------------------

@lru_cache
def get_perfectly_even_distance_sum(num_onsets):
    """See calculate_evenness."""
    return abs(cmath.exp(2j * math.pi / num_onsets) - 1) * num_onsets


@lru_cache
def get_perfectly_uneven_distance_sum(cycle_length, num_onsets):
    """Unused; see alternative return of calculate_evenness"""
    return abs(cmath.exp(2j * math.pi / cycle_length) - 1) * (num_onsets - 1) + abs(
        cmath.exp(2j * math.pi * (num_onsets - 1) / cycle_length) - 1)


def calculate_evenness(on_offs):
    """
    Calculates the evenness of a beat, by imagining the onsets placed around a circle, and then finding the perimeter
    of the polygon that joins them. This is then compared to the perimeter of a regular polygon of the same size,
    which is get_perfectly_even_distance_sum. It seems to work, although the perfectly uneven version doesn't give
    a value of 0, so the scaling is kind of weird. The alternative (commented out) return below seems to be a way
    of addressing this, but I don't want to mess with it.
    """
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
    drum_pitch: int = NotImplemented  # the drum sound to use
    melody_inst: ScampInstrument = NotImplemented  # The melody instrument to use in the first part
    pulse_length: float = 0.5
    cycle_length = len(beat_strengths)
    bar_duration = pulse_length * cycle_length

    # Used for the pitchy stuff at the beginning; a cycle of fourths
    root_pitches = [39 + (5 * i) % 12 for i in range(24)]

    # Genotype is a list of on/off switches for beats and volumes for those beats
    # At the end, this is interpreted differently, as chromatic pitch space.
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
            kit.play_note(self.drum_pitch if on_off else None, volume * volume_mul, self.pulse_length,
                          f"text: {int(volume * 10)}")

    def evenness(self):
        return calculate_evenness(self.beats())

    def beat_strength_alignment(self, beat_strengths):
        """
        Measures the alignment of this beat to a list of beat strengths/indispensabilities
        """
        try:
            return sum(beat_strength * volume * on_off
                       for beat_strength, volume, on_off in zip(beat_strengths, self.volumes(), self.beats())) / \
                sum(beat_strength_values[:sum(self.beats())])
        except ZeroDivisionError:
            return 0

    def busyness(self):
        """Measures how much this is on."""
        return sum(self.beats()) / self.cycle_length

    def activity_array(self, on_off_vs_volume_weighted: float = 1):
        """
        A volume-weighted (to an adjustable extend) array of activity for each beat. So it's zero wherever the
        beat switch is off and somewhere between 1 and the volume value wherever the beat switch is on.

        :param on_off_vs_volume_weighted: if 1, it's completely weighted by volume; if 0 it's just on/off
        """
        return np.array([on_off * ((1 - on_off_vs_volume_weighted) + on_off_vs_volume_weighted * volume)
                         for on_off, volume in zip(self.beats(), self.volumes())])

    def __reduce__(self):
        # Return a tuple containing the constructor and arguments to recreate the object
        return self.__class__, self.genotype_array


class SnareLoop(DrumLoop):
    drum_pitch = 38
    inst = piano
    end_inst = strings  # Used at the end when the beat switches reinterpret as harmony
    # controls the entrance of the comp harmony through play probability
    play_prob_param = TimeVaryingParameter([0, 0, 1], [20 / SPEED_FACTOR, 80 / SPEED_FACTOR], clock=s, units="time")

    # intervals above root (cycled through)
    # The snare loop is also used to play piano comp chords, alternating between these two varieties
    chord_configurations = [
        [4, 10, 15],  # 7 sharp 9
        [4, 9, 14],  # major (6, 9)
    ]

    def __init__(self, *genotype: float, playback_mask=None, harmony_playback_record=None):
        super().__init__(*genotype)
        self.playback_mask = playback_mask
        self.harmony_playback_record = harmony_playback_record

    # ----------------------------------- The Opening Pitchy stuff ------------------------------------------

    held_chord = None

    def play_comp_chords(self):
        if self.playback_mask is not None:
            volumes_np = np.array(self.volumes())
            long_note_thresh = np.percentile(volumes_np, 75)
            for root_pitch, chord_config, volume, on_off, coin_flip in zip(self.root_pitches,
                                                                           itertools.cycle(self.chord_configurations),
                                                                           self.volumes(),
                                                                           self.beats(), self.playback_mask):
                if on_off and coin_flip:
                    if SnareLoop.held_chord is not None:
                        SnareLoop.held_chord.end()
                        SnareLoop.held_chord = None
                    if volume >= long_note_thresh:
                        SnareLoop.held_chord = self.inst.start_chord(
                            [root_pitch + 12 + interval for interval in chord_config],
                            remap(volume, 0.5, 1.0, 0, 1))
                        wait(self.pulse_length)
                    else:
                        self.inst.play_chord([root_pitch + 12 + interval for interval in chord_config],
                                             remap(volume, 0.5, 1.0, 0, 1),
                                             self.pulse_length, "staccato")
                else:
                    wait(self.pulse_length)
        else:
            self._play_comp_chords_first_time_random()

    def _play_comp_chords_first_time_random(self):
        volumes_np = np.array(self.volumes())
        long_note_thresh = np.percentile(volumes_np, 75)
        short_note_thresh = np.percentile(volumes_np, 50)
        playback_mask = []
        for root_pitch, chord_config, volume, on_off in zip(self.root_pitches,
                                                            itertools.cycle(self.chord_configurations), self.volumes(),
                                                            self.beats()):
            if on_off and volume >= short_note_thresh and random.random() < SnareLoop.play_prob_param():
                playback_mask.append(1)
                if SnareLoop.held_chord is not None:
                    SnareLoop.held_chord.end()
                    SnareLoop.held_chord = None
                if volume >= long_note_thresh:
                    SnareLoop.held_chord = self.inst.start_chord(
                        [root_pitch + 12 + interval for interval in chord_config],
                        remap(volume, 0.5, 1.0, 0, 1))
                    wait(self.pulse_length)
                else:
                    self.inst.play_chord([root_pitch + 12 + interval for interval in chord_config],
                                         remap(volume, 0.5, 1.0, 0, 1),
                                         self.pulse_length, "staccato")
            else:
                playback_mask.append(0)
                wait(self.pulse_length)
        self.playback_mask = playback_mask

    # -------------------------------- The ending: beat switches reinterpreted as pitch classes -----------------------

    def play_harmony(self):
        """
        Plays the chord progression from measure 1 to measure 2 as a set of horizontal voice-leadings
        that are not necessarily aligned, but that become more aligned over time.
        """
        if hasattr(self, 'harmony_playback_record') and self.harmony_playback_record is not None:
            for pitch_pairs, change_points in zip(*self.harmony_playback_record):
                fork(self._play_harmony_voice, args=(pitch_pairs, change_points))
            wait_for_children_to_finish()
        else:
            self._play_harmony_first_time_random()

    def _play_harmony_first_time_random(self):
        voices = []
        note_change_points = []
        for pitch_pairs in self.get_voices():
            if random.random() < end_play_prob:
                change_points = self.get_random_note_change_points()
                voices.append(pitch_pairs)
                note_change_points.append(change_points)
                fork(self._play_harmony_voice, args=(pitch_pairs, change_points))
        wait_for_children_to_finish()
        self.harmony_playback_record = voices, note_change_points

    def _play_harmony_voice(self, pitches, note_start_points):
        """Plays a single voice leading"""
        wait(note_start_points[0] * self.pulse_length)
        dur1 = note_start_points[1] - note_start_points[0]
        dur2 = 24 - note_start_points[1]
        self.end_inst.play_note(pitches[0], 0.8 if dur1 < 3 else [0.3, 1] if pitches[1] is not None else [0.3, 1, 0],
                                dur1 * self.pulse_length)
        self.end_inst.play_note(pitches[1], [1, 0] if pitches[0] is not None else [0.7, 0],
                                max(dur2, 5) * self.pulse_length)

    def timing_coherence(self):
        """
        Measures how much the the volumes (reinterpreted as probabilities for the start points of the voices)
        are concentrated in a single location in the first 12 and last 12.
        """
        vols = self.timing_probabilities()
        return (max(vols[:12]) / sum(vols[:12]) + max(vols[12:]) / sum(vols[12:])) / 2

    def timing_probabilities(self):
        """
        Volumes are reinterpreted as weightings for the start points of the two notes of each individual voice.
        Rescaled from 0 to 1 and squared to make it less even.
        """
        return tuple(((x - 0.1) / 0.9) ** 2 for x in self.volumes())

    def get_pc_lists(self):
        """
        Reinterpret the beat part of genotype as a list of pitch classes that are on or off.
        There are two PC lists because the genotype covers 24 beats (or two aggregates)
        """
        return list(np.where(self.genotype_array[:12])[0]), list(np.where(self.genotype_array[12:24])[0])

    @staticmethod
    def chord_from_pc_list(pc_list, start_pitch, max_size=math.inf, min_gap=4):
        """Constructs a chord from a pitch class list. Could be better, but it's good enough."""
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
        """Gets the two chords that we voice-lead between"""
        return [SnareLoop.chord_from_pc_list(pc_list, start_pitch, max_size) for pc_list in self.get_pc_lists()]

    def get_voices(self):
        """
        Gets a list of all the voices that make up the chord progression. (Gets the chords, then slices them
        horizontally.) We use zip_longest, so when the chords are different sizes, some of the voices have a
        value of None for one of the notes.
        """
        return list(itertools.zip_longest(*self.get_chords()))

    def get_random_note_change_points(self):
        """
        Using the timing_probabilities as a weighting, randomly picks a start time for note 1 and note 2 to play
        a voice. As timing_coherence goes up, this starts to return more consistently the same time points, making
        the chords line up.
        """
        return (random.choices(list(range(12)), weights=self.timing_probabilities()[:12])[0],
                random.choices(list(range(12, 24)), weights=self.timing_probabilities()[12:24])[0])

    @staticmethod
    def voice_leading_distance(chord1, chord2):
        """
        Calculate the average minimum distance between each note in chord2 and the notes in chord1.
        (This is not used, but was at some point)

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
        Measures the consonance of a chord based on the weighted consonance/dissonance of the associated intervals

        :param chord: List of MIDI pitches representing the chord.
        :param interval_consonance: consonance score (weighting) for each of the 12 intervals

        :return: Measure of consonance for the chord.
        """

        # Generate all pairs of notes in the chord
        pairs = itertools.combinations(chord, 2)

        # Add up the consonances/dissonances of all the intervals
        consonant_count = sum(interval_consonance[abs(max(*pair) - min(*pair)) % 12] for pair in pairs)

        # Atan warp the output
        return atan_warp(consonant_count, -10, 10, 0, 1)

    def __reduce__(self):
        # Return a tuple containing the constructor and arguments to recreate the object
        return self._reconstruct, (self.genotype_array, self.playback_mask, self.harmony_playback_record)

    @staticmethod
    def _reconstruct(genotype_array, playback_mask, harmony_playback_record):
        # This method reconstructs the object from the keyword arguments
        return SnareLoop(*genotype_array, playback_mask=playback_mask,
                         harmony_playback_record=harmony_playback_record)


class HiHatLoop(DrumLoop):
    drum_pitch = 42
    inst = sax
    end_inst = marimba  # used for the arpeggios at the end
    min_pitch, max_pitch = 54, 78
    # Used to regulate the sax as it comes in
    play_prob_param = TimeVaryingParameter([0, 0, 1], [50 / SPEED_FACTOR, 50 / SPEED_FACTOR], clock=s, units="time")

    def __init__(self, *genotype: float, playback_mask=None, coin_flipped_arpeggio_pitches=None):
        super().__init__(*genotype)
        self.playback_mask = playback_mask
        self.coin_flipped_arpeggio_pitches = coin_flipped_arpeggio_pitches

    # ---------------------- First part: sax melodies -----------------------

    def play_melody(self):
        if self.playback_mask is not None:
            pitch = self.root_pitches[0] + 15
            interval_pattern = itertools.cycle([-2, -1, -3, 4])
            for root_pitch, volume, on_off, coin_flip in zip(self.root_pitches, self.volumes(), self.beats(),
                                                             self.playback_mask):
                pitch = wrap_to_range(pitch, self.min_pitch, self.max_pitch)
                if on_off and coin_flip:
                    for _ in range(2):
                        self.inst.play_note(pitch,
                                            remap(volume, 0.2, 1.0, 0, 1),
                                            self.pulse_length / 2)
                        pitch += next(interval_pattern)
                else:
                    for _ in range(2):
                        next(interval_pattern)
                    wait(self.pulse_length)
        else:
            self._play_melody_first_time_random()

    def _play_melody_first_time_random(self):
        pitch = self.root_pitches[0] + 15
        interval_pattern = itertools.cycle([-2, -1, -3, 4])
        playback_mask = []
        for root_pitch, volume, on_off in zip(self.root_pitches, self.volumes(), self.beats()):
            pitch = wrap_to_range(pitch, self.min_pitch, self.max_pitch)
            if on_off and random.random() < HiHatLoop.play_prob_param():
                playback_mask.append(1)
                for _ in range(2):
                    self.inst.play_note(pitch,
                                        remap(volume, 0.2, 1.0, 0, 1),
                                        self.pulse_length / 2)
                    pitch += next(interval_pattern)
            else:
                playback_mask.append(0)
                for _ in range(2):
                    next(interval_pattern)
                wait(self.pulse_length)
        self.playback_mask = playback_mask

    # ------------------------- Ending marimba Arpeggios ---------------------------

    def get_pc_lists(self):
        return list(np.where(self.genotype_array[:12])[0]), list(np.where(self.genotype_array[12:24])[0])

    def _get_arpeggio_pitches(self, pc_octave=72):
        """
        Using the beat switches as pitch class switches now, we loop backwards through the pitch classes that are
        present in the first bar, and then loop backwards through the pitch classes that are present in the second bar.
        The volumes determine when we jump up an octave...kind of. It's very messy and weird.
        """
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
        if self.coin_flipped_arpeggio_pitches is None:
            self._play_arpeggios_first_time_random(pc_octave)
        else:
            for pitch, volume in zip(self.coin_flipped_arpeggio_pitches, self.volumes()):
                self.end_inst.play_note(pitch, volume ** 0.5, self.pulse_length)

    def _play_arpeggios_first_time_random(self, pc_octave=72):
        # Cycle through pcs (in reverse), going down to next closest pc each time
        # Jump up an octave (new hi volume) with every large volume value
        pitches_played = []
        for pitch, volume in zip(self._get_arpeggio_pitches(pc_octave), self.volumes()):
            if random.random() < end_play_prob ** 1.3:
                self.end_inst.play_note(pitch, volume ** 0.5, self.pulse_length)
                pitches_played.append(int(pitch))
            else:
                wait(self.pulse_length)
                pitches_played.append(None)
        self.coin_flipped_arpeggio_pitches = pitches_played

    def __reduce__(self):
        # Return a tuple containing the constructor and arguments to recreate the object
        return self._reconstruct, (self.genotype_array, self.playback_mask,
                                   self.coin_flipped_arpeggio_pitches)

    @staticmethod
    def _reconstruct(genotype_array, playback_mask, coin_flipped_arpeggio_pitches):
        # This method reconstructs the object from the keyword arguments
        return HiHatLoop(*genotype_array, playback_mask=playback_mask,
                         coin_flipped_arpeggio_pitches=coin_flipped_arpeggio_pitches)


class KickLoop(DrumLoop):
    drum_pitch = 36
    inst = bass
    play_prob_param = TimeVaryingParameter(1, clock=s, units="time")

    def __init__(self, *genotype: float, playback_mask=None, coin_flipped_end_bass_line=None):
        super().__init__(*genotype)
        self.playback_mask = playback_mask
        self.coin_flipped_end_bass_pcs = coin_flipped_end_bass_line

    # --------------------- First part: bass line following the circle of fourths (self.root_pitches) ----------------

    def play_bassline(self):
        """
        The on/off beat switches determine when to play, so we hear segments on a circle of fourths with parts
        cut out of it.
        """
        if self.playback_mask is None:
            self._play_bassline_first_time_random()
        else:
            for root_pitch, volume, on_off, flip in zip(self.root_pitches, self.volumes(), self.beats(),
                                                        self.playback_mask):
                if on_off and flip:
                    self.inst.play_note(root_pitch, remap(volume, 0.5, 1.0, 0, 1),
                                        self.pulse_length)
                else:
                    wait(self.pulse_length)

    def _play_bassline_first_time_random(self):
        flips = []
        for root_pitch, volume, on_off in zip(self.root_pitches, self.volumes(), self.beats()):
            if on_off and random.random() < KickLoop.play_prob_param():
                flips.append(True)
                self.inst.play_note(root_pitch, remap(volume, 0.5, 1.0, 0, 1),
                                    self.pulse_length)
            else:
                flips.append(False)
                wait(self.pulse_length)
        self.playback_mask = flips

    # --------------------- Ending part: one (longer) note per bar ----------------

    def play_bassline_end(self):
        """
        For the ending, we are now using activity_array(0.5) as probabilities
        to determine which pitch class to play in the first bar (activity_array[:12]) and second bar
        (activity_array[12:]). The selected value (0-11) determines the pitch class and the metric position.
        """
        if self.coin_flipped_end_bass_pcs:
            for pitch_class in self.coin_flipped_end_bass_pcs:
                if pitch_class is None:  # got skipped randomly
                    wait(12 * self.pulse_length)
                else:
                    wait(pitch_class * self.pulse_length)
                    self.inst.play_note(pitch_class + 36, 1, (12 - pitch_class) * self.pulse_length)
        else:
            self._play_bassline_end_first_time_random()

    def _play_bassline_end_first_time_random(self):
        activities = self.activity_array(0.5)

        bass_line_pcs_played = []

        if sum(activities[:12]) > 0 and random.random() < end_play_prob ** 0.5:
            first_pitch = random.choices(range(0, 12), weights=activities[:12])[0]
            wait(first_pitch * self.pulse_length)
            self.inst.play_note(first_pitch + 36, 1, (12 - first_pitch) * self.pulse_length)
            bass_line_pcs_played.append(first_pitch)
        else:
            # wait(self.bar_duration)
            wait(12 * self.pulse_length)
            bass_line_pcs_played.append(None)

        if sum(activities[12:]) > 0 and random.random() < end_play_prob ** 0.5:
            second_pitch = random.choices(range(0, 12), weights=activities[12:])[0]
            wait(second_pitch * self.pulse_length)
            self.inst.play_note(second_pitch + 36, 1, (12 - second_pitch) * self.pulse_length)
            bass_line_pcs_played.append(second_pitch)
        else:
            # wait(self.bar_duration)
            wait(12 * self.pulse_length)
            bass_line_pcs_played.append(None)

        self.coin_flipped_end_bass_pcs = bass_line_pcs_played

    def __reduce__(self):
        # Return a tuple containing the constructor and arguments to recreate the object
        return self._reconstruct, (self.genotype_array, self.playback_mask, self.coin_flipped_end_bass_pcs)

    @staticmethod
    def _reconstruct(genotype_array, playback_mask, coin_flipped_end_bass_line):
        # This method reconstructs the object from the keyword arguments
        return KickLoop(*genotype_array, playback_mask=playback_mask,
                        coin_flipped_end_bass_line=coin_flipped_end_bass_line)
