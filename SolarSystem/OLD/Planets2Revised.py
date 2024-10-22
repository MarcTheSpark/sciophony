"""
TODO: Visualize?
"""

import itertools
from scamp import *
from scamp_extensions.utilities import remap
from marciano.solar_system_model2 import SolarSystem
import math


DAYS_PER_BEAT = 91.25

# first run: calculate the solar system model for the next 100000 days
#ss = SolarSystem(0, 100000) 0 means today and 100000 the days from today
#ss.save_to_npy("solarSystemModel.npz")
#ss = SolarSystem("01-01-2011","01-01-2016")
#print(ss[17.3].get_position("earth")) # position of earth at day 17.3 after first day of simulation
#exit()

# subsequent runs: load the precalculated solarSystem model from memory

ss = SolarSystem.load_from_npy("../solarSystemModel.npz")


def ss_now():
    return ss[s.beat() * DAYS_PER_BEAT]


s = Session()
s.synchronization_policy = "no synchronization"
s.timing_policy = "absolute"

# s.print_available_midi_output_devices()
# s.print_default_soundfont_presets()

mercury_inst = s.new_part("marimba")
venus_inst = s.new_part("Shakuhachi 2")
mars_inst = s.new_part("cello")
earth_inst = s.new_part("Atmosphere")
jupiter_inst = s.new_part("Bass")
saturn_inst= s.new_part("Acoustic Bass ")
neptune_inst = s.new_part("Aclustic Bass")
uranus_inst = s.new_part("Acoustic Bass ")
piano = s.new_part("piano")
bass = s.new_part("acoustic bass")
dguitar = s.new_part("DistortionGuitar")
drums = s.new_part("POWER")

def metro():
    while True:
        drums.play_note(48, 1, 1)

# fork(metro, initial_tempo=150)
# wait_for_children_to_finish()

max_planet_speeds = {
    'mercury': 0.05, 'venus': 0.04, 'earth': 0.04,
    'mars': 0.03, 'jupiter': 0.02, 'saturn': 0.013,
    'uranus': 0.01, 'neptune': 0.007
}

min_planet_pair_distances = {
    ('mercury', 'sun'): 0.31049603253105623, ('sun', 'venus'): 0.7091818143811311,
    ('earth', 'sun'): 0.9772859039442983, ('mars', 'sun'): 1.3811754700192649,
    ('jupiter', 'sun'): 4.950343846047148, ('saturn', 'sun'): 9.063672768093655,
    ('sun', 'uranus'): 18.44663815205913, ('neptune', 'sun'): 29.847206360123817,
    ('mercury', 'venus'): 0.24973145227758592, ('earth', 'mercury'): 0.5205665511961323,
    ('mars', 'mercury'): 0.9231946589884408, ('jupiter', 'mercury'): 4.490508880537328,
    ('mercury', 'saturn'): 8.604391478544475, ('mercury', 'uranus'): 17.996139565572346,
    ('mercury', 'neptune'): 29.522812507671485, ('earth', 'venus'): 0.2686901837188754,
    ('mars', 'venus'): 0.6489488117841657, ('jupiter', 'venus'): 4.225407736871972,
    ('saturn', 'venus'): 8.354301535858543, ('uranus', 'venus'): 17.7267419012662,
    ('neptune', 'venus'): 29.125513453961037, ('earth', 'mars'): 0.3647878516655113,
    ('earth', 'jupiter'): 3.9433866834040985, ('earth', 'saturn'): 8.08405978448911,
    ('earth', 'uranus'): 17.460898749771548, ('earth', 'neptune'): 28.84595945857811,
    ('jupiter', 'mars'): 3.5237804570651385, ('mars', 'saturn'): 7.4776974455330745,
    ('mars', 'uranus'): 16.781592951249884, ('mars', 'neptune'): 28.407482384201725,
    ('jupiter', 'saturn'): 4.034517785046178, ('jupiter', 'uranus'): 13.00624969615264,
    ('jupiter', 'neptune'): 24.88453940020603, ('saturn', 'uranus'): 9.21941153169599,
    ('neptune', 'saturn'): 20.224025273831543, ('neptune', 'uranus'): 10.328885824614021
}

