from scamp import wait, ScampInstrument, current_clock
import itertools


def cantor_rest_pattern(dur):
    pattern_so_far = (dur,)
    longest_rest = dur
    yield dur
    while True:
        longest_rest *= 3
        yield from (longest_rest,) + pattern_so_far
        pattern_so_far = pattern_so_far + (longest_rest,) + pattern_so_far
        
        

def infinite_cantor(inst: ScampInstrument, pitch, volume, duration, note_fade_function=lambda l: min(1, l ** 0.35), min_note_dur=0.01):
    pitch = itertools.repeat(pitch) if not hasattr(pitch, '__iter__') else iter(pitch)
    volume = itertools.repeat(volume) if not hasattr(volume, '__iter__') else iter(volume)
        
    for wait_dur, p, v in zip(cantor_rest_pattern(duration), pitch, volume):
        true_note_length = current_clock().absolute_beat_length() * duration
        vol_multiplier = note_fade_function(true_note_length)
        if true_note_length < min_note_dur:
            break
        if hasattr(p, '__len__'):
            inst.play_chord(p, v * vol_multiplier, duration)
        else:
            inst.play_note(p, v * vol_multiplier, duration)
        wait(wait_dur)
        
        
def play_cantor(inst: ScampInstrument, n, pitch, volume, duration):
    if n == 0:
        inst.play_note(pitch, volume, duration)
    else:
        play_cantor(inst, n - 1, pitch, volume, duration / 3)
        wait(duration / 3)
        play_cantor(inst, n - 1, pitch, volume, duration / 3)