#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
`DRES_Sim.py`

This class definition represents a single D-RES simulation instance, and includes
various runtime paramters specific to a that run. Multiple `dres_sim` objects can 
be created as part of any generic workflow, to compare results from different 
runs (within the same Python session). 

When calling the constructor (e.g. `sim = DRES_Sim()`), the user should specify the
following parameters:
    - ev_model
    - start_date
    - end_date
    - charging_price
    - discharging_price
    - pop_size
    - max_iter
    - initial_soc
    - delta_t
    - capacity
    - min_soc
    - max_soc
    - vehicle_power
"""


###############################################################################################################
# Standard Python Libraries
import os
import ast
import socket
import yaml

# Custom Libraries
from dres.dafni_utilities import IO_file_paths, performance, message_api, generate_run_metadata
import dres.nemo as nemo
import dres.base_model as base_model

###############################################################################################################


class DRES_Sim():
    # Gather simulation parameters from system environment variables
    
    def __init__(self, 
                # Defaults
                ev_model = "include_evs",
                start_date = '2019-01-07',
                end_date = '2019-01-07',
                charging_price = "[148.7,127.4,125.3,111.5,112.1,125.4,141.1,161.2,156.2,158.8,153.7,144.9,146.8,141.8,136.2,136.7,295.6,298.6,282.2,163.8,147.8,137.7,125.3,120.3]",
                discharging_price = "[148.7,127.4,125.3,111.5,112.1,125.4,141.1,161.2,156.2,158.8,153.7,144.9,146.8,141.8,136.2,136.7,295.6,298.6,282.2,163.8,147.8,137.7,125.3,120.3]",
                pop_size = 10,
                max_iter = 10,
                initial_soc = 0.3,
                delta_t = 1,
                capacity = 16.45,
                min_soc = 0.1,
                max_soc = 0.9,
                vehicle_power = 0.011,
                rescale_load = 1.0,
                data_root = None,
                input_dir = 'inputs',
                legacy = False,
            ):
        
        # Interpret environment variables, second argument specifies default, 
        # these are only used during local testing (Jupyter & Docker Desktop),
        # DAFNI defaults are applied in `model_definition.yaml`
        self.ev_model = os.getenv("ev_model", ev_model)
        self.start_date = os.getenv('start_date', start_date)
        self.end_date = os.getenv('end_date', end_date)
        self.charging_price = os.getenv("charging_price", charging_price)
        self.discharging_price = os.getenv("discharging_price", discharging_price)
        self.pop_size = os.getenv("pop_size", pop_size)
        self.max_iter = os.getenv("max_iter", max_iter)
        self.initial_soc = os.getenv("initial_soc", initial_soc)
        self.delta_t = os.getenv("delta_t", delta_t)
        self.capacity = os.getenv("capacity", capacity)
        self.min_soc = os.getenv("min_soc", min_soc)
        self.max_soc = os.getenv("max_soc", max_soc)
        self.vehicle_power = os.getenv("vehicle_power", vehicle_power)
        self.rescale_load =  os.getenv("rescale_load", rescale_load)

        # Type setting
        self.start_date = self.start_date.replace("''","'")
        self.end_date = self.end_date.replace("''","'")
        self.charging_price = ast.literal_eval(self.charging_price)
        self.discharging_price = ast.literal_eval(self.discharging_price)
        self.pop_size = int(self.pop_size)
        self.max_iter = int(self.max_iter)
        self.initial_soc = float(self.initial_soc)
        self.delta_t = float(self.delta_t)
        self.capacity = float(self.capacity)
        self.min_soc = float(self.min_soc)
        self.max_soc = float(self.max_soc)
        self.vehicle_power = float(self.vehicle_power)
        self.rescale_load = float(self.rescale_load)

        # Set code performance start time
        self.t0 = performance(always_verbose=True)

        # Set paths to data
        self.INPUT_FOLDER, self.OUTPUT_FOLDER = IO_file_paths(data_root=data_root, input_dir=input_dir)

        # Determine whether Windows or Unix
        if os.name == 'nt':
            self.machine_id = "Windows"
        else:
            self.machine_id = socket.gethostname()
        
        # Run conditions
        self.input_dir = input_dir
        self.legacy = legacy

        # Gather assets
        self.assets = nemo.load_yaml(dir=self.INPUT_FOLDER, filename="assets")

        with open(os.path.join(self.OUTPUT_FOLDER,'assets.yaml'), 'w') as f:
            yaml.dump(self.assets, f)
        
        
    # Main run sequence
    def build_baseline_model(self):
        message_api(msg="# Build baseline power network model")
        

        # LEGACY VAR - TO BE DELETED
        weather_state="normal"
        storm_wind_speeds=None
        slack_p_nom=None

        network = base_model.create_pypsa_network()
        base_model.create_bus_network(network, self)
        base_model.create_transmission_network(network, self)
        base_model.add_loads_to_network(network, self)
        base_model.add_wind_turbines_to_network(network, self, weather_state, storm_wind_speeds)
        base_model.add_generators_to_network(network, self.assets)
        base_model.add_storage_to_network(network, self)
        base_model.define_transformers(network, self)
        base_model.add_shunts_to_network(network, self)
        base_model.add_offshore_marine_to_network(network, self)
        base_model.add_slack_control(network, self)

        return network

