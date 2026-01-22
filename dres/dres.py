from .config import get_or_create_config
from pathlib import Path

from .plots import Plots
from .ev import EV


# DRES class to hold paths and other global settings
class Paths():

    def __init__(self, verbose=True):

        # Initialise `dres` object with data_root location
        cfg = get_or_create_config()
        self.data_root = Path(cfg['paths']['data_root'])
        self.inputs = self.data_root / 'inputs'
        self.outputs = self.data_root / 'outputs'
        
        # Prompt user on data_root location and how to change it
        if verbose:
            print(f"D-RES is configured to access data stored here: {self.data_root}.")
            print(f'To change this path, use:  dres.config.update_data_root("{str(Path.home() / "...")}")\n')


# DRES main class
class DRES():

    def __init__(self):
        
        # Initialise `dres` object with data_root location
        self.verbose = False
        self.paths = Paths(verbose=self.verbose)
        self.ev = EV(self)
        self.plots = Plots(self)
    