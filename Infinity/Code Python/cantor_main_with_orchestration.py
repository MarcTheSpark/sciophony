from cantor_orchestration import CantorChords, CantorMelody, MetronomeSwell, default_environment
import itertools
from scamp import *


MIDI_PLAYBACK = False
MIDI_EXPORT = False  # "CantorMidi.mid"

# Affects all melodies/metronomes/etc. (scales duration)
default_environment.scaling_factor = 2.4092913453966096
# print(4 / default_environment.tripling_time * 60)  # calculate bpm 

s = Session(tempo=48.18582690793219)

if MIDI_PLAYBACK:
    piano = s.new_midi_part("piano","IAC driver BUS 1")
    piano.send_midi_cc(64,1)
    perc = s.new_midi_part("power","IAC driver BUS 2")
    guitar = s.new_midi_part("nylon guitar","IAC driver BUS 3")
    flute = s.new_midi_part("flute","IAC driver BUS 4")
    bass = s.new_midi_part("bass","IAC driver BUS 5")
    drum_kit = s.new_midi_part("drum kit", "IAC driver BUS 6")
else:
    piano = s.new_part("piano")
    piano.send_midi_cc(64,1)
    perc = s.new_part("power")
    guitar = s.new_part("nylon guitar")
    flute = s.new_part("flute")
    bass = s.new_part("bass")
    drum_kit = s.new_part("power")  #s.new_midi_part("drum kit", "IAC driver BUS 6")


if MIDI_EXPORT:
    s.start_transcribing()
    s.fast_forward()


def start_pitch(i):
    i %= 11
    return 92 - 12 * (i // 2) - 7 * (i % 2)


def cantor_cascade(how_many, volume=0.33, min_note_dur=0.008, decay_coefficient=0.33):
    for i in range(how_many):
        fork(CantorMelody(piano, start_pitch(i), min_note_dur=min_note_dur, volume_function=lambda i, dur: volume * dur ** decay_coefficient).play)
        wait(default_environment.tripling_time)
    wait_for_children_to_finish()
    

def log_tripling():
    i = 0
    while True:
        print(f"{i} tripling times")
        tripling_indicator.play_note(60 + (2 * i) % 8, 1.0, 0.25, blocking=False)
        wait(default_environment.tripling_time)
        i += 1


# fork(log_tripling)

guitar_chords = [(58, 63, 68), (61, 63, 64)]

score = [
    (0, lambda: cantor_cascade(2, 0.7)),
    (0, CantorMelody(bass, 37,intervals= [0], further_scaling=9, max_segments=16).play),
    (4.5, CantorChords(guitar, guitar_chords, max_segments=4).play),
    (7, CantorMelody(flute, start_pitch(0),further_scaling=3, max_segments=32).play),
    (10, CantorChords(guitar, guitar_chords, max_segments=2).play),
    (13, lambda: cantor_cascade(4, 0.8)),
    (13, CantorChords(guitar, guitar_chords, max_segments=8).play),
    (24, CantorMelody(bass, 42,intervals= [0], further_scaling=9).play),
    (25, CantorChords(guitar, guitar_chords, max_segments=16).play),
    (26, CantorMelody(flute, start_pitch(0),further_scaling=3, max_segments=32).play),
    (28, lambda: cantor_cascade(7, 0.9, 0.007, 0.3)),
    (45, lambda: cantor_cascade(11, 0.9, 0.005, 0.25)),
]
 
 
swell_envelope= Envelope([0.2, 1.0, 0], [1.5, 2.5],[-1, -3])


swells = [
    MetronomeSwell(perc, 70, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
    MetronomeSwell(perc, 71, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
    MetronomeSwell(perc, 54, swell_envelope, subdivision_depth=0, play_condition=lambda i: i % 3 !=0),
    MetronomeSwell(perc, 79, swell_envelope/2, subdivision_depth=0, play_condition=lambda i: i % 3 !=0)
]

for i, swell in enumerate(itertools.cycle(swells)):
    score.append((i, swell.play))
    if i > 65:
        break


#More, bigger perc sounds


score.sort(key=lambda e: e[0])


# play score
t = 0
for tripling_t, func in score:
    wait((tripling_t - t) * default_environment.tripling_time)
    fork(func)
    t = tripling_t
    
wait_for_children_to_finish()

s.stop_transcribing().export_to_midi_file(MIDI_EXPORT)
