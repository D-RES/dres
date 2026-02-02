# %% [markdown]
# # Analysys of Spaghetti Model data and real data

# %% [markdown]
# ### Load `dres` package

# %%
import dres

# %% [markdown]
# Initialise `dres` instance(s) - include single positional argument directing the call towards the appropriate `simulation-#.yaml`. Once initialised, various functions and properties can be accessed through `sim.{tab-completion}`. For example:

# %%
sim_mod = dres.go('simulation-1-spaghetti')
sim_data = dres.go('simulation-2-reflex')

# %% [markdown]
# ---

# %% [markdown]
# ## 1. Saghetti model (legacy approach)

# %% [markdown]
# ### 1.1 Examine patterns in arrival/departure times and duration unplugged (single vehicle)

# %% [markdown]
# For a single EV, we want to see histograms of all departure (unplug) and arrival (plug-in) events, along with a heatmapped across the full time range, showing the number of hours day that the vehicle is unplugged.

# %%
sim_mod.plots.ev.plot_departure_histogram()

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
sim_mod.plots.ev.ev_charge_rate()

# %% [markdown]
# #### 1.2.2 Plot EV SoC timeline

# %%
max_ev_charge_rate = 0.000137
sim_mod.plots.ev.ev_soc_timeline(max_ev_charge_rate)

# %% [markdown]
# ---

# %% [markdown]
# ## 2. ReFLEX Data

# %% [markdown]
# ### 2.1 Examine patterns in arrival/departure times and duration unplugged (single vehicle)

# %%
sim_data.ev.list_most_common_ev_entries()

# %%
sim_data.plots.ev.plot_departure_histogram(bin_minutes=10, ev_id='EV0065')

# %% [markdown]
# ### 2.2 State of charge (single vehicle)

# %% [markdown]
# #### 2.2.1 Estimate EV Charge Rate (CR)

# %%
sim_data.plots.ev.ev_charge_rate(ev_id='EV0065')

# %% [markdown]
# #### 2.2.2 Plot EV SoC timeline

# %%
max_ev_charge_rate = 0.00000001775  # small value forced
sim_data.plots.ev.ev_soc_timeline(max_ev_charge_rate, ev_id='EV0094')

# %%



