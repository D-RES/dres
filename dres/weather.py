#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
`weather.py`
{DESCRIPTION TO FOLLOW}
"""


###############################################################################################################
# Standard Python Libraries
import numpy as np
# Custom Libraries
from .dafni_utilities import message_api


###############################################################################################################


def simulate_storm_wind_speed(duration_hours=24, peak_wind_speed=30, normal_wind_speed=10):
    """Simulate wind speed increasing and decreasing during a storm."""
    hours = np.arange(0, duration_hours)
    # Wind speed increases from normal to peak and then decreases
    wind_speeds = np.piecewise(hours,
                               [hours <= duration_hours // 3,
                                (hours > duration_hours //
                                 3) & (hours <= 2 * duration_hours // 3),
                                hours > 2 * duration_hours // 3],
                               [lambda x: normal_wind_speed + (peak_wind_speed - normal_wind_speed) * (x / (duration_hours // 3)),
                                lambda x: peak_wind_speed,
                                lambda x: peak_wind_speed - (peak_wind_speed - normal_wind_speed) * ((x - 2 * duration_hours // 3) / (duration_hours // 3))])
    return wind_speeds
