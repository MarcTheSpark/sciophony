import pygame
import numpy as np
import math
import time

# Initialize Pygame
pygame.init()

# Set the width and height of the screen (width, height).
size = (1280, 720)
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
YELLOW = (255, 255, 0)


# Cell size
width, height = 20, 20
# Number of cells in each direction
cols, rows = size[0] // width, size[1] // height

# Create a 2D array of cells
grid = np.zeros((rows, cols), dtype=int)

# Initialize grid randomly
grid[np.random.random((rows, cols)) > 0.9] = 1


def draw_grid():
    entities = [x for x in find_entities(grid) if 2 < len(x) < 10]
    entities_peeps = sum(entities, start=[])
    for row in range(rows):
        for col in range(cols):
            color = BLACK if grid[row][col] == 0 else YELLOW if (row, col) in entities_peeps else WHITE
            pygame.draw.rect(screen, color, [col * width, row * height, width, height])


def update_grid():
    global grid, count_down_to_pause
    if not count_down_to_pause:
        return
    count_down_to_pause -= 1
    new_grid = grid.copy()
    for row in range(rows):
        for col in range(cols):
            # Count live neighbors
            live_neighbors = sum([grid[(row + i) % rows][(col + j) % cols] 
                                  for i in range(-1, 2) 
                                  for j in range(-1, 2) 
                                  if (i != 0 or j != 0)])
            if grid[row][col] == 1:
                if live_neighbors < 2 or live_neighbors > 3:
                    new_grid[row][col] = 0
            else:
                if live_neighbors == 3:
                    new_grid[row][col] = 1
    grid = new_grid


# -------- Analysis ---------

def is_valid_cell(grid, row, col, visited):
    return (0 <= row < len(grid) and 0 <= col < len(grid[0]) and 
            not visited[row][col] and grid[row][col] == 1)

def dfs(grid, row, col, visited, entity):
    # Directions for adjacent cells (8 directions including diagonals)
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
    visited[row][col] = True
    entity.append((row, col))

    for dr, dc in directions:
        new_row, new_col = row + dr, col + dc
        if is_valid_cell(grid, new_row, new_col, visited):
            dfs(grid, new_row, new_col, visited, entity)

def find_entities(grid):
    visited = [[False for _ in range(len(grid[0]))] for _ in range(len(grid))]
    entities = []

    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if grid[row][col] == 1 and not visited[row][col]:
                entity = []
                dfs(grid, row, col, visited, entity)
                entities.append(entity)

    return entities


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
                print(find_entities(grid))
                print(time.perf_counter() - start)


    # --- Game logic should go here
    update_grid()

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
