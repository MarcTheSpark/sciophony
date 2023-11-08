import numpy as np
from marciano.microwave import get_value_at, get_max_value_for_sharpness
from marciano.spherical_spiral import position_on_spiral
from scamp import *
from scamp_extensions.utilities import remap, TimeVaryingParameter
import random


ANALYZE_POP_LOCATIONS = False
TIME_STEP = 0.02
PIECE_DURATION = 250

s = Session()

cello = s.new_part("cello")
grav_player = s.new_osc_part("gravPlayer", 57120)

sharpness = TimeVaryingParameter([0, 1], [PIECE_DURATION])
arc_length = TimeVaryingParameter([0, 60], [PIECE_DURATION])

pop_lengths_min = TimeVaryingParameter([3, 0.1], [PIECE_DURATION])
pop_lengths_max = TimeVaryingParameter([7, 1], [PIECE_DURATION])
pop_template_mix = TimeVaryingParameter([0.9, 0.1], [PIECE_DURATION], [-3])
pop_pitch_min = TimeVaryingParameter([20, 30], [PIECE_DURATION])
pop_pitch_max = TimeVaryingParameter([34, 100], [PIECE_DURATION])
pop_volume_min = TimeVaryingParameter([0.3, 0.6], [PIECE_DURATION])
pop_volume_max = TimeVaryingParameter([0.5, 1.0], [PIECE_DURATION])
pop_attack_time = TimeVaryingParameter([2, 0.01], [PIECE_DURATION], [-3])

chords = [[52, 57, 64], [52, 59, 67], [52, 61, 69]]
chord_handle = None
current_chord = None

if ANALYZE_POP_LOCATIONS:
    s.fast_forward()
    all_times = []
    all_values = []
else:
    pop_locations = [0.8, 3.64, 8.48, 15.5, 24.74, 27.2, 27.48, 29.18, 36.26, 39.48, 42.16, 45.48, 49.02, 50.76, 54.54, 57.28, 61.28, 64.46, 67.7, 69.76, 71.12, 74.3, 76.94, 79.18, 80.84, 82.36, 83.58, 86.06, 88.48, 89.78, 91.24, 92.7, 93.64, 95.7, 96.28, 97.92, 98.86, 100.3, 101.4, 102.44, 102.92, 104.0, 105.02, 105.84, 106.56, 107.34, 108.86, 109.64, 110.56, 111.36, 111.86, 113.32, 114.98, 117.2, 119.18, 119.96, 120.32, 121.1, 121.82, 122.16, 122.72, 123.08, 123.96, 124.52, 124.96, 125.32, 125.82, 126.2, 126.52, 127.02, 127.52, 127.88, 128.54, 129.12, 129.92, 130.72, 131.46, 132.12, 132.94, 133.38, 134.22, 134.94, 135.48, 135.9, 136.14, 136.64, 137.24, 137.5, 138.2, 138.54, 138.76, 139.64, 140.26, 141.02, 141.54, 141.86, 142.0, 142.46, 142.74, 143.2, 143.86, 144.6, 145.3, 145.56, 145.78, 146.32, 146.54, 146.86, 147.44, 147.9, 148.52, 149.06, 149.34, 149.76, 150.2, 150.78, 150.92, 151.16, 151.46, 151.7, 151.86, 152.2, 152.74, 153.2, 153.46, 153.88, 154.28, 154.54, 154.82, 155.26, 155.76, 156.52, 156.92, 157.8, 158.26, 158.9, 159.2, 159.56, 160.18, 160.68, 161.0, 161.4, 161.84, 162.12, 162.44, 162.82, 163.26, 163.64, 164.02, 164.48, 164.68, 164.84, 165.22, 165.46, 165.66, 165.98, 166.66, 166.82, 167.34, 167.64, 168.06, 168.38, 168.7, 168.94, 169.14, 169.54, 170.2, 170.5, 170.84, 171.14, 171.56, 171.76, 171.98, 172.5, 173.34, 173.88, 174.04, 174.24, 174.66, 175.32, 175.68, 176.06, 176.52, 176.76, 177.4, 177.66, 177.96, 178.12, 178.56, 179.04, 179.4, 179.9, 180.16, 180.68, 181.26, 181.48, 182.24, 182.72, 182.84, 183.06, 183.34, 183.68, 183.92, 184.14, 184.42, 184.54, 185.1, 185.42, 185.74, 185.94, 186.28, 186.68, 186.94, 187.38, 187.94, 188.48, 188.74, 189.34, 189.52, 189.74, 190.4, 190.86, 191.1, 191.3, 191.58, 191.8, 192.24, 192.66, 192.9, 193.24, 194.18, 194.46, 194.74, 195.12, 195.58, 195.94, 196.36, 196.56, 196.86, 197.4, 197.8, 197.86, 198.1, 198.52, 198.86, 199.08, 199.36, 199.64, 200.04, 200.36, 201.0, 201.36, 201.52, 201.88, 202.26, 202.58, 202.82, 203.12, 203.34, 203.5, 204.18, 204.56, 205.12, 205.44, 205.72, 206.1, 206.52, 206.9, 207.12, 207.34, 207.74, 207.88, 208.16, 208.74, 209.06, 209.36, 209.58, 209.8, 210.02, 210.14, 210.44, 210.72, 211.28, 211.52, 211.72, 212.02, 212.38, 212.72, 213.02, 213.44, 213.78, 214.0, 214.28, 214.78, 215.1, 215.58, 216.12, 216.46, 216.9, 217.12, 217.74, 218.0, 218.5, 218.7, 219.1, 219.48, 219.78, 219.98, 220.26, 220.58, 220.84, 221.02, 221.26, 221.46, 221.72, 222.06, 222.4, 222.7, 223.0, 223.26, 223.48, 223.84, 224.18, 224.72, 225.06, 225.56, 225.96, 226.52, 226.78, 227.08, 227.56, 228.04, 228.52, 228.84, 229.16, 229.36, 229.54, 229.82, 230.4, 230.68, 231.1, 231.46, 231.6, 232.1, 232.58, 232.84, 233.16, 233.4, 233.72, 234.22, 234.48, 235.02, 235.2, 235.48, 236.0, 236.24, 236.92, 237.38, 237.68, 237.86, 238.04, 238.32, 238.52, 238.94, 239.3, 239.64, 239.82, 240.2, 240.58, 240.82, 241.76, 242.14, 242.64, 243.0, 243.28, 243.52, 243.84, 244.22, 244.48, 244.94, 245.3, 245.54, 245.9, 246.26, 246.48, 246.78, 247.22, 248.06, 248.76, 249.1, 249.36, 249.82]


