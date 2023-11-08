import healpy as hp
import matplotlib.pyplot as plt
import numpy as np
from pylab import *

K_cmb = 2.725 #CMB temperature
K_2_microK = 10**6

try:
    microwave_map = hp.read_map("../downgraded.fits")
except FileNotFoundError:
    print("Downgraded map not found.")
    try:
        print("Trying to load local copy of full map.")
        microwave_map = hp.read_map('COM_CMB_IQU-smica-field-Int_2048_R2.01_full.fits') # read Planck map
    except FileNotFoundError:
        print("Local copy not found; tring to load remote copy.")
        microwave_map = hp.read_map('https://irsa.ipac.caltech.edu/data/Planck/release_2/all-sky-maps/maps/component-maps/cmb/COM_CMB_IQU-smica-field-Int_2048_R2.01_full.fits') # read Planck map
    print("Success. Downgrading map.")
    downsampled_microwave_map = hp.ud_grade(microwave_map, nside_out=hp.get_nside(microwave_map) // 4)
    print("Saving downgraded map for future use.")
    hp.write_map("../downgraded.fits", downsampled_microwave_map)
    microwave_map = downsampled_microwave_map

microwave_map *= K_2_microK

def get_filtered_map(original_map, l_max):
    # Compute the spherical harmonic coefficients (a_lm)
    clm = hp.anafast(original_map)
    # Apply low-pass filter: Keep only the modes with l < l_max
    mask = np.arange(len(clm)) < l_max
    filtered_clm = clm * mask

    # Synthesize the filtered map from the filtered spherical harmonic coefficients
    return hp.synfast(filtered_clm, nside=hp.get_nside(original_map), verbose=False)



nside = hp.get_nside(microwave_map)


def get_value_at(which_map, theta, phi):
    # Get pixel index
    return which_map[hp.ang2pix(nside, theta, phi)]


# print(get_value_at(0, np.pi))

# projection = np.array([[get_value_at(microwave_map, theta, phi)
#                        for phi in np.linspace(0, 2 * np.pi, 3200)]
#                        for theta in np.linspace(0, np.pi, 1800)])


try:
    filtered_maps = hp.read_map("../filteredmaps.fits", field=range(20))
except FileNotFoundError:
    filtered_maps = []
    x = 4
    while x < 3000:
        filtered_maps.append(get_filtered_map(microwave_map, x))
        x *= 1.4
    hp.write_map("../filteredmaps.fits", filtered_maps)

for filtered_map in filtered_maps:
    projection = get_value_at(filtered_map, np.linspace(0, np.pi, 1800)[:, np.newaxis],  np.linspace(0, 2 * np.pi, 3200))

    plt.imshow(projection, cmap='viridis', origin='lower')

    plt.show()
