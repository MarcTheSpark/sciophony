import random
from collections import defaultdict
import json


def list_to_tuple(obj):
    # Base case: if obj is not a list, return it as is
    if not isinstance(obj, list):
        return obj
    # Recursive case: if obj is a list, convert each element to tuple
    return tuple(list_to_tuple(item) for item in obj)


class SaveRandom:

    def __init__(self, x=None, mode="saving", randgen=random):
        self.randgen = randgen
        random.seed(x)
        self.situation_states = defaultdict(list)
        self.current_mode = mode

    def apply_situation(self, situation, read_at: int = None):
        if self.current_mode == "saving":
            self.situation_states[situation].append(self.randgen.getstate())
        else:
            if situation in self.situation_states and len(self.situation_states[situation]) > (0 if read_at is None else read_at):
                self.randgen.setstate(
                    list_to_tuple(self.situation_states[situation].pop(0)) if read_at is None
                    else list_to_tuple(self.situation_states[situation][read_at])
                )

    def seed(self, x):
        self.randgen.seed(x)

    def random(self, situation=None, read_at=None):
        self.apply_situation(situation, read_at)
        return self.randgen.random()

    def randint(self, a, b, situation=None, read_at=None):
        self.apply_situation(situation, read_at)
        return self.randgen.randint(a, b)

    def choice(self, seq, situation=None, read_at=None):
        self.apply_situation(situation, read_at)
        return self.randgen.choice(seq)

    def choices(self, population, weights=None, *, cum_weights=None, k=1, situation=None, read_at=None):
        self.apply_situation(situation, read_at)
        return self.randgen.choices(population, weights=weights, cum_weights=cum_weights, k=k)

    @classmethod
    def load_from_json(cls, file_path, seed=None):
        obj = cls(seed)
        obj.current_mode = "reading"
        with open(file_path, 'r') as f:
            obj.situation_states = json.load(f)
        return obj

    def save_to_json(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.situation_states, f)
