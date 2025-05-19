from cantor_tempo_utils import get_metronome_subdivisions, get_tempo_tripling_dur
from itertools import accumulate
import pygame

LINE_IMG = "line_images/DashedLine.png"
GRID_DEPTH = 3
MIN_LINE_WIDTH = 2
MAX_LINE_WIDTH = 15

tripling_time = get_tempo_tripling_dur(scaling_factor=2.4092913453966096)

grids_by_heirarchy = [
    tuple(accumulate(get_metronome_subdivisions(2, i, scaling_factor=2.4092913453966096)))
    for i in range(GRID_DEPTH)
]

grids_by_heirarchy.insert(0, grids_by_heirarchy[0][2::3])


# thin out so that each grid doesn't contain the previous subdivision
grids_by_heirarchy = grids_by_heirarchy[:1] + [
    tuple(x for x in this_grid if x not in last_grid)
    for last_grid, this_grid in zip(grids_by_heirarchy, grids_by_heirarchy[1:])
]

# Initialize pygame
pygame.init()
clock = pygame.time.Clock()


WIDTH, HEIGHT = 1920, 1080
ASPECT = WIDTH / HEIGHT
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cantor Visualization")

dashed_line_image = pygame.image.load(LINE_IMG).convert_alpha()


current_time = 0


def t_to_x(t, time_at_left=None, width_duration=tripling_time):
    if time_at_left is None:
        time_at_left = current_time
    return (t - time_at_left) * WIDTH / width_duration
    

def blit_dashed_line(screen, dashed_line_image, x, width, opacity):
    # Stretch the image horizontally based on the width (for line thickness)
    stretched_image = pygame.transform.scale(dashed_line_image, (width, HEIGHT))
    
    # Set opacity (alpha)
    stretched_image.set_alpha(opacity)
    
    # Blit the image onto the screen at the x position
    screen.blit(stretched_image, (x, 0))
    

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    screen.fill((0, 0, 0))  # White background
    mod_current_time = current_time % tripling_time # tripling_time - 0.01 if current_time % 2 < 1 else 0
    progress = mod_current_time / tripling_time
    for i, grid in enumerate(grids_by_heirarchy[::-1]):
        for grid_line in grid:
            x_pos = t_to_x(grid_line, time_at_left=mod_current_time)
            opacity = 255 * (i + 1 - progress) / len(grids_by_heirarchy)

            thickness_factor = (3 ** (i-progress)) / 3 ** GRID_DEPTH
            line_thickness = MIN_LINE_WIDTH + (MAX_LINE_WIDTH - MIN_LINE_WIDTH) * thickness_factor

            blit_dashed_line(screen, dashed_line_image, x_pos - line_thickness / 2, line_thickness, opacity)
    
    pygame.display.flip()
    current_time += clock.tick(60) / 3000

    
