TEMPO = 150
LUNAR_MONTH_IN_DAYS = 29.53059
WEEK_IN_DAYS = 7
# NOTE: The duration of EARTH_YEAR is a little larger than it should be due to the imprecision in numerical integration
# in the solar system model (we're taking the planet starting points and integrating once a day to get new position and
# velocity, assuming acceleration only comes from the sun.
EARTH_YEAR = 365.473
# we base the beat on earth year, as through we're observing the cosmos at regular dates as we move around the sun
DAYS_PER_BEAT = EARTH_YEAR / 8  # LUNAR_MONTH_IN_DAYS  # 90
START_OFFSET = 10  # in days, from when the model was calculated.
