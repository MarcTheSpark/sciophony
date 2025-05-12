from scamp import *
from itertools import cycle

s = Session()
s.tempo = 120

piano = s.new_part("piano")

# [1, 0, 1, 1, 1, 0, 0, 1, 0]
# [1, 2, 2, 2, 1, 0, 0, 0]
# 
# 
# [2.5, -0.5, 1, 1, -1.5, 0.5]

rhythm_loop = [2.5, -0.5, 1, 1, -1.5, 0.5]

def collatz(n):
    while True:
        yield n
        if n % 2 == 0:
            n //= 2
        else:
            n = 3*n + 1


collatz_iterator = collatz(7)

for dur in cycle(rhythm_loop):
    if dur > 0:
        piano.play_note(50 + next(collatz_iterator), 0.7, dur)
    else:
        wait(abs(dur))