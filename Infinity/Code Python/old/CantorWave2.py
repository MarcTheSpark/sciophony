import matplotlib.pyplot as plt
import numpy as np
from scipy.io.wavfile import write
import math

LENGTH = 50
SAMPLE_RATE = 48000
DEPTH =  int(math.log(LENGTH * SAMPLE_RATE, 3))



def rescale_to_range(arr, new_min, new_max):  # ChatGPT
    min_val = np.min(arr)
    max_val = np.max(arr)
    scaled_arr = (arr - min_val) / (max_val - min_val) * (new_max - new_min) + new_min
    return scaled_arr


x = np.linspace(0, 1, SAMPLE_RATE * LENGTH)


ys = []

for k in range(1, DEPTH + 1):
    y = np.sin(3 ** k * np.pi * x) / (k + 1)
    if ys:
        y[ys[-1] <= 0] = 0
    ys.append(y)
#     plt.ylim(-1, 1)
#     plt.plot(x, y)
#     plt.show()

y_sum = np.sum([ys[:5]], axis = 1)[0]
pitch_wave = rescale_to_range(y_sum, 50, 90)
volume_wave = rescale_to_range(y_sum, 0.4, 1.0)

from scamp import *

s = Session()

clarinet = s.new_part("clarinet")

while True:
    samp = int(s.time() % LENGTH * SAMPLE_RATE)
    clarinet.play_note(pitch_wave[samp], volume_wave[samp], 0.1)
