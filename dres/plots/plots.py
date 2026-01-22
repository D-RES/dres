from . import evs as evs_plots
from . import network as network_plots
from . import weather as weather_plots
from . import io as io_plots


# Submodule wrapper class
class _SubmoduleWrapper():
    """
    Wrapper for a plotting submodule that automatically passes parent DRES instance.
    
    This allows syntax like: sim.plots.ev.plot_departure_histogram()
    which calls: evs_plots.plot_departure_histogram(sim)
    """
    
    def __init__(self, parent, module):
        self._parent = parent
        self._module = module
    
    def __getattr__(self, name):
        """
        When a function is accessed, return a wrapper that passes parent as first arg.
        """
        if hasattr(self._module, name):
            func = getattr(self._module, name)
            def wrapper(*args, **kwargs):
                return func(self._parent, *args, **kwargs)
            return wrapper
        raise AttributeError(f"module '{self._module.__name__}' has no attribute '{name}'")


# Plots container class
class Plots():
    """
    Container class that provides access to plotting functions organized by category.
    
    Usage:
        sim = DRES()
        sim.plots.ev.plot_departure_histogram()  # Calls evs_plots.plot_departure_histogram(sim)
        sim.plots.weather.wind_scatter3d()  # Calls weather_plots.wind_scatter3d(sim)
        sim.plots.network.network_map()  # Calls network_plots.network_map(sim)
        sim.plots.io.from_df()  # Calls io_plots.from_df(sim)
    """
    
    def __init__(self, parent):
        self._parent = parent
        
        # Expose submodules as wrapped objects that auto-pass parent
        self.ev = _SubmoduleWrapper(parent, evs_plots)
        self.weather = _SubmoduleWrapper(parent, weather_plots)
        self.network = _SubmoduleWrapper(parent, network_plots)
        self.io = _SubmoduleWrapper(parent, io_plots)
