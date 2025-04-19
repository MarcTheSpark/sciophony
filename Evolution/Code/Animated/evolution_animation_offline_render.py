"""
Offline rendering version of the animation script; which saves frames to the given folder. Assembled these frames
with ffmpeg.
"""

import pygame
from scamp_extensions.utilities import ceil_to_multiple
from evolution_recording_player import s, EvolutionMusicRecordingPlayer
from evolution_species import *
import math
import pathlib

SAVE_FRAMES_FOLDER = "vidframes"
FPS = 60

current_dir = pathlib.Path(__file__).parent
snapshots_file = current_dir.joinpath("recorded_snapshots.pk")
music = EvolutionMusicRecordingPlayer(snapshots_file, daemon=True)
music.delete_fast_forwards(shift_to_zero=True)
# music.print_snapshot_report(100)
music.delete_beat_ranges((516, 528), (744, 792), (924, 972))

# Initialize pygame
pygame.init()

# Set up display
WIDTH, HEIGHT = 1920, 1080
ASPECT = WIDTH / HEIGHT
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Evolution animation")

# Define global constants for colors
COLOR_INACTIVE = (230, 230, 230)  # Light Grey
COLOR_ACTIVE = (0, 0, 0)  # Black
COLOR_PLAYING_INACTIVE = (100, 100, 100)  # Dark grey
COLOR_PLAYING_ACTIVE_INST = (255, 221, 85)  # Yellow
COLOR_PLAYING_ACTIVE = (0, 0, 255)  # Blue

HIGHLIGHT_IMAGE_FADE_HALFLIFE = 0.3

PLAYING_ACTIVE_EXPANSION_FACTOR = 1.2
PLAYING_INACTIVE_EXPANSION_FACTOR = 1

ROW_START = 0.1
ROW_WIDTH = 0.9
SQR_WIDTH = ROW_WIDTH / 24
SQR_HEIGHT = SQR_WIDTH * ASPECT
FINAL_DRUM_WIDTH = 0.9
FINAL_DRUM_SQR_HEIGHT = FINAL_DRUM_WIDTH / 24 * ASPECT

# Constants for X thickness
MIN_DISTURBANCE_WIDTH = 2  # Minimum X thickness
MAX_DISTURBANCE_WIDTH = 10  # Maximum X thickness

EQUAL_VOLUME = np.full(24, 0.7)


def draw_part_filled_box(surface, x, y, size, strength, state, opacity=1, is_inst=False):
    """
    Draws a box partially filled from the bottom up according to the filled_portion and the state.

    Parameters:
    - surface: The surface to draw the box onto
    - x, y: Top-left position of the box on the surface
    - size: Size of the square box (width and height are the same)
    - strength: Fraction (0 to 1) indicating how much of the box should be filled
    - state: Can be "inactive", "active", or "playing" to determine the fill and outline color
    - opacity: Float (0 to 1) indicating the opacity level of the box
    - is_inst: an instrument, not a drum, and therefore highlights yellow
    """
    opacity = int(opacity * 255)
    # Set the color based on the state
    if state == "playing active":
        outline_color = fill_color = COLOR_PLAYING_ACTIVE if is_inst else COLOR_PLAYING_ACTIVE
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
    filled_height = size * strength

    # Draw the filled portion (bottom-up) on the surface
    filled_rect = pygame.Rect(x, y + size - filled_height, size, filled_height)
    pygame.draw.rect(surface, fill_color, filled_rect)

    # Draw the outline on the surface
    pygame.draw.rect(surface, outline_color, (x, y, size, size), int(outline_thickness))


def draw_always_filled_box(surface, x, y, size, strength, state, opacity=1, is_inst=False):
    """
    Draws a box fully filled.

    Parameters:
    - surface: The surface to draw the box onto
    - x, y: Top-left position of the box on the surface
    - size: Size of the square box (width and height are the same)
    - strength: Fraction (0 to 1) indicating how much of the box should be filled
    - state: Can be "inactive", "active", or "playing" to determine the fill and outline color
    - opacity: Float (0 to 1) indicating the opacity level of the box
    - is_inst: an instrument, not a drum, and therefore highlights yellow
    """
    opacity = int(opacity * 255)
    # Set the color based on the state
    if state == "playing active":
        outline_color = fill_color = COLOR_PLAYING_ACTIVE if is_inst else COLOR_PLAYING_ACTIVE
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
    filled_height = size if "active" in state else 0

    # Draw the filled portion (bottom-up) on the surface
    filled_rect = pygame.Rect(x, y + size - filled_height, size, filled_height)
    pygame.draw.rect(surface, fill_color, filled_rect)

    # Draw the outline on the surface
    # pygame.draw.rect(surface, outline_color, (x, y, size, size), int(outline_thickness))


