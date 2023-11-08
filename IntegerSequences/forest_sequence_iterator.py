def forest_seq_gen():
    sequence_so_far = []
    while True:
        # going to check all possible arithmetic sequences, and keep a list of forbidden values
        forbidden_values = set()
        seq_len = len(sequence_so_far)  # precalculate to avoid redundancy
        for seq_step_size in range(1, len(sequence_so_far) // 2 + 1):
            # try every sequence step size up to half the length of the sequence so far
            # a and b are the first two terms of the sequence, looking back 2 and 1 step sizes respectively
            a, b = sequence_so_far[seq_len - 2 * seq_step_size], sequence_so_far[seq_len - seq_step_size]
            # forbid the value that would make a sequence
            forbidden_values.add(a + 2 * (b - a))
        new_value = 1
        while new_value in forbidden_values:
            new_value += 1
        yield new_value
        sequence_so_far.append(new_value)


if __name__ == '__main__':
    from itertools import islice
    print(list(islice(forest_seq_gen(), 1000)))