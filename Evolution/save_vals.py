from collections import defaultdict
import json


class SaveVals:

    def __init__(self):
        self.values_by_situation = defaultdict(list)

    def save(self, value, situation):
        self.values_by_situation[situation].append(value)
        return value

    def read(self, situation, i=0, how_many=1):
        return self.values_by_situation[situation][i: i + how_many]

    def consume(self, situation, i=0, how_many=1):
        return [self.values_by_situation[situation].pop(i) for _ in range(how_many)]

    @classmethod
    def load_from_json(cls, file_path):
        obj = cls()
        with open(file_path, 'r') as f:
            obj.values_by_situation = json.load(f)
        return obj

    def save_to_json(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.values_by_situation, f)
