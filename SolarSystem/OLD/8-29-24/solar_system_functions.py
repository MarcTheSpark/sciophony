import dataclasses
from typing import Sequence
from marciano.solar_system_model2 import SolarSystem
import itertools
from scamp import *
from scamp_extensions.utilities import remap
import math
from global_constants import DAYS_PER_BEAT



# first run: calculate the solar system model for the next 100000 days
# ss = SolarSystem(0, 100000)
# ss.save_to_npy("solarSystemModel.npz")

# subsequent runs: load the precalculated solarSystem model from memory
ss = SolarSystem.load_from_npy("solarSystemModel.npz")



def days_to_beats(num_days):
    """Converts from a number of days to how long that is in beats in our program"""
    return num_days / DAYS_PER_BEAT


def get_solar_system_state(beat=None):
    if beat is None:
        beat = current_clock().master.beat()
    return ss[beat * DAYS_PER_BEAT]


max_planet_speeds = {'mercury': 0.03377467181658569, 'venus': 0.020631344486021684, 'earth': 0.017600297857352575,
                     'mars': 0.015306741151730923, 'jupiter': 0.007920293148978685, 'saturn': 0.005865026730854264,
                     'uranus': 0.004092044119806315, 'neptune': 0.003171517106514422}

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

planet_pitch_bases = {
    "mercury": 100,
    "venus": 90,
    "earth": 80,
    "mars": 60,
    "jupiter": 45,
    "saturn": 33,
    "uranus": 28,
    "neptune": 24
}

planet_pitch_ranges = {
    "mercury": 12,
    "venus": 20,
    "earth": 20,
    "mars": 20,
    "jupiter": 20,
    "saturn": 20,
    "uranus": 20,
    "neptune": 20
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

planet_rotation_period_in_days = {
    'mercury': 58.65,
    'venus': -243.02,
    'earth': 0.996,
    'moon': 27.32,
    'mars': 1.025,
    'jupiter': 0.413,
    'saturn': 0.446,
    'uranus': -0.717,
    'neptune': 0.671,
    'pluto': -6.388
}

planet_length_of_day_in_days = {
    'mercury': 175.94,
    'venus': 116.75,
    'earth': 1.0,
    'moon': 29.53,
    'mars': 1.029,
    'jupiter': 0.413,
    'saturn': 0.446,
    'uranus': 0.717,
    'neptune': 0.671,
    'pluto': 6.388
}


@dataclasses.dataclass
class OrbitMelody:
    inst: ScampInstrument
    planet: str
    sampling_period: int
    sampling_phase: int
    angle_filter: float = math.pi
    sample_duration: float = 0.25
    volume_scale: float = 1
    volume_basis: str = "xVelocity"  # one of "angleDiff", "xVelocity", or "yVelocity"
    pitch_base: float = None  # defaults to dictionary lookup
    pitch_range: float = None  # defaults to dictionary lookup
    muted: bool = False
    # visual properties
    play_expansion_factor: float = 2
    trail_expansion_factor: float = 1.5
    just_played_pc: int = dataclasses.field(default=None, init=False)
    just_played_volume: float = None

    def __post_init__(self):
        if self.planet not in planet_pitch_bases:
            raise ValueError(f"Unrecognized planet {self.planet}")
        if self.pitch_base is None:
            self.pitch_base = planet_pitch_bases[self.planet]
        if self.pitch_range is None:
            self.pitch_range = planet_pitch_ranges[self.planet]

    def play(self):
        for i in itertools.count():
            snapshot = get_solar_system_state()
            x, y, z = snapshot.get_position(self.planet)
            vx, vy, vz = snapshot.get_velocity(self.planet)
            angle_earth = snapshot.get_angle("earth")
            angle_planet = snapshot.get_angle(self.planet)
            # see https://stackoverflow.com/a/2007279/46617
            angle_diff = abs(math.atan2(math.sin(angle_planet - angle_earth), math.cos(angle_planet - angle_earth)))
            pitch = round((x / planet_average_distances[self.planet] * self.pitch_range) + self.pitch_base)
            volume = abs(vx) / max_planet_speeds[self.planet] if self.volume_basis == "xVelocity" else \
                abs(vy) / max_planet_speeds[self.planet] if self.volume_basis == "yVelocity" else \
                1 - angle_diff / self.angle_filter
            if i % self.sampling_period == self.sampling_phase and angle_diff <= self.angle_filter and not self.muted:
                self.just_played_pc = pitch % 12
                self.just_played_volume = volume
                self.inst.play_note(pitch, volume * self.volume_scale, self.sample_duration)
            else:
                wait(self.sample_duration)


def angle_dist(angle1, angle2):
    return min(abs(angle2 % math.tau - angle1 % math.tau),
               abs((angle2 + math.pi) % math.tau - (angle1 + math.pi) % math.tau))


@dataclasses.dataclass
class OrbitBeat:
    inst: ScampInstrument
    planet: str
    pitch: int
    volume: int
    note_dur: int
    play_angles: Sequence[float] = (0,)
    sample_duration: float = 0.25
    muted: bool = False
    # visual properties
    play_expansion_factor: float = 4
    just_played: bool = dataclasses.field(default=False, init=False)

    def __post_init__(self):
        if self.planet not in planet_pitch_bases:
            raise ValueError(f"Unrecognized planet {self.planet}")

    def play(self):
        """Bases it on crossing the angle zero instead of time since the start"""
        last_angle = get_solar_system_state().get_angle(self.planet)

        while True:
            wait(self.sample_duration)
            this_angle = get_solar_system_state().get_angle(self.planet)
            for theta in self.play_angles:
                d1 = angle_dist(last_angle, this_angle)
                d2 = angle_dist(last_angle, theta)
                d3 = angle_dist(this_angle, theta)
                if d2 < d1 and d3 < d1 and not self.muted:
                    self.just_played = True
                    self.inst.play_note(self.pitch, self.volume, self.note_dur, blocking=False)

            last_angle = this_angle


@dataclasses.dataclass
class ProximityAlert:
    inst: ScampInstrument
    planet_1: str
    planet_2: str
    distance_threshold: float  # mapped from 0 to 1, where 0 is the closest they get and 1 is the farthest
    pitch: float
    sample_duration: float = 0.25
    muted: bool = False
    alerting: bool = dataclasses.field(default=False, init=False)
    # visual properties
    color: tuple[int, int, int] = (255, 50, 50)

    def __post_init__(self):
        for planet in (self.planet_1, self.planet_2):
            if planet not in planet_pitch_bases:
                raise ValueError(f"Unrecognized planet {planet}")

    def play(self):
        planet_pair = tuple(sorted([self.planet_1, self.planet_2]))
        distance_threshold = remap(self.distance_threshold, min_planet_pair_distances[planet_pair],
                                   max_planet_pair_distances[planet_pair], 0, 1)
        while True:
            x1, y1, z1 = get_solar_system_state().get_position(self.planet_1)
            x2, y2, z2 = get_solar_system_state().get_position(self.planet_2)
            d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if d < distance_threshold and not self.muted:
                self.alerting = True
                self.inst.play_note(self.pitch,
                                    remap(d, 0.2, 1, distance_threshold, min_planet_pair_distances[planet_pair]),
                                    self.sample_duration / 2)
                wait(self.sample_duration / 4)
                self.inst.play_note(self.pitch,
                                    remap(d, 0.2, 1, distance_threshold, min_planet_pair_distances[planet_pair]),
                                    self.sample_duration / 4)
            else:
                self.alerting = False
                wait(self.sample_duration)
