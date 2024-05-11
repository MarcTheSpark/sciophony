from scamp import *

s = Session()

clarinet = s.new_part("clarinet")

def play_cantor(inst: ScampInstrument, n, pitch, volume, duration):
    if n == 0:
        inst.play_note(pitch, volume, duration)
    else:
        play_cantor(inst, n - 1, pitch, volume, duration / 3)
        wait(duration / 3)
        play_cantor(inst, n - 1, pitch, volume, duration / 3)


for i, pitch in enumerate([60, 67, 70, 74, 78, 80]):
    fork(play_cantor, args=(clarinet, i, pitch, 1.0, 5))
wait_for_children_to_finish()