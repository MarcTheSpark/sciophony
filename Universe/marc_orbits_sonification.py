import time

from scamp import *
from marciano import solar_system_model
import math


s = Session(default_soundfont="Wavetable/Plastic Strings")
s.timing_policy = 0.5
solar_system_model.start(s, 50, start_date="2018-01-01")

# strings = s.new_part("plastic")

for _ in range(8):
    s.new_osc_part("organDonor", 57120)


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

planet_year_lengths = {
    "mercury": 88,
    "venus": 225,
    "earth": 365,
    "mars": 687,
    "jupiter": 4333,
    "saturn": 10756,
    "uranus": 30687,
    "neptune": 60190
}

max_planet_speeds = {
    'mercury': 0.05, 'venus': 0.04, 'earth': 0.04,
    'mars': 0.03, 'jupiter': 0.02, 'saturn': 0.013,
    'uranus': 0.01, 'neptune': 0.007
}

pan_widths = {
    'mercury': 0.2, 'venus': 0.3, 'earth': 0.4,
    'mars': 0.5, 'jupiter': 0.6, 'saturn': 0.7,
    'uranus': 0.8, 'neptune': 1.0
}

# print({p: math.log2(l/365) for p, l in planet_year_lengths.items()})
planet_pitches = {p: 84 - 12 * math.log2(d) for p, d in planet_average_distances.items()}


# for drum_pitch in planet_pitches.values():
#     strings.play_note(drum_pitch, 0.7, 3)

start_time = time.time()
def do_planet_orbit(planet, granularity):
    pitch = 84 - 12 * math.log2(solar_system_model.get_distance(planet, "sun"))
    volume = (solar_system_model.get_speed(planet) / max_planet_speeds[planet])
    pan = math.cos(solar_system_model.get_angle(planet)) * pan_widths[planet] / 2 + 0.5
    distance = math.sin(solar_system_model.get_angle(planet)) / 3 + 0.5
    inst = s.instruments[solar_system_model.planets.index(planet)]
    note = inst.start_note(pitch, volume/3, {"param_pan": pan, "param_distance": distance})
    while True:
        pan = math.cos(solar_system_model.get_angle(planet)) * pan_widths[planet] / 2 + 0.5
        pitch = 84 - 12 * math.log2(solar_system_model.get_distance(planet, "sun"))
        volume = (solar_system_model.get_speed(planet) / max_planet_speeds[planet])
        distance = math.sin(solar_system_model.get_angle(planet)) / 4 + 0.5
        note.change_pitch(pitch, granularity)
        note.change_volume(volume/3, granularity)
        note.change_parameter("pan", pan, granularity)
        note.change_parameter("distance", distance, granularity)
        wait(granularity)
        

s.start_transcribing()

for p in solar_system_model.planets:
    fork(do_planet_orbit, args=(p, planet_year_lengths[p] / 365 / 5))

# while True:
#     print(s.time(), time.time() - start_time)
#     wait(1)

wait(180)
for inst in s.instruments:
    inst.end_all_notes()
perf = s.stop_transcribing()

for note in perf.get_note_iterator():
    print(note.pitch.start_level(), max(note.volume.levels), note.volume.max_level())
max_volume = max(note.volume.max_level() if isinstance(note.volume, Envelope) else note.volume for note in perf.get_note_iterator())
print(f"max_volume: {max_volume}")
# perf.apply_volume_filter(lambda v: v/max_volume)

perf.export_to_midi_file("OrbitsSonification.mid")



