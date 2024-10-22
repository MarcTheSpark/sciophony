"""
- Turn planet players functions into planet player objects that you can turn silent/change their angles of playing.
- Particularly interesting would be to have the visual angle of play go from small to large
- Shape the form over time by changing the angles over time. This could be about human attention focusing on different
things, or on different visibilities of the sky on cloudy/clear days.
- At any way, set up a good code interface for playing with form
- Make it so that the percussion of play revolution beat can play on multiple angle triggers
TODO: Visualize?
"""
import math
from scamp import *
from solar_system_functions import OrbitMelody, OrbitBeat, ProximityAlert, days_to_beats, planet_rotation_period_in_days
import threading


class PlanetMusic(threading.Thread):

    def __init__(self, to_logic=False):
        super().__init__(daemon=True)
        self.s: Session = None
        self.started = threading.Condition()
        self.orbit_melodies: list[OrbitMelody] = []
        self.orbit_beats: list[OrbitBeat] = []
        self.proximity_alerts: list[ProximityAlert] = []
        self.to_logic = to_logic

    def run(self):
        self.s = Session()
        self.s.synchronization_policy = "no synchronization"
        self.s.timing_policy = "absolute"
        if self.to_logic:
            drums = self.s.new_midi_part("Drums", "IAC Driver Bus 1", num_channels=1)
            drums2 = self.s.new_midi_part("Drums2", "IAC Driver Bus 1", start_channel=1, num_channels=1)
            mercury_inst = self.s.new_part("marimba")
            venus_inst = self.s.new_part("Shakuhachi 2")
            mars_inst = self.s.new_part("cello")
            earth_inst = self.s.new_midi_part("Atmosphere", "IAC Driver Bus 5")
            jupiter_inst = self.s.new_midi_part("Square Wave", "IAC Driver Bus 6")
            saturn_inst = self.s.new_part("Acoustic Bass ")
            neptune_inst = self.s.new_part("Acoustic Bass")
            uranus_inst = self.s.new_part("Acoustic Bass ")
            piano = self.s.new_part("piano")
            bass = self.s.new_part("acoustic bass")
            dguitar = self.s.new_part("DistortionGuitar")
        else:
            mercury_inst = self.s.new_part("marimba")
            venus_inst = self.s.new_part("Shakuhachi 2")
            mars_inst = self.s.new_part("cello")
            earth_inst = self.s.new_part("Atmosphere")
            jupiter_inst = self.s.new_part("Square Wave")
            saturn_inst = self.s.new_part("Acoustic Bass ")
            neptune_inst = self.s.new_part("Acoustic Bass")
            uranus_inst = self.s.new_part("Acoustic Bass ")
            piano = self.s.new_part("piano")
            bass = self.s.new_part("acoustic bass")
            dguitar = self.s.new_part("DistortionGuitar")
            drums = drums2 = self.s.new_part("POWER")

        self.orbit_beats.extend([
            OrbitBeat(drums2, "mercury", 75, 1, 0.1, play_expansion_factor=5),
            OrbitBeat(drums2, "venus", 69 if self.to_logic else 73, 1, 0.1), #, play_angles=(-0.2, math.pi - 0.2)),
            OrbitBeat(drums, "earth", 39, 1, 0.1), #, play_angles=(-0.2, math.pi-0.2)),
            OrbitBeat(drums, "mars", 48, 1, 0.1), #, play_angles=(0,  1 / 3 * math.tau, 2 / 3 * math.tau))
        ])

        self.proximity_alerts.extend([
            ProximityAlert(drums, "mercury", "venus", 0.3, 66),
            ProximityAlert(drums, "venus", "earth", 0.3, 68),
            ProximityAlert(drums, "earth", "mars", 0.4, 67, color=(100, 200, 200)),
        ])

        self.orbit_melodies.extend([
            OrbitMelody(mercury_inst, "mercury", 1, 0, volume_scale=0.5, sample_duration=0.05),
            OrbitMelody(venus_inst, "venus", 1, 0, volume_scale=0.3),
            OrbitMelody(earth_inst, "earth", 1, 0,
                        sample_duration=days_to_beats(50 * planet_rotation_period_in_days["earth"]), volume_scale=0.2),
            OrbitMelody(mars_inst, "mars", 3, 0, volume_scale=0.6),
            OrbitMelody(jupiter_inst, "jupiter", 1, 0,
                        sample_duration=days_to_beats(50 * planet_rotation_period_in_days["jupiter"]),
                        volume_basis="angleDiff"),
            OrbitMelody(saturn_inst, "saturn", 7, 1),
            OrbitMelody(uranus_inst, "uranus", 11, 4),
            OrbitMelody(neptune_inst, "neptune", 17, 0),
        ])

        for b in self.orbit_beats:
            b.muted = True

        for mel in self.orbit_melodies:
            mel.muted = True

        for pa in self.proximity_alerts:
            pa.muted = True

        for process in self.orbit_melodies + self.orbit_beats + self.proximity_alerts:
            self.s.fork(process.play)

        with self.started:
            self.started.notify_all()

#         wait(4)
        self.orbit_beats[0].muted = False
#         wait(4)
        self.orbit_beats[1].muted = False
#         wait(4)
        self.orbit_beats[2].muted = False
#         wait(4)
        self.orbit_beats[3].muted = False
        wait(10)
#         self.proximity_alerts[0].muted = False
#         wait(10)
#         self.proximity_alerts[1].muted = False
#         wait(10)
#         self.proximity_alerts[2].muted = False
#         wait(10)
        self.orbit_melodies[2].muted = False
        wait(10)
        self.orbit_melodies[4].muted = False
        

        wait_forever()

    def wait_until_started(self):
        with self.started:
            self.started.wait()


if __name__ == '__main__':
    PlanetMusic().run()
