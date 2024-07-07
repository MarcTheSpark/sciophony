import math
import threading
from solar_system_functions import get_solar_system_state
from marciano.solar_system_model2 import object_diameters_km
from planets_music import PlanetMusic
import time
import pygame


planet_music = PlanetMusic()
planet_music.start()


def solar_system_state():
    planet_music.s.rouse_and_hold()
    planet_music.s.release_from_suspension()
    return get_solar_system_state(planet_music.s.beat())


# Global constants
HEIGHT = 1080
WIDTH = 1920
pixels_per_au = 100
pixels_per_au_range = (13.8, 2000)
MAGNIFIED_PIXELS_PER_AU = 35
SUN_SIZE_SCALE_CONSTANT = 1 / 6000
PLANET_SIZE_SCALE_CONSTANT = 1 / 2500

planets = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]

MAGNIFIER_RADIUS_PX = 70
MAGNIFIER_LENS_WIDTH_PROPORTION = 0.957  # width of lens as proportion of width of image
MAGNIFIER_LENS_CENTER_PROPORTION = 0.54, 0.43 # center of lens as proportion of width/height of image

# Load and resize the magnifier glass image
mag_glass_image = pygame.image.load('MagGlass.png')


def resize_magnifier_image(image, radius_pixels):
    new_width = 2 * radius_pixels / MAGNIFIER_LENS_WIDTH_PROPORTION
    new_height = new_width * image.get_height() / image.get_width()
    return pygame.transform.scale(image, (new_width, new_height))


mag_glass_image_resized = resize_magnifier_image(mag_glass_image, MAGNIFIER_RADIUS_PX)
mag_glass_image_resized.set_alpha(255 if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else 0)

min_planet_sizes = {planet: math.sqrt(object_diameters_km[planet]) * 40 * PLANET_SIZE_SCALE_CONSTANT
                    for planet in planets}


def get_planet_pixel_radius(planet, magnified=False):
    return max(min_planet_sizes[planet],
               math.sqrt(object_diameters_km[planet]) * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au) *
               PLANET_SIZE_SCALE_CONSTANT)


min_sun_size = math.sqrt(object_diameters_km["sun"]) * 40 * SUN_SIZE_SCALE_CONSTANT


def get_sun_pixel_radius():
    return max(min_sun_size, math.sqrt(object_diameters_km["sun"]) * pixels_per_au * SUN_SIZE_SCALE_CONSTANT)


# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SUN_COLOR = (255, 255, 0)
PLANET_COLOR = (0, 150, 255)

# Initialize Pygame
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Solar System Model')

# Main loop
running = True
clock = pygame.time.Clock()


def draw_planet(planet, screen, position, color, magnified=False):
    radius = get_planet_pixel_radius(planet, magnified=magnified)
    x, y = position[:2] * (MAGNIFIED_PIXELS_PER_AU if magnified else pixels_per_au)
    pygame.draw.circle(screen, color, (int(x + WIDTH // 2), int(y + HEIGHT // 2)), radius)


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

    # Draw planets
    for planet in planets:
        position = solar_system.get_position(planet)
        draw_planet(planet, screen, position, PLANET_COLOR,
                    magnified=(planet in planets[:4]) if pixels_per_au < MAGNIFIED_PIXELS_PER_AU else False)

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
