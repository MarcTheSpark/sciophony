"""
Defines the ensemble which is imported by all the other playback versions.
"""

from scamp import Session

STREAM_MIDI_TO_LOGIC = False
SPEED_FACTOR = 1  # * 178 / 190

try:
    s = Session(default_soundfont="MuseScore_General", tempo=190 * SPEED_FACTOR)
except ValueError:
    s = Session(tempo=190)
# s.print_default_soundfont_presets()

s.timing_policy = "relative"  # 0.7

if STREAM_MIDI_TO_LOGIC:
    kit = s.new_midi_part("Drum Kit", "IAC Driver Bus 1")
    bass = s.new_midi_part("Bass", "IAC Driver Bus 2")
    piano = s.new_midi_part("Piano", "IAC Driver Bus 3")
    sax = s.new_midi_part("Saxophone", "IAC Driver Bus 4")
    orch_hit = s.new_midi_part("Orchestra Hit", "IAC Driver Bus 5")
    strings = s.new_midi_part("Strings", "IAC Driver Bus 6", num_channels=7)
    marimba = s.new_midi_part("Marimba", "IAC Driver Bus 7")
    metro_kit = s.new_midi_part("Metronome Kit", "IAC Driver Bus 8")
else:
    kit = s.new_part("STANDARD")
    bass = s.new_part("Fingered Bass")
    piano = s.new_part("Piano")
    sax = s.new_part("Saxophone")
    orch_hit = s.new_part("Orchestra hit")
    strings = s.new_part("strings", num_channels=7)
    marimba = s.new_part("marimba")
    metro_kit = s.new_part("STANDARD")