def draw_circle_box(surface, x, y, size, strength, state, opacity=1, is_inst=False):
    """
    Draws a circle instead of a box with strength indicated by radius.

    Parameters:
    - surface: The surface to draw the box onto
    - x, y: Top-left position of the box on the surface
    - size: Size of the square box (width and height are the same)
    - strength: Fraction (0 to 1) indicating how much of the box should be filled
    - state: Can be "inactive", "active", or "playing" to determine the fill and outline color
    - opacity: Float (0 to 1) indicating the opacity level of the box
    - is_inst: an instrument, not a drum, and therefore highlights yellow
    """
    opacity = int(opacity * 255)
    # Set the color based on the state
    if state == "playing active":
        outline_color = fill_color = COLOR_PLAYING_ACTIVE_INST if is_inst else COLOR_PLAYING_ACTIVE
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

    circle_radius = (0.25 + 0.75 * strength) * size / 2 / 1.2

    if state == "playing active":
        circle_radius *= PLAYING_ACTIVE_EXPANSION_FACTOR
    elif state == "playing inactive":
        circle_radius *= PLAYING_INACTIVE_EXPANSION_FACTOR

    # Draw the filled portion (bottom-up) on the surface
    pygame.draw.circle(surface, fill_color, (x + size/2, y + size / 2), circle_radius)

    # # Draw the outline on the surface
    # arc_rect = pygame.Rect(x + size/2 - circle_radius, y + size/2 - circle_radius, circle_radius * 2, circle_radius * 2)
    # pygame.draw.arc(surface, outline_color, arc_rect, 0, math.tau, int(outline_thickness))


draw_box = draw_circle_box


def draw_box_array(x_norm, y_norm, width_norm, active_array, fill_array, playing_indices, max_per_row, opacity=1,
                   rotate=0, anchor="corner", is_inst=False):
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
    - anchor: where x_norm and y_norm specify
    - is_inst: an instrument, not a drum, and therefore highlights yellow
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
        draw_box(box_surface, x_pos, y_pos, box_size, fill_array[i], state, opacity, is_inst)

    # If rotation is not zero, rotate the surface while keeping the top-left corner anchored
    if rotate != 0:
        # Rotate the surface
        rotated_surface = pygame.transform.rotate(box_surface, -rotate * 180 / np.pi)  # Convert radians to degrees

        # Adjust the x and y positions by the offset to keep the top-left corner anchored
        blit_pos = (x_start - rotated_surface.get_width() / 2, y_start - rotated_surface.get_height() / 2) \
            if anchor == "center" else (x_start - box_surface.get_height() * math.sin(rotate), y_start)
        screen.blit(rotated_surface, blit_pos)
    else:
        # If no rotation, just blit the surface directly
        screen.blit(box_surface, (x_start - array_width / 2 * (anchor == "center"), y_start - array_height / 2 * (anchor == "center")))


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


def get_food_environment_surface(x_norm_cycle_start, x_norm_cycle_end, food_array,
                                 color, height_norm=1/3, draw_indices=None):
    surf = pygame.Surface((WIDTH, height_norm * HEIGHT), pygame.SRCALPHA)
    rect_width = (x_norm_cycle_end - x_norm_cycle_start) / 24 * WIDTH
    cycle_start_x = x_norm_cycle_start * WIDTH
    i = -math.ceil(cycle_start_x / rect_width)
    while (left := cycle_start_x + i * rect_width) < WIDTH:
        if draw_indices is not None and i not in draw_indices:
            i += 1
            continue
        pygame.draw.rect(surf, tuple(color) + (int(200 * food_array[i % 24]),), pygame.Rect(left, 0, rect_width, surf.get_height()))
        i += 1
    return surf


