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
BACKGROUND_COLOR = (100, 100, 100, 255)  # Grey background as configured
shapes_drawn = []
shapes_to_fade = []

ONE_FILL = (30, 30, 30, 255)
ZERO_FILL = (255, 255, 255, 255)
OUTLINE_COLOR = (0, 0, 0, 255)
OUTLINE_WIDTH = 3
CANCELLED_INDEX_COLOR = (255, 0, 0, 255)
CANCELLED_LEAD_ZEROS_COLOR = (150, 150, 150, 120)

MOD_INDICATOR_RADIUS = 100
MOD_INDICATOR_THICKNESS = 3
MOD_INDICATOR_DOT_RADIUS = 8
MOD_2_INDICATOR_LOCATION = WIDTH / 4, WIDTH / 8
MODS_5_7_INDICATOR_LOCATION = WIDTH * 3 / 4, WIDTH / 8
FADE_COEFFICIENT = 0.95


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


_mod_indicator_main_group = pyglet.graphics.Group(0)
_mod_indicator_highlight_group = pyglet.graphics.Group(1)


def draw_mod_indicator(modulus, remainder, center_x, center_y, radius, thickness, dot_radius, width_multiplier=1.5,
                       main_color=(150, 150, 150, 255), highlight_color=(0, 255, 0, 255), angle_offset=np.pi / 2,
                       inactive=False, batch=None):
    mod_indicator_shapes = [
        shapes.Arc(center_x, center_y, radius, thickness=thickness, color=main_color, batch=batch,
                   group=_mod_indicator_main_group)
    ]
    for i, angle in enumerate(np.linspace(angle_offset, angle_offset + 2 * np.pi, modulus, endpoint=False)):
        dot_center = center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius
        mod_indicator_shapes.append(
            shapes.Circle(*dot_center, dot_radius,
                          color=main_color, batch=batch,
                          group=_mod_indicator_main_group)
        )
        if remainder == i and not inactive:
            mod_indicator_shapes.append(
                shapes.Circle(*dot_center,
                              dot_radius * width_multiplier,
                              color=main_color if remainder == 0 else main_color,
                              batch=batch, group=_mod_indicator_highlight_group)
            )
            mod_indicator_shapes.append(
                shapes.Circle(*dot_center,
                              dot_radius * width_multiplier,
                              color=highlight_color if remainder == 0 else main_color,
                              batch=batch, group=_mod_indicator_highlight_group)
            )
            shapes_to_fade.append(mod_indicator_shapes[-1])

    if inactive:
        for shape in mod_indicator_shapes:
            shape.opacity = 100
    shapes_drawn.extend(mod_indicator_shapes)


def draw_high_arrow(active, center_x, center_y, length, thickness, thickness_multiplier=1.5,
                    main_color=(150, 150, 150, 255), highlight_color=(0, 255, 0, 255), batch=None):
    if active:
        thickness *= thickness_multiplier
    shapes_drawn.extend([
        shapes.Line(
            center_x, center_y - length / 2, center_x, center_y + length / 2,
            color=main_color, width=thickness, batch=batch),
        shapes.Line(
            center_x, center_y + length / 2, center_x + length / 4, center_y + length / 4,
            color=main_color, width=thickness, batch=batch),
        shapes.Line(
            center_x, center_y + length / 2, center_x - length / 4, center_y + length / 4,
            color=main_color, width=thickness, batch=batch),
        shapes.Circle(
            center_x, center_y + length / 2, thickness / 2, color=main_color, batch=batch),
    ])
    if active:
        active_part = [
            shapes.Line(
                center_x, center_y - length / 2, center_x, center_y + length / 2,
                color=highlight_color, width=thickness, batch=batch),
            shapes.Line(
                center_x, center_y + length / 2, center_x + length / 4, center_y + length / 4,
                color=highlight_color, width=thickness, batch=batch),
            shapes.Line(
                center_x, center_y + length / 2, center_x - length / 4, center_y + length / 4,
                color=highlight_color, width=thickness, batch=batch),
            shapes.Circle(
                center_x, center_y + length / 2, thickness / 2, color=highlight_color, batch=batch),
        ]
        shapes_drawn.extend(active_part)
        shapes_to_fade.extend(active_part)


