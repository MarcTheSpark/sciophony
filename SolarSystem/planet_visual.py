import math
import threading
import numpy as np
from solar_system_functions import get_solar_system_state
from marciano.solar_system_model2 import object_diameters_km
from planets_music import PlanetMusic
import time
import pygame
import random


planet_music = PlanetMusic(to_logic=False)
planet_music.start()


def solar_system_state():
    return get_solar_system_state(planet_music.s.beat())


FRAME_RATE = 30

# Global constants
WINDOW_SCALE = 0.4
WIDTH = 1920 * WINDOW_SCALE
HEIGHT = 1080 * WINDOW_SCALE
pixels_per_au = 180 * WINDOW_SCALE
pixels_per_au_range = (13.8 * WINDOW_SCALE, 2000 * WINDOW_SCALE)
MAGNIFIED_PIXELS_PER_AU = 35 * WINDOW_SCALE
SUN_SIZE_SCALE_CONSTANT = 1 / 6000
PLANET_SIZE_SCALE_CONSTANT = 1 / 2500

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SUN_COLOR = (255, 255, 0)

PITCH_CLASS_COLORS = [
    np.array([255, 0, 0]),    # Red
    np.array([0, 255, 0]),    # Green
    np.array([0, 0, 255]),    # Blue
    np.array([255, 255, 0]),  # Yellow
    np.array([0, 255, 255]),  # Cyan
    np.array([255, 0, 255]),  # Magenta
    np.array([255, 165, 0]),  # Orange
    np.array([128, 0, 128]),  # Purple
    np.array([128, 128, 0]),  # Olive
    np.array([0, 128, 128]),  # Teal
    np.array([192, 192, 192]),  # Silver
    np.array([255, 20, 147])  # Deep Pink
]

PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

MAGNIFIER_RADIUS_PX = 65 * WINDOW_SCALE  # 70
MAGNIFIER_LENS_WIDTH_PROPORTION = 1  # 0.957  # width of lens as proportion of width of image
MAGNIFIER_LENS_CENTER_PROPORTION = 0.5, 0.5  # 0.54, 0.43  # center of lens as proportion of width/height of image

PLANET_RADIUS_RETURN_CONSTANT = 0.87
PLANET_COLOR_RETURN_CONSTANT = 0.95


def au_coords_to_screen_coords(au_coords, magnified=False):
    return np.array([WIDTH / 2, HEIGHT / 2]) + au_coords[:2] * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au)