def do_pops():
    pop_schedule = []
    for t in pop_locations:
        dur = min(t, random.uniform(pop_lengths_min.value_at(t), pop_lengths_max.value_at(t)))
        pop_schedule.append((t - dur, dur))
    pop_schedule.sort(key=lambda x: x[0])
    current_time = 0
    for t, dur in pop_schedule:
        wait(t - current_time)
        current_time = t
        grav_player.play_note(random.uniform(pop_pitch_min(), pop_pitch_max()),
                              random.uniform(pop_volume_min(), pop_volume_max()),
                              dur,
                              {"param_backupDur": dur, "param_templateMix": pop_template_mix(),
                               "param_attackTime": pop_attack_time(), "param_decayTime": pop_attack_time()},
                              blocking=False)


if not ANALYZE_POP_LOCATIONS:
    fork(do_pops)

while s.time() < PIECE_DURATION:
    spiral_loc = position_on_spiral(arc_length(), 0.1)
    value = get_value_at(sharpness(), *spiral_loc)
    max_value = get_max_value_for_sharpness(sharpness())
    if ANALYZE_POP_LOCATIONS:
        all_times.append(s.time())
        all_values.append(value)

    which_chord = 0 if value < -max_value/5 else 1 if value < max_value/5 else 2
    # print(value, which_chord)
    if which_chord != current_chord:
        if chord_handle:
            chord_handle.end()
        chord_handle = cello.start_chord(chords[which_chord], 1.0)
        current_chord = which_chord
    wait(TIME_STEP)

# restructure so that the contour being pulled out is a separate script
# Fast bass line pitch-wise similar to what mariano did, but following the contour. Starts very fast, but slows down, gets heavier?
# put it into logic; get free trial

    # pitch = remap(value, 50, 90, -100, 100)
if ANALYZE_POP_LOCATIONS:
    import matplotlib.pyplot as plt
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import argrelextrema

    all_times = np.array(all_times)
    all_values = np.array(all_values)
    filtered = gaussian_filter1d(all_values, sigma=3)
    local_maxima = argrelextrema(filtered, np.greater)[0]

    plt.title("Original Data")
    plt.plot(all_times, all_values, label='Noisy Data', alpha=0.5)
    plt.plot(all_times[local_maxima], filtered[local_maxima],'rx', markersize=8, label='Local Maxima' )
    plt.legend()
    plt.show()

    print(f"pop_locations={list(all_times[local_maxima])}")

# Filtering a fixed sound (the drone?) with this curve (gets more shimmering)
# Could have the pitches be i-IV, moving back and forth according to low-passed version?
# Incorporating a noise element to the piece that samples the bands of the night sky to spectrums
# Is there a way to make it get sparser as it gets faster?
# Use the curve as a SOUND SOURCE
# Gnomic view radial spectrogram?
