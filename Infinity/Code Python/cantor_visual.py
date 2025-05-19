import pygame
from cantor_tempo_utils import cantor_rest_pattern
from itertools import islice
from typing import Collection
from dataclasses import dataclass


@dataclass
class RectF:
    x: float
    y: float
    width: float
    height: float


class Camera:
    def __init__(self, surface: pygame.Surface):
        # Camera position and zoom
        self._zoom = (surface.get_height() / 2)
        self.offset = pygame.Vector2(0, 0)  # Offset from the top-left of the screen
        self.surface = surface
        self.screen_width = surface.get_width()
        self.screen_height = surface.get_height()

    @property
    def zoom(self):
        return self._zoom / (self.surface.get_height() / 2)
    
    @zoom.setter
    def zoom(self, value):
        # Set zoom level, but prevent it from being too low or too high
        value = max(0.1, min(value, 10))
        self._zoom = value * (self.surface.get_height() / 2)

    def move(self, x, y):
        # Move the camera by an (x, y) offset
        self.offset.x += x
        self.offset.y += y

    def apply(self, position):
        # Converts world coordinates to screen coordinates
        return (pygame.Vector2(position) - self.offset) * self._zoom + pygame.Vector2(self.screen_width / 2, self.screen_height / 2)

    def apply_rect(self, rect):
        # Converts a rectangle from world to screen coordinates and applies zoom
        screen_pos = self.apply((rect.x, rect.y))
        return pygame.Rect(screen_pos.x, screen_pos.y, rect.width * self._zoom, rect.height * self._zoom)

    def world_to_screen(self, pos):
        # A convenience method for converting world coordinates to screen coordinates
        return self.apply(pos)

    def screen_to_world(self, pos):
        # Converts screen coordinates to world coordinates (for mouse clicks, etc.)
        return (pygame.Vector2(pos) - pygame.Vector2(self.screen_width / 2, self.screen_height / 2)) / self._zoom + self.offset

    def draw_rect(self, color, rect, surface=None):
        if surface is None:
            surface = self.surface
        # Draws a rectangle in world coordinates, automatically transforms to screen coordinates
        transformed_rect = self.apply_rect(rect)
        pygame.draw.rect(surface, color, transformed_rect)
        
    def draw_image(self, image, position, surface=None):
        if surface is None:
            surface = self.surface
        # Draws an image at a world coordinate position
        transformed_position = self.apply(position)
        surface.blit(image, transformed_position)
        
        
# Initialize Pygame and set up the screen
pygame.init()
screen = pygame.display.set_mode((1920, 1080))

# Set up the camera
camera = Camera(screen)


class CantorInstance:
    
    def __init__(self, camera, upper_left_corner, dimensions,
                 bar_height_spacing_proportion=0.4, num_levels=5, progress=0,
                 active_color=(230, 200, 0), inactive_color=(120, 120, 120)):
        self.upper_left_corner = upper_left_corner
        self.dimensions = dimensions
        self.bar_height_spacing_proportion = bar_height_spacing_proportion
        self.num_levels = num_levels
        self.progress = progress
        self.camera = camera
        self.active_color = active_color
        self.inactive_color = inactive_color
        
    def draw(self):
        bar_spacing = self.dimensions[1] / self.num_levels
        bar_height = bar_spacing * self.bar_height_spacing_proportion
        for level in range(self.num_levels):
            step_size = self.dimensions[0] / 3 ** level
            step_offset = 0
            k = 1
            rest_pattern = cantor_rest_pattern(1)
            while step_offset < 3 ** level and k < self.progress + 1:
                color = self.active_color if k == self.progress else self.inactive_color
                rect =  RectF(
                    self.upper_left_corner[0] + step_offset * step_size,
                    self.upper_left_corner[1] + bar_spacing * level,
                    step_size,
                    bar_height
                )
                self.camera.draw_rect(color, rect)
                step_offset += 1 + next(rest_pattern)
                k += 1


ci = CantorInstance(camera, (-1, -0.8), (2, 1.6))
clock = pygame.time.Clock()

# Main game loop
running = True
t = 0
while running:
    t += clock.tick(60) / 1000
    ci.progress = int(t / 2 % 16)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEWHEEL:
            # Zoom in/out with the mouse wheel
            camera.zoom *= (1.1 if event.y > 0 else 0.9)

    # Example camera movement with arrow keys
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: camera.move(-0.01, 0)
    if keys[pygame.K_RIGHT]: camera.move(0.01, 0)
    if keys[pygame.K_UP]: camera.move(0, -0.01)
    if keys[pygame.K_DOWN]: camera.move(0, 0.01)

    # Clear the screen
    screen.fill((30, 30, 30))
    
    ci.draw()

    # Display the result
    pygame.display.flip()

pygame.quit()
