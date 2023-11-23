import pygame
import numpy as np
from numpy.fft import fft2, ifft2
from dataclasses import dataclass
from entities import *
import math
import time


# np.random.seed(5)

# Initialize Pygame
pygame.init()

# Set the width and height of the screen (width, height).
size = (720, 720)

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


# Cell size
width, height = 20, 20
# Number of cells in each direction
cols, rows = size[0] // width, size[1] // height

# Create a 2D array of cells
grid = np.zeros((rows, cols), dtype=int)

# Initialize grid randomly
grid[np.random.random((rows, cols)) > 0.94] = 1

entities = {EntityType: [] for EntityType in entity_types}


def draw_grid():
    for row in range(rows):
        for col in range(cols):
            color = BLACK if grid[row][col] == 0 else WHITE
            pygame.draw.rect(screen, color, [col * width, row * height, width, height])

    for entities_of_particular_type in entities.values():
        for entity in entities_of_particular_type:
            pygame.draw.rect(screen, entity.color, [entity.location[0] * width, entity.location[1] * height, width, height])


def update_grid():
    global grid, count_down_to_pause
    count_down_to_pause -= 1
    new_grid = grid.copy()
    for row in range(rows):
        for col in range(cols):
            # Count live neighbors
            live_neighbors = sum([grid[(row + i) % rows][(col + j) % cols] > 0 
                                  for i in range(-1, 2) 
                                  for j in range(-1, 2) 
                                  if (i != 0 or j != 0)])
            if grid[row][col] > 50:
                pass
#                 new_grid[row][col] = 0
            elif grid[row][col] > 0:
                if live_neighbors < 2 or live_neighbors > 3:
                    new_grid[row][col] = 0
                else:
                    new_grid[row][col] = grid[row][col] + 1
            else:
                if live_neighbors == 3:
                    new_grid[row][col] = 1
    grid = new_grid
            

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
    perfect_matches = [(y + kernel_offset[1], x + kernel_offset[0]) for x, y in white_matches if np.all((kernel > 0) == get_wrapped_slice(grid > 0, x, y, *kernel.shape))]
    return perfect_matches


# def find_entities():
#     entities_list.clear()
#     for EntityType in entity_types:
#         for mask in EntityType.masks:
#             for match_location in get_perfect_matches(grid, mask):
#                 entities_list.append(EntityType(match_location))


def update_entities():    
    for EntityType, existing_entities_this_type in entities.items():
        new_and_continuing = []
        match_locations = [match_location for mask in EntityType.masks
                           for match_location in get_perfect_matches(grid, mask)]
        for match_location in match_locations:
            for existing_entity in reversed(existing_entities_this_type):
                # look for a match in the current entities list
                if abs(existing_entity.location[0] - match_location[0] <= 1) and \
                   abs(existing_entity.location[1] - match_location[1] <= 1):
                    # it's the same entity
                    existing_entities_this_type.remove(existing_entity)
                    new_and_continuing.append(existing_entity)
                    existing_entity.location = match_location
                    existing_entity.continue_playing()
                    break
            else:
                # no match in the entities list
                new_entity = EntityType(match_location)
                new_and_continuing.append(new_entity)
                new_entity.start_playing()
        
        # Old entities that have not been shifted to new_and_continuing should be ended
        for entity in entities[EntityType]:
            entity.stop_playing()
        entities[EntityType] = new_and_continuing
                
                
# -------- Main Program Loop -----------
while not done:
    # --- Main event loop
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # Add your logic here for what happens when the spacebar is pressed
                if count_down_to_pause != math.inf:
                    count_down_to_pause = math.inf
                else:
                    count_down_to_pause = 0
            elif event.key == pygame.K_SLASH:
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
        update_grid()
        
        # start = time.perf_counter()
        update_entities()
        # print(time.perf_counter() - start)


    # --- Screen-clearing code goes here
    screen.fill(BLACK)

    # --- Drawing code should go here
    draw_grid()

    # --- Go ahead and update the screen with what we've drawn.
    pygame.display.flip()

    # --- Limit to 10 frames per second
    clock.tick(15)

# Close the window and quit.
pygame.quit()
