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

import cmath
import random
import itertools
import math
import threading
import numpy as np
from scamp import *
from marciano.evolution import TraitInfo, Individual, Population
from marciano.utility_funcs import target_fit_score
from scamp_extensions.utilities import TimeVaryingParameter, rotate_sequence, remap, wrap_to_range, atan_warp
from scamp_extensions.rhythm import indispensability_array_from_expression
from functools import lru_cache
from modspread import get_mod_n_spread_array
from save_vals import SaveVals

STREAM_MIDI_TO_LOGIC = False

random.seed(10)
saver = SaveVals()

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


def do_metro():
    """In case we need a metronome to figure out where we are."""
    while True:
        for j in range(4):
            for i in range(3):
                if j == i == 0:
                    metro_kit.play_note(67, 1.0, 0.5)
                else:
                    wait(0.5)


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
        return self.__class__,  self.genotype_array


# ---------------------------------------- SET UP ENSEMBLE ------------------------------------------------

SPEED_FACTOR = 1  # * 178 / 190

try:
    s = Session(default_soundfont="MuseScore_General", tempo=190 * SPEED_FACTOR)
except ValueError:
    s = Session(tempo=190)
# s.print_default_soundfont_presets()

s.timing_policy = "relative"  # 0.7

if STREAM_MIDI_TO_LOGIC:
    kit = s.new_midi_part("Drum Kit", "IAC Driver Bus 1")
    bass = s.new_midi_part("Bass", "IAC Driver Bus 2")
    piano = s.new_midi_part("Piano", "IAC Driver Bus 3")
    sax = s.new_midi_part("Saxophone", "IAC Driver Bus 4")
    orch_hit = s.new_midi_part("Orchestra Hit", "IAC Driver Bus 5")
    strings = s.new_midi_part("Strings", "IAC Driver Bus 6", num_channels=7)
    marimba = s.new_midi_part("Marimba", "IAC Driver Bus 7")
    metro_kit = s.new_midi_part("Metronome Kit", "IAC Driver Bus 8")
else:
    kit = s.new_part("STANDARD")
    bass = s.new_part("Fingered Bass")
    piano = s.new_part("Piano")
    sax = s.new_part("Saxophone")
    orch_hit = s.new_part("Orchestra hit")
    strings = s.new_part("strings", num_channels=7)
    marimba = s.new_part("marimba")
    metro_kit = s.new_part("STANDARD")


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
            short_note_thresh = np.percentile(volumes_np, 50)
            for root_pitch, chord_config, volume, on_off, coin_flip in zip(self.root_pitches,
                                                                           itertools.cycle(self.chord_configurations), self.volumes(),
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
        for root_pitch, chord_config, volume, on_off in zip(self.root_pitches,
                                                            itertools.cycle(self.chord_configurations), self.volumes(),
                                                            self.beats()):
            if on_off and saver.save(int(volume >= short_note_thresh and random.random() < SnareLoop.play_prob_param()), "snare_piano"):
                if SnareLoop.held_chord is not None:
                    SnareLoop.held_chord.end()
                    SnareLoop.held_chord = None
                if volume >= long_note_thresh:
                    SnareLoop.held_chord = self.inst.start_chord([root_pitch + 12 + interval for interval in chord_config],
                                                                 remap(volume, 0.5, 1.0, 0, 1))
                    wait(self.pulse_length)
                else:
                    self.inst.play_chord([root_pitch + 12 + interval for interval in chord_config],
                                         remap(volume, 0.5, 1.0, 0, 1),
                                         self.pulse_length, "staccato")
            else:
                if not on_off:
                    saver.save(0, "snare_piano")
                wait(self.pulse_length)
        self.playback_mask = saver.values_by_situation["snare_piano"][-len(self.root_pitches):]

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
        saver.save([voices, note_change_points], "harmony_voices")
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
            for root_pitch, volume, on_off, coin_flip in zip(self.root_pitches, self.volumes(), self.beats(), self.playback_mask):
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
        for root_pitch, volume, on_off in zip(self.root_pitches, self.volumes(), self.beats()):
            pitch = wrap_to_range(pitch, self.min_pitch, self.max_pitch)
            if on_off and saver.save(int(random.random() < HiHatLoop.play_prob_param()), "hihat_sax"):
                for _ in range(2):
                    self.inst.play_note(pitch,
                                        remap(volume, 0.2, 1.0, 0, 1),
                                        self.pulse_length / 2)
                    pitch += next(interval_pattern)
            else:
                if not on_off:
                    saver.save(0, "hihat_sax")
                for _ in range(2):
                    next(interval_pattern)
                wait(self.pulse_length)
        self.playback_mask = saver.values_by_situation["hihat_sax"][-len(self.beats()):]

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
        saver.save(pitches_played, "end_arpeggio_pitches")
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
            for root_pitch, volume, on_off, flip in zip(self.root_pitches, self.volumes(), self.beats(), self.playback_mask):
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
                if pitch_class is None:   # got skipped randomly
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

        saver.save(bass_line_pcs_played, "bass_pitches_end")
        self.coin_flipped_end_bass_pcs = bass_line_pcs_played
        
    def __reduce__(self):
        # Return a tuple containing the constructor and arguments to recreate the object
        return self._reconstruct, (self.genotype_array, self.playback_mask, self.coin_flipped_end_bass_pcs)

    @staticmethod
    def _reconstruct(genotype_array, playback_mask, coin_flipped_end_bass_line):
        # This method reconstructs the object from the keyword arguments
        return KickLoop(*genotype_array, playback_mask=playback_mask,
                        coin_flipped_end_bass_line=coin_flipped_end_bass_line)


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


class EvolutionMusicRecording:

    def __init__(self, pickled_snapshots_file):
        import pickle
        with open(pickled_snapshots_file, "rb") as f:
            self.snapshots = pickle.load(f)

        self.b = self.snapshots[0][0]
        self.t = self.snapshots[0][1]
        self.snapshot_index = 0

    def current_snapshot(self):
        return self.snapshots[self.snapshot_index]

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

    def normalize(self, db, dt, remove_fast_forward=False):
        self.snapshots = [
            (i * db, i * dt, *snapshot[2:])
            for i, snapshot in enumerate(self.snapshots)
            if not remove_fast_forward or not snapshot[4]
        ]
        self.b = self.t = self.snapshot_index = 0

    def is_fast_forwarding(self):
        return self.current_snapshot()[4]



# s.fast_forward()
# EvolutionMusic("recorded_snapshots.pk").run()  # Runs and saves recorded_snapshots.pk
# saver.save_to_json("saved_vals.json")