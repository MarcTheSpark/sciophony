import numpy as np
from dataclasses import dataclass
from scamp import *
from scamp_extensions.pitch import Scale
import math
from global_settings import *

s = Session().run_as_server()

bamboo = s.new_osc_part("bamboo", 57120)
woodTap = s.new_osc_part("woodTap", 57120)
bee = s.new_osc_part("bee", 57120)
ocarina = s.new_osc_part("ocarina", 57120)
whale = s.new_osc_part("whale", 57120)
cricket = s.new_osc_part("cricket", 57120)


@dataclass
class Entity:
    
    location: tuple[int, int]
    
    mask_match: int = None  # which mask did it match with

    mask_rotations = ()

    scale = Scale.chromatic(60)

    @property
    def rx(self):
        return self.location[0] / GRID_SIZE[0]
    
    @property
    def ry(self):
        return self.location[1] / GRID_SIZE[1]
    
    @property
    def rpos(self):
        return self.rx, self.ry

    def dist_from_scope_center(self):
        return math.dist(self.location, MICROSCOPE_CENTER) / MICROSCOPE_RADIUS

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

    def get_pitch(self):
        return self.scale.round(85 - 35 * self.ry)
    
    def start_playing(self):
        self.note = bamboo.start_note(self.get_pitch(), self.volume_env,
                                      {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})
    
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
        return int(self.scale.round(92 - 30 * self.ry))
    
    def intro_gesture(self):
        for pitch in range(self.get_pitch() - 3,self.get_pitch()):
            bee.play_note(pitch, 0.7, FRAMEDUR, {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})
        self.intro_done = True

    def start_playing(self):
        s.fork(self.intro_gesture)
    
    def continue_playing(self):
        if self.sustained_note is None and self.intro_done:
            self.sustained_note = bee.start_chord(
                [self.get_pitch(),self.get_pitch()+2],
                0.6,
                {"param_pan": self.rx}
            )
     
    def stop_playing(self):
        if self.sustained_note is not None:    
            self.sustained_note.end()
            bee.play_note(self.get_pitch() - 6,
                              0.9,
                              FRAMEDUR,
                              {"param_pan": self.rx})


@dataclass
class Loaf(Entity):
        
    masks = [np.array([[0, 1, 1, 0],
                       [1, 0, -1, 1],
                       [0, 1, 0, 1],
                       [0, 0, 1, 0]])]

    mask_rotations = (1, 2, 3)  # add 90, 180, and 270 degree mask rotation

    color = (255, 0, 255)  # PURPLE

    def __post_init__(self):
        self.note = None
 
    def get_pitch(self):
        return int(self.scale.round(70 - self.ry * 20))

    def start_playing(self):
        self.note = whale.start_note(self.get_pitch(), 0.7, {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})
     
    def stop_playing(self):
        self.note.end()


@dataclass
class Beacon(Entity):
    masks = [np.array([[1, 1, 0, 0],
                       [1, 2, 0, 0],
                       [0, 0, 1, 1],
                       [0, 0, 1, 1]]),
             np.array([[1, 1, 0, 0],
                       [1, -1, 0, 0],
                       [0, 0, 0, 1],
                       [0, 0, 1, 1]])]

    mask_rotations = (1,)  # add 90, 180, and 270 degree mask rotation

    color = (100, 100, 255)

    def __post_init__(self):
        self.note = None

    def get_pitch(self):
        return int(self.scale.round(110 - self.ry * 20))

    def start_playing(self):
        self.note = cricket.start_note(self.get_pitch(), 0.7,
                                     {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})

    def stop_playing(self):
        self.note.end()


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

    def get_pitch(self):
        return int(self.scale.round(100 - 50 * self.ry)) + self.phase

    def start_playing(self):
        self.note = woodTap.start_note(self.get_pitch(),
                                       self.get_volume(),
                                       {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})

    def continue_playing(self):
        self.note.end()
        self.phase = 1 - self.phase
        self.time_alive += 1
        self.note = woodTap.start_note(self.get_pitch(),
                                       self.get_volume(),
                                       {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})
    
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
        return 85 - 30 * self.ry

    def start_playing(self):
        self.sustained_note = ocarina.start_note(self.get_pitch(),
                                                 0.7,
                                                 {"param_pan": self.rx, "param_dist": self.dist_from_scope_center() / 2})
        
    def continue_playing(self):
        self.life_span += FRAMEDUR
        pitch = self.get_pitch()
        if pitch != self.last_pitch:
            self.sustained_note.change_pitch(pitch)
            self.sustained_note.change_parameter("pan", self.rx)
            self.sustained_note.change_parameter("dist", self.dist_from_scope_center() / 2)
        self.last_pitch = pitch
        
    def stop_playing(self):
        s.fork(self.end_gesture)
        
    def end_gesture(self):
        end_gesture_length = min(5, max(5 * FRAMEDUR, self.life_span))
        self.sustained_note.change_parameter("dist", 1,  min(5, end_gesture_length), -2)
        self.sustained_note.change_pitch(
            self.get_pitch() + 10 if self.direction == 1 else self.get_pitch() - 10,
            end_gesture_length
        )
        wait(end_gesture_length)
        self.sustained_note.end()


# -------------------- Extra processing ---------------------

entity_types = [Box, Beehive, Blinker, Glider, Loaf, Beacon]


# add rotations to glider masks
for entity_type in entity_types:
    original_rotations = list(entity_type.masks)
    for rotation_times in entity_type.mask_rotations:
        for entity_mask in original_rotations:
            entity_type.masks.append(np.rot90(entity_mask, rotation_times))

