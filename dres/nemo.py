#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
`NeMo.py` ('NetworkModel')
This is a utility library for parsing input data for power network models, specifically PyPSA-based models.
This allows **static** data definitions via a YAMML file, and avoids hard-coded model context within runtime
script(s). In particular, this avoids use of the network.add() operation to define model components.
"""


###############################################################################################################
# Standard Python Libraries
import yaml
import os
# Custom Libraries
from .dafni_utilities import message_api, performance


###############################################################################################################


def load_yaml(dir="", filename=""):
    t0 = performance()

    # Handle extension (can be included or omitted in call)
    filename = f'{filename.replace(".yaml", "")}.yaml'

    # Full filename
    ffilename = os.path.join(dir, filename)

    # Open and parse, if exists
    with open(ffilename) as stream:
        try:
            out = yaml.safe_load(stream)
            
            performance(t0)
            return out
        except yaml.YAMLError as exc:
            # message_api(f'Exception raised while attempting to load `{ffilename}`: {exc}.')
            
            performance(t0)
            return None


def define_assets(network, assets, asset_class=None):

    # Handle pluralised asset class name (arg. can be specified plural/singular)
    if asset_class[-3:] == "ses":
        asset_name = f"{asset_class.rstrip('ses')}s"
        asset_class = f'{asset_name}es'
    elif asset_class[-1:] == "s":
        asset_name = asset_class.rstrip('s')
        asset_class = f'{asset_name}s'

    try:
        for K in assets[asset_class].keys():
            # Live console messages
            properties = assets[asset_class][K]

            # Add new network object
            network.add(asset_class.rstrip('s'), name=K,
                        **assets[asset_class][K])
    except:
        return None
