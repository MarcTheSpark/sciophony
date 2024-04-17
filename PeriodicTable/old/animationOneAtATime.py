import time

import numpy as np
from marciano.periodictable import Element
import random
import pyglet
from pyglet.graphics import Batch
from periodic_table_music import PTableSonification, aradius, metalics, boilings, r_heats, negs, radios
from scamp_extensions.utilities import remap

from pyglet import shapes
from pyglet.text import Label


# Hyperparameters
WIDTH, HEIGHT = 1920, 1080
ELEMENT_WIDTH, ELEMENT_HEIGHT = 82, 85
ELEMENT_PADDING_X, ELEMENT_PADDING_Y = 10, 10
TABLE_ORIGIN_X, TABLE_ORIGIN_Y = 140, 50
LANTHENIDE_ORIGIN_X, LANTHENIDE_ORIGIN_Y = TABLE_ORIGIN_X + 2.7 * (ELEMENT_WIDTH + ELEMENT_PADDING_X), 660
LEGEND_DIM = 800, 100
LEGEND_ORIGIN = WIDTH / 2, 75


def get_element_position(period, group):
    if isinstance(group, int):
        x = TABLE_ORIGIN_X + (group - 1) * (ELEMENT_WIDTH + ELEMENT_PADDING_X)
        y = TABLE_ORIGIN_Y + (period - 1) * (ELEMENT_HEIGHT + ELEMENT_PADDING_Y)
    else:
        if group.startswith("La"):
            group_number = int(group[2:])
            x = LANTHENIDE_ORIGIN_X + (group_number - 1) * (ELEMENT_WIDTH + ELEMENT_PADDING_X)
            y = LANTHENIDE_ORIGIN_Y
        elif group.startswith("Ac"):
            group_number = int(group[2:])
            x = LANTHENIDE_ORIGIN_X + (group_number - 1) * (ELEMENT_WIDTH + ELEMENT_PADDING_X)
            y = LANTHENIDE_ORIGIN_Y + ELEMENT_HEIGHT + ELEMENT_PADDING_Y  # Place Actinides below Lanthanides
        else:
            x, y = 0, 0  # Default to upper left corner if something goes wrong
    return x, y


legend_drawables = []


def draw_discrete_legend(batch, center_x, y, width, height, title_font_size, label_font_size, labels_and_colors,
                         title="Electronegativity", patch_label_padding=14):
    x = center_x - width / 2
    legend_drawables.clear()

    # Draw title at the top of the legend area
    legend_drawables.append(Label(title, font_name='Times New Roman', font_size=title_font_size,
                                  x=x + width / 2, y=y + height, anchor_x='center', anchor_y='baseline',
                                  color=(255, 255, 255, 255), batch=batch))

    num_labels = len(labels_and_colors)
    spacing = 10  # Space between patches

    # Calculate size of each square patch
    # Assuming equal space for each label, adjust based on your application's specifics
    total_spacing = spacing * (num_labels - 1)
    total_label_width = sum([Label(text, font_size=label_font_size).content_width for text, _ in labels_and_colors])
    available_width_for_squares = width - total_spacing - total_label_width
    square_size = min(height*0.5, available_width_for_squares / num_labels)  # Each square's side length
    square_spacing_size = width / num_labels

    patch_x = x
    for label_text, color in labels_and_colors:
        # Draw color patch as a square
        draw_color_patch(batch, patch_x, y + height / 2 - square_size / 2, square_size, square_size, color)

        # Calculate the width of the label to adjust the position of the next color patch correctly
        label_width = Label(label_text, font_size=label_font_size).content_width
        label_x = patch_x + square_size + patch_label_padding

        # Draw label on the same row as the square
        legend_drawables.append(Label(label_text, font_name='Times New Roman', font_size=label_font_size,
                                      x=label_x, y=y + height/2, anchor_x='left', anchor_y='baseline',
                                      color=(255, 255, 255, 255), batch=batch))

        # Update patch_x for the next square-label pair, including space for the label
        patch_x += square_spacing_size + label_width + spacing  # Adjust spacing as needed


