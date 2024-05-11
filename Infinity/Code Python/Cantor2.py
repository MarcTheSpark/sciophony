from scamp import *

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

def play_cantor(inst: ScampInstrument, n, pitch, volume, duration):
    if n == 0:
        inst.play_note(pitch, volume, duration)
    else:
        play_cantor(inst, n - 1, pitch, volume, duration / 3)
        wait(duration / 3)
        play_cantor(inst, n - 1, pitch, volume, duration / 3)


for i, (inst, pitch) in enumerate(insts_and_pitches):
    fork(play_cantor, args=(inst, i, pitch, 1.0, 30))
    
wait_for_children_to_finish()


# have the long notes swell/evolve over time in terms of timbre, or maybe gliss?