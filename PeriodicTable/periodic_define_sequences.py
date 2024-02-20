from marciano.periodictable import get_attribute_sequence
from scamp_extensions.utilities import remap
import numpy as np
from matplotlib import pyplot as plt

heats = get_attribute_sequence("SpecificHeat")[:99]
boilings = get_attribute_sequence("BoilingPoint")[:99]
anumbers = get_attribute_sequence("AtomicNumber")[:99]
negs = get_attribute_sequence("Electronegativity")[:99]
metalics = [0 if x == "Metal" else 1 if x == "Metalloid" else 2 for x in get_attribute_sequence("Metalicity")[:99]]
radios = get_attribute_sequence("Radioactive")[:99]
aradius = get_attribute_sequence("AtomicRadius")[:99]
discovery_years = get_attribute_sequence("Year")[:99]

r_heats = remap(heats, 48, 108, input_warp="exp")
r_boilings = remap(boilings, 48, 84, output_warp=4)
r_negs = remap(negs, 48, 84, output_warp=4)
r_metalics = remap(metalics, 48, 84)
r_radius = remap(aradius, 48, 84)

nyears = np.array(discovery_years)
discovery_perc = [sum(nyears < y) / len(nyears) for y in range(1700, 2000)]


def plot_discovery_curve():
    plt.plot(range(1700, 2000), discovery_perc)
    plt.show()


def plot_sequences():
    plt.plot(anumbers, r_heats, label="heats")
    plt.plot(anumbers, r_boilings, label="boiling")
    plt.plot(anumbers, r_negs, label="Eneg")
    plt.plot(anumbers, r_radius, label="Radius")
    plt.plot(anumbers, r_metalics, "o", label="Metal")
    which_radios = np.where(np.array(radios) > 0)[0]
    plt.plot(which_radios, np.full(len(which_radios), 45), "*", label="RadioActive")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    plot_discovery_curve()
    plot_sequences()
