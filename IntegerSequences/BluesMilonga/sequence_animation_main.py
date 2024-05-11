import math
import threading
import time
import numpy as np
import pyglet
from pyglet import shapes
import sequence_blues_milonga
from sequence_definitions import A319419
from expenvelope import Envelope

# Define constants for easy configuration
WIDTH, HEIGHT = 1920, 1080
SQUARE_WIDTH = int(WIDTH * 0.9 / 10)
BACKGROUND_COLOR = (20, 20, 20, 255)  # Grey background as configured

ONE_FILL = (255, 255, 255, 255)
ZERO_FILL = (20, 20, 20, 255)
NEGATIVE_FILL = (170, 0, 0, 255)
OUTLINE_COLOR = (80, 80, 80, 255)
OUTLINE_WIDTH = 4
CANCELLED_INDEX_COLOR = (255, 0, 0, 255)
CANCELLED_LEAD_ZEROS_COLOR = (150, 150, 150, 120)


def draw_binary_squares(binary_tup, x, y, square_width, one_fill, zero_fill, negative_fill, outline_color, outline_width,
                        batch=None, shapes_list=None, square_height=None, skip_digits=()):

    square_height = square_width if square_height is None else square_height
    batch = pyglet.graphics.Batch() if batch is None else batch
    shapes_list = [] if shapes_list is None else shapes_list

    for i, bit in enumerate(binary_tup):
        if i in skip_digits:
            continue
        # Determine fill color based on the bit
        fill_color = one_fill if bit == 1 else zero_fill if bit == 0 else negative_fill
        # Create and add a bordered square shape to the batch
        shapes_list.append(
            shapes.Rectangle(x + i * square_width, y, square_width, square_height,
                             color=fill_color, batch=batch)
        )
        if outline_color:
            shapes_list.extend([
                shapes.Rectangle(x + i * square_width, y + square_height - outline_width, square_width, outline_width, color=outline_color,
                                 batch=batch),  # Top
                shapes.Rectangle(x + i * square_width, y, square_width, outline_width, color=outline_color, batch=batch),  # Bottom
                shapes.Rectangle(x + i * square_width, y, outline_width, square_height, color=outline_color, batch=batch),  # Left
                shapes.Rectangle(x + (i + 1) * square_width - outline_width, y, outline_width, square_height, color=outline_color,
                                 batch=batch)  # Right
            ])

    return batch


# Create a Pyglet window
window = pyglet.window.Window(1920, 1080, style=pyglet.window.Window.WINDOW_STYLE_DEFAULT)
window.set_fullscreen(True)
main_batch = pyglet.graphics.Batch()
shapes_drawn = []


@window.event
def on_draw():
    update_drawing()
    pyglet.gl.glClearColor(*[c / 255.0 for c in BACKGROUND_COLOR])  # Convert to GL color format
    window.clear()
    main_batch.draw()


i = 0


# ------------ FOR SAVING FRAMES ----------
# @window.event
# def on_draw():
#     global i
#     n = sequence_blues_milonga.reversed_indices[i]
#     pyglet.gl.glClearColor(*[c / 255.0 for c in BACKGROUND_COLOR])  # Convert to GL color format
#     window.clear()
#     batch, objects = make_batch(n)
#     batch.draw()
#     pyglet.image.get_buffer_manager().get_color_buffer().save(f"frames/{n:06}.png")
#     i += 1


HISTORY_LENGTH = 128
y_curve = Envelope([HEIGHT, (HEIGHT - SQUARE_WIDTH) / 2], [HISTORY_LENGTH], [4])
square_width_curve = Envelope([SQUARE_WIDTH / 4, SQUARE_WIDTH], [HISTORY_LENGTH], [4])


def make_batch(num):
    batch = pyglet.graphics.Batch()
    shapes_list = []

    # print(value, bin(value))

    for i, x in enumerate(range(num - HISTORY_LENGTH, num + 1)):
        if x < 0:
            continue
        binary = tuple(map(int, f'{x:010b}'))
        square_width = square_width_curve.value_at(i)
        y_position = y_curve.value_at(i)
        draw_binary_squares(binary, (WIDTH - len(binary) * square_width) / 2, y_position,
                            square_width, ONE_FILL, ZERO_FILL, NEGATIVE_FILL, OUTLINE_COLOR if x == num else None,
                            OUTLINE_WIDTH, batch=batch, shapes_list=shapes_list)

    return batch, shapes_list


num = None


def update_drawing():
    global main_batch, shapes_drawn, num
    if sequence_blues_milonga.current_num != num:
        num = sequence_blues_milonga.current_num
        main_batch, shapes_drawn = make_batch(num)


threading.Thread(target=sequence_blues_milonga.main, daemon=True).start()
# Run the application
pyglet.app.run()
