import math
import random
import time


class FreshnessTracker:

    def __init__(self, time_func=time.time, half_life=3, reset_time=math.inf):
        """
        Tracks how fresh different values are; i.e. how long since we've seen them. Freshness is restored exponentially
        over time.

        :param time_func: the function to query to know what time it is.
        :param half_life: time until half of the value's freshness is restored
        :param reset_time: time at which freshness is fully restored (otherwise it would never quite return)
        """
        self._tracked_values = {}
        self.time = time_func
        self.half_life = half_life
        self.reset_time = reset_time

    def freshness(self, value, log_value=True):
        current_time = self.time()
        if value not in self._tracked_values or current_time - self._tracked_values[value] > self.reset_time:
            if log_value: self._tracked_values[value] = current_time
            return 1
        else:
            freshness = 1 - 2 ** -((current_time - self._tracked_values[value]) / self.half_life)
            if log_value: self._tracked_values[value] = current_time
            return freshness

    def tracked_freshness_values(self):
        return {self.freshness(x) for x in self._tracked_values}


