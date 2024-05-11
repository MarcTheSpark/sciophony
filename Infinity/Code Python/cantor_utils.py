from scamp import wait, ScampInstrument


def cantor_rest_pattern(dur):
    pattern_so_far = (dur,)
    longest_rest = dur
    yield dur
    while True:
        longest_rest *= 3
        yield from (longest_rest,) + pattern_so_far
        pattern_so_far = pattern_so_far + (longest_rest,) + pattern_so_far
        
        

def infinite_cantor(inst: ScampInstrument, pitch, volume, duration):
    for wait_dur in cantor_rest_pattern(duration):
        inst.play_note(pitch, volume, duration)
        wait(wait_dur)
        
        
def play_cantor(inst: ScampInstrument, n, pitch, volume, duration):
    if n == 0:
        inst.play_note(pitch, volume, duration)
    else:
        play_cantor(inst, n - 1, pitch, volume, duration / 3)
        wait(duration / 3)
        play_cantor(inst, n - 1, pitch, volume, duration / 3)