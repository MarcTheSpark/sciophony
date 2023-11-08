from marciano.periodictable import Element
from scamp import *
from scamp_extensions.utilities import remap
from scamp_extensions.pitch import Scale


s = Session()

scale = Scale.from_pitches([60, 62, 63, 65])

piano = s.new_part("piano")

elements = [Element(atomic_number) for atomic_number in range(1, 100)]
years = [0, 1750, 1800, 1850, 1900, 1920, 2000]  # temps in kelvin (goign up exponentially)


for year in years:
    print(f"Year {year} CE")
    for element in elements:
        if not element.discovered_by(year):
            wait(0.1)
            continue
        chord = list(set([remap(element.electronegativity, 60, 80, 0, 4), remap(element.electronegativity, 60, 40, 0, 4)]))
        piano.play_chord(scale.round(chord), remap(element.electronegativity, 0.4, 1.0, 0, 4), 0.1)
