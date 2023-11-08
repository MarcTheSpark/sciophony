from periodic_define_sequences import *
from scamp import *
import numpy as np
from scamp_extensions.pitch import Scale
import random


s=Session()

s.tempo=60
scale=Scale.from_pitches([62,66,69,70,72,73,74])
guitar=s.new_part("DistortionGuitar")
piano=s.new_part("piano")
bass=s.new_part("Slap Bass")
cello=s.new_part("Cello")
oboe=s.new_part("Oboe")
drums=s.new_part("Orchestra")
contrabass=s.new_part("Contrabass")

metal_chords = {
    "metal":[72,78,86,93],
    "metalloid":[70,78,86],
    "nonmetal":[66,69,78,85]
}


def play_radius_oboe(current_year):
    for radius, discovery_year in zip(r_radius,discovery_years):
        if np.isnan(radius) or discovery_year > current_year:
            wait(0.25)
        else:
            oboe.play_note([scale.round(radius+3)],1,0.25)
            #piano.play_note(scale.round(radius),1,0.125)


def play_heat_piano(current_year):
    for heat,discovery_year in zip(r_heats,discovery_years):
        if np.isnan(heat) or discovery_year > current_year:
            wait(0.25)
        else:
            piano.play_note(scale.round(heat),1,0.125)
            piano.play_note(scale.round(heat+3),1,0.125)


def play_undiscovered(current_year):
    
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

    for volume in volumes:
        if volume > 0:
            if random.random() < 0.5:
                drums.play_note(37,volume,0.25)
            else:
                drums.play_note(37,volume,0.125)
                drums.play_note(37,volume,0.125)
        else:
            wait(0.25)


def play_boil_bass(current_year):
    for mstate,boil,discovery_year in zip(metalics,r_boilings,discovery_years):
        if np.isnan(boil) or discovery_year > current_year:
            wait(0.25)
        else:
            if mstate < 5:
                bass.play_note(scale.round(boil-12),1,0.125)
                wait(0.125)
            else:
                bass.play_note(scale.round(boil-12),1,0.125)
                bass.play_note(scale.round(boil-9),1,0.125)
                


def play_negs_cello(current_year):
    for negs,discovery_year in zip(r_negs,discovery_years):
        if np.isnan(negs) or discovery_year > current_year:
            wait(0.25)
        else:
            cello.play_note(scale.round(negs),1,0.1)
            cello.play_note(scale.round(negs+7),1,0.05)
            cello.play_note(scale.round(negs+3),1,0.1)
            

def play_metal_chords(current_year):
    last_state=None
    volume=1
    for mstate,discovery_year in zip(metalics,discovery_years):
        if mstate != last_state:
            volume=1
        else:
            if volume == 1:
                volume = 0.8
            else:
                volume *= 0.95
        if discovery_year < current_year:
            if mstate == 3:
                piano.play_chord(metal_chords["metal"],volume,0.125)
                piano.play_chord(metal_chords["metal"],volume,0.125)
            elif mstate == 2:
                piano.play_chord(metal_chords["metalloid"],volume,0.25)
            else: 
                piano.play_chord(metal_chords["nonmetal"],volume,0.25)
            last_state=mstate
        else:
            wait(0.25)
            
            
def play_drums_begin():
    drums.play_note(35,1,1,blocking=False)
    drums.play_note(36,1,1,blocking=False)
    drums.play_note(37,1,1,blocking=False)
    drums.play_note(38,1,1)

def mendeleyev():
    for pitch in [49,57,52,55]:
        drums.play_note(pitch,1,0.25)    

years_to_play=[1700,1789,1820,1869,1900,1970]
#YEARS=[2820]
for year_to_play in years_to_play:
    if year_to_play == 1869:
        s.fork(mendeleyev)    
    l=contrabass.start_note(26,0.5)
    s.fork(play_drums_begin)
    wait(1)
    print(f"Current year: {year_to_play}")
    s.fork(play_undiscovered, args=(year_to_play, ))
    s.fork(play_heat_piano, args=(year_to_play, ))
    s.fork(play_metal_chords, args=(year_to_play, ))
    s.fork(play_boil_bass, args=(year_to_play, ))
    s.fork(play_negs_cello, args=(year_to_play, ))
    s.fork(play_radius_oboe, args=(year_to_play, ))
    s.wait_for_children_to_finish()
    l.end()
wait_for_children_to_finish()