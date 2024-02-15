import numpy as np
import os
from marciano.microwave import get_value_at, get_max_value_for_sharpness
from marciano.spherical_spiral import position_on_spiral
from expenvelope import Envelope
from scipy.interpolate import interp1d


PIECE_DURATION = 250

sharpness_env = Envelope([0, 1], [PIECE_DURATION], curve_shapes=[1.5])
arc_length_env = Envelope([0, 60], [PIECE_DURATION])


def calc_times_and_values():
    times = np.arange(0, PIECE_DURATION, 0.05)
    values = []

    for t in times:
        sharpness = sharpness_env.value_at(t)
        arc_length = arc_length_env.value_at(t)
        spiral_loc = position_on_spiral(arc_length, 0.1)
        values.append(get_value_at(sharpness, *spiral_loc))
    return times, np.array(values)


def calc_cello_times_and_values():
    cello_sharpness_env = Envelope([0.01, 0.01], [PIECE_DURATION])
    times = np.arange(0, PIECE_DURATION, 0.05)
    values = []

    for t in times:
        cello_sharpness = cello_sharpness_env.value_at(t)
        arc_length = arc_length_env.value_at(t)
        spiral_loc = position_on_spiral(arc_length, 0.1)
        values.append(get_value_at(cello_sharpness, *spiral_loc))
    return times, np.array(values)


# zone_boundaries=(5.0, 14.45, 25, 42, 71, 120, 200)
def get_zones(data, zone_boundaries=(5.0, 25, 60, 120, 180, 240)):
    zone_boundaries = list(zone_boundaries)
    # Create boundary array including negative boundaries
    extended_boundaries = [-b for b in zone_boundaries[::-1]] + zone_boundaries
    # Use np.digitize to bin the data points
    bin_indices = np.digitize(data, extended_boundaries)

    # Adjust indices to reflect the zone numbers including negatives
    # Calculate the offset since np.digitize returns indices starting from 1
    offset = len(zone_boundaries)
    return bin_indices - offset


filename = 'scan_values.npz'

if os.path.exists(filename):
    print("Loading saved values...", end="")
    # Load the NumPy arrays from the file if it exists
    data = np.load(filename)
    scan_times = data['times']
    scan_values = data['values']
    cello_scan_values = data['cello_values']
    print("Done.")
else:
    print("Calculating values...", end="")
    # Otherwise, calculate the NumPy arrays and save them to the file
    scan_times, scan_values = calc_times_and_values()
    _, cello_scan_values = calc_cello_times_and_values()
    np.savez(filename, times=scan_times, values=scan_values, cello_values=cello_scan_values)
    print("Done.")


cello_scan_value_at_time = interp1d(cello_scan_values, scan_values)


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
local_minima_indices = find_local_maxima(-scan_values, 5)
local_extrema_indices = np.sort(np.concatenate([local_maxima_indices, local_minima_indices]))

scan_value_at_time = interp1d(scan_times, scan_values)


# bin the scan values into zones
# zones = get_zones(scan_values)
zones = get_zones(cello_scan_values)

# Get the zone values at all local extrema
_zones_at_extrema = zones[local_extrema_indices]

# Filter out only the extrema that are in a different zone than the previous extrema
_changes = np.concatenate(([True], _zones_at_extrema[1:] != _zones_at_extrema[:-1]))
key_extrema_indices = local_extrema_indices[_changes]

_processed_zone_segments = []
for index, next_index in zip(key_extrema_indices[:-1], key_extrema_indices[1:]):
    current_zone, next_zone = zones[index], zones[next_index]
    current_scan_value, next_scan_value = scan_values[index], scan_values[next_index]
    min_zone, max_zone = min(current_zone, next_zone), max(current_zone, next_zone)
    min_scan_value, max_scan_value = min(current_scan_value, next_scan_value), max(current_scan_value, next_scan_value)
    boundaries_for_this_segment = np.linspace(min_scan_value, max_scan_value, max_zone - min_zone, endpoint=False)[1:]
    # print(f"{current_zone=}, {next_zone=}, {scan_values[index]=}, "
    #       f"{scan_values[next_index]=}, {boundaries_for_this_segment=}")
    this_segment_zones = np.digitize(scan_values[index: next_index], boundaries_for_this_segment)
    if next_zone > current_zone:
        this_segment_zones += current_zone
    else:
        this_segment_zones += next_zone + 1
    # print(set(this_segment_zones))
    _processed_zone_segments.append(this_segment_zones)

processed_zones = np.concatenate(_processed_zone_segments)
if len(processed_zones) < len(scan_values):
    # extend the last zone to the full length of scan values
    processed_zones = np.concatenate([processed_zones, np.full(len(scan_values) - len(processed_zones), processed_zones[-1])])


chord_zone_at_time = interp1d(scan_times, processed_zones)


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    plt.title("Original Data")
    zones_wide = zones * 40
    processed_zones_wide = processed_zones * 40
    plt.plot(scan_times, scan_values, label='Noisy Data', alpha=0.5)
    plt.plot(scan_times[local_extrema_indices], scan_values[local_extrema_indices], 'rx', markersize=8, label='Local Extrema')
    plt.plot(scan_times[key_extrema_indices], zones_wide[key_extrema_indices], 'ro', markersize=8, label='Local Extrema')
    plt.plot(scan_times, processed_zones_wide, color="red", alpha=0.6)
    plt.legend()
    plt.show()
