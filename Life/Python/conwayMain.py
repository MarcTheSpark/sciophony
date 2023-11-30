import pygame
import numpy as np
from numpy.fft import fft2, ifft2
from dataclasses import dataclass
from entities import *
import math
import time
from global_settings import *
from pythonosc.udp_client import SimpleUDPClient


sc_osc_client = SimpleUDPClient("127.0.0.1", 57120)

# np.random.seed(5)

# Initialize Pygame
pygame.init()

# Set the width and height of the screen (width, height).
size = (GRID_SIZE[0] * SQUARE_SIZE, GRID_SIZE[1] * SQUARE_SIZE)

screen = pygame.display.set_mode(size)
pygame.display.set_caption("Conway's Game of Life")

count_down_to_pause = math.inf

# Loop until the user clicks the close button.
done = False

# Used to manage how fast the screen updates.
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

microscope_circle = pygame.image.load('Images/Microscope.png').convert_alpha()
microscope_circle = pygame.transform.scale(microscope_circle, (MICROSCOPE_RADIUS * SQUARE_SIZE * 2,
                                                               MICROSCOPE_RADIUS * SQUARE_SIZE * 2))
# Cell size
width, height = SQUARE_SIZE, SQUARE_SIZE
# Number of cells in each direction
cols, rows = GRID_SIZE

# Create a 2D array of cells
grid = np.zeros((rows, cols), dtype=int)

# Initialize grid randomly
grid[np.random.random((rows, cols)) > 0.9] = 1
# grid[5:10, 0:5] = Glider.masks[3]


entities = {EntityType: [] for EntityType in entity_types}


last_grid_drawn = None
grid_buffer = pygame.Surface(screen.get_size())


def draw_grid(grid):
    global last_grid_drawn
    if last_grid_drawn is None:
        # redraw the whole grid
        for row in range(rows):
            for col in range(cols):
                color = (90, 90, 60) if grid[row][col] == 0 else WHITE
                pygame.draw.rect(grid_buffer, color, [col * width, row * height, width, height])
    else:
        # we are updating an old grid, so only redraw what has changed
        updated_cells = np.where(grid != last_grid_drawn)
        for row, col in zip(*updated_cells):
            color = (90, 90, 60) if grid[row][col] == 0 else WHITE
            pygame.draw.rect(grid_buffer, color, [col * width, row * height, width, height])

    last_grid_drawn = grid
    screen.blit(grid_buffer, (0, 0))


def draw_entities():
    for entities_of_particular_type in entities.values():
        for entity in entities_of_particular_type:
            pygame.draw.rect(screen, entity.color, [entity.location[0] * width, entity.location[1] * height, width, height])


def draw_microscope_overlay():
    CORNER_TL = (SQUARE_SIZE * (MICROSCOPE_CENTER[0] - MICROSCOPE_RADIUS),
                 SQUARE_SIZE * (MICROSCOPE_CENTER[1] - MICROSCOPE_RADIUS))
    CORNER_BR = (SQUARE_SIZE * (MICROSCOPE_CENTER[0] + MICROSCOPE_RADIUS),
                 SQUARE_SIZE * (MICROSCOPE_CENTER[1] + MICROSCOPE_RADIUS))
    screen.blit(microscope_circle, CORNER_TL)  # Replace x_position and y_position with your coordinates
    pygame.draw.rect(screen, BLACK, [0, 0, CORNER_TL[0], size[1]])
    pygame.draw.rect(screen, BLACK, [0, 0, size[0], CORNER_TL[1]])
    pygame.draw.rect(screen, BLACK, [0, CORNER_BR[1], size[0], size[1] - CORNER_BR[1]])
    pygame.draw.rect(screen, BLACK, [CORNER_BR[0], 0, size[0] - CORNER_BR[0], size[1]])