def draw_binary_both(number, batch):
    binary = tuple(map(int, bin(number)[2:]))

    cancelled_indices = []
    for i, (digit, next_digit) in enumerate(zip(binary, binary[1:])):
        if next_digit != digit:
            cancelled_indices.append(i)
    cancelled_indices.append(len(binary) - 1)

    cancelled_lead_zeros = []
    for i, digit in enumerate(binary):
        if i not in cancelled_indices and digit == 0:
            cancelled_lead_zeros.append(i)
        elif i not in cancelled_indices:
            break

    if len(set(cancelled_lead_zeros + cancelled_indices)) == len(binary) and len(cancelled_lead_zeros) > 0:
        # everything is canceled but some of it was a lead zero
        # technically this isn't complete cancellation; it's a zero
        # so allow back in one of the lead zeros so that it reads as a zero
        cancelled_lead_zeros.pop(-1)

    binary_pruned = tuple(
        x for i, x in enumerate(binary) if i not in cancelled_indices and i not in cancelled_lead_zeros)
    draw_binary_squares(binary, (WIDTH - len(binary) * SQUARE_WIDTH) / 2, HEIGHT * 2 / 3, SQUARE_WIDTH,
                        ONE_FILL, ZERO_FILL, OUTLINE_COLOR, OUTLINE_WIDTH, batch=batch,
                        cancelled_indices=cancelled_indices, cancelled_lead_zeros=cancelled_lead_zeros)

    if len(binary_pruned) > 0:
        draw_binary_squares(binary_pruned, (WIDTH - len(binary_pruned) * SQUARE_WIDTH) / 2, HEIGHT / 3, SQUARE_WIDTH,
                            ONE_FILL, ZERO_FILL, OUTLINE_COLOR, OUTLINE_WIDTH, batch=batch)
    else:
        shapes_drawn.append(
            pyglet.text.Label('∅',
                              font_name='Times',
                              font_size=SQUARE_WIDTH,
                              x=WIDTH // 2, y=HEIGHT / 3,
                              anchor_x='center', anchor_y='baseline',
                              bold=True, batch=batch,
                              color=ZERO_FILL)
        )


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
num = None


def update_drawing(_):
    global main_batch, current_num_in_music, num
    if sequence_blues_milonga.current_num != num:
        num = sequence_blues_milonga.current_num
        value = A319419(num)
        main_batch = pyglet.graphics.Batch()
        shapes_drawn.clear()
        shapes_to_fade.clear()
        draw_binary_both(num, main_batch)
        draw_mod_indicator(2, value % 2, *MOD_2_INDICATOR_LOCATION, MOD_INDICATOR_RADIUS,
                           MOD_INDICATOR_THICKNESS, MOD_INDICATOR_DOT_RADIUS, inactive=value <= 0, batch=main_batch)
        draw_mod_indicator(5, value % 5, MODS_5_7_INDICATOR_LOCATION[0] - MOD_INDICATOR_RADIUS,
                           MODS_5_7_INDICATOR_LOCATION[1], MOD_INDICATOR_RADIUS, MOD_INDICATOR_THICKNESS,
                           MOD_INDICATOR_DOT_RADIUS, angle_offset=0, inactive=value <= 0, batch=main_batch)
        draw_mod_indicator(7, value % 7, MODS_5_7_INDICATOR_LOCATION[0] + MOD_INDICATOR_RADIUS,
                           MODS_5_7_INDICATOR_LOCATION[1], MOD_INDICATOR_RADIUS, MOD_INDICATOR_THICKNESS,
                           MOD_INDICATOR_DOT_RADIUS, angle_offset=math.pi, inactive=value <= 0, batch=main_batch)
        draw_high_arrow(value > 10, WIDTH / 2, MOD_2_INDICATOR_LOCATION[1], HEIGHT / 10, 10, batch=main_batch)
    else:
        for shape in shapes_to_fade:
            shape.opacity = int(shape.opacity * FADE_COEFFICIENT)


pyglet.clock.schedule_interval(update_drawing, 0.01)
threading.Thread(target=sequence_blues_milonga.main, daemon=True).start()
# Run the application
pyglet.app.run()
