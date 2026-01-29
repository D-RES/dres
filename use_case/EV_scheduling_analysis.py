# %% [markdown]
# # EV Scheduling

# %% [markdown]
# Load the `dres` package. (If this fails, `dres` hasn't been installed yet - add a temporary cell below and run `!pip install -e .`, after which the cell can be deleted)

# %%
import dres

# %% [markdown]
# Initialise `dres`. Various functions and properties can be accessed through `sim.{tab-completion}`. For example:

# %%
sim = dres.go()
sim.ev.load_ev_data(ev_data_file='ev_schedule_data_reflex.csv', type_of_schedule='charge_event') # Load
sim.ev.schedule_data                                            # View all data

# %% [markdown]
# ---

# %% [markdown]
# ## 1. Saghetti model (legacy approach)

# %% [markdown]
# ### 1.1 Examine patterns in arrival/departure times and duration unplugged (single vehicle)

# %% [markdown]
# We can choose to load specific EV data, to inspect what it contains, before use this data:

# %%
sim.ev.load_ev_data(ev_data_file='processed_ev_usage.csv', type_of_schedule='journey')      # Load
sim.ev.schedule_data                                            # View all data

# %% [markdown]
# For a single EV, we want to see histograms of all departure (unplug) and arrival (plug-in) events, along with a heatmapped across the full time range, showing the number of hours day that the vehicle is unplugged.

# %%
sim.plots.ev.plot_departure_histogram()

# %% [markdown]
# ### 1.2 State of charge (single vehicle)

# %% [markdown]
# #### 1.2.1 Estimate EV Charge Rate (CR)

# %% [markdown]
# Using the arrive/depart events, find the maxium charge gradient steepness. 
# 
# This is intended to highlight occasions when the EV is unplugged before it is fully charged. On these occasions, we know that the SOC was still increasing at the moment before the EV was unplugged, we can therefore isolate a known time period and a known SOC differential - hence the estimated charge rate (CR).
# 
# This does not account for smart charging (i.e. this routine may under-estimate the CR on occasions where the charging process is interrupted by a control signal, but it cannot over-estimate the CR); however, if we find a notable distribution of high-valued CR on the right-hand side of the histogram, this gives a good estimate of the maximum CR.

# %%
sim.ev.load_ev_data(ev_data_file='processed_ev_usage.csv', type_of_schedule='journey')      # Load
sim.plots.ev.ev_charge_rate()

# %% [markdown]
# #### 1.2.2 Plot EV SoC timeline

# %%
max_ev_charge_rate = 0.000137
sim.plots.ev.ev_soc_timeline(max_ev_charge_rate)

# %% [markdown]
# ---

# %% [markdown]
# ## 2. ReFLEX Data

# %% [markdown]
# ### 2.1 Examine patterns in arrival/departure times and duration unplugged (single vehicle)

# %%
sim_reflex = dres.go()
sim_reflex.ev.load_ev_data(ev_data_file='ev_schedule_data_reflex.csv', type_of_schedule='charge_event') # Load
sim_reflex.ev.schedule_data                                            # View all data

# %%
sim_reflex.ev.list_most_common_ev_entries()

# %%
sim_reflex.plots.ev.plot_departure_histogram(bin_minutes=10, ev_id='EV0065')

# %% [markdown]
# ### 2.2 State of charge (single vehicle)

# %% [markdown]
# #### 2.2.1 Estimate EV Charge Rate (CR)

# %%
sim_reflex.plots.ev.ev_charge_rate(ev_id='EV0065')

# %% [markdown]
# #### 2.2.2 Plot EV SoC timeline

# %%
max_ev_charge_rate = 0.00000001775 # small value forced
sim_reflex.plots.ev.ev_soc_timeline(max_ev_charge_rate, ev_id='EV0094')

# %%



