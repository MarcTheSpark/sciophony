from scamp import *
import random
s = Session()

grav_player = s.new_osc_part("gravPlayer", 57120)
cello = s.new_part("cello")

def cello_loop():
    while True:
        cello.play_chord([52, 59, 67], [0.2, 0.7], 15)
        cello.play_chord([52, 61, 69], [0.6, 0.3], 5)

fork(cello_loop)
while True:
    dur = random.randint(1, 5)
    grav_player.play_note(
        random.choice([40, 43, 47, 49, 52, 55]),
        random.uniform(0.7, 0.8),
        dur,
        {"param_templateMix": 0.4,
         "param_backupDur": dur,
         "param_pan": random.uniform(-1, 1),
         "param_which": 8}
    )