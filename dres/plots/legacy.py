import matplotlib.pyplot as plt
import numpy as np

"""
LEGACY PLOTTING FUNCTIONS FROM ORIGINAL DEVELOPMENT OF DRES (WQ, 2025)
"""

# --------------------------------------- STORM CONDITIONS ---------------------------------------
def storm_conditions(storm_wind_speeds):
    plt.figure(figsize=(10, 6))
    plt.plot(np.arange(0, 24), storm_wind_speeds)
    plt.title('Wind Speed Variation over 24 Hours during a Storm')
    plt.xlabel('Hours')
    plt.ylabel('Wind Speed (m/s)')
    plt.grid(True)
    plt.show()

    return plt