def draw_color_patch(batch, x, y, width, height, color):
    border_thickness = 1  # Adjust the thickness of the border here
    border_color = (200, 200, 200)  # RGB for grey

    # Draw the grey border as a larger rectangle
    legend_drawables.append(shapes.Rectangle(x - border_thickness, y - border_thickness, width + border_thickness * 2,
                                             height + border_thickness * 2, color=border_color, batch=batch))

    # Draw the colored patch on top, slightly smaller to create the border effect
    legend_drawables.append(shapes.Rectangle(x, y, width, height, color=color, batch=batch))


def draw_legend(batch, center_x, y, width, height, title_font_size, label_font_size, color1, color2, title="Electronegativity",
                label_low="Low", label_high="High"):
    x = center_x - width / 2
    legend_drawables.clear()
    # Calculate positions and sizes based on inputs
    gradient_height = height - title_font_size - label_font_size - 20  # Space for title and labels
    label_y = y + gradient_height + 5

    # Draw title
    legend_drawables.append(Label(title, font_name='Times New Roman', font_size=title_font_size,
                        x=x + width / 2, y=y + height, anchor_x='center', anchor_y='baseline',
                        color=(255, 255, 255, 255), batch=batch))

    # Draw gradient
    draw_gradient(batch, x, y + label_font_size + 15, width, gradient_height, color1, color2)

    # Draw labels
    legend_drawables.append(Label(label_low, font_name='Times New Roman', font_size=label_font_size,
                      x=x - 10, y=label_y, anchor_x='right', anchor_y='baseline',
                      color=(255, 255, 255, 255), batch=batch))
    legend_drawables.append(Label(label_high, font_name='Times New Roman', font_size=label_font_size,
                       x=x + width + 10, y=label_y, anchor_x='left', anchor_y='baseline',
                       color=(255, 255, 255, 255), batch=batch))


def interp_color(color1, color2, ratio):
    return tuple(int(color1[j] + (color2[j] - color1[j]) * ratio) for j in range(3)) + (255,)


def draw_gradient(batch, x, y, width, height, color1, color2, num_steps=50):
    step_width = width / num_steps
    for i in range(num_steps):
        ratio = i / num_steps
        color = interp_color(color1, color2, ratio)
        legend_drawables.append(shapes.Rectangle(x + i * step_width, y, step_width, height, color=color, batch=batch))


batch = Batch()  # Create a single batch for drawing
drawable_objects = []

window = pyglet.window.Window(WIDTH, HEIGHT)
elements = [Element(i) for i in range(1, 100)]


class ElementDrawables:

    def __init__(self, element, location=None, dimensions=(ELEMENT_WIDTH, ELEMENT_HEIGHT), main_font_size=36,
                 small_font_size=12):
        self.element = element
        if location is None:
            self.x, self.y = get_element_position(self.element.period, self.element.group)
        else:
            self.x, self.y = location
        self.width, self.height = dimensions
        self.main_font_size, self.small_font_size = main_font_size, small_font_size
        self.drawables = self.create_drawables()

    # Modify the draw_element function to create objects once and add them to the batch
    def create_drawables(self):
        x, y = self.x, self.y
        w, h = self.width, self.height
        adjusted_y = HEIGHT - y - h
        rectangle1 = pyglet.shapes.Rectangle(x, adjusted_y, w, h, color=(240, 240, 240),
                                            batch=batch)
        rectangle2 = pyglet.shapes.Rectangle(x+5, adjusted_y+5, w-10, h-10, color=(0, 0, 0),
                                            batch=batch)
        label_symbol = pyglet.text.Label(self.element.symbol,
                                         font_name='Times New Roman',
                                         font_size=self.main_font_size,
                                         x=x + w / 2, y=adjusted_y + h / 2,
                                         anchor_x='center', anchor_y='center',
                                         color=(240, 240, 240, 255),
                                         batch=batch)
        label_mass = pyglet.text.Label(str(self.element.atomic_mass),
                                       font_name='Times New Roman',
                                       font_size=self.small_font_size,
                                       x=x + 0.12 * w, y=adjusted_y + h - 0.12 * h * 0.3,
                                       anchor_x='left', anchor_y='top',
                                       color=(240, 240, 240, 255),
                                       batch=batch)

        return rectangle1, rectangle2, label_symbol, label_mass

    def set_visible(self, visible):
        for drawable in self.drawables:
            drawable.opacity = 255 if visible else 0

    def set_color(self, color):
        r, g, b, *alpha = [x / 255.0 for x in color]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        self.drawables[0].color = color
        for drawable in self.drawables[1:]:
            drawable.color = (0, 0, 0) if luminance > 0.5 else (255, 255, 255)


