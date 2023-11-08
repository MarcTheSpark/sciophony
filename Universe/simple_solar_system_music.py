from scamp import *
from marciano import solar_system_model


s = Session()
solar_system_model.start(s, days_per_beat=50, start_date="2018-01-01")

piano = s.new_part("piano")
flute = s.new_part("flute")

# print(solar_system_model.get_position("earth"))
# print(solar_system_model.get_velocity("mars"))
# print(solar_system_model.get_distance("sun", "neptune"))
# print(solar_system_model.get_distance("earth", "jupiter"))


# -------------------------- Piano notes as before ----------------------------------

while True:
    dist_earth_mars = solar_system_model.get_distance("earth", "mars")
    piano.play_note(90 - 30 * dist_earth_mars, 0.5 / dist_earth_mars, 0.2)


# -------------------------- sustained flute bend ----------------------------------

# sustained_note = flute.start_note(82 - 8 * solar_system_model.get_distance("earth", "mars"), 0.5 / solar_system_model.get_distance("earth", "mars"))
# 
# while True:
#     dist_earth_mars = solar_system_model.get_distance("earth", "mars")
#     sustained_note.change_pitch(82 - 8 * solar_system_model.get_distance("earth", "mars"), 0.5)
#     sustained_note.change_volume(0.5 / solar_system_model.get_distance("earth", "mars"), 0.5)
#     wait(0.3)



