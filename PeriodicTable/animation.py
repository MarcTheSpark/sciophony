import time
from marciano.periodictable import Element
import random
import pyglet
from pyglet.graphics import Batch
from periodic_table_music import PTableSonification

# Hyperparameters
WIDTH, HEIGHT = 1920, 1080
ELEMENT_WIDTH, ELEMENT_HEIGHT = 92, 100
ELEMENT_PADDING_X, ELEMENT_PADDING_Y = 10, 10
TABLE_ORIGIN_X, TABLE_ORIGIN_Y = 50, 50
LANTHENIDE_ORIGIN_X, LANTHENIDE_ORIGIN_Y = 305, 750


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


# Assuming the rest of your setup remains the same...

batch = Batch()  # Create a single batch for drawing
drawable_objects = []

window = pyglet.window.Window(WIDTH, HEIGHT)
elements = [Element(i) for i in range(1, 100)]


class ElementDrawables:

    def __init__(self, element):
        self.element = element
        self.drawables = self.create_drawables()

    # Modify the draw_element function to create objects once and add them to the batch
    def create_drawables(self):
        x, y = get_element_position(self.element.period, self.element.group)
        adjusted_y = HEIGHT - y - ELEMENT_HEIGHT
        rectangle = pyglet.shapes.Rectangle(x, adjusted_y, ELEMENT_WIDTH, ELEMENT_HEIGHT, color=(50, 50, 250),
                                            batch=batch)
        label_symbol = pyglet.text.Label(self.element.symbol,
                                         font_name='Times New Roman',
                                         font_size=36,
                                         x=x + ELEMENT_WIDTH / 2, y=adjusted_y + ELEMENT_HEIGHT / 2,
                                         anchor_x='center', anchor_y='center',
                                         batch=batch)
        label_mass = pyglet.text.Label(str(self.element.atomic_mass),
                                       font_name='Times New Roman',
                                       font_size=12,
                                       x=x + ELEMENT_PADDING_X, y=adjusted_y + ELEMENT_HEIGHT - ELEMENT_PADDING_Y,
                                       anchor_x='left', anchor_y='top',
                                       batch=batch)

        return rectangle, label_symbol, label_mass

    def set_visible(self, visible):
        for drawable in self.drawables:
            drawable.opacity = 255 if visible else 0


# Pre-create drawable objects for all elements
element_drawables = [ElementDrawables(element) for element in elements]

last = time.time()

sonification = PTableSonification()
sonification.play()

year_label = pyglet.text.Label(str(sonification.current_year), font_name='Times New Roman', font_size=48, x=WIDTH / 2,
                               y=0.94 * HEIGHT, color=(255, 255, 255, 255), anchor_x='center', anchor_y='top')


@window.event
def on_draw():
    global last, year_label
    for i, ed in enumerate(element_drawables):
        if i + 1 in sonification.elements_played:
            ed.set_visible(True)
        else:
            ed.set_visible(False)
    last = time.time()
    window.clear()
    if str(sonification.current_year) != year_label.text:
        year_label = pyglet.text.Label(
            str(sonification.current_year), font_name='Times New Roman', font_size=48, x=WIDTH / 2,
            y=0.94 * HEIGHT, color=(255, 255, 255, 255), anchor_x='center', anchor_y='top')
    year_label.draw()
    batch.draw()  # Draw all elements in the batch



pyglet.app.run()