def count_neighbors(grid):
    rows, cols = grid.shape
    neighbor_count = np.zeros((rows, cols), dtype=int)

    for i in [-1, 0, 1]:
        for j in [-1, 0, 1]:
            if i == 0 and j == 0:
                continue  # Skip the cell itself
            # Roll the grid and add to neighbor count
            neighbor_count += np.roll(np.roll(grid, i, axis=0), j, axis=1)

    return neighbor_count


def update_grid(grid):
    global count_down_to_pause
    count_down_to_pause -= 1

    new_grid = grid.copy()
    live_neighbors_grid = count_neighbors(grid > 0)
    
    # Masks for different conditions
    died_of_old_age = grid > 50
    alive = (grid > 0) & (grid <= 50)
    underpopulated_or_overpopulated = (live_neighbors_grid < 2) | (live_neighbors_grid > 3)
    reproduction = live_neighbors_grid == 3

    # Apply the rules
    new_grid[died_of_old_age] = 0
    new_grid[alive & underpopulated_or_overpopulated] = 0
    new_grid[alive & ~underpopulated_or_overpopulated] += 1
    new_grid[(grid == 0) & reproduction] = 1

    return new_grid

# -------- Analysis ---------


def fft_convolve2d(grid, kernel):
    grid = (grid > 0).astype(int)
    # Roll the kernel to center it at (0, 0)
    kernel_padded = np.zeros_like(grid)
    kernel_padded[:kernel.shape[0], :kernel.shape[1]] = kernel
    
    # FFT convolution
    grid_fft = fft2(grid)
    kernel_fft = fft2(kernel_padded)
    convolved = ifft2(grid_fft * kernel_fft.conjugate()).real

    return convolved


def get_mask_matches(grid, kernel, threshold_proportion=1, tolerance=1e-5):
    # Perform FFT-based convolution
    convolution_result = fft_convolve2d(grid, kernel)

    # Calculate the threshold
    threshold = threshold_proportion * np.sum(kernel)
    # Detect matches with tolerance
    match_indices = np.where(np.abs(convolution_result - threshold) < tolerance)

    # Convert indices to coordinates
    matches = list(zip(match_indices[0], match_indices[1]))  # (x, y) format
    return matches


def get_wrapped_slice(arr, x, y, w, h):
    rows, cols = arr.shape
    return arr[np.arange(x, x + w) % rows][:, np.arange(y, y + h) % cols]


def get_kernel_offset(kernel):
    # Find indices where value is greater than 1 or less than 0
    indices = np.argwhere((kernel > 1) | (kernel < 0))
    # Get the first such index, if any
    return indices[0] if len(indices) > 0 else (0, 0)


def get_perfect_matches(grid, kernel, threshold_proportion=1, tolerance=1e-5):
    """Detects matches that also match dark space, not just white. Also, adds the offset."""
    white_matches = get_mask_matches(grid > 0, kernel > 0, threshold_proportion=threshold_proportion, tolerance=tolerance)
    kernel_offset = get_kernel_offset(kernel)
    # for reasons I don't understand, the x and y here are flipped. :-/
    perfect_matches = [(int((y + kernel_offset[1]) % cols), int((x + kernel_offset[0]) % rows)) for x, y in white_matches if np.all((kernel > 0) == get_wrapped_slice(grid > 0, x, y, *kernel.shape))]
    return perfect_matches


def distance_mod_n(a, b, n):
    diff = abs(a - b) % n
    return min(diff, n - diff)


