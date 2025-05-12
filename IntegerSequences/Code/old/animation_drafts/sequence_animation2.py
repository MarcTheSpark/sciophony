import math
import threading

import numpy as np
import pyglet
from pyglet import shapes
import sequence_blues_milonga
from sequence_definitions import A319419

# Define constants for easy configuration
WIDTH, HEIGHT = 1920, 1080
SQUARE_WIDTH = 70
BACKGROUND_COLOR = (20, 20, 20, 255)  # Grey background as configured
shapes_drawn = []


ONE_FILL = (255, 255, 255, 255)
ZERO_FILL = (20, 20, 20, 255)
NEGATIVE_FILL = (170, 0, 0, 255)
OUTLINE_COLOR = (80, 80, 80, 255)
OUTLINE_WIDTH = 2
CANCELLED_INDEX_COLOR = (255, 0, 0, 255)
CANCELLED_LEAD_ZEROS_COLOR = (150, 150, 150, 120)


def draw_binary_squares(binary_tup, x, y, square_width, one_fill, zero_fill, negative_fill, outline_color, outline_width,
                        batch=None,  square_height=None):
    batch = pyglet.graphics.Batch() if batch is None else batch

    for i, bit in enumerate(binary_tup):
        # Determine fill color based on the bit
        fill_color = one_fill if bit == 1 else zero_fill if bit == 0 else negative_fill

        # Create and add a bordered square shape to the batch
        shapes_drawn.append(
            shapes.Rectangle(x + i * square_width, y, square_width, square_height if square_height is not None else square_width, color=fill_color, batch=batch)
        )
        if outline_color:
            shapes_drawn.append(
                shapes.Box(x + i * square_width, y, square_width, square_height if square_height is not None else square_width,
                           thickness=outline_width, color=outline_color, batch=batch)
            )

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
        main_batch = pyglet.graphics.Batch()
        shapes_drawn.clear()
        # print(value, bin(value))
        for i, x in enumerate(range(num, max(0, num - (HEIGHT // SQUARE_WIDTH * 2)), -1)):
            binary = tuple(map(int, f'{x:011b}'))
            draw_binary_squares(binary, 0, HEIGHT - (i/2 + 1) * SQUARE_WIDTH,
                                SQUARE_WIDTH, ONE_FILL, ZERO_FILL, NEGATIVE_FILL, OUTLINE_COLOR if i == 0 else None, OUTLINE_WIDTH,
                                square_height=SQUARE_WIDTH if i == 0 else SQUARE_WIDTH / 2, batch=main_batch)
        for i, x in enumerate(range(num, max(0, num - (HEIGHT // SQUARE_WIDTH * 2)), -1)):
            sequence_value = A319419(x)
            binary = tuple(map(int, f'{sequence_value:09b}')) if sequence_value >= 0 else (0, ) * 8 + (-1, )

            draw_binary_squares(binary, SQUARE_WIDTH * 12, HEIGHT - (i/2 + 1) * SQUARE_WIDTH,
                                SQUARE_WIDTH, ONE_FILL, ZERO_FILL, NEGATIVE_FILL, OUTLINE_COLOR if i == 0 else None, OUTLINE_WIDTH,
                                square_height=SQUARE_WIDTH if i == 0 else SQUARE_WIDTH / 2, batch=main_batch)


pyglet.clock.schedule_interval(update_drawing, 0.001)
threading.Thread(target=sequence_blues_milonga.main, daemon=True).start()
# Run the application
pyglet.app.run()
