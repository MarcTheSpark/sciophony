from scamp import *
import random

s = Session()

lines = []

t = 0
dt = 0.003

def mouse_listener(x, y):
    global t
    lines.append(f"{t} {x} {y} {random.uniform(1, 7)}")
    t += dt
    

s.register_mouse_listener(mouse_listener, relative_coordinates=True)

wait(10)

with open("fakedata.txt", "w") as f:
    f.write("\n".join(lines))