def update_entities(grid):    
    for EntityType, existing_entities_this_type in entities.items():
        new_and_continuing = []
        match_locations = [(which_mask, match_location)
                           for which_mask, mask in enumerate(EntityType.masks)
                           for match_location in get_perfect_matches(grid, mask)]
        for which_mask, match_location in match_locations:
            for existing_entity in reversed(existing_entities_this_type):
                # look for a match in the current entities list
                if distance_mod_n(existing_entity.location[0], match_location[0], cols) <= 1 and \
                   distance_mod_n(existing_entity.location[1], match_location[1], rows) <= 1:
                    # it's the same entity
                    existing_entities_this_type.remove(existing_entity)
                    new_and_continuing.append(existing_entity)
                    existing_entity.location = match_location
                    existing_entity.mask_match = which_mask
                    existing_entity.continue_playing()
                    break
            else:
                # no match in the entities list
                new_entity = EntityType(match_location, mask_match=which_mask)
                new_and_continuing.append(new_entity)
                new_entity.start_playing()
        
        # Old entities that have not been shifted to new_and_continuing should be ended
        for entity in entities[EntityType]:
            entity.stop_playing()
        entities[EntityType] = new_and_continuing


def get_mean_activity_heights(grid):
    # Calculating the mean row for each column where there are ones
    mean_rows = []
    for column in grid.T:  # Transpose the array to iterate over columns
        rows_with_ones = np.where(column[::-1] > 0)[0]  # Find the indices of rows with ones
        if len(rows_with_ones) > 0:
            mean_row = np.mean(rows_with_ones)
        else:
            mean_row = 0  # In case there are no ones in the column
        mean_rows.append(mean_row)
    return mean_rows


def get_visible_grid_mask(buffer=1):
    """Returns the portion of the grid that is visible in the microscope circle"""
    # Create an empty grid with the same dimensions as GRID_SIZE
    y, x = np.ogrid[:GRID_SIZE[1], :GRID_SIZE[0]]
    # Calculate the square of the distance from each point to the MICROSCOPE_CENTER
    distance_squared = (x - MICROSCOPE_CENTER[0])**2 + (y - MICROSCOPE_CENTER[1])**2

    return (distance_squared < ((MICROSCOPE_RADIUS + 1)**2)).astype(int)

visibility_mask = get_visible_grid_mask()

# -------- Main Program Loop -----------
sc_osc_client.send_message("/shells/start", None)

# # START PROFILING
import cProfile, pstats, io
from pstats import SortKey
pr = cProfile.Profile()
pr.enable()

while not done:
    # --- Main event loop
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            for instrument in s.instruments:
                instrument.end_all_notes()
            done = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # Add your logic here for what happens when the spacebar is pressed
                if count_down_to_pause != math.inf:
                    count_down_to_pause = math.inf
                else:
                    count_down_to_pause = 0
            elif event.key == pygame.K_1:
                grid[:, :] = 0
                grid[np.random.random((rows, cols)) > 0.9] = 1
            elif event.key == pygame.K_RIGHTBRACKET:
                count_down_to_pause += 1
            elif event.key == pygame.K_BACKSLASH:
                start = time.perf_counter()
                print(get_mask_matches(grid, box))
                print(time.perf_counter() - start)

    if count_down_to_pause:
        # --- Game logic should go here
        grid = update_grid(grid)
        update_entities(grid * visibility_mask)

    # --- Drawing code should go here
    draw_grid(grid * visibility_mask)
    draw_entities()
    draw_microscope_overlay()

    # --- Go ahead and update the screen with what we've drawn.
    pygame.display.flip()

    # --- Send info to shell granulator
    column_activities = [int(x) for x in np.sum(grid > 0, axis=0)]
    sc_osc_client.send_message("/shells/activity", column_activities)
    activity_heights = [float(x) for x in get_mean_activity_heights(grid)]
    sc_osc_client.send_message("/shells/heights", activity_heights)

    # --- Limit to 10 frames per second
    clock.tick(FRAMERATE)

sc_osc_client.send_message("/shells/stop", None)

for instrument in s.instruments:
    instrument.end_all_notes()
# Close the window and quit.
pygame.quit()

# # STOP AND PRINT PROFILING
# Open a file for writing the profiling results
with open('profiling_output.txt', 'w') as file:
    sortby = SortKey.TIME
    ps = pstats.Stats(pr, stream=file).sort_stats(sortby)

    # Print the stats directly to the file
    ps.print_stats()

print("Profiling results saved to 'profiling_output.txt'")
