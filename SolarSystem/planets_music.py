"""
- Turn planet players functions into planet player objects that you can turn silent/change their angles of playing.
- Particularly interesting would be to have the visual angle of play go from small to large
- Shape the form over time by changing the angles over time. This could be about human attention focusing on different
things, or on different visibilities of the sky on cloudy/clear days.
- At any way, set up a good code interface for playing with form
- Make it so that the percussion of play revolution beat can play on multiple angle triggers
TODO: Visualize?
"""

from scamp import *
from solar_system_functions import ss, play_planet, planet_pitch_base, play_planet_revolution_beat, play_planet_proximity_alert
import threading


class PlanetMusic(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self.s: Session = None
        self.started = threading.Condition()

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

        self.s.fork(play_planet_proximity_alert, args=("earth", "mars", 0.4, 67, drums))
        self.s.fork(play_planet_proximity_alert, args=("mercury", "venus", 0.3, 66, drums))
        self.s.fork(play_planet, args=("neptune", planet_pitch_base["neptune"], 20, 3, 17, 0, neptune_inst))
        self.s.fork(play_planet, args=("neptune", planet_pitch_base["neptune"], 20, 3, 17, 0, neptune_inst))
        self.s.fork(play_planet, args=("uranus", planet_pitch_base["uranus"], 20, 3, 11, 4, uranus_inst))
        self.s.fork(play_planet, args=("saturn", planet_pitch_base["saturn"], 20, 3, 7, 1, saturn_inst))
        self.s.fork(play_planet, args=("jupiter", planet_pitch_base["jupiter"], 20, 1, 4, 1, jupiter_inst))
        self.s.fork(play_planet, args=("mars", planet_pitch_base["mars"], 20, 0.6, 3, 0, mars_inst))
        self.s.fork(play_planet, args=("earth", planet_pitch_base["earth"], 20, 0.2, 1, 0, earth_inst))
        self.s.fork(play_planet, args=("venus", planet_pitch_base["venus"], 20, 0.3, 1, 0, venus_inst))
        self.s.fork(play_planet, args=("mercury", planet_pitch_base["mercury"], 12, 0.5, 1, 0, mercury_inst))

        self.s.fork(play_planet_revolution_beat, args=("mercury", 75, 1, 0.1, drums))
        self.s.fork(play_planet_revolution_beat, args=("venus", 73, 1, 0.1, drums))
        self.s.fork(play_planet_revolution_beat, args=("earth", 39, 1, 0.1, drums))
        self.s.fork(play_planet_revolution_beat, args=("mars", 63, 1, 0.1, drums))

        with self.started:
            self.started.notify_all()
        wait_forever()

    def wait_until_started(self):
        with self.started:
            self.started.wait()


if __name__ == '__main__':
    PlanetMusic().run()