food_surface1 = get_food_environment_surface(ROW_START, ROW_START + ROW_WIDTH, beat_strengths, (50, 200, 25), draw_indices=range(24))
food_surface2 = get_food_environment_surface(ROW_START, ROW_START + ROW_WIDTH, snare_beat_strengths, (50, 200, 25), draw_indices=range(24))


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
                           opacity=1.0, is_inst=False):
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
            color = COLOR_PLAYING_ACTIVE_INST if is_inst else COLOR_PLAYING_ACTIVE
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
                                width_norm=0.038, x_spread=0.07, opacity=1, is_inst=True):
    draw_box_array(x_center_norm - x_spread, y_norm, width_norm, genes[:12][::-1], EQUAL_VOLUME,
                   playing_indices_first_bar,  # only highlight if it's not a preimage
                   1, opacity=opacity, is_inst=is_inst)
    draw_box_array(x_center_norm + x_spread - width_norm, y_norm, width_norm, genes[12:24][::-1], EQUAL_VOLUME,
                   playing_indices_second_bar,  # only highlight if it's not a preimage
                   1, opacity=opacity, is_inst=is_inst)

    active_pitches = tuple(a or b for a, b in zip(genes[:12][::-1], genes[12:24][::-1]))

    draw_text_on_box_array(x_center_norm - 0.019, y_norm, 0.038, active_pitches,
                           ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"][::-1],
                           playing_indices_first_bar | playing_indices_second_bar, 1,
                           font_size=50, opacity=opacity, is_inst=is_inst)


class HighlightImage:
    def __init__(self, image_path, highlight_image_path, center_x, center_y, width, height=None,
                 fade_half_life=HIGHLIGHT_IMAGE_FADE_HALFLIFE, highlight_amount=0, surface=screen, anchor=None, opacity=1):
        # Load the images
        self.image = pygame.image.load(image_path).convert_alpha()
        self.highlight_image = pygame.image.load(highlight_image_path).convert_alpha()

        # Store screen-related parameters
        self._center_x = center_x
        self._center_y = center_y
        self.anchor = anchor
        self.opacity = opacity
        self.width = width
        self.height = height if height else (self.image.get_height() / self.image.get_width() *
                                             surface.get_width() / surface.get_height() * width)
        self.surface = surface

        # Initialize highlight fading parameters
        self.fade_half_life = fade_half_life
        self.highlight_amount = highlight_amount

        # Scale images to the given size
        self.image = pygame.transform.smoothscale(self.image, (int(self.width * self.surface.get_width()), int(self.height * self.surface.get_height())))
        self.highlight_image = pygame.transform.smoothscale(self.highlight_image, (int(self.width * self.surface.get_width()), int(self.height * self.surface.get_height())))

    @property
    def center_x(self):
        if self.anchor:
            return beat_boxes[self.anchor]().position[0] + self._center_x
        else:
            return self._center_x

    @property
    def center_y(self):
        if self.anchor:
            return beat_boxes[self.anchor]().position[1] + self._center_y
        else:
            return self._center_y

    def draw(self, dt):
        if self.anchor:
            self.opacity = beat_boxes[self.anchor]().opacity
        # Get the position and size to draw the image
        screen_width, screen_height = self.surface.get_size()
        pos_x = int(self.center_x * screen_width - self.image.get_width() / 2)
        pos_y = int(self.center_y * screen_height - self.image.get_height() / 2)

        # Draw the base image
        image_surface = self.image.copy()
        image_surface.set_alpha(int(self.opacity * 255))
        self.surface.blit(image_surface, (pos_x, pos_y))

        # Update highlight amount using exponential decay based on dt and fade_half_life
        decay_factor = math.pow(2, -(dt / 1000) / self.fade_half_life)
        self.highlight_amount *= decay_factor

        # If highlight_amount is below threshold, do not draw the overlay
        if self.highlight_amount >= 0.01:
            # Create a transparent version of the highlight image
            highlight_surface = self.highlight_image.copy()
            highlight_surface.set_alpha(int(self.highlight_amount * 255 * self.opacity))

            # Draw the highlight image with adjusted opacity
            self.surface.blit(highlight_surface, (pos_x, pos_y))


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
                f"width={self.width}, opacity={self.opacity}, rotate={self.rotate})")

    def __str__(self):
        return self.__repr__()


