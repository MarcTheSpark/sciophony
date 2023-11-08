from marciano.periodictable import Element
from scamp import *

# Extracting info
# helium = Element(2)  # instantiate element by number
# helium = Element("helium")  # instantiate element by name
# 
# print(helium.AtomicMass)
# print(helium.Type)

s = Session()

piano = s.new_part("piano")

elements = [Element(atomic_number) for atomic_number in range(1, 100)]
temperatures = [0, 100, 500, 1000, 1500, 2500, 4000, 6000]  # temps in kelvin (goign up exponentially)

for temperature in temperatures:
    print(f"Temperature: {temperature}")
    for element in elements:
        phase = element.phase_at(temperature)
        pitch = 45 if phase == "solid" else 61 if phase == "liquid" else 76
        piano.play_note(pitch, 0.8, 0.07)
    wait(0.5)
    