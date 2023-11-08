# # l = [6, 2, 1, -5, "hello", 40.2]
# # 
# # list_iterator = iter(l)
# # 
# # print(next(list_iterator))
# 
# for x in range(200000000000000):
#     if x % 5 == 0:
#         print(x)
#     if x > 100:
#         break
#     
#     
# for x in [5, 2, 6, 7]:
#     print(x)
#     
#     
# it = iter([5, 2, 6, 7])
# while True:
#     try:
#         x = next(it)
#     except StopIteration:
#         break
#     print(x)

from itertools import cycle
from scamp import *
from scamp_extensions.pitch import Scale
import random


s= Session()

piano = s.new_part("piano")
scl = Scale.melodic_minor(71)


def pitch_generator(p, intervals):
    while True:
        yield p
        p += random.choice(intervals)
        

for pitch, duration in zip(pitch_generator(3, [-5, -1, 2, 4]), cycle([0.25, 1.0, 0.5, 0.25, 0.125])):
    piano.play_note(scl[pitch], 0.8, duration)