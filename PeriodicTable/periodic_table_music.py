import threading
import time
from marciano.periodictable import Element
from periodic_define_sequences import *
from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
import random
import atexit
from scamp_extensions.process import non_repeating_shuffle


class PTableSonification:

    def __init__(self, years_to_play=(1700, 1789, 1820, 1869, 1900, 1970), scale=Scale.from_pitches([62, 66, 69, 70, 72, 73, 74])):

        self.years_to_play = years_to_play
        self.scale = scale
        self.metal_pitch_iterators = {  # i.e. which instruments to use on the orchestral percussion
            "metal": non_repeating_shuffle([77, 80, 81]),
            "metalloid": non_repeating_shuffle([43, 45, 95]),
            "nonmetal": non_repeating_shuffle([60, 62, 64])
        }
        self.current_year = years_to_play[0]
        self.elements_played = []

    def play(self, midi=False):
        threading.Thread(target=self._play, args=(midi, ), daemon=True).start()

    def _play(self, midi=False):
        if midi:
            from ensemble_midi import s
        else:
            from ensemble import s

        self.s = s
        self.vibes, self.piano, self.bass, self.cello, self.oboe, self.drums, self.contrabass = self.s.instruments
        self.main()

    @staticmethod
    def get_volume_sequence(current_year, active_when_discovered=True, min_volume=0.6, max_volume=1.0):
        active_sequence_length = None
        volumes = []
        for discovery_year in discovery_years:
            if (discovery_year <= current_year) if active_when_discovered else (discovery_year > current_year):
                # active
                if active_sequence_length is None:
                    active_sequence_length = 1
                else:
                    active_sequence_length += 1
            else:
                # not active
                if active_sequence_length is not None:
                    # went from active to inactive; calculate the block of active elements
                    step_size = (max_volume - min_volume) / (active_sequence_length - 1) if active_sequence_length > 1 \
                        else (max_volume - min_volume)
                    volumes.extend(min_volume + i * step_size for i in range(active_sequence_length))
                    active_sequence_length = None
                volumes.append(0)
        if active_sequence_length is not None:
            # went from active to inactive; calculate the block of active elements
            step_size = (max_volume - min_volume) / (active_sequence_length - 1) if active_sequence_length > 1 \
                else (max_volume - min_volume)
            volumes.extend(min_volume + i * step_size for i in range(active_sequence_length))
        return volumes

    @staticmethod
    def get_discovered_sequence(year):
        return [discovery_year <= year for discovery_year in discovery_years]

    @staticmethod
    def get_phrase_groups(discovered_sequence, num_false_to_end_phrase=1):
        # List to store lengths of groups
        groups = []
        current_length = 1  # Start with 1 because we're counting the first element already
        current_value = discovered_sequence[0]  # First value to compare with

        for value in discovered_sequence[1:]:  # Start from the second element
            if value == current_value:
                # If the value is the same as the current, increment the length
                current_length += 1
            else:
                # If the value changes, append the current length to lengths and reset counters
                groups.append(current_length if current_value else -current_length)
                current_length = 1
                current_value = value

        # Append the last group's length
        groups.append(current_length if current_value else -current_length)

        if num_false_to_end_phrase > 1:
            merged_groups = []
            for group in groups:
                if group > 0:
                    if len(merged_groups) > 0 and merged_groups[-1] > 0:
                        merged_groups[-1] += group
                    else:
                        merged_groups.append(group)
                elif abs(group) < num_false_to_end_phrase:
                    merged_groups[-1] += abs(group)
                else:
                    merged_groups.append(group)
            return merged_groups
        else:
            return groups

    @staticmethod
    def get_phrase_volumes(year, phrase_envelope: Envelope, num_false_to_end_phrase=1, stretch_envelope=True):
        volumes = []
        discovered_sequence = PTableSonification.get_discovered_sequence(year)
        groups = PTableSonification.get_phrase_groups(discovered_sequence, num_false_to_end_phrase=num_false_to_end_phrase)
        current_element_index = 0
        for group in groups:
            if group < 0:
                # stretch of inactive elements
                volumes.extend([0] * abs(group))
            elif group == 1:
                # avoid potential divide-by-zero if just a group of 1
                volumes.append(phrase_envelope.start_level())
            else:
                env = phrase_envelope.normalize_to_duration(group - 1) if stretch_envelope else phrase_envelope
                volumes.extend([env.value_at(i) * is_discovered
                                for i, is_discovered in zip(range(group), discovered_sequence[current_element_index:])])
            current_element_index += abs(group)
        return volumes

    def play_radius_oboe(self, current_year):
        oboe_note = None
        last_pitch = None
        np.array(r_radius)
        active_array = (~np.isnan(r_radius) & (np.array(discovery_years) <= current_year)).astype(int)
        staccato_array = np.concatenate([np.diff(active_array) < 0, [True]])

        for active, staccato, radius, discovery_year in zip(active_array, staccato_array, r_radius, discovery_years):
            if active:
                pitch = self.scale.round(radius + 3)
                if last_pitch != pitch:
                    if oboe_note:
                        oboe_note.end()
                    props = "param_15: 0.5" if staccato else "param_17: 0.5"
                    oboe_note = self.oboe.start_note(pitch, 0.6 if staccato else 1, props)

                last_pitch = pitch
                wait(0.25)
            else:
                if oboe_note:
                    oboe_note.end()
                last_pitch = oboe_note = None
                wait(0.25)
        if oboe_note:
            oboe_note.end()

    def play_heat_piano(self, current_year):
        """
        Playing down the scale on the piano based on specific heat. Does so at double speed with rising gestures.
        :return:
        """
        for heat, discovery_year, volume in zip(r_heats, discovery_years, self.get_volume_sequence(current_year)):
            if np.isnan(heat) or discovery_year > current_year:
                wait(0.25)
            else:
                degree = round(self.scale.pitch_to_degree(heat))
                self.piano.play_chord(self.scale[degree, degree + 2], volume + random.uniform(-0.1, 0.1), 0.125,
                                      NotePlaybackAdjustment.scale_params(length=random.uniform(0.5, 0.8)))
                self.piano.play_note(self.scale[degree + 3], volume * 0.8 + random.uniform(-0.1, 0.1), 0.125,
                                     NotePlaybackAdjustment.scale_params(length=random.uniform(0.5, 0.8)))

    def play_undiscovered(self, current_year):
        """
        Plays a series of snare rim-shots, randomly either double or single, for every element that is undiscovered.
        """
        # generate a list, backwards, of the volumes, so that each stretch of undiscovered elements has a crescendo
        volume = 1
        volumes = []
        for discovery_year in reversed(discovery_years):
            if discovery_year <= current_year:
                # already discovered; silent
                volumes.append(0)
                volume = 1
            else:
                volumes.append(volume)
                volume *= 0.9
        volumes.reverse()

        # play through the volumes, or rest where 0
        for i, volume in enumerate(volumes):
            if volume > 0:
                if random.random() < 0.5:
                    self.drums.play_note(37, volume, 0.25)
                else:
                    self.drums.play_note(37, volume, 0.125)
                    self.drums.play_note(37, volume, 0.125)
            else:
                self.elements_played.append(i + 1)
                wait(0.25)

    def play_boil_bass(self, current_year):
        """
        Plays a slap bass part based on the boiling point.
        """
        for mstate, boil, discovery_year in zip(metalics, r_boilings, discovery_years):
            if np.isnan(boil) or discovery_year > current_year:
                wait(0.25)
            else:
                if mstate < 5:
                    self.bass.play_note(self.scale.round(boil - 12), 1, 0.125)
                    wait(0.125)
                else:
                    self.bass.play_note(self.scale.round(boil - 12), 1, 0.125)
                    self.bass.play_note(self.scale.round(boil - 9), 1, 0.125)

    def play_negs_cello(self, current_year):
        """Plays triplets based on electronegativity"""
        volumes = PTableSonification.get_phrase_volumes(current_year, Envelope([0.7, 1, 0.5], [1, 2]),
                                                        num_false_to_end_phrase=2)
        for negs, volume in zip(r_negs, volumes):
            if np.isnan(negs) or volume == 0:
                wait(0.25)
            else:
                self.cello.play_note(self.scale.round(negs), volume, 1 / 12, "length * 1.2")
                self.cello.play_note(self.scale.round(negs + 7), volume * 0.6, 1 / 12, "length * 1.2")
                self.cello.play_note(self.scale.round(negs + 3), volume * 0.8, 1 / 12, "length * 0.7")

    def play_metal_chords(self, current_year):
        """
        Plays different chords based on metal status of the element. (and a double chord if metal)
        """
        last_state = None
        volume = 1
        for mstate, discovery_year in zip(metalics, discovery_years):
            if mstate != last_state:
                volume = 0.9
            else:
                if volume == 0.9:
                    volume = 0.7
                else:
                    volume *= 0.95
            if discovery_year < current_year:
                pitch = next(self.metal_pitch_iterators["metal"]) if mstate == 0 \
                    else next(self.metal_pitch_iterators["metalloid"]) if mstate == 1 \
                    else next(self.metal_pitch_iterators["nonmetal"])
                adjusted_volume = volume * 0.1 if mstate == 0 else volume
                if random.random() < 0:
                    self.vibes.play_note(pitch, adjusted_volume, 0.125)
                    self.vibes.play_note(pitch, adjusted_volume, 0.125)
                else:
                    self.vibes.play_note(pitch, adjusted_volume, 0.25)
                last_state = mstate
            else:
                wait(0.25)

    def mendeleyev(self):
        """
        A signal of a few percussion notes indicating that we've arrived at we've arrived at the year of discovery.
        """
        for pitch in [49, 57, 52, 55]:
            self.drums.play_note(pitch, 1, 0.25)

    def main(self):
        atexit.register(lambda: low_held_note.end())
        for year_to_play in self.years_to_play:
            self.current_year = year_to_play
            self.elements_played = []

            if year_to_play == 1869:
                self.mendeleyev()

            self.drums.play_chord([35, 36, 37, 38], 1, 1)
            low_held_note = self.contrabass.start_note(26, 0.5)
            wait(1)
            print(f"Current year: {year_to_play}")
            self.s.fork(self.play_undiscovered, args=(year_to_play,))
            # self.s.fork(self.play_heat_piano, args=(year_to_play,))
            # self.s.fork(self.play_metal_chords, args=(year_to_play,))
            # self.s.fork(self.play_boil_bass, args=(year_to_play, ))
            self.s.fork(self.play_negs_cello, args=(year_to_play, ))
            # self.s.fork(self.play_radius_oboe, args=(year_to_play,))
            self.s.wait_for_children_to_finish()
            low_held_note.end()
        wait_for_children_to_finish()


if __name__ == "__main__":
    sonification = PTableSonification()
    sonification.play()
    while True:
        time.sleep(0.2)

"""
- Weird that metal status and specific heat are the same instrument. (fixed bug)
- Should harmony be so static?
- Slap bass boiling point stuff incorporates metals meaninglessly?
- Work on the melodic profile of the different parts so that they don't do so many repeated notes. E.g. the oboe? Make
the performance more expressive? May it hold, when it's the same note?
"""