def planet_screen_coords(planet):
    magnified = (planet in PLANETS[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False
    return au_coords_to_screen_coords(solar_system_state().get_position(planet), magnified)


# Load and resize the magnifier glass image
mag_glass_image = pygame.image.load('MagCircle.png')

# Create a secondary surface (canvas) for drawing objects
trails_canvas = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
FADE_ALPHA = 2
FADE_SURFACE = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
FADE_SURFACE.fill((0, 0, 0, FADE_ALPHA))
planet_trail_radius_muls = {planet: 0 for planet in PLANETS}


def scale_canvas(canvas, zoom_factor):
    """
    Scale the content of the canvas by the given zoom factor and return a new canvas
    with the original dimensions.

    :param canvas: The original canvas to be scaled.
    :param zoom_factor: The factor by which to scale the canvas content.
    :return: A new canvas with the scaled content.
    """
    # Get the dimensions of the original canvas
    width, height = canvas.get_size()

    # Scale the content of the canvas
    scaled_content = pygame.transform.scale(canvas, (int(width * zoom_factor), int(height * zoom_factor)))

    # Create a new canvas with the same dimensions as the original
    new_canvas = pygame.Surface((width, height), pygame.SRCALPHA)

    offset_x = (width - scaled_content.get_width()) // 2
    offset_y = (height - scaled_content.get_height()) // 2

    # Blit the scaled content onto the new canvas
    new_canvas.blit(scaled_content, (offset_x, offset_y))

    return new_canvas


def resize_magnifier_image(image, radius_pixels):
    new_width = 2 * radius_pixels / MAGNIFIER_LENS_WIDTH_PROPORTION
    new_height = new_width * image.get_height() / image.get_width()
    return pygame.transform.scale(image, (new_width, new_height))


mag_glass_image_resized = resize_magnifier_image(mag_glass_image, MAGNIFIER_RADIUS_PX)
mag_glass_image_resized.set_alpha(255 if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else 0)

min_planet_sizes = {planet: math.sqrt(object_diameters_km[planet]) * 40 * PLANET_SIZE_SCALE_CONSTANT
                    for planet in PLANETS}


def get_planet_pixel_radius(planet, magnified=False):
    return max(min_planet_sizes[planet],
               math.sqrt(object_diameters_km[planet]) * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au) *
               PLANET_SIZE_SCALE_CONSTANT)


min_sun_size = math.sqrt(object_diameters_km["sun"]) * 40 * SUN_SIZE_SCALE_CONSTANT


def get_sun_pixel_radius():
    return max(min_sun_size, math.sqrt(object_diameters_km["sun"]) * pixels_per_au * SUN_SIZE_SCALE_CONSTANT)


planet_radius_muls = {planet: 1 for planet in PLANETS}
planet_colors = {planet: WHITE for planet in PLANETS}

# Initialize Pygame
pygame.init()

pygame.font.init()


def draw_text(screen, text, position, font_size, h_anchor='left', v_anchor='top', color=(255, 255, 255)):
    """
    Draws text on a Pygame surface with specified position and alignment.

    :param screen: Pygame surface to draw the text on
    :param text: The text to draw
    :param position: Tuple (x, y) specifying the position to draw the text
    :param font_size: Size of the font
    :param h_anchor: Horizontal anchor ('left', 'center', 'right')
    :param v_anchor: Vertical anchor ('top', 'center', 'bottom')
    :param color: Color of the text (default is white)
    """
    font = pygame.font.Font(None, font_size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()

    # Set horizontal anchor
    if h_anchor == 'center':
        text_rect.centerx = position[0]
    elif h_anchor == 'right':
        text_rect.right = position[0]
    else:  # 'left' is default
        text_rect.x = position[0]

    # Set vertical anchor
    if v_anchor == 'center':
        text_rect.centery = position[1]
    elif v_anchor == 'bottom':
        text_rect.bottom = position[1]
    else:  # 'top' is default
        text_rect.y = position[1]

    screen.blit(text_surface, text_rect)


screen = pygame.display.set_mode((WIDTH, HEIGHT)) #, pygame.FULLSCREEN)
pygame.display.set_caption('Solar System Model')


# Main loop
running = True
clock = pygame.time.Clock()


def draw_planet(planet, screen, position, magnified=False):
    radius = get_planet_pixel_radius(planet, magnified=magnified) * planet_radius_muls[planet]
    x, y = position[:2] * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au)
    pygame.draw.circle(screen, WHITE, (int(x + WIDTH // 2), int(y + HEIGHT // 2)), radius)


def draw_planet_trail(planet, screen, position, magnified=False):
    radius = get_planet_pixel_radius(planet, magnified=magnified) * planet_trail_radius_muls[planet]
    x, y = position[:2] * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au)
    pygame.draw.circle(screen, planet_colors[planet], (int(x + WIDTH // 2), int(y + HEIGHT // 2)), radius)


def draw_jagged_line(screen, start_pos, end_pos, num_segments=10, jaggedness=20, color=(255, 255, 255), thickness=2):
    # Convert start and end positions to NumPy arrays
    start_pos = np.array(start_pos, dtype=float)
    end_pos = np.array(end_pos, dtype=float)

    # Calculate the direction vector and normalize it
    direction_vector = (end_pos - start_pos) / num_segments
    magnitude = np.linalg.norm(direction_vector)
    unit_vector = direction_vector / magnitude

    # Calculate the perpendicular direction vector
    perp_vector = np.array([-unit_vector[1], unit_vector[0]])

    # Initialize the list of points
    points = [start_pos]

    for i in range(1, num_segments):
        # Calculate the next point along the line
        next_point = start_pos + i * direction_vector

        # Add randomness along the perpendicular direction
        deviation = np.random.uniform(-jaggedness, jaggedness)
        next_point += perp_vector * deviation

        # Append the calculated point to the list
        points.append(next_point)

    # Append the end position to the list
    points.append(end_pos)

    # Draw the line segments
    for i in range(len(points) - 1):
        pygame.draw.line(screen, color, points[i], points[i + 1], thickness)


def draw_proximity_line(screen, planet1, planet2, color):
    draw_jagged_line(screen, planet_screen_coords(planet1), planet_screen_coords(planet2),
                     jaggedness=pixels_per_au/10,
                     color=color)


planet_music.wait_until_started()


while running:
    planet_music.s.rouse_and_hold()
    planet_music.s.release_from_suspension()
    # pixels_per_au /= 1.005
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            old_ppa = pixels_per_au

            if event.button == 4:  # Scroll up
                pixels_per_au *= 1.1  # Increase exponentially
            elif event.button == 5:  # Scroll down
                pixels_per_au /= 1.1  # Decrease exponentially
            pixels_per_au = max(min(pixels_per_au, pixels_per_au_range[1]), pixels_per_au_range[0])

            if pixels_per_au != old_ppa:
                trails_canvas = scale_canvas(trails_canvas, pixels_per_au/old_ppa)

    screen.fill(BLACK)

    # Get solar system state
    solar_system = solar_system_state()

    # Blit the canvas to the main display surface
    screen.blit(trails_canvas, (0, 0))
    # Apply fading effect by drawing a semi-transparent rectangle over the canvas
    trails_canvas.blit(FADE_SURFACE, (0, 0))

    # draw proximity alerts
    for proximity_alert in planet_music.proximity_alerts:
        if proximity_alert.alerting:
            draw_proximity_line(screen, proximity_alert.planet_1, proximity_alert.planet_2, proximity_alert.color)

    for orbit_beat in planet_music.orbit_beats:
        if orbit_beat.just_played:
            planet_radius_muls[orbit_beat.planet] = max(planet_radius_muls[orbit_beat.planet],
                                                        orbit_beat.play_expansion_factor)
            orbit_beat.just_played = False

    for orbit_melody in planet_music.orbit_melodies:
        if orbit_melody.just_played_pc is not None:
            planet_radius_muls[orbit_melody.planet] = max(planet_radius_muls[orbit_melody.planet],
                                                          orbit_melody.play_expansion_factor)
            planet_trail_radius_muls[orbit_melody.planet] = max(planet_trail_radius_muls[orbit_melody.planet],
                                                                orbit_melody.trail_expansion_factor)
            planet_colors[orbit_melody.planet] = (PITCH_CLASS_COLORS[orbit_melody.just_played_pc] *
                                                  orbit_melody.just_played_volume ** 1.7)
            orbit_melody.just_played_pc = None
        position = solar_system.get_position(orbit_melody.planet)

        if not orbit_melody.muted:
            draw_planet_trail(
                orbit_melody.planet, trails_canvas, position,
                magnified=(orbit_melody.planet in PLANETS[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False
            )
        planet_trail_radius_muls[orbit_melody.planet] *= 0.96

    # Draw the sun at the center
    pygame.draw.circle(screen, SUN_COLOR, (WIDTH // 2, HEIGHT // 2), get_sun_pixel_radius())

    # Draw PLANETS
    for planet in PLANETS:
        planet_radius_muls[planet] = 1 + (planet_radius_muls[planet] - 1) * PLANET_RADIUS_RETURN_CONSTANT
        position = solar_system.get_position(planet)
        draw_planet(planet, screen, position,
                    magnified=(planet in PLANETS[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False)

    # draw magnifying glass
    if pixels_per_au < MAGNIFIED_PIXELS_PER_AU and (alpha := mag_glass_image_resized.get_alpha()) < 255:
        mag_glass_image_resized.set_alpha(min(255, alpha + 20))
    elif pixels_per_au >= MAGNIFIED_PIXELS_PER_AU and (alpha := mag_glass_image_resized.get_alpha()) > 0:
        mag_glass_image_resized.set_alpha(max(0, alpha - 20))

    if mag_glass_image_resized.get_alpha() > 0:
        if mag_glass_image_resized.get_alpha() == 255:
            draw_text(screen,f"{MAGNIFIED_PIXELS_PER_AU / pixels_per_au:.2f}x",
                      (WIDTH // 2, HEIGHT // 2 - MAGNIFIER_RADIUS_PX), 20,
                      'center', 'bottom')
        # Draw the magnifier glass image on top of everything else
        screen.blit(mag_glass_image_resized,
                    (WIDTH // 2 - mag_glass_image_resized.get_width() * MAGNIFIER_LENS_CENTER_PROPORTION[0],
                     HEIGHT // 2 - mag_glass_image_resized.get_height() * MAGNIFIER_LENS_CENTER_PROPORTION[1]))

    pygame.display.flip()
    clock.tick(FRAME_RATE)

pygame.quit()