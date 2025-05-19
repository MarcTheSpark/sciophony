from scamp import *
from cantor_tempo_utils import cantor_rest_pattern


s = Session()


drums = s.new_part("power")

cantor_accel_bar = TempoEnvelope((60, 180), (3, ), ("exp * 2", ), "tempo")


def play_cantor_pattern(inst, pitch, depth):
    dur =  3 ** (1 - depth)
    rests = cantor_rest_pattern(dur)
    while current_clock().beat() < 3:
        inst.play_note(pitch, 0.8, dur)
        if current_clock().beat() >= 3: break
        wait(next(rests))
        

s.start_transcribing()
s.fast_forward()

for _ in range(1):
    s.tempo = 60
    s.set_tempo_target(180, 3, -2.1972245773362196)
    for i, p in enumerate([36, 38, 46, 53, 54]):
        fork(play_cantor_pattern, (drums, p, i))
    
    for i in range(27):
        drums.play_note(42, 0.4, 3/27/2)
        drums.play_note(42, 0.4, 3/27/2)
    wait_for_children_to_finish()
s.stop_transcribing().export_to_midi_file("accelerating_beat_once.mid", flatten_tempo_changes=True )
