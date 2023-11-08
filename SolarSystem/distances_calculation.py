import itertools
from marciano.solar_system_model2 import SolarSystem, planets


DAYS_PER_BEAT = 90

# subsequent runs: load the precalculated solarSystem model from memory
ss = SolarSystem.load_from_npy("solarSystemModel.npz")

min_planet_distances = {tuple(sorted([p1, p2])): float("inf") for p1, p2 in itertools.combinations(planets, 2)}
max_planet_distances = {tuple(sorted([p1, p2])): 0 for p1, p2 in itertools.combinations(planets, 2)}

for i in range(100000):
    snapshot = ss[i]
    for p1, p2 in itertools.combinations(planets, 2):
        dist = snapshot.get_distance(p1, p2)
        pair = tuple(sorted([p1, p2]))
        if dist < min_planet_distances[pair]:
            min_planet_distances[pair] = dist
        if dist > max_planet_distances[pair]:
            max_planet_distances[pair] = dist


print(min_planet_distances)
print("---------------------------")
print(max_planet_distances)