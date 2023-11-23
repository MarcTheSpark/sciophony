import numpy as np
from dataclasses import dataclass
from scamp import *
import math

s = Session().run_as_server()

flute = s.new_part("flute")
piano = s.new_part("piano")

class Entity:
    
    def start_playing(self):
        pass  # print(f"{type(self)} started at {self.location}")
        
    def continue_playing(self):
        pass  # print(f"{type(self)} continuing at {self.location}")
    
    def stop_playing(self):
        pass  # print(f"{type(self)} stopped at {self.location}")


@dataclass
class Box(Entity):
    
    location: tuple[int, int]
    
    masks = [np.array([[0, 0, 0, 0],
                       [0, 2, 1, 0],
                       [0, 1, 1, 0],
                       [0, 0, 0, 0]])]
    
    color = (255, 255, 0)  # YELLOW
    
    volume_env = Envelope([0.8, 0.35], [2])
    
    def __post_init__(self):
        self.note = None
    
    def start_playing(self):
        self.note = flute.start_note(85 - self.location[1], self.volume_env, {"param_10": self.location[0] / 36})
    
    def stop_playing(self):
        self.note.end()
    

@dataclass
class Beehive(Entity):
    
    location: tuple[int, int]
    
    masks = [np.array([[0, 0, 0, 0, 0, 0],
                       [0, 0, 1, 1, 0, 0],
                       [0, 1, -1, 0, 1, 0],
                       [0, 0, 1, 1, 0, 0],
                       [0, 0, 0, 0, 0, 0]]),
             np.array([[0, 0, 0, 0, 0],
                       [0, 0, 1, 0, 0],
                       [0, 1, -1, 1, 0],
                       [0, 1, 0, 1, 0],
                       [0, 0, 1, 0, 0],
                       [0, 0, 0, 0, 0]])]
    
    color = (0, 100, 255)  # BLUE
    
    

@dataclass
class Blinker(Entity):
    
    location: tuple[int, int]
    
    masks = [np.array([[0, 0, 0, 0, 0],
                       [0, 1, 2, 1, 0],
                       [0, 0, 0, 0, 0]]),
             np.array([[0, 0, 0],
                       [0, 1, 0],
                       [0, 2, 0],
                       [0, 1, 0],
                       [0, 0, 0]])]

    color = (130, 255, 130)  # GREEN
    
    def __post_init__(self):
        self.phase = 1
        self.note = None
        self.time_alive = 0
 
    def get_volume(self):
        x = self.time_alive / 10
        return 0.4 * math.sin(x) ** 2 + 0.3 * math.atan(x)
        
    def start_playing(self):
        self.note = piano.start_note(100 - self.location[1] + self.phase,
                                     self.get_volume(),
                                     {"param_10": self.location[0] / 36})

    def continue_playing(self):
        self.note.end()
        self.phase = 1 - self.phase
        self.time_alive += 1
        self.note = piano.start_note(100 - self.location[1] + self.phase,
                                     self.get_volume(),
                                     {"param_10": self.location[0] / 36})
    
    def stop_playing(self):
        self.note.end()
        
   
@dataclass
class Glider(Entity):
    
    location: tuple[int, int]
    
    masks = [np.array([[0, 0, 0, 0, 0],
                       [0, 0, 0, 1, 0],
                       [0, 1, -1, 1, 0],
                       [0, 0, 1, 1, 0],
                       [0, 0, 0, 0, 0]]),
             np.array([[0, 0, 0, 0, 0],
                       [0, 1, 0, 0, 0],
                       [0, 0, 2, 1, 0],
                       [0, 1, 1, 0, 0],
                       [0, 0, 0, 0, 0]]),
             np.array([[0, 0, 0, 0, 0],
                       [0, 0, 1, 0, 0],
                       [0, 0, -1, 1, 0],
                       [0, 1, 1, 1, 0],
                       [0, 0, 0, 0, 0]]),
             np.array([[0, 0, 0, 0, 0],
                       [0, 1, 0, 1, 0],
                       [0, 0, 2, 1, 0],
                       [0, 0, 1, 0, 0],
                       [0, 0, 0, 0, 0]])]
    
    color = (255, 150, 150)  # PINK


# -------------------- Extra processing ---------------------

# add rotations to glider masks
original_rotations = list(Glider.masks)
for rotation_times in range(1, 4):
    for glider_mask in original_rotations:
        Glider.masks.append(np.rot90(glider_mask, rotation_times))

entity_types = [Box, Beehive, Blinker, Glider]
