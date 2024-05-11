from scamp import *
import functools

s = Session()

piano = s.new_part("piano")
clarinet = s.new_part("clarinet")
bassoon = s.new_part("bassoon")
contrabass = s.new_part("contrabass")
perc = s.new_part("power")

insts_and_pitches = (
    (contrabass, 36),
    (bassoon, 48),
    (clarinet, 55),
    (clarinet, 66),
    (clarinet, 74),
    (piano, 82),
    (piano, 98),
    (perc, 59)
)
                 

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
    
# infinite_cantor(clarinet, 60, 1, 0.5)

for i, pitch in enumerate([60, 67, 70, 74, 78, 80]):
    fork(infinite_cantor, args=(clarinet, pitch, 1.0, 5 * 3 ** (-i)))
    
# Try accelerating, fading infinite cantors. (shepard tone style?)
wait_for_children_to_finish()