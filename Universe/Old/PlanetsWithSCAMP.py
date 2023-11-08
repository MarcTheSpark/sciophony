import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from astropy.time import Time
from astroquery.jplhorizons import Horizons
from scamp import *


sim_start_date = "2018-01-01"     # simulating a solar system starting from this date
# sim_duration = 2 * 365                # (int) simulation duration in days
m_earth = 5.9722e24 / 1.98847e30  # Mass of Earth relative to mass of the sun
m_moon = 7.3477e22 / 1.98847e30
view_radius = 30.0


class Object:                   # define the objects: the Sun, Earth, Mercury, etc
    def __init__(self, name, r, v):
        self.name = name
        self.r    = np.array(r, dtype=np.float64)
        self.v    = np.array(v, dtype=np.float64)


class SolarSystem:
    
    def __init__(self, thesun, start_time):
        self.thesun = thesun
        self.planets = []
        self.time = start_time
        
    def add_planet(self, planet):
        self.planets.append(planet)
        
    def evolve(self):           # evolve the trajectories
        dt = 1.0
        self.time += dt
        
        for p in self.planets:
            p.r += p.v * dt
            acc = -2.959e-4 * p.r / np.sum(p.r**2)**(3./2)  # in units of AU/day^2
            p.v += acc * dt


ss = SolarSystem(Object("Sun", [0, 0, 0], [0, 0, 0]), start_time=Time(sim_start_date).jd)

for i, nasaid in enumerate([1, 2, 3, 4, 5, 6, 7, 8]):  # The 1st, 2nd, 3rd, 4th planet in solar system
    obj = Horizons(id=nasaid, location="@sun", epochs=ss.time).vectors()
    ss.add_planet(Object(nasaid,
                         [np.double(obj[xi]) for xi in ['x', 'y', 'z']], 
                         [np.double(obj[vxi]) for vxi in ['vx', 'vy', 'vz']]))
#     ax.text(0, - (texty[i] + 0.1), names[i], color=colors[i], zorder=1000, ha='center', fontsize='large')

s = Session()


def do_animation_no_visual():
    while True:
        wait(0.02)
        ss.evolve()
    

def do_animation_with_visual():
    s.run_as_server()
    plt.style.use('dark_background')
    fig = plt.figure(figsize=[9, 9])
    ax = plt.axes([0., 0., 1., 1.], xlim=(-view_radius, view_radius), ylim=(-view_radius, view_radius))
    ax.set_aspect('equal')
    ax.axis('off')
    
    sun_scatter = ax.scatter(0, 0, color="yellow", s=30)
    planets_scatter = ax.scatter([p.r[0] for p in ss.planets],
                                 [p.r[1] for p in ss.planets], color="white", s=5)
    
    def animate(i):
        planets_scatter.set_offsets([p.r[:2] for p in ss.planets])
        return planets_scatter,
    
    s.fork(do_animation_no_visual)
    ani = animation.FuncAnimation(fig, animate, repeat=True, blit=True, interval=20)
    plt.show()


# ---------------- PUT SCAMP CODE HERE --------------

piano = s.new_part("piano")

def scamp_main():
    while True:
        dist_earth_mars = np.linalg.norm(ss.planets[3].r - ss.planets[2].r)
        piano.play_note(90 - 30 * dist_earth_mars, 0.5 / dist_earth_mars, 0.2)

# ---------------------------------------------------
fork(scamp_main)
do_animation_with_visual()
# do_animation_no_visual()
