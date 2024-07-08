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
from solar_system_functions import OrbitMelody, OrbitBeat, ProximityAlert
import threading


class PlanetMusic(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self.s: Session = None
        self.started = threading.Condition()
        self.orbit_melodies: list[OrbitMelody] = []
        self.orbit_beats: list[OrbitBeat] = []
        self.proximity_alerts: list[ProximityAlert] = []

    def run(self):
        self.s = Session()
        self.s.synchronization_policy = "no synchronization"
        self.s.timing_policy = "absolute"
        mercury_inst = self.s.new_part("marimba")
        venus_inst = self.s.new_part("Shakuhachi 2")
        mars_inst = self.s.new_part("cello")
        earth_inst = self.s.new_part("Atmosphere")
        jupiter_inst = self.s.new_part("Bass")
        saturn_inst = self.s.new_part("Acoustic Bass ")
        neptune_inst = self.s.new_part("Acoustic Bass")
        uranus_inst = self.s.new_part("Acoustic Bass ")
        piano = self.s.new_part("piano")
        bass = self.s.new_part("acoustic bass")
        dguitar = self.s.new_part("DistortionGuitar")
        drums = self.s.new_part("POWER")

        self.orbit_beats.extend([
            OrbitBeat(drums, "mercury", 75, 1, 0.1, play_expansion_factor=5),
            OrbitBeat(drums, "venus", 73, 1, 0.1, play_angles=(-0.2, math.pi / 2-0.2)),
            OrbitBeat(drums, "earth", 39, 1, 0.1, play_angles=(0-0.2, math.pi-0.2)),
            OrbitBeat(drums, "mars", 63, 1, 0.1, play_angles=(0, 2 / 3 * math.tau))
        ])

        self.proximity_alerts.extend([
            ProximityAlert(drums, "mercury", "venus", 0.3, 66),
            ProximityAlert(drums, "earth", "mars", 0.4, 67, color=(100, 200, 200)),
        ])

        self.orbit_melodies.extend([
            OrbitMelody(mercury_inst, "mercury", 1, 0, volume_scale=0.5, sample_duration=0.05),
            OrbitMelody(venus_inst, "venus", 1, 0, volume_scale=0.3),
            OrbitMelody(earth_inst, "earth", 1, 0, volume_scale=0.2),
            OrbitMelody(mars_inst, "mars", 3, 0, volume_scale=0.6),
            OrbitMelody(jupiter_inst, "jupiter", 4, 1),
            OrbitMelody(saturn_inst, "saturn", 7, 1),
            OrbitMelody(uranus_inst, "uranus", 11, 4),
            OrbitMelody(neptune_inst, "neptune", 17, 0),
        ])

        for process in self.orbit_melodies + self.orbit_beats + self.proximity_alerts:
            self.s.fork(process.play)

        with self.started:
            self.started.notify_all()

        # for b in self.orbit_beats:
        #     b.muted = True
        #
        # for mel in self.orbit_melodies:
        #     mel.muted = True
        #
        # for pa in self.proximity_alerts:
        #     pa.muted = True

        wait_forever()

    def wait_until_started(self):
        with self.started:
            self.started.wait()


if __name__ == '__main__':
    PlanetMusic().run()
