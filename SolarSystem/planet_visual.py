import math
import threading

import numpy as np

from solar_system_functions import get_solar_system_state
from marciano.solar_system_model2 import object_diameters_km
from planets_music import PlanetMusic
import time
import pygame
import random


planet_music = PlanetMusic()
planet_music.start()


def solar_system_state():
    planet_music.s.rouse_and_hold()
    planet_music.s.release_from_suspension()
    return get_solar_system_state(planet_music.s.beat())


# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SUN_COLOR = (255, 255, 0)
DEFAULT_PLANET_COLOR = np.array([255, 255, 255])
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

# Global constants
HEIGHT = 1080
WIDTH = 1920
pixels_per_au = 100
pixels_per_au_range = (13.8, 2000)
MAGNIFIED_PIXELS_PER_AU = 35
SUN_SIZE_SCALE_CONSTANT = 1 / 6000
PLANET_SIZE_SCALE_CONSTANT = 1 / 2500

PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

MAGNIFIER_RADIUS_PX = 70
MAGNIFIER_LENS_WIDTH_PROPORTION = 0.957  # width of lens as proportion of width of image
MAGNIFIER_LENS_CENTER_PROPORTION = 0.54, 0.43  # center of lens as proportion of width/height of image

PLANET_RADIUS_RETURN_CONSTANT = 0.87
PLANET_COLOR_RETURN_CONSTANT = 0.95


def au_coords_to_screen_coords(au_coords, magnified=False):
    return np.array([WIDTH / 2, HEIGHT / 2]) + au_coords[:2] * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au)


def planet_screen_coords(planet):
    magnified = (planet in PLANETS[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False
    return au_coords_to_screen_coords(solar_system_state().get_position(planet), magnified)


# Load and resize the magnifier glass image
mag_glass_image = pygame.image.load('MagGlass.png')


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
planet_colors = {planet: DEFAULT_PLANET_COLOR for planet in PLANETS}



# Initialize Pygame
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Solar System Model')

# Main loop
running = True
clock = pygame.time.Clock()


def draw_planet(planet, screen, position, magnified=False):
    radius = get_planet_pixel_radius(planet, magnified=magnified) * planet_radius_muls[planet]
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
    # pixels_per_au /= 1.005
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                pixels_per_au *= 1.1  # Increase exponentially
            elif event.button == 5:  # Scroll down
                pixels_per_au /= 1.1  # Decrease exponentially
            pixels_per_au = max(min(pixels_per_au, pixels_per_au_range[1]), pixels_per_au_range[0])

    screen.fill(BLACK)

    # Get solar system state
    solar_system = solar_system_state()

    # Draw the sun at the center
    pygame.draw.circle(screen, SUN_COLOR, (WIDTH // 2, HEIGHT // 2), get_sun_pixel_radius())

    # draw proximity alerts
    for proximity_alert in planet_music.proximity_alerts:
        if proximity_alert.alerting:
            draw_proximity_line(screen, proximity_alert.planet_1, proximity_alert.planet_2, proximity_alert.color)

    # Draw PLANETS
    for planet in PLANETS:
        planet_radius_muls[planet] = 1 + (planet_radius_muls[planet] - 1) * PLANET_RADIUS_RETURN_CONSTANT
        planet_colors[planet] = DEFAULT_PLANET_COLOR + (
                    planet_colors[planet] - DEFAULT_PLANET_COLOR) * PLANET_COLOR_RETURN_CONSTANT
        position = solar_system.get_position(planet)
        draw_planet(planet, screen, position,
                    magnified=(planet in PLANETS[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False)

    for orbit_beat in planet_music.orbit_beats:
        if orbit_beat.just_played:
            planet_radius_muls[orbit_beat.planet] = max(planet_radius_muls[orbit_beat.planet],
                                                        orbit_beat.play_expansion_factor)
            orbit_beat.just_played = False

    for orbit_melody in planet_music.orbit_melodies:
        if orbit_melody.just_played_pc is not None:
            planet_colors[orbit_melody.planet] = \
                DEFAULT_PLANET_COLOR * (1 - orbit_melody.just_played_volume) + \
                PITCH_CLASS_COLORS[orbit_melody.just_played_pc] * orbit_melody.just_played_volume
            planet_radius_muls[orbit_melody.planet] = max(
                planet_radius_muls[orbit_melody.planet],
                1 + orbit_melody.just_played_volume * (orbit_melody.play_expansion_factor - 1)
            )
            orbit_melody.just_played_pc = None
    # Beats should be pulsing in planet size that fade back to normal (always in the process of fading back to normal)

    # Melodies should be colors, that fade back to white (always in the process of fading back to white, sets a new
    # color when there's a new melody note)


    # draw magnifying glass
    if pixels_per_au < MAGNIFIED_PIXELS_PER_AU and (alpha := mag_glass_image_resized.get_alpha()) < 255:
        mag_glass_image_resized.set_alpha(min(255, alpha + 10))
    elif pixels_per_au >= MAGNIFIED_PIXELS_PER_AU and (alpha := mag_glass_image_resized.get_alpha()) > 0:
        mag_glass_image_resized.set_alpha(max(0, alpha - 10))

    if mag_glass_image_resized.get_alpha() > 0:
        # Draw the magnifier glass image on top of everything else
        screen.blit(mag_glass_image_resized,
                    (WIDTH // 2 - mag_glass_image_resized.get_width() * MAGNIFIER_LENS_CENTER_PROPORTION[0],
                     HEIGHT // 2 - mag_glass_image_resized.get_height() * MAGNIFIER_LENS_CENTER_PROPORTION[1]))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