ROTATION_START = 550
ROTATION_DUR = 20
BEAT_FADE_DUR = 7
PC_CHART_STRINGS_FADE_IN_START = ROTATION_START + ROTATION_DUR  # Note: Changing this messing things up!
PC_CHART_MALLETS_FADE_IN_START = PC_CHART_STRINGS_FADE_IN_START + 18
PC_CHART_BASS_FADE_IN_START = PC_CHART_MALLETS_FADE_IN_START + 25
PC_CHART_FADE_IN_DUR = 8

PC_CHART_MALLETS_FADE_OUT_START = 768
PC_CHART_MALLETS_FADE_OUT_DUR = 24
PC_CHART_BASS_FADE_OUT_START = 792
PC_CHART_BASS_FADE_OUT_DUR = 24
PC_CHART_STRINGS_FADE_OUT_START = 816
PC_CHART_STRINGS_FADE_OUT_DUR = 5

FINAL_DRUM_ROTATE_START = 822
FINAL_DRUM_ROTATE_DUR = 28

FINAL_DRUM_FADE_OUT_START = 894
FINAL_DRUM_FADE_OUT_DUR = 30

END_BEAT = 936

# Ensure that the rotation finishes on the start of a cycle
# FINAL_DRUM_ROTATE_START = ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12) - FINAL_DRUM_ROTATE_DUR


dashed_line = pygame.image.load("images/DashLine.png").convert_alpha()

highlight_images = {
    "kick": HighlightImage("images/kick.png", "images/kickOn.png", -0.05, SQR_HEIGHT / 2, 0.07, anchor="kick"),
    "snare": HighlightImage("images/snare.png", "images/snareOn.png", -0.05, SQR_HEIGHT / 2, 0.04, anchor="snare"),
    "hihat": HighlightImage("images/hihat.png", "images/hihatOn.png", -0.05, SQR_HEIGHT / 2, 0.04, anchor="hihat"),
    "kick_bass": HighlightImage("images/bass.png", "images/bassOn.png", -0.05, SQR_HEIGHT / 2, 0.07, anchor="kick_bass"),
    "snare_piano": HighlightImage("images/piano.png", "images/pianoOn.png", -0.05, SQR_HEIGHT / 2, 0.07, anchor="snare_piano"),
    "hihat_sax": HighlightImage("images/synth.png", "images/synthOn.png", -0.05, SQR_HEIGHT / 2, 0.04, anchor="hihat_sax"),
}

extra_highlight_images = {
    "bass": HighlightImage("images/bass.png", "images/bassOn.png", 0.23, 0.065, 0.07),
    "violin": HighlightImage("images/violin.png", "images/violinOn.png", 0.5, 0.065, 0.07),
    "mallet": HighlightImage("images/mallet.png", "images/malletOn.png", 0.77, 0.065, 0.07),
}

