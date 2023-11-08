import re
from itertools import count


def A319419(n):
    """
    In binary expansion of n, delete one symbol from each run. Set a(n)=-1 if the result is the empty string.
    """
    s = ''.join(d[:-1] for d in re.split('(0+)|(1+)', bin(n)[2:]) if d not in {'', '0', '1', None})
    return -1 if s == '' else int(s, 2)


def A319419_generator(start_n, stop_n=None):
    """
    Generator version of A319419, starting at the start_n'th term
    """
    for n in range(start_n, stop_n) if stop_n else count(start_n):
        yield A319419(n)


if __name__ == '__main__':
    print([A319419(i) for i in range(100)])