max_planet_pair_distances = {
    ('mercury', 'sun'): 0.46182919562077057, ('sun', 'venus'): 0.7383444064410529,
    ('earth', 'sun'): 1.0234867278091473, ('mars', 'sun'): 1.6665010186039917,
    ('jupiter', 'sun'): 5.465697132813099, ('saturn', 'sun'): 10.091479925491868,
    ('sun', 'uranus'): 20.140034803368057, ('neptune', 'sun'): 30.73136788499384,
    ('mercury', 'venus'): 1.199648085384062, ('earth', 'mercury'): 1.4832575725747559,
    ('mars', 'mercury'): 2.1269089829466323, ('jupiter', 'mercury'): 5.926850695285498,
    ('mercury', 'saturn'): 10.550643481369374, ('mercury', 'uranus'): 20.57074729188699,
    ('mercury', 'neptune'): 31.19022883031638, ('earth', 'venus'): 1.736468217335235,
    ('mars', 'venus'): 2.399737724015796, ('jupiter', 'venus'): 6.190218238653268,
    ('saturn', 'venus'): 10.800607383700743, ('uranus', 'venus'): 20.86106224855338,
    ('neptune', 'venus'): 31.45066957226546, ('earth', 'mars'): 2.684190170008978,
    ('earth', 'jupiter'): 6.4726099238650185, ('earth', 'saturn'): 11.071530828957291,
    ('earth', 'uranus'): 21.12627207402731, ('earth', 'neptune'): 31.731661996084757,
    ('jupiter', 'mars'): 6.888376173829116, ('mars', 'saturn'): 11.675581162226987,
    ('mars', 'uranus'): 21.803544142234255, ('mars', 'neptune'): 32.17142159744344,
    ('jupiter', 'saturn'): 15.289059264831577, ('jupiter', 'uranus'): 25.55675346410654,
    ('jupiter', 'neptune'): 35.69342076885146, ('saturn', 'uranus'): 29.73610840449459,
    ('neptune', 'saturn'): 40.34813577180017, ('neptune', 'uranus'): 50.51722587680125
}

planet_average_distances = {
    "mercury": 0.4,
    "venus": 0.7,
    "earth": 1.0,
    "mars": 1.5,
    "jupiter": 5.2,
    "saturn": 9.6,
    "uranus": 19.2,
    "neptune": 30.0
}

planet_pitch_base = {
    "mercury": 120,
    "venus": 100,
    "earth": 80,
    "mars": 60,
    "jupiter": 45,
    "saturn":33,
    "uranus": 28,
    "neptune": 24
}

planet_days_revolution = {
    "mercury": 88,
    "venus": 225,
    "earth": 365,
    "mars": 687,
    "jupiter": 4333,
    "saturn": 10759,
    "uranus": 30687,
    "neptune": 60187
}


def play_planet(which_planet, pitch_base, pitch_range, volume_scale, sampling_rate, sampling_phase, inst,
                angle_filter=math.pi):
    for i in itertools.count():
        snapshot = ss_now()
        x, y, z = snapshot.get_position(which_planet)
        vx,vy,vz = snapshot.get_velocity(which_planet)
        angle_earth = snapshot.get_angle("earth")
        angle_planet = snapshot.get_angle(which_planet)
        # see https://stackoverflow.com/a/2007279/46617
        angle_diff = abs(math.atan2(math.sin(angle_planet-angle_earth), math.cos(angle_planet-angle_earth)))
        pitch = round((x/ planet_average_distances[which_planet] * pitch_range) + pitch_base)
        volume = abs(vx) / max_planet_speeds[which_planet] * volume_scale
        if i % sampling_rate == sampling_phase and angle_diff <= angle_filter:
            inst.play_note(pitch,volume,0.1)
        else:
            wait(0.1)


def play_planet_revolution_beat(planet_name, pitch, volume, note_dur, inst):
    """Bases it on crossing the angle zero instead of time since the start"""
    last_angle = ss_now().get_angle(planet_name)
    while True:
        wait(0.1)
        this_angle = ss_now().get_angle(planet_name)
        if this_angle > 0 and last_angle <= 0:
            inst.play_note(pitch, volume, note_dur, blocking=False)
        last_angle = this_angle


# play_planet_revolution_beat2("mercury", 75, 1, 0.1, drums)
# exit()

