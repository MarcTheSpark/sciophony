"""
This plays the recording of snapshots of which individuals are active, made by evolution_on_thread.py.
"""

from evolution_on_thread import *


evolution_recording = EvolutionMusicRecording("recorded_snapshots.pk")


STREAM_MIDI_TO_LOGIC = False


# s.print_default_soundfont_presets()

s.timing_policy = "relative"  # 0.7


def play_disturbances(disturbances):
    for x in disturbances:
        lh = [int(50 - 10 * x), int(55 - 10 * x), int(60 - 10 * x)]
        rh = [int(67 + 10 * x), int(72 + 10 * x), int(77 + 10 * x)]
        orch_hit.play_chord(lh + rh if x else None, 0.4 + 0.6 * x, 0.5)


s.start_transcribing([strings])
# s.fast_forward()

while True:
    if evolution_recording.is_fast_forwarding():
        evolution_recording.advance_beat(12)
        continue

    for species, loop_object in evolution_recording.playing_individuals.items():
        if species in ('kick', 'snare', 'hihat'):
            fork(loop_object.play_bar)
        elif species == 'kick_bass':
            fork(loop_object.play_bassline)
        elif species == 'snare_piano':
            fork(loop_object.play_comp_chords)
        elif species == 'hihat_sax':
            fork(loop_object.play_melody)
        elif species == 'kick_end':
            fork(loop_object.play_bassline_end)
        elif species == 'snare_harmony':
            fork(loop_object.play_harmony)
        elif species == 'hihat_marimba':
            fork(loop_object.play_arpeggios)
    if not np.all(evolution_recording.disturbances == 0):
        fork(play_disturbances, (evolution_recording.disturbances,))

    try:
        evolution_recording.advance_beat(12)
    except IndexError:
        # at end of recording
        break
    wait(12)

s.stop_transcribing().to_score(time_signature="3/4").export_music_xml("Notation/strings3.musicxml")