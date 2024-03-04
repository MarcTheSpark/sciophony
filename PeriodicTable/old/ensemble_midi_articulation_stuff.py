from scamp import Session, ScampInstrument
from scamp_extensions.playback import MultiPresetInstrument

s = Session()

vibes = s.new_midi_part("IAC driver Bus 1")
piano = s.new_midi_part("IAC driver Bus 2")
bass = s.new_midi_part("IAC driver Bus 3")
cello = s.new_midi_part("IAC driver Bus 4")
# oboe = MultiPresetInstrument(s, "Oboe").add_preset(
#     "legato",
#     s.new_midi_part("IAC driver Bus 5", start_channel=1, num_channels=1),
#     make_default=True
# ).add_preset(
#     "staccato",
#     s.new_midi_part("IAC driver Bus 5", start_channel=2, num_channels=1),
# ).add_preset(
#     "vibrato",
#     s.new_midi_part("IAC driver Bus 5", start_channel=3, num_channels=1),
# )
oboe = s.new_midi_part("IAC driver Bus 5")
#
#
# def add_keyswitches(original_play_note_method, keyswitch_dict: {}, only_on_change=True):
#     last_preset = None
#
#     def wrapper(self, pitch, volume, duration, properties=None, preset="legato"):
#         nonlocal last_preset
#         if preset in keyswitch_dict and (preset != last_preset or not only_on_change):
#             original_play_note_method(self, keyswitch_dict[preset], volume, 0.1, blocking=False)
#             last_preset = preset
#         return original_play_note_method(self, pitch, volume, duration, properties=properties)
#     return wrapper
#
#
# oboe.play_note = add_keyswitches(oboe.play_note.__func__, {
#     "legato": 24,
#     "staccato": 26,
#     "vibrato": 28
# }).__get__(oboe, ScampInstrument)


while True:
    oboe.play_note(70, 0.8, 1.0, "param_24: 0")
    oboe.play_note(61, 0.8, 1.0, "param_24: 0.5")
    oboe.play_note(80, 0.8, 1.0, "param_24: 1.0 ")
drums = s.new_midi_part("IAC driver Bus 6")
contrabass = s.new_midi_part("IAC driver Bus 7")