from periodic_define_sequences import *
from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
import random
import atexit
from ensemble_midi import *
from scamp_extensions.process import non_repeating_shuffle

s.tempo = 60
scale = Scale.from_pitches([62, 66, 69, 70, 72, 73, 74])  # D dom 7 with a Bb and a C# added

# metal_chords = {
#     "metal": [72, 78, 86, 93],
#     "metalloid": [70, 78, 86],
#     "nonmetal": [66, 69, 78, 85]
# }

metal_pitch_iterators = {  # i.e. which instruments to use on the orchestral percussion
    "metal": non_repeating_shuffle([65, 68, 69]),
    "metalloid": non_repeating_shuffle([31, 33, 83]),
    "nonmetal": non_repeating_shuffle([48, 49, 50, 51, 52])
}


def play_radius_oboe(current_year):
    oboe_note = None
    last_pitch = None
    for radius, discovery_year in zip(r_radius, discovery_years):
        if np.isnan(radius) or discovery_year > current_year:
            if oboe_note:
                oboe_note.end()
            last_pitch = oboe_note = None
            wait(0.25)
        else:
            pitch = scale.round(radius + 3)
            if last_pitch != pitch:
                if oboe_note:
                    oboe_note.end()
                oboe_note = oboe.start_note(pitch, 1)
            last_pitch = pitch
            wait(0.25)
    if oboe_note:
        oboe_note.end()


def play_heat_piano(current_year):
    """
    Playing down the scale on the piano based on specific heat. Does so at double speed with rising gestures.
    :return:
    """
    for heat, discovery_year, volume in zip(r_heats, discovery_years, get_volume_sequence(current_year)):
        if np.isnan(heat) or discovery_year > current_year:
            wait(0.25)
        else:
            degree = round(scale.pitch_to_degree(heat))
            piano.play_chord(scale[degree, degree + 1], volume, 0.125)
            piano.play_note(scale[degree + 3], volume * 0.8, 0.125)


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


def play_undiscovered(current_year):
    """
    Plays a series of snare rim-shots, randomly either double or single, for every element that is undiscovered.
    """

    # play through the volumes, or rest where 0
    for volume in get_volume_sequence(current_year, active_when_discovered=False, min_volume=0.4, max_volume=1.0):
        if volume > 0:
            if random.random() < 0.5:
                drums.play_note(37, volume, 0.25)
            else:
                drums.play_note(37, volume, 0.125)
                drums.play_note(37, volume, 0.125)
        else:
            wait(0.25)


def play_boil_bass(current_year):
    """
    Plays a slap bass part based on the boiling point.
    """
    for mstate, boil, discovery_year in zip(metalics, r_boilings, discovery_years):
        if np.isnan(boil) or discovery_year > current_year:
            wait(0.25)
        else:
            if mstate < 5:
                bass.play_note(scale.round(boil - 12), 1, 0.125)
                wait(0.125)
            else:
                bass.play_note(scale.round(boil - 12), 1, 0.125)
                bass.play_note(scale.round(boil - 9), 1, 0.125)


def play_negs_cello(current_year):
    """Plays triplets based on electronegativity"""
    for negs, discovery_year in zip(r_negs, discovery_years):
        if np.isnan(negs) or discovery_year > current_year:
            wait(0.25)
        else:
            cello.play_note(scale.round(negs), 1, 1/12)
            cello.play_note(scale.round(negs + 7), 1, 1/12)
            cello.play_note(scale.round(negs + 3), 1, 1/12)


def play_metal_chords(current_year):
    """
    Plays different chords based on metal status of the element. (and a double chord if metal)
    """
    last_state = None
    volume = 1
    for mstate, discovery_year in zip(metalics, discovery_years):
        if mstate != last_state:
            volume = 1
        else:
            if volume == 1:
                volume = 0.8
            else:
                volume *= 0.95
        if discovery_year < current_year:
            pitch = next(metal_pitch_iterators["metal"]) if mstate == 0 \
                else next(metal_pitch_iterators["metalloid"]) if mstate == 1 \
                else next(metal_pitch_iterators["nonmetal"])
            if random.random() < 0.5:
                vibes.play_note(pitch, volume, 0.125)
                vibes.play_note(pitch, volume, 0.125)
            else:
                vibes.play_note(pitch, volume, 0.25)

            last_state = mstate
        else:
            wait(0.25)


def mendeleyev():
    """
    A signal of a few percussion notes indicating that we've arrived at we've arrived at the year of discovery.
    """
    for pitch in [49, 57, 52, 55]:
        drums.play_note(pitch, 1, 0.25)


years_to_play = [1700, 1789, 1820, 1869, 1900, 1970]
years_to_play = years_to_play[3:]

atexit.register(lambda: low_held_note.end())
for year_to_play in years_to_play:
    if year_to_play == 1869:
        s.fork(mendeleyev)
    drums.play_chord([35, 36, 37, 38], 1, 1)
    low_held_note = contrabass.start_note(26, 0.5)
    wait(1)
    print(f"Current year: {year_to_play}")
    s.fork(play_undiscovered, args=(year_to_play,))
    s.fork(play_heat_piano, args=(year_to_play,))
    # s.fork(play_metal_chords, args=(year_to_play, ))
    # s.fork(play_boil_bass, args=(year_to_play, ))
    # s.fork(play_negs_cello, args=(year_to_play, ))
    # s.fork(play_radius_oboe, args=(year_to_play, ))
    s.wait_for_children_to_finish()
    low_held_note.end()
wait_for_children_to_finish()


"""
- Weird that metal status and specific heat are the same instrument. (fixed bug)
- Should harmony be so static?
- Slap bass boiling point stuff incorporates metals meaninglessly?
- Work on the melodic profile of the different parts so that they don't do so many repeated notes. E.g. the oboe? Make
the performance more expressive? May it hold, when it's the same note?
"""
