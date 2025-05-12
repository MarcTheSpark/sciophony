import math
import threading

import numpy as np
import pyglet
from pyglet import shapes
import sequence_blues_milonga
from sequence_definitions import A319419

# Define constants for easy configuration
WIDTH, HEIGHT = 1920, 1080
SQUARE_WIDTH = 150
BACKGROUND_COLOR = (20, 20, 20, 255)  # Grey background as configured
shapes_drawn = []


ONE_FILL = (255, 255, 255, 255)
ZERO_FILL = (20, 20, 20, 255)
OUTLINE_COLOR = (80, 80, 80, 255)
OUTLINE_WIDTH = 3
CANCELLED_INDEX_COLOR = (255, 0, 0, 255)
CANCELLED_LEAD_ZEROS_COLOR = (150, 150, 150, 120)


def draw_binary_squares(binary_tup, x, y, square_width, one_fill, zero_fill, outline_color, outline_width,
                        batch=None, cancelled_indices=(), cancelled_lead_zeros=()):
    """
    Draw the binary representation of `number` as squares at position (x, y).

    Parameters:
    - x, y: The starting coordinates for the drawing.
    - square_width: The width and height of each square.
    - number: The integer number to be converted to binary.
    - one_fill_color: The color used to fill squares representing '1' in binary.
    - zero_fill_color: The color used to fill squares representing '0' in binary.
    - outline_color: The color of the square outlines.
    - outline_width: The width of the square outlines.
    """
    batch = pyglet.graphics.Batch() if batch is None else batch

    for i, bit in enumerate(binary_tup):
        # Determine fill color based on the bit
        fill_color = one_fill if bit == 1 else zero_fill

        # Create and add a bordered square shape to the batch
        shapes_drawn.append(
            shapes.Rectangle(x + i * square_width, y, square_width, square_width, color=fill_color, batch=batch)
        )
        shapes_drawn.append(
            shapes.Box(x + i * square_width, y, square_width, square_width,
                       thickness=outline_width, color=outline_color, batch=batch)
        )
        if i in cancelled_indices:
            shapes_drawn.extend([
                shapes.Line(x + (i + 1) * square_width, y, x + i * square_width, y + square_width,
                            color=CANCELLED_INDEX_COLOR, width=5, batch=batch),
                shapes.Line(x + i * square_width, y, x + (i + 1) * square_width, y + square_width,
                            color=CANCELLED_INDEX_COLOR, width=5, batch=batch)
            ])
        elif i in cancelled_lead_zeros:
            shapes_drawn.extend([
                shapes.Line(x + (i + 1) * square_width, y, x + i * square_width, y + square_width,
                            color=CANCELLED_LEAD_ZEROS_COLOR, width=3, batch=batch),
                shapes.Line(x + i * square_width, y, x + (i + 1) * square_width, y + square_width,
                            color=CANCELLED_LEAD_ZEROS_COLOR, width=3, batch=batch)
            ])

    return batch


# Create a Pyglet window
window = pyglet.window.Window(1920, 1080, style=pyglet.window.Window.WINDOW_STYLE_DEFAULT)
window.set_fullscreen(True)
main_batch = pyglet.graphics.Batch()


@window.event
def on_draw():
    pyglet.gl.glClearColor(*[c / 255.0 for c in BACKGROUND_COLOR])  # Convert to GL color format
    window.clear()
    main_batch.draw()


current_num_in_music = None


def update_drawing(_):
    global main_batch, current_num_in_music
    if sequence_blues_milonga.current_num != num:
        num = sequence_blues_milonga.current_num
        value = A319419(num)
        main_batch = pyglet.graphics.Batch()
        shapes_drawn.clear()
        # print(value, bin(value))
        binary = tuple(map(int, bin(num)[2:]))
        draw_binary_squares(binary, (WIDTH - len(binary) * SQUARE_WIDTH) / 2, HEIGHT / 2 - SQUARE_WIDTH / 2, SQUARE_WIDTH,
                            ONE_FILL, ZERO_FILL, OUTLINE_COLOR, OUTLINE_WIDTH, batch=main_batch)


pyglet.clock.schedule_interval(update_drawing, 0.01)
threading.Thread(target=sequence_blues_milonga.main, daemon=True).start()
# Run the application
pyglet.app.run()
