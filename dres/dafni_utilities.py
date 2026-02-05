#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
`dafni_utilities.py`
This is a utility library testing and deploying models on the Data Analytics Facility for National
Infrastructure (DAFNI). Functions include `performance`, `message_api` and `test_api` for live console messages
over API to the https:\\energymodels.eng.ed.ac.uk/dafni_tools platform.
"""


###############################################################################################################
# Standard Python Libraries
import time
import requests
import json
import inspect
import os
import socket
from datetime import datetime

###############################################################################################################



def performance(t0=None, msg="", always_verbose=False, verbose=False):
    """
    Print calling function and corresponding performance.
    """

    if verbose is None:
        verbose = os.getenv("verbose_console", "True").lower() in ("true", "1", "yes")

    if verbose or always_verbose:
        if t0 is None:
            t0 = time.perf_counter()
            if verbose is None:
                print("Runtime performance:")
            return t0
        else:
            t1 = time.perf_counter()
            if msg != "":
                msg = f" {msg} [finished in {t1 - t0 :0.4f} seconds]"
            else:
                try:
                    msg = f" ⎔ (`{inspect.stack()[1][3]}`, called from `{inspect.stack()[2][3]}`) {msg}- finished in {t1 - t0 :0.4f} seconds)"
                except:
                    msg = f" ⎔ {msg}- finished in {t1 - t0 :0.4f} seconds)"
            print(msg)
            try:
                message_api(msg)
            except:
                None
            return t1
    else:
        return None


def message_api(msg):

    try:
        # Determine whether Windows or Unix
        if os.name == 'nt':
            host_name = "Windows"
        else:
            host_name = socket.gethostname()

        
        try:
            called_by_function = inspect.stack()[2][3]
        except:
            called_by_function = ""

        payload = json.dumps({
            'text': msg,
            'function': called_by_function,
            'hostname': host_name
        })
        headers = {'Content-Type': "application/json",
                'Accept': "application/json"}
        requests.put("https://energymodels.eng.ed.ac.uk/dafnitools/api/",
                    data=payload, headers=headers)

    except:
        None


def test_api():

    headers = {'Content-Type': "application/json",
               'Accept': "application/json"}
    return requests.post("http://localhost:8002/dafnitools/api/test/", headers=headers)


def generate_run_metadata(run_metadata, OUTPUT_FOLDER):

    run_metadata['timestamp'] = datetime.strftime(datetime.now(), format="%Y-%m-%d %H:%M:%S")

    # Save run_metadata.json
    fname = os.path.join(OUTPUT_FOLDER, 'run_metadata.json')
    try:
        run_metadata['save_method'] = 1
        with open(fname, 'w', encoding='utf-8') as f:  
            json.dump(run_metadata, f, ensure_ascii=False, indent=4)
    except:
        run_metadata['save_method'] = 2
        with open(fname, 'w', encoding='utf-8') as f:  
            json.dump(json.dumps(run_metadata), f, ensure_ascii=False, indent=4)

    return None