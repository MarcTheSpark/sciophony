
def play_melody_line(inst, sequence, scale, analysis_cycle=8):
    for i in itertools.count():
        if i % analysis_cycle == 0:
            next_values = [sequence(n) % 6 for n in range(i, i + analysis_cycle)]
            sorted_by_freq = sort_by_frequency(set(next_values))
            positions_to_play = sorted([next_values.index(note) for note in sorted_by_freq[-3:-1]])
            notes_to_play = sorted_by_freq[-2:]
            wait(positions_to_play[0] * 0.25)
            inst.play_note(scale[notes_to_play[0] + 12], 1, (positions_to_play[1] - positions_to_play[0]) * 0.25)
            inst.play_note(scale[notes_to_play[1] + 12], 1, (analysis_cycle - positions_to_play[1]) * 0.25)

fork(play_melody_line, args=(clarinet, A319419_symmetry, blues_scale))