# Pre-create drawable objects for all elements
element_drawables = [ElementDrawables(element, (650, 170), (620, 740), 270, 60) for element in elements]

last = time.time()

years = (1700, 1789, 1820, 1869, 1932, 1945, 1986)
sonification = PTableSonification([2000])
# sonification.play(midi=True)
start_sonification = lambda dt: sonification.play(midi=True)

year_label = None


def set_element_colors(values, low_color, high_color):
    for ed, value in zip(element_drawables, remap(values, 0, 1)):
        if not np.isnan(value):
            ed.set_color(interp_color(low_color, high_color, value))
        else:
            ed.set_color((255, 255, 255))


def set_discrete_element_colors(values, value_colors: dict):
    for ed, value in zip(element_drawables, values):
        if value in value_colors:
            ed.set_color(value_colors[value])
        else:
            ed.set_color((255, 255, 255))


def new_year(current_year):
    global year_label
    year_label = pyglet.text.Label(
        str(current_year), font_name='Times New Roman', font_size=48, x=WIDTH / 2,
        y=0.94 * HEIGHT, color=(255, 255, 255, 255), anchor_x='center', anchor_y='top')

    if current_year <= 1700:
        set_discrete_element_colors(metalics, value_colors={0: (230, 232, 250), 1: (120, 199, 199), 2: (195, 98, 65)})
        draw_discrete_legend(batch, *LEGEND_ORIGIN, LEGEND_DIM[0] * 0.7, LEGEND_DIM[1], 25, 14,
                             (("Metal", (230, 232, 250)), ("Metalloid", (120, 199, 199)), ("Non-metal", (195, 98, 65))),
                             title="Metallic Character")
    elif current_year <= 1789:
        set_element_colors(boilings, (0, 0, 200), (255, 60, 0))
        draw_legend(batch, *LEGEND_ORIGIN, *LEGEND_DIM, 25, 14, (0, 0, 200), (255, 60, 0), title="Boiling Point")
    elif current_year <= 1820:
        set_element_colors(r_heats, (0, 0, 200), (255, 60, 0))
        draw_legend(batch, *LEGEND_ORIGIN, *LEGEND_DIM, 25, 14, (0, 0, 200), (255, 60, 0), title="Specific Heat",
                    label_low="Low", label_high="High")
    elif current_year <= 1869:
        set_element_colors(aradius, (0, 0, 200), (255, 60, 0))
        draw_legend(batch, *LEGEND_ORIGIN, *LEGEND_DIM, 25, 14, (0, 0, 200), (255, 60, 0), title="Atomic Radius", label_low="Small", label_high="Large")
    elif current_year <= 1932:
        set_element_colors(negs, (0, 0, 200), (255, 60, 0))
        draw_legend(batch, *LEGEND_ORIGIN, *LEGEND_DIM, 25, 14, (0, 0, 200), (255, 60, 0), title="Electronegativity",
                    label_low="Small", label_high="Large")
    else:
        set_discrete_element_colors(radios, value_colors={False: (20, 20, 20), True: (255, 255, 0)})
        draw_discrete_legend(batch, *LEGEND_ORIGIN, LEGEND_DIM[0] * 0.6, LEGEND_DIM[1], 25, 14,
                             (("Radioactive", (255, 255, 0)), ("Non-radioactive", (20, 20, 20))),
                             title="Radioactivity")


# new_year(sonification.current_year)


@window.event
def on_draw():
    global last, year_label
    last = time.time()
    window.clear()
    # if str(sonification.current_year) != year_label.text:
    #     new_year(sonification.current_year)

    for i, ed in enumerate(element_drawables):
        ed.set_visible(False)
        # if i + 1 in sonification.elements_played:
        #     ed.set_visible(True)
        # else:
        #     ed.set_visible(False)
    element_drawables[0].set_visible(True)
    # year_label.draw()
    batch.draw()  # Draw all elements in the batch


pyglet.clock.schedule_once(start_sonification, 0)
pyglet.app.run()
