import dataclasses

import numpy as np
import pygame
from scamp_extensions.utilities import TimeVaryingParameter
from evolution_marc_on_thread import s, EvolutionMusic


# Initialize pygame
pygame.init()

# Set up display
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Partially Filled Box Array")

# Define global constants for colors
COLOR_INACTIVE = (200, 200, 200)  # Light Grey
COLOR_ACTIVE = (0, 0, 0)  # Black
COLOR_PLAYING_INACTIVE = (100, 100, 100)  # Dark grey
COLOR_PLAYING_ACTIVE = (0, 0, 255)  # Blue


# Function to draw a partially filled box
def draw_part_filled_box(x, y, size, filled_portion, state, opacity=1):
    """
    Draws a box partially filled from the bottom up according to the filled_portion and the state.

    Parameters:
    - x, y: Top-left position of the box
    - size: Size of the square box (width and height are the same)
    - filled_portion: Fraction (0 to 1) indicating how much of the box should be filled
    - state: Can be "inactive", "active", or "playing" to determine the fill and outline color
    - opacity: Float (0 to 1) indicating the opacity level of the box
    """
    opacity = int(opacity * 255)
    # Set the color based on the state
    if state == "playing active":
        outline_color = fill_color = COLOR_PLAYING_ACTIVE
    elif state == "playing inactive":
        outline_color = COLOR_PLAYING_INACTIVE
        fill_color = COLOR_INACTIVE
    elif state == "active":
        outline_color = fill_color = COLOR_ACTIVE
    else:
        outline_color = fill_color = COLOR_INACTIVE

    # Add the opacity (alpha channel) to the colors
    fill_color = (*fill_color[:3], opacity)  # (R, G, B, A)
    outline_color = (*outline_color[:3], opacity)  # (R, G, B, A)

    # Calculate outline thickness proportional to the box size
    outline_thickness = max(1, size // 10)

    # Calculate the height of the filled portion
    filled_height = size * filled_portion

    # Create a temporary surface for the box with per-pixel alpha
    box_surface = pygame.Surface((size, size), pygame.SRCALPHA)

    # Draw the filled portion (bottom-up) on the surface
    filled_rect = pygame.Rect(0, size - filled_height, size, filled_height)
    pygame.draw.rect(box_surface, fill_color, filled_rect)

    # Draw the outline on the surface
    pygame.draw.rect(box_surface, outline_color, (0, 0, size, size), int(outline_thickness))

    # Blit the surface with alpha onto the main screen
    screen.blit(box_surface, (x, y))


# Function to draw an array of boxes
def draw_box_array(x_norm, y_norm, width_norm, active_array, fill_array, playing_index, max_per_row, opacity=1):
    """
    Draws an array of square boxes based on the given parameters.

    Parameters:
    - x_norm, y_norm: Normalized starting position of the array (0 to 1, proportional to WIDTH/HEIGHT)
    - width_norm: Normalized total width of the array (0 to 1, proportional to WIDTH)
    - active_array: List of binary values (1 for active, 0 for inactive)
    - fill_array: List of filled portions (values from 0 to 1) for each box
    - playing_index: Index of the currently playing box
    - max_per_row: Maximum number of boxes per row
    - opacity: Float (0 to 1) indicating the opacity level of the box
    """
    # Determine the number of boxes
    num_boxes = len(active_array)

    # Calculate total width for the boxes in one row and size of each square box
    total_width = width_norm * WIDTH
    box_size = total_width / min(max_per_row, num_boxes)  # Ensure boxes are square

    # Calculate starting position based on normalized values
    x_start = x_norm * WIDTH
    y_start = y_norm * HEIGHT

    # Draw each box
    for i in range(num_boxes):
        # Determine the row and column of the box
        row = i // max_per_row
        col = i % max_per_row

        # Calculate the x and y positions for the current box
        x_pos = x_start + col * box_size
        y_pos = y_start + row * box_size

        # Determine the state of the box
        if active_array[i] == 1:
            if i == playing_index:
                state = "playing active"
            else:
                state = "active"
        else:
            if i == playing_index:
                state = "playing inactive"
            else:
                state = "inactive"

        # Draw the box with appropriate filled portion
        draw_part_filled_box(x_pos, y_pos, box_size, fill_array[i], state, opacity)


music = EvolutionMusic(daemon=True)
music.start()


class GenotypeGridDrawing(np.ndarray):
    def __new__(cls, position, width, opacity):
        data = np.array([*position, width, opacity], dtype=float)
        obj = np.asarray(data).view(cls)
        return obj

    @property
    def position(self):
        return tuple(float(x) for x in self[:2])

    @property
    def width(self):
        return float(self[2])

    @property
    def opacity(self):
        return float(self[3])

    def __repr__(self):
        return (f"{self.__class__.__name__}(position={self.position}, "
                f"width={self.width}, opacity={self.opacity})")

    def __str__(self):
        return self.__repr__()


beat_boxes = {
    "kick": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.06, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.06, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.06, 0.1), 0.26, 1))
    ),
    "snare": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.37, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.37, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.37, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.37, 0.1), 0.26, 1))
    ),
    "hihat": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.68, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.68, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.68, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.68, 0.1), 0.26, 1))
    ),
    "kick_bass": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (60, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (64, GenotypeGridDrawing((0.06, 0.6), 0.26, 1)),
    ),
    "snare_piano": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.37, 0.6), 0.26, 0)),
        (132, GenotypeGridDrawing((0.37, 0.6), 0.26, 0)),
        (136, GenotypeGridDrawing((0.37, 0.6), 0.26, 1)),
    ),
    "hihat_sax": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (192, GenotypeGridDrawing((0.68, 0.6), 0.26, 0)),
        (196, GenotypeGridDrawing((0.68, 0.6), 0.26, 1)),
    )
}

active_overrides = {
    "snare_piano": [[0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1], [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0], [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0], [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0]],
}

beat_y_pos = TimeVaryingParameter([0.38, 0.38, 0.22, 0.06], [40, 10, 10], [0, 2, -2])
kick_bass_opacity = TimeVaryingParameter([0, 0, 1], [60, 4])
snare_piano_opacity = TimeVaryingParameter([0, 0, 1], [132, 4])
hihat_sax_opacity = TimeVaryingParameter([0, 0, 1], [192, 4])
s.fast_forward_to_beat(80)

last_playing_index = 0
# Main loop
running = True
while running:
    s.rouse_and_hold()
    s.release_from_suspension()
    # Fill the background
    screen.fill((255, 255, 255))  # White background

    playing_index = (s.beat() // 0.5) % 24
    for gene_box in music.playing_individuals:
        current_drawing: GenotypeGridDrawing = beat_boxes[gene_box]()
        if current_drawing.opacity > 0:
            if gene_box in active_overrides and len(active_overrides[gene_box]) > 0:
                active_array = active_overrides[gene_box].pop(0) if last_playing_index != playing_index == 0 else active_overrides[gene_box][0]
            else:
                active_array = music.playing_individuals[gene_box].genotype_array[:24]

            fill_array = music.playing_individuals[gene_box].genotype_array[24:48]
            draw_box_array(*current_drawing.position, current_drawing.width, active_array, fill_array, playing_index,
                           6, opacity=current_drawing.opacity)
    last_playing_index = playing_index

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Update the display
    pygame.display.flip()

# Quit pygame
pygame.quit()


