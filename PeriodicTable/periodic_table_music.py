from periodic_define_sequences import *
from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
import random

s = Session()

s.tempo = 60
scale = Scale.from_pitches([62, 66, 69, 70, 72, 73, 74])  # D dom 7 with a Bb and a C# added
guitar = s.new_part("DistortionGuitar")
vibes = s.new_part("vibraphone")
piano = s.new_part("piano")
bass = s.new_part("Slap Bass")
cello = s.new_part("Cello")
oboe = s.new_part("Oboe")
drums = s.new_part("Orchestra")
contrabass = s.new_part("Contrabass")

metal_chords = {
    "metal": [72, 78, 86, 93],
    "metalloid": [70, 78, 86],
    "nonmetal": [66, 69, 78, 85]
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
    for heat, discovery_year in zip(r_heats, discovery_years):
        if np.isnan(heat) or discovery_year > current_year:
            wait(0.25)
        else:
            piano.play_note(scale.round(heat), 1, 0.125)
            piano.play_note(scale.round(heat + 3), 1, 0.125)


def play_undiscovered(current_year):
    """
    Plays a series of snare rim-shots, randomly either double or single, for every element that is undiscovered.
    """
    # generate a list, backwards, of the volumes, so that each stretch of undiscovered elements has a crescendo
    volume = 1
    volumes = []
    for discovery_year in reversed(discovery_years):
        if discovery_year < current_year:
            # already discovered; silent
            volumes.append(0)
            volume = 1
        else:
            volumes.append(volume)
            volume *= 0.9
    volumes.reverse()

    # play through the volumes, or rest where 0
    for volume in volumes:
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
            if mstate == 0:
                # print("metal")
                for _ in range(2):
                    vibes.play_chord(metal_chords["metal"], volume, 0.125)
            elif mstate == 1:
                # print("metalloid")
                vibes.play_chord(metal_chords["metalloid"], volume, 0.25)
            else:
                # print("nonmetal")
                vibes.play_chord(metal_chords["nonmetal"], volume, 0.25)
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

for year_to_play in years_to_play:
    if year_to_play == 1869:
        s.fork(mendeleyev)
    low_held_note = contrabass.start_note(26, 0.5)
    drums.play_chord([35, 36, 37, 38], 1, 1)
    wait(1)
    print(f"Current year: {year_to_play}")
    s.fork(play_undiscovered, args=(year_to_play,))
    s.fork(play_heat_piano, args=(year_to_play,))
    s.fork(play_metal_chords, args=(year_to_play, ))
    # s.fork(play_boil_bass, args=(year_to_play, ))
    # s.fork(play_negs_cello, args=(year_to_play, ))
    s.fork(play_radius_oboe, args=(year_to_play, ))
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