def play_planet_proximity_alert(planet_1, planet_2, distance_threshold, pitch, inst=drums):
    """
    Plays a proximity alert when the given planets approach closely
    :param planet_1: first planet name
    :param planet_2: second planet name
    :param distance_threshold: from 0 to 1, where 0 corresponds to the closest distance between the planets, and
        1 corresponds to the farthest. So if set to 0.25, the alert will sound when the planets are in the closest
        25% of their range of distances.
    :param pitch: pitch to play
    :param inst: instrument to use
    """
    planet_pair = tuple(sorted([planet_1, planet_2]))
    distance_threshold = remap(distance_threshold, min_planet_pair_distances[planet_pair],
                               max_planet_pair_distances[planet_pair], 0, 1)
    while True:
        x1, y1, z1 = ss_now().get_position(planet_1)
        x2, y2, z2 = ss_now().get_position(planet_2)
        d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if d < distance_threshold:
            inst.play_note(pitch, remap(d, 0.2, 1, distance_threshold, min_planet_pair_distances[planet_pair]), 0.05)
            wait(0.025)
            inst.play_note(pitch, remap(d, 0.2, 1, distance_threshold, min_planet_pair_distances[planet_pair]), 0.025)
        else:
            wait(0.1)

# proximity between planets

#fork(play_planet_proximity_alert, args=("earth", "mars", 0.4, 67))
#fork(play_planet_proximity_alert, args=("earth", "mercury", 0.3, 66))
#fork(play_planet_proximity_alert, args=("earth", "jupiter", 0.3, 64))
#fork(play_planet_proximity_alert, args=("jupiter", "saturn", 0.3, 65))
#fork(play_planet_proximity_alert, args=("mercury", "venus", 0.3, 66))



#wait_for_children_to_finish()
#play_planet(planet_name,pitch_base,pitch_range,volume_scale,sampling_rate,sampling_phase,inst,angle_filter=2*math.pi):


""" s.fork(play_planet,args=("neptune",planet_pitch_base["neptune"],20,3,17,0,neptune_inst))
s.fork(play_planet,args=("uranus",planet_pitch_base["uranus"],20,3,11,4,uranus_inst))
s.fork(play_planet,args=("saturn",planet_pitch_base["saturn"],20,3,7,1,saturn_inst))
s.fork(play_planet,args=("jupiter",planet_pitch_base["jupiter"],20,1,4,1,jupiter_inst))
s.fork(play_planet,args=("mars",planet_pitch_base["mars"],20,0.6,3,0,mars_inst))
s.fork(play_planet,args=("earth",planet_pitch_base["earth"],20,0.2,1,0,earth_inst))
s.fork(play_planet,args=("venus",planet_pitch_base["venus"],20,0.3,1,0,venus_inst))
s.fork(play_planet,args=("mercury",planet_pitch_base["mercury"],12,0.5,1,0,mercury_inst)) 

s.fork(play_planet_revolution_beat, args=("mercury",75,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("venus",73,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("earth",39,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("mars",63,1,0.1,drums)) """


#wait(10)
# parameters of play planet: planet_name,pitch_base,pitch_range (20)
# #volume_scale,sampling_rate,sampling_phase,inst,angle_filter=2*math.pi):


s.fork(play_planet_revolution_beat, args=("mercury",75,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("venus",73,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("earth",39,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("mars",63,1,0.1,drums)) 

wait(3)
n_clock=s.fork(play_planet,args=("neptune",planet_pitch_base["neptune"],20,4,4,0,neptune_inst))
s_clock=s.fork(play_planet,args=("saturn",planet_pitch_base["saturn"],20,4,4,2,saturn_inst))
j_clock=s.fork(play_planet,args=("jupiter",planet_pitch_base["jupiter"],20,0.4,1,0,jupiter_inst))#,(math.pi)/2))

wait(10)
#s.fork(play_speed_earth)

u_clock=s.fork(play_planet,args=("uranus",planet_pitch_base["uranus"],20,3,4,1,uranus_inst))
print("uranus")


wait(5)
print("mars")
s.fork(play_planet,args=("mars",planet_pitch_base["mars"],20,0.6,3,0,mars_inst))
wait(5)
print("earth")
s.fork(play_planet,args=("earth",planet_pitch_base["earth"],20,0.2,1,0,earth_inst))
wait(5)
print("venus")
s.fork(play_planet,args=("venus",planet_pitch_base["venus"],20,0.3,1,0,venus_inst))
wait(5)
print("mercury")

s.fork(play_planet,args=("mercury",planet_pitch_base["mercury"],12,0.5,1,0,mercury_inst))

wait(5)
print("eath close to mars")

s.fork(play_earth_mars_close,args=("earth","mars"))

wait_forever()
#wait(5)



"""
def play_planet_revolution_beat(planet_name, pitch, volume, note_dur, inst):
    days_since_year_start = 0

    while True:
        wait(0.1)
        days_since_year_start += DAYS_PER_BEAT/10
        if days_since_year_start >= planet_days_revolution[planet_name]:
            inst.play_note(pitch, volume, note_dur, blocking=False)
            days_since_year_start %= planet_days_revolution[planet_name]

"""
