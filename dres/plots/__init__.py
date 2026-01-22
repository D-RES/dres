"""
Plotting module for DRES.

Organized into submodules:
- evs: EV-related plotting functions
- weather: Wind and weather plotting functions  
- network: Network map plotting functions
- io: General I/O plotting functions
- legacy: Legacy plotting functions

The Plots class provides a convenient interface that automatically
passes the DRES instance to plotting functions.
"""

from .plots import Plots

# Re-export commonly used functions for convenience
from .evs import plot_departure_histogram, ev_charge_rate, ev_soc_timeline

__all__ = ['Plots', 'plot_departure_histogram', 'ev_charge_rate', 'ev_soc_timeline']
