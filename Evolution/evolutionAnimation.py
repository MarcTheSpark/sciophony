import dataclasses

import numpy as np
import pygame
from scamp_extensions.utilities import TimeVaryingParameter
from evolution_marc_on_thread import s, EvolutionMusic
from save_vals import SaveVals
import math

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

# Constants for X thickness
MIN_DISTURBANCE_WIDTH = 2  # Minimum X thickness
MAX_DISTURBANCE_WIDTH = 10  # Maximum X thickness


def draw_part_filled_box(surface, x, y, size, filled_portion, state, opacity=1):
    """
    Draws a box partially filled from the bottom up according to the filled_portion and the state.

    Parameters:
    - surface: The surface to draw the box onto
    - x, y: Top-left position of the box on the surface
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

    # Draw the filled portion (bottom-up) on the surface
    filled_rect = pygame.Rect(x, y + size - filled_height, size, filled_height)
    pygame.draw.rect(surface, fill_color, filled_rect)

    # Draw the outline on the surface
    pygame.draw.rect(surface, outline_color, (x, y, size, size), int(outline_thickness))


def draw_box_array(x_norm, y_norm, width_norm, active_array, fill_array, playing_indices, max_per_row, opacity=1,
                   rotate=0):
    """
    Draws an array of square boxes and rotates the entire array while keeping the top-left corner anchored.

    Parameters:
    - x_norm, y_norm: Normalized starting position of the array (0 to 1, proportional to WIDTH/HEIGHT)
    - width_norm: Normalized total width of the array (0 to 1, proportional to WIDTH)
    - active_array: List of binary values (1 for active, 0 for inactive)
    - fill_array: List of filled portions (values from 0 to 1) for each box
    - playing_indices: Indices of currently playing boxes
    - max_per_row: Maximum number of boxes per row
    - opacity: Float (0 to 1) indicating the opacity level of the box
    - rotate: Float value for the rotation in radians (applied to the whole array)
    """
    # Determine the number of boxes
    num_boxes = len(active_array)

    # Calculate total width for the boxes in one row and size of each square box
    total_width = width_norm * WIDTH
    box_size = total_width / min(max_per_row, num_boxes)  # Ensure boxes are square

    # Calculate starting position based on normalized values
    x_start = x_norm * WIDTH
    y_start = y_norm * HEIGHT

    # Create an intermediate surface for the box array
    array_width = total_width
    array_height = box_size * ((num_boxes + max_per_row - 1) // max_per_row)  # Calculate height based on rows
    box_surface = pygame.Surface((array_width, array_height), pygame.SRCALPHA)

    # Draw each box onto the intermediate surface
    for i in range(num_boxes):
        # Determine the row and column of the box
        row = i // max_per_row
        col = i % max_per_row

        # Calculate the x and y positions for the current box on the surface
        x_pos = col * box_size
        y_pos = row * box_size

        # Determine the state of the box
        if active_array[i] == 1:
            if i in playing_indices:
                state = "playing active"
            else:
                state = "active"
        else:
            if i in playing_indices:
                state = "playing inactive"
            else:
                state = "inactive"

        # Draw the box with appropriate filled portion onto the surface
        draw_part_filled_box(box_surface, x_pos, y_pos, box_size, fill_array[i], state, opacity)

    # If rotation is not zero, rotate the surface while keeping the top-left corner anchored
    if rotate != 0:
        # Rotate the surface
        rotated_surface = pygame.transform.rotate(box_surface, -rotate * 180 / np.pi)  # Convert radians to degrees

        # Adjust the x and y positions by the offset to keep the top-left corner anchored
        screen.blit(rotated_surface, (x_start - box_surface.get_height() * math.sin(rotate), y_start))
    else:
        # If no rotation, just blit the surface directly
        screen.blit(box_surface, (x_start, y_start))


def overlay_exes_on_box(x_norm, y_norm, width_norm, ex_array, playing_indices, max_per_row):
    """
    Draws a series of red Xs on top of the box array. The thickness of each X is determined by the ex_array values.

    Parameters:
    - x_norm, y_norm: Normalized starting position of the array (0 to 1, proportional to WIDTH/HEIGHT)
    - width_norm: Normalized total width of the array (0 to 1, proportional to WIDTH)
    - ex_array: Numpy array with values from 0 to 1, determining whether and how thick the X should be
    - playing_indices: Index of currently playing boxes, which makes the X twice as thick
    - max_per_row: Maximum number of boxes per row
    """
    # Determine the number of boxes
    num_boxes = len(ex_array)

    # Calculate total width and size of each square box
    total_width = width_norm * WIDTH
    box_size = total_width / min(max_per_row, num_boxes)  # Ensure boxes are square

    # Calculate starting position based on normalized values
    x_start = x_norm * WIDTH
    y_start = y_norm * HEIGHT

    # Draw each X
    for i in range(num_boxes):
        # Only draw an X if ex_array[i] > 0
        if ex_array[i] > 0:
            # Determine the row and column of the box
            row = i // max_per_row
            col = i % max_per_row

            # Calculate the x and y positions for the current box
            x_pos = x_start + col * box_size
            y_pos = y_start + row * box_size

            # Determine the thickness of the X based on ex_array[i]
            thickness = MIN_DISTURBANCE_WIDTH + ex_array[i] * (MAX_DISTURBANCE_WIDTH - MIN_DISTURBANCE_WIDTH)

            # Double the thickness if it's the playing index
            if i in playing_indices:
                thickness *= 2
                x_pos -= box_size * 0.1
                y_pos -= box_size * 0.1
                box_size *= 1.2

            # Draw the X with the calculated thickness
            draw_x_on_box(x_pos, y_pos, box_size, thickness)


def draw_x_on_box(x, y, size, thickness):
    """
    Draws a red X on top of a box at the given position with the specified thickness.

    Parameters:
    - x, y: Top-left position of the box
    - size: Size of the square box
    - thickness: Thickness of the X lines
    """
    color = (255, 0, 0)  # Red color for the X

    # Draw the two diagonal lines that form the X
    draw_line_round_corners_polygon(screen, (x, y), (x + size, y + size), color, int(thickness))
    draw_line_round_corners_polygon(screen, (x, y + size), (x + size, y), color, int(thickness))


def draw_line_round_corners_polygon(surf, p1, p2, c, w):
    p1v = pygame.math.Vector2(p1)
    p2v = pygame.math.Vector2(p2)
    lv = (p2v - p1v).normalize()
    lnv = pygame.math.Vector2(-lv.y, lv.x) * w // 2
    pts = [p1v + lnv, p2v + lnv, p2v - lnv, p1v - lnv]
    pygame.draw.polygon(surf, c, pts)
    pygame.draw.circle(surf, c, p1, round(w / 2))
    pygame.draw.circle(surf, c, p2, round(w / 2))


def draw_text_on_box_array(x_norm, y_norm, width_norm, active_array, texts, playing_indices, max_per_row, font_size=20,
                           opacity=1.0):
    """
    Draws centered text on each box in the array with adjustable opacity. The color of the text depends on whether the box is active, playing, or inactive.

    Parameters:
    - x_norm, y_norm: Normalized starting position of the array (0 to 1, proportional to WIDTH/HEIGHT)
    - width_norm: Normalized total width of the array (0 to 1, proportional to WIDTH)
    - active_array: A list or array of 1s and 0s indicating if the box is active (1) or inactive (0)
    - texts: A list of text strings to display on each box (one or two characters each)
    - playing_indices: List of indices where boxes are currently playing
    - max_per_row: Maximum number of boxes per row
    - font_size: Font size for the text
    - opacity: A value between 0 and 1 that determines the opacity of the text (1 is fully opaque, 0 is fully transparent)
    """
    # Determine the number of boxes
    num_boxes = len(active_array)

    # Calculate total width and size of each square box
    total_width = width_norm * WIDTH
    box_size = total_width / min(max_per_row, num_boxes)  # Ensure boxes are square

    # Calculate starting position based on normalized values
    x_start = x_norm * WIDTH
    y_start = y_norm * HEIGHT

    # Set up the font
    font = pygame.font.SysFont(None, font_size)

    # Clamp opacity value between 0 and 1
    opacity = max(0, min(1, opacity))
    alpha_value = int(opacity * 255)  # Convert opacity to alpha (0-255)

    # Draw each text
    for i in range(num_boxes):
        # Determine the row and column of the box
        row = i // max_per_row
        col = i % max_per_row

        # Calculate the x and y positions for the current box
        x_pos = x_start + col * box_size
        y_pos = y_start + row * box_size

        # Get the text for the current box
        text = texts[i]

        # Determine the color based on the box's state
        if i in playing_indices:
            color = (0, 0, 255)  # Blue for playing
        elif active_array[i] == 1:
            color = (0, 0, 0)  # Black for active
        else:
            color = (169, 169, 169)  # Grey for inactive

        # Render the text on a separate surface
        text_surface = font.render(text, True, color)

        # Convert the surface to support alpha transparency
        text_surface = text_surface.convert_alpha()

        # Set the opacity (alpha) value
        text_surface.fill((255, 255, 255, alpha_value), special_flags=pygame.BLEND_RGBA_MULT)

        # Center the text on the box
        text_rect = text_surface.get_rect(center=(x_pos + box_size // 2, y_pos + box_size // 2))

        # Blit the text onto the screen
        screen.blit(text_surface, text_rect)


def draw_pc_voice_leading_chart(x_center_norm, y_norm, genes, playing_indices_first_bar, playing_indices_second_bar,
                                width_norm=0.038, x_spread=0.07, opacity=1):
    draw_box_array(x_center_norm - x_spread, y_norm, width_norm, genes[:12][::-1], genes[24:36][::-1],
                   playing_indices_first_bar,  # only highlight if it's not a preimage
                   1, opacity=opacity)
    draw_box_array(x_center_norm + x_spread - width_norm, y_norm, width_norm, genes[12:24][::-1], genes[36:48][::-1],
                   playing_indices_second_bar,  # only highlight if it's not a preimage
                   1, opacity=opacity)

    active_pitches = tuple(a or b for a, b in zip(genes[:12][::-1], genes[12:24][::-1]))

    draw_text_on_box_array(x_center_norm - 0.019, 0.1, 0.038, active_pitches,
                           ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"][::-1],
                           playing_indices_first_bar | playing_indices_second_bar, 1,
                           font_size=50, opacity=opacity)


music = EvolutionMusic(daemon=True)
music.start()


class GenotypeGridDrawing(np.ndarray):
    def __new__(cls, position, width, opacity, rotate=0.):
        data = np.array([*position, width, opacity, rotate], dtype=float)
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

    @property
    def rotate(self):
        return float(self[4])

    def __repr__(self):
        return (f"{self.__class__.__name__}(position={self.position}, "
                f"width={self.width}, opacity={self.opacity})")

    def __str__(self):
        return self.__repr__()


ROTATION_START = 610
ROTATION_DUR = 14
BEAT_FADE_DUR = 7
PC_CHART_FADE_START = 625  # Note: Changing this messing things up!
PC_CHART_FADE_DUR = 10

beat_boxes = {
    "kick": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.06, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.06, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.06, 0.1), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.06, 0.1), 0.26, 0))
    ),
    "snare": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.37, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.37, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.37, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.37, 0.1), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.37, 0.1), 0.26, 0))
    ),
    "hihat": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.68, 0.36), 0.26, 1)),
        (40, GenotypeGridDrawing((0.68, 0.36), 0.26, 1), 2),
        (50, GenotypeGridDrawing((0.68, 0.22), 0.26, 1), -2),
        (60, GenotypeGridDrawing((0.68, 0.1), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.68, 0.1), 0.26, 0))
    ),
    "kick_bass": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (56, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (60, GenotypeGridDrawing((0.06, 0.6), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.6), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
    ),
    "snare_piano": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.37, 0.6), 0.26, 0)),
        (128, GenotypeGridDrawing((0.37, 0.6), 0.26, 0)),
        (132, GenotypeGridDrawing((0.37, 0.6), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.6), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.37, 0.6), 0.26, 0)),
    ),
    "hihat_sax": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((0.06, 0.6), 0.26, 0)),
        (188, GenotypeGridDrawing((0.68, 0.6), 0.26, 0)),
        (192, GenotypeGridDrawing((0.68, 0.6), 0.26, 1)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.6), 0.26, 1)),
        (ROTATION_START + BEAT_FADE_DUR, GenotypeGridDrawing((0.68, 0.6), 0.26, 0)),
    ),
}

pieces = [
    # LEFT
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1), 0.228, 0, rotate=math.pi / 2))
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.23 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),

    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.23 + 0.07, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.23 + 0.07, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.23 + 0.07, 0.1), 0.228, 0, rotate=math.pi / 2)),
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.06, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.23 + 0.07, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.23 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.23 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),
    ),
    # MIDDLE
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1), 0.228, 0, rotate=math.pi / 2))
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),

    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 + 0.07, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.5 + 0.07, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.5 + 0.07, 0.1), 0.228, 0, rotate=math.pi / 2)),
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.37, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 + 0.07, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.5 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.5 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),
    ),
    # RIGHT
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1), 0.228, 0, rotate=math.pi / 2))
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.77 - 0.07 + 0.038, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),

    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 2 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.77 + 0.07, 0.1), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.77 + 0.07, 0.1), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.77 + 0.07, 0.1), 0.228, 0, rotate=math.pi / 2)),
    ),
    TimeVaryingParameter.from_points(
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 0)),
        (ROTATION_START, GenotypeGridDrawing((0.68, 0.1 + 3 * 0.26/6 * WIDTH/HEIGHT), 0.26, 1)),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.77 + 0.07, 0.1 + 0.038 * 6 * WIDTH/HEIGHT), 0.228, 1, rotate=math.pi/2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR / 2, GenotypeGridDrawing((0.77 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 1, rotate=math.pi / 2)),
        (PC_CHART_FADE_START + PC_CHART_FADE_DUR, GenotypeGridDrawing((0.77 + 0.07, 0.1 + 0.038 * 6 * WIDTH / HEIGHT), 0.228, 0, rotate=math.pi / 2)),
    ),
]


ending_opacity = TimeVaryingParameter([0, 0, 1], [PC_CHART_FADE_START, 10])
saved_values = SaveVals.load_from_json("saved_vals.json")

last_playing_index = 0
# Main loop
running = True
while running:
    s.rouse_and_hold()
    s.release_from_suspension()
    # Fill the background
    screen.fill((255, 255, 255))  # White background

    playing_index = int(s.beat() // 0.5) % 24
    new_cycle = last_playing_index != playing_index == 0

    for piece in pieces:
        current_drawing = piece()
        if current_drawing.opacity > 0:
            draw_box_array(*current_drawing.position, current_drawing.width, (0,) * 6, (0,) * 6,
                           [],  # only highlight if it's not a preimage
                           6, opacity=current_drawing.opacity, rotate=current_drawing.rotate)

    for gene_box, gene_box_drawing_info in beat_boxes.items():
        current_drawing = gene_box_drawing_info()
        if current_drawing.opacity > 0:
            if gene_box in music.playing_individuals:
                active_array = music.playing_individuals[gene_box].genotype_array[:24]

                if gene_box in saved_values.values_by_situation:
                    if new_cycle:
                        saved_values.consume(gene_box, how_many=24)
                    mask = saved_values.read(gene_box, how_many=24)

                    active_array = tuple(int(a and b) for a, b in zip(active_array, mask))
                fill_array = music.playing_individuals[gene_box].genotype_array[24:48]
                preimage = None
            elif f"{gene_box}_preimage" in saved_values.values_by_situation:
                preimage = saved_values.read(f"{gene_box}_preimage")[0]
                active_array = preimage[:24]
                if gene_box in saved_values.values_by_situation:
                    mask = saved_values.read(gene_box, how_many=24)
                    active_array = tuple(int(a and b) for a, b in zip(active_array, mask))
                fill_array = preimage[24:48]
            else:
                continue

            draw_box_array(*current_drawing.position, current_drawing.width, active_array, fill_array,
                           [] if preimage is not None else [playing_index],  # only highlight if it's not a preimage
                           6, opacity=current_drawing.opacity)

            if np.any(music.disturbances):
                dist_copy = music.disturbances.copy()
                dist_copy[playing_index + 1:] = 0
                overlay_exes_on_box(*current_drawing.position, current_drawing.width,
                                    dist_copy, [playing_index], 6)

    if "snare_harmony" in music.playing_individuals:
        genes = music.playing_individuals["snare_harmony"].genotype_array
        if new_cycle:
            saved_values.consume("harmony_voices")
        voices, change_points = saved_values.read("harmony_voices")[0]

        playing_indices_first_bar = set()
        playing_indices_second_bar = set()
        for pitch_pair, changes in zip(voices, change_points):
            if changes[0] <= playing_index < changes[1] and pitch_pair[0] is not None:
                playing_indices_first_bar.add(11 - pitch_pair[0] % 12)
            elif playing_index >= changes[1] and pitch_pair[1] is not None:
                playing_indices_second_bar.add(11 - pitch_pair[1] % 12)

        draw_pc_voice_leading_chart(0.5, 0.1, genes, playing_indices_first_bar, playing_indices_second_bar, opacity=ending_opacity())

    if "kick_end" in music.playing_individuals:
        genes = music.playing_individuals["kick_end"].genotype_array
        if new_cycle:
            saved_values.consume("bass_pitches_end")
        bass_pitches = saved_values.read("bass_pitches_end")[0]

        draw_pc_voice_leading_chart(0.23, 0.1, genes,
                                    {11 - bass_pitches[0]} if bass_pitches[0] is not None and bass_pitches[0] <= playing_index < 12 else set(),
                                    {11 - bass_pitches[1]} if bass_pitches[1] is not None and 12 + bass_pitches[1] <= playing_index else set(),
                                    opacity=ending_opacity())

    if "hihat_marimba" in music.playing_individuals:
        genes = music.playing_individuals["hihat_marimba"].genotype_array
        if new_cycle:
            saved_values.consume("end_arpeggio_pitches")
        arpeggio_pitches = saved_values.read("end_arpeggio_pitches")[0]

        draw_pc_voice_leading_chart(0.77, 0.1, genes,
                                    {11 - arpeggio_pitches[playing_index] % 12} if playing_index < 12 and arpeggio_pitches[playing_index] is not None else set(),
                                    {11 - arpeggio_pitches[playing_index] % 12} if playing_index >= 12 and arpeggio_pitches[playing_index] is not None else set(),
                                    opacity=ending_opacity())

    last_playing_index = playing_index

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Update the display
    pygame.display.flip()

# Quit pygame
pygame.quit()


