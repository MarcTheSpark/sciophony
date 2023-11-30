import numpy as np
from dataclasses import dataclass
from scamp import *
import math
from global_settings import *

s = Session().run_as_server()

flute = s.new_part("flute")
piano = s.new_part("piano")
bassoon = s.new_part("bassoon")
drums = s.new_part("Power")
whistle =s.new_part("whistle")


@dataclass
class Entity:
    
    location: tuple[int, int]
    
    mask_match: int = None  # which mask did it match with

    mask_rotations = ()

    @property
    def rx(self):
        return self.location[0] / GRID_SIZE[0]
    
    @property
    def ry(self):
        return self.location[1] / GRID_SIZE[1]
    
    @property
    def rpos(self):
        return self.rx, self.ry
    
    def start_playing(self):
        pass  # print(f"{type(self)} started at {self.location}")
        
    def continue_playing(self):
        pass  # print(f"{type(self)} continuing at {self.location}")
    
    def stop_playing(self):
        pass  # print(f"{type(self)} stopped at {self.location}")




@dataclass
class Box(Entity):
        
    masks = [np.array([[0, 0, 0, 0],
                       [0, 2, 1, 0],
                       [0, 1, 1, 0],
                       [0, 0, 0, 0]])]
    
    color = (255, 255, 0)  # YELLOW
        
    volume_env = Envelope([0.8, 0.35], [2])
    
    def __post_init__(self):
        self.note = None
    
    def start_playing(self):
        self.note = flute.start_note(85 - self.location[1], self.volume_env, {"param_10": self.rx})
    
    def stop_playing(self):
        self.note.end()
    

@dataclass
class Beehive(Entity):
        
    masks = [np.array([[0, 0, 0, 0, 0, 0],
                       [0, 0, 1, 1, 0, 0],
                       [0, 1, -1, 0, 1, 0],
                       [0, 0, 1, 1, 0, 0],
                       [0, 0, 0, 0, 0, 0]])]

    mask_rotations = (1,)  # add 90 degree mask rotation

    
    color = (0, 100, 255)  # BLUE
    

    def __post_init__(self):
       
        self.sustained_note = None
        self.intro_done = False
 
    def get_pitch(self):
        return 80 - self.location[1]
    
    def intro_gesture(self):
        for pitch in range(self.get_pitch()-3,self.get_pitch()):
            bassoon.play_note(pitch, 0.7, FRAMEDUR, {"param_10": self.rx})
        self.intro_done = True

    def start_playing(self):
        s.fork(self.intro_gesture)
    
    def continue_playing(self):
        if self.sustained_note is None:
            self.sustained_note = bassoon.start_chord(
                [self.get_pitch(),self.get_pitch()+2],
                0.6,
                {"param_10": self.rx}
            )
     
    def stop_playing(self):
        if self.sustained_note is not None:    
            self.sustained_note.end()
            bassoon.play_note(self.get_pitch() - 6,
                              0.9,
                              FRAMEDUR,
                              {"param_10": self.rx})

@dataclass
class Blinker(Entity):
        
    masks = [np.array([[0, 0, 0, 0, 0],
                       [0, 1, 2, 1, 0],
                       [0, 0, 0, 0, 0]])]
    
    mask_rotations = (1,)  # add 90 degree mask rotation

    color = (130, 255, 130)  # GREEN
    
    mask_match: int = None  # which mask did it match with

    
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
                                     {"param_10": self.rx})

    def continue_playing(self):
        self.note.end()
        self.phase = 1 - self.phase
        self.time_alive += 1
        self.note = piano.start_note(100 - self.location[1] + self.phase,
                                     self.get_volume(),
                                     {"param_10": self.rx})
    
    def stop_playing(self):
        self.note.end()
        
   
@dataclass
class Glider(Entity):
        
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
    
    mask_rotations = (1, 2, 3)  # add 90, 180, and 270 degree mask rotations
    
    color = (255, 150, 150)  # PINK
    
    mask_match: int = None  # which mask did it match with (initially)

    def __post_init__(self):
        self.sustained_note = None
        self.intro_done = False
        self.last_pitch = None
        self.direction = 1 if 4 <= self.mask_match < 12 else 0
        self.life_span = FRAMEDUR
 
    def get_pitch(self):
        return int(100 - 40 * self.ry)

    def start_playing(self):
        self.sustained_note = whistle.start_note(self.get_pitch(),
                                                 0.7,
                                                 {"param_10": self.rx})
        
    def continue_playing(self):
        self.life_span += FRAMEDUR
        pitch = self.get_pitch()
        if pitch != self.last_pitch:
            self.sustained_note.change_pitch(pitch, 0.5)
            self.sustained_note.change_parameter("10", self.rx, 0.5)
        self.last_pitch = pitch
        
    def stop_playing(self):
        s.fork(self.end_gesture)
        
    def end_gesture(self):
        end_gesture_length = min(5, max(5 * FRAMEDUR, self.life_span))
        self.sustained_note.change_volume(0,  min(5, end_gesture_length))
        self.sustained_note.change_pitch(
            self.get_pitch() + 20 if self.direction == 1 else self.get_pitch() - 20,
            end_gesture_length
        )
        wait(end_gesture_length)
        self.sustained_note.end()



# -------------------- Extra processing ---------------------

entity_types = [Box, Beehive, Blinker, Glider]


# add rotations to glider masks
for entity_type in entity_types:
    original_rotations = list(entity_type.masks)
    for rotation_times in entity_type.mask_rotations:
        for entity_mask in original_rotations:
            entity_type.masks.append(np.rot90(entity_mask, rotation_times))

