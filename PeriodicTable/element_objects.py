import random

from marciano import periodictable
from scamp_extensions.pitch import Scale
from scamp_extensions.utilities import remap
from scamp import *


electronegativity_range = periodictable.get_attribute_range("Electronegativity")


def get_pitch_classes_from_electronegativity(electronegativity):
    pcs = sorted((7 * x) % 12 for x in range(4 + int(electronegativity / electronegativity_range[1] * 8)))
    return pcs


radius_range = periodictable.get_attribute_range("AtomicRadius")


def get_chord_bounds_from_radius(radius):
    half_chord_range = remap(radius, 3, 40, *radius_range)
    return 60 - half_chord_range, 60 + half_chord_range


atomic_mass_range = periodictable.get_attribute_range("AtomicMass")


def get_num_notes_from_mass(atomic_mass):
    return int(remap(atomic_mass, 1, 20, *atomic_mass_range, output_warp=-3))


random.seed(0)
jitters = [random.uniform(-0.1, 0.1) for _ in range(100)]
powers = [1, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]

def get_chord_from_element(element):
    if not isinstance(element, periodictable.Element):
        element = periodictable.Element(element)
    pcs = get_pitch_classes_from_electronegativity(element.electronegativity)
    scale = Scale.from_pitches(pcs + [12])
    num_notes = get_num_notes_from_mass(element.atomic_mass)
    if element.name != "Helium":
        num_notes = max(2, num_notes)
    chord_bounds = get_chord_bounds_from_radius(element.atomic_radius)
    jitter_iter = iter(jitters)

    possible_pitch_space_divisions = [[0.5]] if num_notes == 1 else [
        [(i / (num_notes - 1)) ** power + jitter for i, jitter in zip(range(num_notes), jitter_iter)]
        for power in powers
    ]

    chord_range = chord_bounds[1] - chord_bounds[0]
    possible_chords = [scale.round([chord_bounds[0] + chord_range * normalized_pitch for normalized_pitch in psd])
                       for psd in possible_pitch_space_divisions]
    possible_chords.sort(key=lambda chord: len(set(int(x) % 12 for x in chord)))

    return scale.round(possible_chords[-1])


s = Session()

strings = s.new_part("Strings")


for element in periodictable.all_elements[:86]:
    print(element.name)
    print(get_chord_from_element(element))
    strings.play_chord(get_chord_from_element(element), 0.5, 1)
