# %% [markdown]
# # Sumo traffic sim outputs

# %% [markdown]
# ### Load D-RES package

# %%
import dres

# %% [markdown]
# ### Load two model variants (one looking at EV schedules, second looking at behaviour at charging stations)

# %%
sim_ev = dres.go('simulation-3-sumo-ev-timeseries')
sim_chrg = dres.go('simulation-4-sumo-station-timeseries')

# %% [markdown]
# ### List EVs with longest SoC records

# %%
sim_ev.ev.list_most_common_ev_entries().head(20)

# %% [markdown]
# ### Plot SoC timeline for a single EV 

# %%
sim_ev.plots.ev.plot_ev_soc('morning119')

# %% [markdown]
# ### Plot SoC timeline for a single charging station

# %%
sim_chrg.plots.ev.plot_ev_soc('cs_5')

# %%