beat_boxes = {
    "kick": TimeVaryingParameter.from_points(
        (4, GenotypeGridDrawing((ROW_START, 4/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (12, GenotypeGridDrawing((ROW_START, 4 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (64, GenotypeGridDrawing((ROW_START, 4/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), 2),
        (74, GenotypeGridDrawing((ROW_START, 3/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), -2),
        (84, GenotypeGridDrawing((ROW_START, 2/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 2/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 2/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "snare": TimeVaryingParameter.from_points(
        (16, GenotypeGridDrawing((ROW_START, 12/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (24, GenotypeGridDrawing((ROW_START, 12/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (46, GenotypeGridDrawing((ROW_START, 12/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (136, GenotypeGridDrawing((ROW_START, 12/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), 2),
        (146, GenotypeGridDrawing((ROW_START, 11/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), -2),
        (156, GenotypeGridDrawing((ROW_START, 10/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 10/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 10/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "hihat": TimeVaryingParameter.from_points(
        (28, GenotypeGridDrawing((ROW_START, 20/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (36, GenotypeGridDrawing((ROW_START, 20/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (196, GenotypeGridDrawing((ROW_START, 20/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), 2),
        (206, GenotypeGridDrawing((ROW_START, 19/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1), -2),
        (216, GenotypeGridDrawing((ROW_START, 18/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 18/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 18/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "kick_bass": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((ROW_START, 6/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (78, GenotypeGridDrawing((ROW_START, 6/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (84, GenotypeGridDrawing((ROW_START, 6/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 6/24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 6/24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "snare_piano": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((ROW_START, 14 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (152, GenotypeGridDrawing((ROW_START, 14 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (156, GenotypeGridDrawing((ROW_START, 14 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 14 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 14 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "hihat_sax": TimeVaryingParameter.from_points(
        (0, GenotypeGridDrawing((ROW_START, 22 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (212, GenotypeGridDrawing((ROW_START, 22 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
        (216, GenotypeGridDrawing((ROW_START, 22 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START, 22 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 1)),
        (ROTATION_START - 1, GenotypeGridDrawing((ROW_START, 22 / 24 - SQR_HEIGHT / 2), ROW_WIDTH, 0)),
    ),
    "all_drums": TimeVaryingParameter.from_points(
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12),
         GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 2, 0.5 - FINAL_DRUM_SQR_HEIGHT / 2), FINAL_DRUM_WIDTH, 0)),
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12),
         GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 2, 0.5 - FINAL_DRUM_SQR_HEIGHT / 2), FINAL_DRUM_WIDTH, 1)),
        (FINAL_DRUM_FADE_OUT_START,
         GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 2, 0.5 - FINAL_DRUM_SQR_HEIGHT / 2), FINAL_DRUM_WIDTH, 1)),
        (FINAL_DRUM_FADE_OUT_START + FINAL_DRUM_FADE_OUT_DUR,
         GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 2, 0.5 - FINAL_DRUM_SQR_HEIGHT / 2), FINAL_DRUM_WIDTH, 0)),
    )
}

pieces = {  # Note: these are drawn with anchor = "center"
    "snareA": TimeVaryingParameter.from_points(
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START + ROW_WIDTH / 4, 10 / 24), ROW_WIDTH / 2, 0)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START + ROW_WIDTH / 4, 10 / 24), ROW_WIDTH / 2, 1)),
        (ROTATION_START, GenotypeGridDrawing((ROW_START + ROW_WIDTH / 4, 10 / 24), ROW_WIDTH / 2, 1), 2),
        (ROTATION_START + ROTATION_DUR/2, GenotypeGridDrawing(position=(0.387, 0.476), width=0.453, opacity=1.0, rotate=-math.pi/4), -2),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (ROTATION_START + ROTATION_DUR + PC_CHART_FADE_IN_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (ROTATION_START + ROTATION_DUR + PC_CHART_FADE_IN_DUR + 1, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 0, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START - PC_CHART_FADE_IN_DUR - 1, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 0, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START - PC_CHART_FADE_IN_DUR, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START, GenotypeGridDrawing((0.5 - 0.07 + 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2), 2),
        (FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR / 2, GenotypeGridDrawing(position=(0.362, 0.5176666666666667), width=0.453, opacity=1.0, rotate=-math.pi / 4), -2),
        (FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 1, rotate=0)),
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12), GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 1, rotate=0)),
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12) + 1, GenotypeGridDrawing((0.5 - FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 0, rotate=0)),
    ),
    "snareB": TimeVaryingParameter.from_points(
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START + ROW_WIDTH * 3 / 4, 10 / 24), ROW_WIDTH / 2, 0)),
        (ROTATION_START - BEAT_FADE_DUR, GenotypeGridDrawing((ROW_START + ROW_WIDTH * 3 / 4, 10 / 24), ROW_WIDTH / 2, 1)),
        (ROTATION_START, GenotypeGridDrawing((ROW_START + ROW_WIDTH * 3 / 4, 10 / 24), ROW_WIDTH / 2, 1), 2),
        (ROTATION_START + ROTATION_DUR / 2, GenotypeGridDrawing((0.663, 0.476), width=0.453, opacity=1.0, rotate=-math.pi/4), -2),
        (ROTATION_START + ROTATION_DUR, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (ROTATION_START + ROTATION_DUR + PC_CHART_FADE_IN_DUR, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (ROTATION_START + ROTATION_DUR + PC_CHART_FADE_IN_DUR + 1, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 0, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START - PC_CHART_FADE_IN_DUR - 1, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 0, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START - PC_CHART_FADE_IN_DUR, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2)),
        (FINAL_DRUM_ROTATE_START, GenotypeGridDrawing((0.5 + 0.07 - 0.038 / 2, 0.13 + 0.038 * ASPECT * 6), 0.228 * 2, 1, rotate=-math.pi / 2), 2),
        (FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR / 2, GenotypeGridDrawing(position=(0.638, 0.5176666666666667), width=0.453, opacity=1.0, rotate=-math.pi / 4), -2),
        (FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, GenotypeGridDrawing((0.5 + FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 1, rotate=0)),
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12), GenotypeGridDrawing((0.5 + FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 1, rotate=0)),
        (ceil_to_multiple(FINAL_DRUM_ROTATE_START + FINAL_DRUM_ROTATE_DUR, 12) + 1, GenotypeGridDrawing((0.5 + FINAL_DRUM_WIDTH / 4, 0.5), FINAL_DRUM_WIDTH / 2, 0, rotate=0)),
    )
}

# FOR CALCULATING THE INTERMEDIATE POSITION
# print(pieces["snareA"].value_at(ROTATION_START + ROTATION_DUR / 2))
# print(pieces["snareB"].value_at(ROTATION_START + ROTATION_DUR / 2))

strings_pc_chart_opacity = TimeVaryingParameter.from_points(
    (0, 0), (PC_CHART_STRINGS_FADE_IN_START, 0), (PC_CHART_STRINGS_FADE_IN_START + PC_CHART_FADE_IN_DUR, 1),
    (PC_CHART_STRINGS_FADE_OUT_START, 1), (PC_CHART_STRINGS_FADE_OUT_START + PC_CHART_STRINGS_FADE_OUT_DUR, 0))

bass_pc_chart_opacity = TimeVaryingParameter.from_points(
    (0, 0), (PC_CHART_BASS_FADE_IN_START, 0), (PC_CHART_BASS_FADE_IN_START + PC_CHART_FADE_IN_DUR, 1),
    (PC_CHART_BASS_FADE_OUT_START, 1), (PC_CHART_BASS_FADE_OUT_START + PC_CHART_BASS_FADE_OUT_DUR, 0))

mallets_pc_chart_opacity = TimeVaryingParameter.from_points(
    (0, 0), (PC_CHART_MALLETS_FADE_IN_START, 0), (PC_CHART_MALLETS_FADE_IN_START + PC_CHART_FADE_IN_DUR, 1),
    (PC_CHART_MALLETS_FADE_OUT_START, 1), (PC_CHART_MALLETS_FADE_OUT_START + PC_CHART_MALLETS_FADE_OUT_DUR, 0))

bg_opacity = TimeVaryingParameter([1, 1, 0], [ROTATION_START - ROTATION_DUR, ROTATION_DUR])
play_line_opacity = TimeVaryingParameter([0, 0, 1, 1, 0], [0.5, 6.5, ROTATION_START - ROTATION_DUR - 7, ROTATION_DUR])


clock = pygame.time.Clock()

last_playing_index = 0
# Main loop
running = True


def fill_bg():
    """
    Blit the background before drawing each frame.
    """
    screen.fill((255, 255, 255))  # White background
    if (bg_op := bg_opacity()) > 0:
        if bg_op < 1:
            faded_food_surface1 = food_surface1.copy()
            faded_food_surface2 = food_surface2.copy()
            faded_food_surface1.set_alpha(int(bg_op * 255))
            faded_food_surface2.set_alpha(int(bg_op * 255))
        else:
            faded_food_surface1 = food_surface1
            faded_food_surface2 = food_surface2
        screen.blit(faded_food_surface1, (0, 0))
        screen.blit(faded_food_surface2, (0, HEIGHT / 3))
        screen.blit(faded_food_surface1, (0, HEIGHT * 2 / 3))


def draw_dashed_time_indicator():
    if (bg_op := play_line_opacity()) > 0:
        dashed_line.set_alpha(int(bg_op * 255))
        line_x = WIDTH * (ROW_START + smooth_playing_index * SQR_WIDTH) - dashed_line.get_width() / 2
        screen.blit(dashed_line, (line_x, 0))


def draw_ephemera():
    """
    Draws the ephemeral chunks that the beat is broken up into as it rotates to be vertical at the end.
    """
    for piece_name, piece in pieces.items():
        current_drawing = piece()
        if current_drawing.opacity > 0:
            gene_box = piece_name[:-1]
            piece_start_index = 0 if piece_name[-1] == "A" else 12
            genotype_array = np.array(music.playing_individuals[gene_box].genotype_array)
            if s.beat() > FINAL_DRUM_ROTATE_START:
                strength_fade = min(max((s.beat() - FINAL_DRUM_ROTATE_START) / FINAL_DRUM_ROTATE_DUR, 0), 1)
                genotype_array[24:] = (1 - strength_fade) * EQUAL_VOLUME + strength_fade * genotype_array[:24]
            else:
                strength_fade = min(max((s.beat() - ROTATION_START) / ROTATION_DUR, 0), 1)
                genotype_array[24:] = (1 - strength_fade) * genotype_array[24:] + strength_fade * EQUAL_VOLUME
            strengths = genotype_array[piece_start_index + 24: piece_start_index + 36]
            active = genotype_array[piece_start_index: piece_start_index + 12]

            draw_box_array(*current_drawing.position, current_drawing.width, active, strengths,
                           [], 12, opacity=current_drawing.opacity, rotate=current_drawing.rotate,
                           anchor="center")


def draw_beat_boxes():
    """
    Draws the main beat boxes.
    """
    global PLAYING_INACTIVE_EXPANSION_FACTOR
    for gene_box, gene_box_drawing_info in beat_boxes.items():
        current_drawing = gene_box_drawing_info()
        if current_drawing.opacity > 0:
            preimage = False
            if gene_box == "all_drums":
                PLAYING_INACTIVE_EXPANSION_FACTOR = 4
                active_arrays = [
                    np.array(music.playing_individuals[gb].genotype_array[:24])
                    for gb in ("kick", "snare", "hihat")
                ]
                active_array = np.any(active_arrays, axis=0).astype(int)
                fill_array = np.sum(active_arrays, axis=0) / 3
            elif gene_box in music.playing_individuals:
                active_array = music.playing_individuals[gene_box].genotype_array[:24]
                fill_array = music.playing_individuals[gene_box].genotype_array[24:48]

                if hasattr(music.playing_individuals[gene_box], 'playback_mask') and music.playing_individuals[gene_box].playback_mask is not None:
                    mask = music.playing_individuals[gene_box].playback_mask
                    active_array = tuple(int(a and b) for a, b in zip(active_array, mask))
            elif gene_box in (next_playing_individuals := music.snapshot_at_beat(music.beat() + 12)[2]):
                active_array = next_playing_individuals[gene_box].genotype_array[:24]
                fill_array = next_playing_individuals[gene_box].genotype_array[24:48]

                if hasattr(next_playing_individuals[gene_box], 'playback_mask') and next_playing_individuals[gene_box].playback_mask is not None:
                    mask = next_playing_individuals[gene_box].playback_mask
                    active_array = tuple(int(a and b) for a, b in zip(active_array, mask))

                preimage = True
            else:
                continue

            if gene_box in music.playing_individuals and playing_index != last_playing_index and active_array[playing_index] and gene_box in highlight_images:
                highlight_images[gene_box].highlight_amount = 1

            is_inst = gene_box in ("snare_piano", "kick_bass", "hihat_sax")
            draw_box_array(*current_drawing.position, current_drawing.width, active_array, fill_array,
                           [] if preimage else [playing_index],  # only highlight if it's not a preimage
                           24, opacity=current_drawing.opacity, is_inst=is_inst)

            if np.any(music.disturbances):
                dist_copy = music.disturbances.copy()
                dist_copy[playing_index + 1:] = 0
                overlay_exes_on_box(*current_drawing.position, current_drawing.width,
                                    dist_copy, [playing_index], 24)


def draw_highlight_images(dt):
    for highlight_image in highlight_images.values():
        highlight_image.draw(dt)


def draw_snare_harmony(dt):
    genes = music.playing_individuals["snare_harmony"].genotype_array
    voices, change_points = music.playing_individuals["snare_harmony"].harmony_playback_record

    playing_indices_first_bar = set()
    playing_indices_second_bar = set()
    for pitch_pair, changes in zip(voices, change_points):
        if changes[0] <= playing_index < changes[1] and pitch_pair[0] is not None:
            playing_indices_first_bar.add(11 - pitch_pair[0] % 12)
        elif playing_index >= changes[1] and pitch_pair[1] is not None:
            playing_indices_second_bar.add(11 - pitch_pair[1] % 12)

    draw_pc_voice_leading_chart(0.5, 0.13, genes, playing_indices_first_bar, playing_indices_second_bar,
                                opacity=strings_pc_chart_opacity())
    extra_highlight_images["violin"].opacity = strings_pc_chart_opacity()
    if len(playing_indices_first_bar.union(playing_indices_second_bar)) > 0:
        extra_highlight_images["violin"].highlight_amount = 1
    extra_highlight_images["violin"].draw(dt)


def draw_ending_bass(dt):
    genes = music.playing_individuals["kick_end"].genotype_array
    bass_pitches = music.playing_individuals["kick_end"].coin_flipped_end_bass_pcs

    first_half_bass_pitches = {11 - bass_pitches[0]} if bass_pitches[0] is not None and bass_pitches[
        0] <= playing_index < 12 else set()
    second_half_bass_pitches = {11 - bass_pitches[1]} if bass_pitches[1] is not None and 12 + bass_pitches[
        1] <= playing_index else set()
    draw_pc_voice_leading_chart(0.23, 0.13, genes,
                                first_half_bass_pitches,
                                second_half_bass_pitches,
                                opacity=bass_pc_chart_opacity())
    extra_highlight_images["bass"].opacity = bass_pc_chart_opacity()
    if len(first_half_bass_pitches.union(second_half_bass_pitches)) > 0:
        extra_highlight_images["bass"].highlight_amount = 1
    extra_highlight_images["bass"].draw(dt)


def draw_ending_marimba(dt):
    genes = music.playing_individuals["hihat_marimba"].genotype_array
    arpeggio_pitches = music.playing_individuals["hihat_marimba"].coin_flipped_arpeggio_pitches

    first_half_arp_pitches = {11 - arpeggio_pitches[playing_index] % 12} if playing_index < 12 and arpeggio_pitches[
        playing_index] is not None else set()
    second_half_arp_pitches = {11 - arpeggio_pitches[playing_index] % 12} if playing_index >= 12 and arpeggio_pitches[
        playing_index] is not None else set()
    draw_pc_voice_leading_chart(0.77, 0.13, genes,
                                first_half_arp_pitches,
                                second_half_arp_pitches,
                                opacity=mallets_pc_chart_opacity())
    extra_highlight_images["mallet"].opacity = mallets_pc_chart_opacity()
    if len(first_half_arp_pitches.union(second_half_arp_pitches)) > 0:
        extra_highlight_images["mallet"].highlight_amount = 1
    extra_highlight_images["mallet"].draw(dt)


def draw_frame(dt):
    # Fill the background
    fill_bg()
    draw_ephemera()
    draw_beat_boxes()
    draw_highlight_images(dt)

    if "snare_harmony" in music.playing_individuals:
        draw_snare_harmony(dt)

    if "kick_end" in music.playing_individuals:
        draw_ending_bass(dt)

    if "hihat_marimba" in music.playing_individuals:
        draw_ending_marimba(dt)

    draw_dashed_time_indicator()


i = 0

while running and s.beat() < END_BEAT:
    dt = 1000 / FPS
    s.tempo_history.go_to_beat(music.beat())
    s.fast_forward(music.is_fast_forwarding())
    playing_index = int(s.beat() // 0.5) % 24
    smooth_playing_index = (0.5 + s.beat() / 0.5) % 24

    try:
        draw_frame(dt)
    except IndexError:
        running = False
        break

    last_playing_index = playing_index

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break

    if SAVE_FRAMES_FOLDER:
        pygame.image.save(screen, f"{SAVE_FRAMES_FOLDER}/frame_{i:05d}.png")

    i += 1

    # Update the display
    pygame.display.flip()

    music.advance_time(1 / FPS)
    # print(f"t={music.time()}, b={music.beat()}")
    # clock.tick(FPS)  # no need for this; slows it down when it can go faster

# Quit pygame
pygame.quit()


