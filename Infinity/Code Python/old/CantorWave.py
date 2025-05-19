import matplotlib.pyplot as plt
import numpy as np
from scipy.io.wavfile import write
import math

LENGTH = 10
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

for top_sum in range(1, len(ys) + 1):
    y_sum = np.sum([ys[:top_sum]], axis = 1)[0]
    wave = rescale_to_range(y_sum, -0.9, 0.9)
    write(f'CantorWaves/wave{top_sum}.wav', SAMPLE_RATE, wave)
    plt.plot(x, wave)
    plt.show()


