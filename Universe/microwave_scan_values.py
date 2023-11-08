import numpy as np
import os
from marciano.microwave import get_value_at, get_max_value_for_sharpness
from marciano.spherical_spiral import position_on_spiral
from expenvelope import Envelope
from scipy.interpolate import interp1d


PIECE_DURATION = 250

sharpness_env = Envelope([0, 1], [PIECE_DURATION])
arc_length_env = Envelope([0, 60], [PIECE_DURATION])


def calc_times_and_values():
    times = np.arange(0, PIECE_DURATION, 0.05)
    values = []

    for t in times:
        sharpness = sharpness_env.value_at(t)
        arc_length = arc_length_env.value_at(t)
        spiral_loc = position_on_spiral(arc_length, 0.1)
        values.append(get_value_at(sharpness, *spiral_loc))
    return times, values


filename = 'scan_values.npz'

if os.path.exists(filename):
    print("Loading saved values...", end="")
    # Load the NumPy arrays from the file if it exists
    data = np.load(filename)
    scan_times = data['times']
    scan_values = data['values']
    print("Done.")
else:
    print("Calculating values...", end="")
    # Otherwise, calculate the NumPy arrays and save them to the file
    scan_times, scan_values = calc_times_and_values()
    np.savez(filename, times=scan_times, values=scan_values)
    print("Done.")


def find_local_maxima(arr, radius):
    local_maxima = []

    for i in range(len(arr)):
        start = max(0, i - radius)  # Ensure start is not negative
        end = min(len(arr), i + radius + 1)  # Ensure end is not greater than array length

        # Check if the current element is the maximum within the specified radius
        if arr[i] == max(arr[start:end]):
            local_maxima.append(i)

    return np.array(local_maxima)


local_maxima_indices = find_local_maxima(scan_values, 5)
scan_value_at_time = interp1d(scan_times, scan_values)

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    plt.title("Original Data")
    plt.plot(scan_times, scan_values, label='Noisy Data', alpha=0.5)
    plt.plot(scan_times[local_maxima_indices], scan_values[local_maxima_indices], 'rx', markersize=8, label='Local Maxima')
    plt.legend()
    plt.show()
