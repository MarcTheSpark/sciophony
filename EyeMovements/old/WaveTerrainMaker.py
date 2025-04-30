import numpy as np
import soundfile as sf
from scipy.io.wavfile import write
from scipy.signal import get_window
from scipy.ndimage import rotate
import math
import random
import matplotlib.pyplot as plt


class SourceSound:
    def __init__(self, filepath):
        # Load sound file and convert to mono if needed
        self.data, self.samplerate = sf.read(filepath)
        if self.data.ndim > 1:  # If stereo, downmix to mono
            self.data = self.data.mean(axis=1)

    def get_grain(self, dur, window_function="hann"):
        # Calculate number of samples for the grain
        num_samples = int(dur * self.samplerate)
        
        # Extract a random section of the audio (grain)
        start_idx = np.random.randint(0, len(self.data) - num_samples)
        grain = self.data[start_idx:start_idx + num_samples]

        # Apply windowing function
        window = get_window(window_function, num_samples)
        grain *= window

        return grain


class WaveTerrain:
    def __init__(self, width, height):
        # Initialize the terrain array with zeros
        self.terrain = np.zeros((height, width))

    def _get_cosine_squared_envelope(self, size):
        """Generate a 2D cosine-squared envelope that goes to zero at the edges."""
        y, x = np.ogrid[:size, :size]
        center = size // 2
        radius = center

        # Create a radial distance array from the center
        dist_from_center = np.sqrt((x - center) ** 2 + (y - center) ** 2)

        # Apply cos^2 window: it's 1 at the center and smoothly goes to 0 at the edges
        envelope = np.cos(np.pi * dist_from_center / (2 * radius)) ** 2
        envelope[dist_from_center >= radius] = 0  # Set values beyond radius to 0

        return envelope

    def paint_grain(self, grain, x, y, theta=0):
        """Paint a square grain at (x, y) with a cosine-squared envelope and rotation by theta."""
        grain_len = len(grain)
        grain_size = grain_len  # Make the grain square by setting width equal to the grain length

        # Prepare a 2D array to represent the square grain
        grain_2d = np.tile(grain, (grain_size, 1))

        # Apply the cosine-squared envelope
        envelope = self._get_cosine_squared_envelope(grain_size)
        grain_2d *= envelope

        # Rotate the grain by the specified angle
        grain_2d_rotated = rotate(grain_2d, theta, reshape=False)

        # Apply the rotated grain to the terrain at the specified coordinates
        self._apply_grain(grain_2d_rotated, x, y)

    def _apply_grain(self, grain_2d, x, y):
        """Overlay the grain onto the terrain at (x, y) with boundary handling."""
        grain_height, grain_width = grain_2d.shape
        terrain_height, terrain_width = self.terrain.shape

        # Calculate the coordinates for the top-left corner in the terrain
        x_start = x - grain_width // 2
        y_start = y - grain_height // 2

        # Determine the overlapping region in the terrain
        terrain_x_min = max(x_start, 0)
        terrain_x_max = min(x_start + grain_width, terrain_width)
        terrain_y_min = max(y_start, 0)
        terrain_y_max = min(y_start + grain_height, terrain_height)

        # Determine the corresponding region in the grain
        grain_x_min = max(-x_start, 0)
        grain_x_max = grain_x_min + (terrain_x_max - terrain_x_min)
        grain_y_min = max(-y_start, 0)
        grain_y_max = grain_y_min + (terrain_y_max - terrain_y_min)

        # Overlay the grain section onto the terrain section
        self.terrain[terrain_y_min:terrain_y_max, terrain_x_min:terrain_x_max] += grain_2d[grain_y_min:grain_y_max, grain_x_min:grain_x_max]


    def show(self):
        """Display the terrain as an image."""
        plt.figure(figsize=(10, 10))
        plt.imshow(self.terrain, cmap='gray', origin='lower')
        plt.colorbar(label="Amplitude")
        plt.title("Wave Terrain Visualization with Cosine-Squared Envelope")
        plt.show()
        
    def save_to_wav(self, filename, sample_rate=44100):
        """Save the 2D terrain to a mono .wav file."""
        # Flatten the terrain row-by-row according to SuperCollider's indexing convention
        flattened_terrain = self.terrain.flatten('C')  # Row-major (C-style) flattening
        
        # Normalize the audio to the range [-1.0, 1.0]
        max_amplitude = np.max(np.abs(flattened_terrain))
        if max_amplitude > 0:
            normalized_terrain = flattened_terrain / max_amplitude
        else:
            normalized_terrain = flattened_terrain  # Avoid division by zero if terrain is all zeros
        
        # Convert to 32-bit float format (common for audio processing)
        normalized_terrain = np.float32(normalized_terrain)

        # Write to the wav file
        write(filename, sample_rate, normalized_terrain)
        print(f"Terrain saved to {filename} at {sample_rate} Hz.")


# Load sound file
source1 = SourceSound("waterpipe.mp3")
source2 = SourceSound("hardrain.wav")
source3 = SourceSound("xylophone.wav")
terrain = WaveTerrain(width=4000, height=4000)

for _ in range(100):
    grain = random.choice([source3]).get_grain(0.06, "hann")
    terrain.paint_grain(grain, x=random.randint(0, 4000), y=random.randint(0, 4000),
                        theta=random.uniform(0, 360))

# Access the terrain data
terrain.show()
terrain.save_to_wav("GeneratedTerrain2.wav")
