from scamp import Session

s = Session()

vibes = s.new_midi_part("IAC driver Bus 1")
piano = s.new_midi_part("IAC driver Bus 2")
bass = s.new_midi_part("IAC driver Bus 3")
cello = s.new_midi_part("IAC driver Bus 4")
oboe = s.new_midi_part("IAC driver Bus 5")
drums = s.new_midi_part("IAC driver Bus 6")
contrabass = s.new_midi_part("IAC driver Bus 7")
synth = s.new_midi_part("IAC driver Bus 8")