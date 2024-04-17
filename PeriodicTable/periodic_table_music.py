import threading
import time
from itertools import zip_longest
from periodic_define_sequences import *
from marciano.periodictable import all_elements
from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
import random
import atexit
from scamp_extensions.process import non_repeating_shuffle


class PTableSonification:

    def __init__(self, years_to_play=(1669, 1789, 1820, 1869, 1932, 1945, 1986), scale=Scale.from_pitches([62, 66, 69, 70, 72, 73, 74])):

        self.years_to_play = years_to_play
        self.scale = scale
        self.metal_pitch_iterators = {  # i.e. which instruments to use on the orchestral percussion
            "metal": non_repeating_shuffle([77, 80, 81]),
            "metalloid": non_repeating_shuffle([43, 45, 95]),
            "nonmetal": non_repeating_shuffle([60, 62, 64])
        }
        self.current_year = years_to_play[0]
        self.elements_played = []

    def play(self, midi=False, start_time=0):
        threading.Thread(target=self._play, args=(midi, start_time), daemon=True).start()

    def _play(self, midi=False, start_time=0):
        if midi:
            from ensemble_midi import s
        else:
            from ensemble import s

        self.s = s
        self.s.synchronization_policy = "no synchronization"
        self.s.timing_policy = "absolute"
        self.s.fast_forward_to_time(start_time)
        self.vibes, self.piano, self.bass, self.cello, self.oboe, self.drums, self.contrabass, self.synth = self.s.instruments
        # s.start_transcribing()
        # s.fast_forward()
        self.main()
        # s.stop_transcribing().export_to_midi_file("Periodic.midi")

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
    def get_phrase_volumes(year, phrase_envelope: Envelope, num_false_to_end_phrase=1, stretch_envelope=True,
                           singleton_volume_choice="start"):
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
                volumes.append(phrase_envelope.start_level() if singleton_volume_choice == "start"
                               else phrase_envelope.end_level() if singleton_volume_choice == "end"
                               else phrase_envelope.average_level() if singleton_volume_choice == "average"
                               else singleton_volume_choice)
            else:
                env = phrase_envelope.normalize_to_duration(group - 1) if stretch_envelope else phrase_envelope
                volumes.extend([env.value_at(i) * is_discovered
                                for i, is_discovered in zip(range(group), discovered_sequence[current_element_index:])])
            current_element_index += abs(group)
        return volumes

    def play_radius_oboe(self, current_year, is_solo=False):
        r_radius_array = np.array(r_radius)
        active_array = (~np.isnan(r_radius_array) & (np.array(discovery_years) <= current_year)).astype(int)
        if not is_solo:
            active_array &= np.array(r_radius_array) < 72
            r_radius_array += 12
        volumes = self.get_phrase_volumes(current_year, Envelope([0.4, 0.9], [1], [2]),
                                          2, singleton_volume_choice="end")

        notes = []
        current_dur, current_pitch, start_volume, end_volume = 0, None, None, None


        # pre-build notes list
        for radius, is_active, volume in zip(r_radius_array, active_array, volumes):
            if is_active:
                pitch = self.scale.round(radius + 3)
                if current_dur > 0 and current_pitch is not None:
                    # currently building a note
                    if pitch == current_pitch:
                        current_dur += 0.25
                        end_volume = volume
                    else:
                        notes.append((current_dur, current_pitch, start_volume, end_volume))
                        current_dur, current_pitch, start_volume, end_volume = 0.25, pitch, volume, volume
                elif current_dur > 0:
                    # currently building a rest
                    notes.append((current_dur, None, None, None))
                    current_dur, current_pitch, start_volume, end_volume = 0.25, pitch, volume, volume
                else:
                    current_dur, current_pitch, start_volume, end_volume = 0.25, pitch, volume, volume
            elif current_dur > 0 and current_pitch is not None:
                notes.append((current_dur, current_pitch, start_volume, end_volume))
                current_dur, current_pitch, start_volume, end_volume = 0.25, None, None, None
            else:
                current_dur += 0.25
        notes.append((current_dur, current_pitch, start_volume, end_volume))

        for i, note in enumerate(notes):
            dur, pitch, start_volume, end_volume = note

            if pitch is not None:
                if is_solo:
                    is_staccato = (notes[i + 1][1] is None and note[0] < 0.5) if i + 1 < len(notes) else True
                else:
                    is_staccato = True
                volume = (start_volume, end_volume) if start_volume != end_volume else start_volume
                properties = ("param_15: 0.5" if is_staccato else "param_17: 0.5") \
                    if type(self.oboe.playback_implementations[0]) is MIDIStreamPlaybackImplementation else \
                    ("staccato" if is_staccato else None)
                if is_solo:
                    self.oboe.play_note(pitch, volume, dur, properties)
                else:
                    self.oboe.play_note(pitch, volume, 0.25, properties)
                    if dur > 0.25:
                        wait(dur - 0.25)
            else:
                wait(dur)

    def play_heat_piano(self, current_year, is_solo=False):
        """
        Playing down the scale on the piano based on specific heat. Does so at double speed with rising gestures.
        :return:
        """
        if not is_solo:
            self.play_heat_piano_comping(current_year)
            return
        NUM_REPEATS_WHEN_COMPING = 1
        COMP_REPEAT_DECAY = 0.7
        repeats_left = NUM_REPEATS_WHEN_COMPING

        last_degree = None
        for heat, discovery_year, volume in zip(r_heats, discovery_years,
                                                self.get_volume_sequence(current_year, min_volume=0.4, max_volume=0.8)):
            if np.isnan(heat) or discovery_year > current_year:
                wait(0.25)
            else:
                degree = round(self.scale.pitch_to_degree(heat))
                if not is_solo and degree == last_degree:
                    repeats_left -= 1
                    volume *= COMP_REPEAT_DECAY ** (NUM_REPEATS_WHEN_COMPING - repeats_left)
                else:
                    repeats_left = NUM_REPEATS_WHEN_COMPING
                if is_solo or repeats_left > 0:
                    self.piano.play_chord(self.scale[degree, degree + 2], volume + random.uniform(-0.1, 0.1), 0.125,
                                          NotePlaybackAdjustment.scale_params(length=random.uniform(0.5, 0.8)))
                    self.piano.play_note(self.scale[degree + 3], volume * 0.8 + random.uniform(-0.1, 0.1), 0.125,
                                         NotePlaybackAdjustment.scale_params(length=random.uniform(0.5, 0.8)))
                else:
                    wait(0.25)
                last_degree = degree

    def play_heat_piano_comping(self, current_year):
        """
        Playing down the scale on the piano based on specific heat. Does so at double speed with rising gestures.
        :return:
        """

        hyv = list(zip(r_heats, discovery_years, self.get_volume_sequence(current_year, min_volume=0.4, max_volume=0.6)))
        skip_counter = 0
        for i, (heat, discovery_year, volume) in enumerate(hyv):
            if np.isnan(heat) or discovery_year > current_year:
                wait(0.25)
            elif skip_counter > 0:
                skip_counter -= 1
                wait(0.25)
            else:
                how_long_same_degree = 1
                degree = round(self.scale.pitch_to_degree(heat))
                for h, y, v in hyv[i + 1:]:
                    if np.isnan(h) or y > current_year:
                        break
                    d = round(self.scale.pitch_to_degree(h))
                    if d != degree:
                        break
                    how_long_same_degree += 1

                if how_long_same_degree == 1:
                    self.piano.play_chord(self.scale[degree - 4, degree, degree + 2], volume + random.uniform(-0.1, 0.1), 0.125)
                    wait(0.125)
                else:
                    self.s.fork(
                        PTableSonification._roll_chord,
                        (self.piano,
                         self.scale[degree - 4, degree, degree + 2],
                         volume,
                         0.25 * how_long_same_degree - 0.125)
                    )
                    skip_counter = how_long_same_degree - 1
                    wait(0.25)

    @staticmethod
    def _roll_chord(inst: ScampInstrument, chord, volume, length, spacing=0.06, humanization=0.1):
        length_left = length
        for chord_note in chord:
            volume = volume * 2 ** random.uniform(-humanization, humanization)

            inst.play_note(chord_note, volume, length_left, blocking=False)
            wait_dur = spacing * 2 ** random.uniform(-humanization, humanization)
            wait(wait_dur)
            length_left -= wait_dur
        wait_for_children_to_finish()

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

    def play_boil_bass(self, current_year, is_solo=False):
        """
        Plays a slap bass part based on the boiling point.
        """
        volumes = PTableSonification.get_phrase_volumes(current_year, Envelope.from_levels([0.7, 1]),
                                                        num_false_to_end_phrase=2)

        # calculating max note length so that it doesn't overlap with the next note
        max_durs = []
        last_active_i = None
        for i, v in enumerate(volumes):
            if v > 0:
                max_durs.append(0.25)
                last_active_i = i
            elif last_active_i is not None:
                max_durs[last_active_i] += 0.25
                max_durs.append(0)

        up_down = Envelope([0, 2, 0], [0.15, 0.15])
        fall = Envelope([0, -2], [1], curve_shapes=[1])

        last_pitch = 0
        for boil, volume, max_dur, el in zip(r_boilings, volumes, max_durs, all_elements):
            if np.isnan(boil) or volume == 0:
                wait(0.25)
            else:
                pitch = self.scale.round(boil)
                if not is_solo:
                    volume *= 0.7
                max_dur -= 0.25  # allow space between the groups
                if max_dur > 0.25:  # long note at the end of a group of active notes
                    if is_solo:
                        # when solo, do a long embellished pitch
                        embellished_pitch = pitch + (up_down if last_pitch > pitch else fall) if pitch > 45 else pitch
                        self.bass.play_note(embellished_pitch, volume, min(0.75, max_dur), blocking=False)

                    else:
                        # when not solo, do a medium-short, falling note (not the other more active up_down)
                        self.bass.play_note(pitch +fall if pitch > 45 else pitch, volume, 0.5, blocking=False)
                        pass
                    wait(0.25)
                    last_pitch = pitch
                elif is_solo or abs(pitch - last_pitch) > 4:  # el.group in (1, 3, 13, 18):
                    # self.bass.play_note(pitch, volume, 0.25, "staccato")
                    self.bass.play_note(pitch, volume, 0.125)
                    wait(0.125)
                    last_pitch = pitch
                else:
                    wait(0.25)
                    continue

    def play_negs_cello(self, current_year, is_solo=False):
        """Plays triplets based on electronegativity"""
        volumes = PTableSonification.get_phrase_volumes(current_year, Envelope([0.7, 1, 0.5], [1, 2]),
                                                        num_false_to_end_phrase=1)
        self.cello.send_midi_cc(15, 0.5)

        for neg, next_neg, volume, next_volume in zip_longest(r_negs, r_negs[1:], volumes, volumes[1:]):
            if np.isnan(neg) or volume == 0:
                wait(0.25)
            elif next_neg is None or np.isnan(next_neg) or next_volume == 0 or next_neg + 10 < neg:
                # end of a phrase when: at the end of the periodic table, next element negativity not defined,
                # next element not discovered, next element has significant drop in electronegativity.
                self.cello.play_note(self.scale.round(neg), min(1, volume * 1.3), 1 / 4)
            else:
                if is_solo or abs(next_neg - neg) > 5:
                    self.cello.play_note(self.scale.round(neg), volume, 1 / 12 * 1.2, blocking=False)
                    wait(1/12)
                    self.cello.play_note(self.scale.round(neg + 7), volume * 0.6, 1 / 12 * 1.2, blocking=False)
                    wait(1 / 12)
                    self.cello.play_note(self.scale.round(neg + 3), volume * 0.8, 1 / 12 * 0.7, blocking=False)
                    wait(1 / 12)
                else:
                    self.cello.play_note(self.scale.round(neg), volume, 1 / 4)

    def play_synth_radioactive(self, current_year, is_solo=False):
        """Plays Big Synth hits on radioactive elements"""
        pitch_it = non_repeating_shuffle([62, 62, 65, 65])
        for radioactive, discovered in zip(radios, discovery_years):
            if radioactive and current_year >= discovered:
                self.synth.play_note(next(pitch_it), 1 if is_solo else 0.5, 0.125)
                wait(0.125)
            else:
                wait(0.25)

    def play_metals(self, current_year, is_solo=False):
        """
        Plays different chords based on metal status of the element. (and a double chord if metal)
        """

        def get_pitch(mstate):
            return next(self.metal_pitch_iterators["metal"]) if mstate == 0 \
                else next(self.metal_pitch_iterators["metalloid"]) if mstate == 1 \
                else next(self.metal_pitch_iterators["nonmetal"])

        multiples = [int(x) for x in remap(negs, 1, 3)]  # if is_solo else [1] * len(metalics)

        last_state = None
        volume = 0.9
        for mstate, discovery_year, multiple in zip(metalics, discovery_years, multiples):
            discovered = discovery_year <= current_year
            current_state = mstate if discovered else None
            if current_state is not None:
                if current_state != last_state:
                    # starting a new group
                    volume = 0.9
                    for _ in range(multiple):
                        self.vibes.play_note(get_pitch(mstate), volume * 0.5 if mstate == 0 else volume, 0.25 / multiple)
                elif is_solo:
                    # continuing group and it's the solo
                    volume = 0.7 if volume == 0.9 else volume * 0.9
                    for _ in range(multiple):
                        self.vibes.play_note(get_pitch(mstate), volume * 0.5 if mstate == 0 else volume, 0.25 / multiple)
                else:
                    wait(0.25)
            else:
                wait(0.25)
            last_state = current_state

    def mendeleyev(self):
        """
        A signal of a few percussion notes indicating that we've arrived at we've arrived at the year of discovery.
        """
        for pitch in [49, 57, 52, 55]:
            self.drums.play_note(pitch, 1, 0.25)

    def main(self):
        atexit.register(lambda: low_held_note.end())
        wait(0.5)
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
            self.s.fork(self.play_metals, args=(year_to_play, year_to_play == 1669 or year_to_play > 1960))
            if year_to_play > 1669:
                self.s.fork(self.play_boil_bass, args=(year_to_play, year_to_play == 1789 or year_to_play > 1960))
            if year_to_play > 1789:
                self.s.fork(self.play_heat_piano, args=(year_to_play, year_to_play == 1820 or year_to_play > 1960))
            if year_to_play > 1820:
                self.s.fork(self.play_radius_oboe, args=(year_to_play, year_to_play == 1869 or year_to_play > 1960))
            if year_to_play > 1930:
                self.s.fork(self.play_negs_cello, args=(year_to_play, year_to_play == 1932 or year_to_play > 1960))
            if year_to_play > 1940:
                self.s.fork(self.play_synth_radioactive, args=(year_to_play, year_to_play == 1945))

            self.s.wait_for_children_to_finish()
            low_held_note.end()
        wait_for_children_to_finish()


if __name__ == "__main__":
    sonification = PTableSonification()
    sonification.play(midi=True)
    while True:
        time.sleep(0.2)
