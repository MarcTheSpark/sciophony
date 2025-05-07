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
from global_constants import TEMPO
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
        self.s = Session(tempo=TEMPO)
        self.s.synchronization_policy = "no synchronization"
        self.s.timing_policy = "absolute"
        if self.to_logic:
            drums = self.s.new_midi_part("Drums", "IAC Driver Bus 1", num_channels=1)
            drums2 = self.s.new_midi_part("Latin Drums", "IAC Driver Bus 1", start_channel=1, num_channels=1)
            mercury_inst = self.s.new_midi_part("marimba", "IAC Driver Bus 2")
            venus_inst = self.s.new_midi_part("Montain Flute", "IAC Driver Bus 3")
            earth_inst = self.s.new_midi_part("Atmosphere", "IAC Driver Bus 4")
            mars_inst = self.s.new_midi_part("Strings", "IAC Driver Bus 5")
            jupiter_inst = self.s.new_midi_part("Square Wave", "IAC Driver Bus 6")
            saturn_inst = self.s.new_midi_part("Bass 1", "IAC Driver Bus 7")
            neptune_inst = self.s.new_midi_part("Bass 2", "IAC Driver Bus 8")
            uranus_inst = self.s.new_midi_part("Bass 3", "IAC Driver Bus 9")
        else:
            drums = drums2 = self.s.new_part("POWER")
            mercury_inst = self.s.new_part("marimba")
            venus_inst = self.s.new_part("Shakuhachi 2")
            mars_inst = self.s.new_part("cello")
            earth_inst = self.s.new_part("Atmosphere")
            jupiter_inst = self.s.new_part("Square Wave")
            saturn_inst = self.s.new_part("Acoustic Bass ")
            neptune_inst = self.s.new_part("Acoustic Bass")
            uranus_inst = self.s.new_part("Acoustic Bass ")

        # # I was using this list of (manually chosen?) angles for some reason, but it seems to work as just every pi/16
        # # so I'll commit this list anyway, commented out and might delete later
        # earth_beat_angles = [-1.5252829951042808, -1.1494456403151276, -0.7741796074050398, -0.3970319478625482,
        #                      -0.015753108422733086, 0.3714288540565829, 0.7655274925949108, 1.1665503282882375,
        #                      1.5733665990466532, 1.9837885843283756, 2.3949214282796834, 2.8037263353892072,
        #                      -3.075554997246311, -2.6781964339238695, -2.287894935818636, -1.90407464585718]
        earth_beat_angles = [-math.pi / 2 + x * math.pi/8 for x in range(16)]
        earth_beat_angles = [x - 0.1 for x in earth_beat_angles]
        earth_kick_angles = earth_beat_angles[::4]
        earth_hihat_angles = [x for x in earth_beat_angles if x not in earth_kick_angles]


        self.orbit_beats.extend([
            OrbitBeat(drums2, "mercury", 75, 0.3, 0.25, play_expansion_factor=5,play_angles=(-math.pi/2,)),
            OrbitBeat(drums2, "venus", 69 if self.to_logic else 73, 1, 0.25,play_angles=(-math.pi/2,)), #, play_angles=(-0.2, math.pi - 0.2)),
            OrbitBeat(drums, "venus", 39, 0.3, 0.25,play_angles=(-math.pi/2,)), #, play_angles=(-0.2, math.pi-0.2)),
            OrbitBeat(drums2, "mars", 63, 0.5, 0.25,play_angles=(-math.pi/2,)), #, play_angles=(0,  1 / 3 * math.tau, 2 / 3 * math.tau))
            OrbitBeat(drums, "earth", 36, 1, 0.25, earth_kick_angles),
            OrbitBeat(drums, "earth", 42, 0.3, 0.25, earth_hihat_angles),
        ])

        self.proximity_alerts.extend([
            ProximityAlert(drums, "mercury", "venus", 0.3, 66),
            ProximityAlert(drums, "venus", "earth", 0.3, 68),
            ProximityAlert(drums, "earth", "mars", 0.4, 67, color=(100, 200, 200)),
        ])

        self.orbit_melodies.extend([
            OrbitMelody(mercury_inst, "mercury", 1, 0, volume_range=(0.1, 0.6)),
            OrbitMelody(venus_inst, "venus", 1, 0, volume_range=(0.1, 0.5)),
            OrbitMelody(earth_inst, "earth", 1, 0),
            OrbitMelody(mars_inst, "mars", 3, 1, volume_range=(0.2, 0.8), play_expansion_factor=2.5, trail_expansion_factor=2),
            OrbitMelody(jupiter_inst, "jupiter", 1, 0, volume_range=(0.2, 0.8), play_expansion_factor=1.6, trail_expansion_factor=1.3),
            OrbitMelody(saturn_inst, "saturn", 4, 2, volume_range=(0.2, 0.8)),
            OrbitMelody(uranus_inst, "uranus", 4, 1, volume_range=(0.2, 0.8), play_expansion_factor=3, trail_expansion_factor=2),
            OrbitMelody(neptune_inst, "neptune", 4, 0, volume_range=(0.2, 0.8), play_expansion_factor=3, trail_expansion_factor=2),
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

        wait(10)
        self.orbit_beats[0].muted = False
        wait(10)
        self.orbit_beats[1].muted = False
        wait(10)
        self.orbit_beats[3].muted = False
        wait(10)

        self.orbit_beats[2].muted = False

        wait(5)
        self.orbit_beats[4].muted = False
        self.orbit_beats[5].muted = False
        wait(20)
        self.orbit_melodies[7].muted = False
        self.orbit_melodies[6].muted = False
        self.orbit_melodies[5].muted = False
        wait(40)
        self.orbit_melodies[4].muted = False
        wait(20)
        self.orbit_melodies[3].muted = False
        wait(20)
        self.orbit_melodies[2].muted = False
        wait(20)
        self.orbit_melodies[1].muted = False
        wait(20)
        self.orbit_melodies[0].muted = False

#         self.orbit_melodies[4].muted = False
#         self.orbit_melodies[5].muted = False
#         self.orbit_melodies[7].muted = False
#         wait(10)
#         self.orbit_melodies[6].muted = False
#         wait(10)
#         self.orbit_melodies[3].muted = False
#         wait(10)
#         self.orbit_melodies[2].muted = False
#         wait(10)
#         self.orbit_melodies[1].muted = False
#         wait(10)
#         self.orbit_melodies[0].muted = False
#         wait(10)
#         self.proximity_alerts[2].muted = False
        wait_forever()

    def wait_until_started(self):
        with self.started:
            self.started.wait()


if __name__ == '__main__':
    PlanetMusic(to_logic=True).run()
