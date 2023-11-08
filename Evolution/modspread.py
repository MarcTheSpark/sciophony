import numpy as np


def _get_linear_decay_array(length, spread):
    return np.array([max(0, 1 - x/spread) for x in range(length)])


def _get_symmetrical_linear_decay_array(length, spread):
    lda = _get_linear_decay_array(length, spread)
    return np.maximum(lda, np.concatenate(([lda[0]], lda[:0:-1])))


def _spread_mod_n(arr, n):
    new_array = np.zeros(len(arr) * n, dtype=arr.dtype)
    new_array[::n] = arr
    new_array.resize((n, len(arr)))
    return np.sum(new_array, axis=0)


def get_mod_n_spread_array(length, n, spread):
    return _spread_mod_n(_get_symmetrical_linear_decay_array(length, spread), n)
