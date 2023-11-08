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
from solar_system_functions import ss, play_planet, play_planet_revolution_beat, play_planet_proximity_alert
import solar_system_functions


solar_system_functions.DAYS_PER_BEAT = 200

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
neptune_inst = s.new_part("Acoustic Bass")
uranus_inst = s.new_part("Acoustic Bass ")
piano = s.new_part("piano")
bass = s.new_part("acoustic bass")
dguitar = s.new_part("DistortionGuitar")
drums = s.new_part("POWER")


fork(play_planet_proximity_alert, args=("earth", "mars", 0.4, 67, drums))
fork(play_planet_proximity_alert, args=("mercury", "venus", 0.3, 66, drums))
wait_forever()


#play_planet(planet_name,pitch_base,pitch_range,volume_scale,sampling_rate,sampling_phase,inst,angle_filter=2*math.pi):


#s.fork(play_planet,args=("neptune",planet_pitch_base["neptune"],20,3,17,0,neptune_inst))
#s.fork(play_planet,args=("uranus",planet_pitch_base["uranus"],20,3,11,4,uranus_inst))
#s.fork(play_planet,args=("saturn",planet_pitch_base["saturn"],20,3,7,1,saturn_inst))
#s.fork(play_planet,args=("jupiter",planet_pitch_base["jupiter"],20,1,4,1,jupiter_inst))
#s.fork(play_planet,args=("mars",planet_pitch_base["mars"],20,0.6,3,0,mars_inst))
#s.fork(play_planet,args=("earth",planet_pitch_base["earth"],20,0.2,1,0,earth_inst))
#s.fork(play_planet,args=("venus",planet_pitch_base["venus"],20,0.3,1,0,venus_inst))
#s.fork(play_planet,args=("mercury",planet_pitch_base["mercury"],12,0.5,1,0,mercury_inst)) 

s.fork(play_planet_revolution_beat, args=("mercury",75,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("venus",73,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("earth",39,1,0.1,drums))
s.fork(play_planet_revolution_beat, args=("mars",63,1,0.1,drums))

#
# #wait(10)
# # parameters of play planet: planet_name,pitch_base,pitch_range (20)
# # #volume_scale,sampling_rate,sampling_phase,inst,angle_filter=2*math.pi):
#
#
# n_clock=s.fork(play_planet,args=("neptune",planet_pitch_base["neptune"],20,4,4,0,neptune_inst))
# s_clock=s.fork(play_planet,args=("saturn",planet_pitch_base["saturn"],20,4,4,2,saturn_inst))
# j_clock=s.fork(play_planet,args=("jupiter",planet_pitch_base["jupiter"],20,0.4,1,0,jupiter_inst))#,(math.pi)/2))
#
# wait(10)
# #s.fork(play_speed_earth)
#
# u_clock=s.fork(play_planet,args=("uranus",planet_pitch_base["uranus"],20,3,4,1,uranus_inst))
# print("uranus")
#
#
# wait(5)
# print("mars")
# s.fork(play_planet,args=("mars",planet_pitch_base["mars"],20,0.6,3,0,mars_inst))
# wait(5)
# print("earth")
# s.fork(play_planet,args=("earth",planet_pitch_base["earth"],20,0.2,1,0,earth_inst))
# wait(5)
# print("venus")
# s.fork(play_planet,args=("venus",planet_pitch_base["venus"],20,0.3,1,0,venus_inst))
# wait(5)
# print("mercury")
#
# s.fork(play_planet,args=("mercury",planet_pitch_base["mercury"],12,0.5,1,0,mercury_inst))
#
# wait(5)
# print("eath close to mars")
#
# s.fork(play_earth_mars_close,args=("earth","mars"))

wait_forever()
#wait(5)

