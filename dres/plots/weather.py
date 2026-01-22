import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os


from ..nemo import load_yaml
from ..api import openmeteo

# PACKAGED PLOTTING FUNCTIONS
#--------------------------------------- WIND ---------------------------------------

def wind_comparison(title, turbine1, turbine2):
    plt.figure(figsize=(10, 6))
    t = turbine1['data'].index
    x = pd.to_datetime(t).to_list()
    y = turbine1['data'].to_list()
    plt.plot(x, y, label=turbine1['name'], color='blue')
    t = turbine2['data'].index
    x = pd.to_datetime(t).to_list()
    y = turbine2['data'].to_list()
    plt.plot(x, y, label=turbine2['name'], color='red', linestyle='--')
    plt.title(f'Power Output Comparison for {title}')
    plt.ylabel('Power (MW)')
    plt.legend()
    dtFmt = mdates.DateFormatter('%H:%M\n%d-%b')  # define the formatting
    # apply the format to the desired axis
    plt.gca().xaxis.set_major_formatter(dtFmt)
    plt.grid(True)
    plt.show()

def wind_scatter3d(network):

    # Identify all wind assets
    all_generators = network.generators_t.p_set.keys().to_list()
    wind_turbines_list = [str for str in all_generators if "Wind" in str]
    farm = [int(str.split("_")[1]) for str in wind_turbines_list]
    turbine = [int(str.split("_")[-1]) for str in wind_turbines_list]
    wind_turbines_hover = [wt.replace(
        '_Turbine', '<br>Turbine') for wt in wind_turbines_list]
    wind_turbines_hover = [wt.replace('WindFarm_', 'WF')
                           for wt in wind_turbines_hover]
    wind_turbines_hover = [wt.replace('_', ' ') for wt in wind_turbines_hover]

    # Reorder list of wind assets by (1) Farm, (2) Turbine. (This is unsorted when as a "_" separated string)
    turbines = pd.DataFrame({
        'name': wind_turbines_list,
        'hover': wind_turbines_hover,
        'farm': farm,
        'turbine': turbine,
        'clr': '#000',
    })
    turbines.sort_values(['farm', 'turbine'], ascending=[
                         True, True], inplace=True)
    turbines.reset_index(drop=True, inplace=True)

    # Create colourscale
    farm_ids = turbines.farm.unique()
    L = len(farm_ids)
    clrs = px.colors.sample_colorscale('HSV', L, 0, 1)
    for i in range(L):
        turbines.loc[turbines['farm'] == farm_ids[i], 'clr'] = clrs[i]

    traces = []
    i = 0
    for index, turbine in turbines.iterrows():
        t = network.generators_t.p_set[turbine['name']].index
        x = pd.to_datetime(t).to_list()
        z = network.generators_t.p_set[turbine['name']].to_list()
        y = i * np.ones(len(x))
        text = [f"{turbine['hover']}" for j in range(len(x))]
        traces.append(go.Scatter3d(
            # x=x,y=y,z=z,
            x=x, y=y, z=z,
            mode="lines",
            name=turbine['name'],
            text=text,
            hovertemplate='%{text}<extra>%{x}<br>%{z}MW</extra>',
            line=dict(
                color=turbine['clr'],
                width=5,
            )
        ))
        i += 1
    layout = go.Layout(
        title="Fig. 1: Wind turbine output under storm conditions",
        height=650,
        scene=dict(
            aspectmode="manual",
            aspectratio=dict(x=1.5, y=1, z=.65),
            camera=dict(
                eye=dict(x=-0.1, y=-1.5, z=0.4),
                center=dict(x=-0.1, y=0, z=-0.25),
                # projection=dict(type="orthographic")
            ),
            xaxis=dict(title=''),
            yaxis=dict(title='', showticklabels=False),
            zaxis=dict(title='Turbine Power [MW]'),
        ),
        showlegend=False
    )
    fig = go.Figure(traces, layout)
    return fig

def wind_raw_data(INPUT_FOLDER, asset_name, freq="h"):

    assets = load_yaml(dir=INPUT_FOLDER, filename="assets")

    fullfilename = os.path.join(
        INPUT_FOLDER, assets['WindFarms'][asset_name]['file'])
    df = pd.read_csv(fullfilename)
    date_range = pd.date_range(
        start=f"2019-01-01 00:00", periods=len(df), freq=freq)
    df.index = date_range

    # Access weather API (OpenMeteo) for wind data
    hourly_weather = openmeteo(
        latitude=assets['WindFarms'][asset_name]['lat'],
        longitude=assets['WindFarms'][asset_name]['lon'],
        start_date=date_range[0].strftime('%Y-%m-%d'),
        end_date=date_range[-1].strftime('%Y-%m-%d'),
        fields=["wind_speed_10m", "wind_speed_100m", "wind_gusts_10m"]
    )

    trace = go.Scatter(
        x=df.index,
        y=df['ActivePower'] * assets['WindFarms'][asset_name]['rescale'],
        name=f"Single turbine output at {asset_name}",
        xaxis='x',
        yaxis='y',
    )
    trace_cap = go.Scatter(
        x=[df.index[0], df.index[-1]],
        y=[assets['WindFarms'][asset_name]['turbine_output'],
            assets['WindFarms'][asset_name]['turbine_output']],
        mode='none',
        fill="tozeroy",
        fillcolor="rgba(99, 110, 250, .25)",
        name=f"Installed capacity (as fraction of farm)",
        xaxis='x',
        yaxis='y',
    )
    trace_wind10 = go.Scatter(
        x=hourly_weather.index,
        y=hourly_weather.wind_speed_10m,
        name=f"Wind speed 10m",
        xaxis='x',
        yaxis='y2',
    )
    trace_wind100 = go.Scatter(
        x=hourly_weather.index,
        y=hourly_weather.wind_speed_100m,
        name=f"Wind speed 100m",
        xaxis='x',
        yaxis='y2',
    )
    trace_gusts10 = go.Scatter(
        x=hourly_weather.index,
        y=hourly_weather.wind_gusts_10m,
        name=f"Wind gusts 10m",
        xaxis='x',
        yaxis='y2',
    )
    farmname = assets['WindFarms'][asset_name]['name']
    n_turbines = assets['WindFarms'][asset_name]['n_turbines']
    farm_capacity = assets['WindFarms'][asset_name]['farm_output']
    layout = go.Layout(
        title=f"{asset_name}: {farmname} data, 1 of {n_turbines} turbines ({farm_capacity}MW farm capacity)",
        height=900,
        legend=dict(orientation="h"),
        plot_bgcolor='#fff',
        yaxis=dict(domain=[0.05, 0.5], gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor='#000000',
                   linewidth=1, linecolor='#000000', ticks='outside', showline=True, title="Active Power [MW]"),
        yaxis2=dict(domain=[0.55, 1.], gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor='#000000',
                    linewidth=1, linecolor='#000000', ticks='outside', showline=True, title="Wind speed [km/h]"),
        xaxis=dict(gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1,
                   zerolinecolor='#000000', ticks='outside', showline=True),
    )
    return go.Figure([trace_wind10, trace_wind100, trace_gusts10, trace_cap, trace], layout)

def wind_raw_data_curve(INPUT_FOLDER, asset_name, freq="h"):

    assets = load_yaml(dir=INPUT_FOLDER, filename="assets")

    fullfilename = os.path.join(
        INPUT_FOLDER, assets['WindFarms'][asset_name]['file'])
    df = pd.read_csv(fullfilename)
    date_range = pd.date_range(
        start=f"2019-01-01 00:00", periods=len(df), freq=freq)
    df.index = date_range

    # Access weather API (OpenMeteo) for wind data
    hourly_weather = openmeteo(
        latitude=assets['WindFarms'][asset_name]['lat'],
        longitude=assets['WindFarms'][asset_name]['lon'],
        start_date=date_range[0].strftime('%Y-%m-%d'),
        end_date=date_range[-1].strftime('%Y-%m-%d'),
        fields=["wind_speed_10m", "wind_speed_100m", "wind_gusts_10m"]
    )

    
    trace_powercurve10 = go.Scatter(
        x=hourly_weather.wind_speed_10m,
        y=df['ActivePower'] * assets['WindFarms'][asset_name]['rescale'],
        mode='markers',
        marker=dict(opacity=0.4, size=2),
        xaxis='x',
        yaxis='y',
        showlegend=False,
    )
    trace_powercurve100 = go.Scatter(
        x=hourly_weather.wind_speed_100m,
        y=df['ActivePower'] * assets['WindFarms'][asset_name]['rescale'],
        mode='markers',
        marker=dict(opacity=0.4, size=2),
        xaxis='x2',
        yaxis='y',
        showlegend=False,
    )

    farmname = assets['WindFarms'][asset_name]['name']
    n_turbines = assets['WindFarms'][asset_name]['n_turbines']
    farm_capacity = assets['WindFarms'][asset_name]['farm_output']
    layout = go.Layout(
        title=f"{asset_name}: {farmname} data, 1 of {n_turbines} turbines ({farm_capacity}MW farm capacity)",
        height=500,
        legend=dict(orientation="h", yanchor='top', y=1.05),
        margin=dict(t=120),
        plot_bgcolor='#fff',
        yaxis=dict(gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor='#000000',
                   showline=False, title="Active Power [MW]"),
        xaxis=dict(domain=[0., 0.45], gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1,
                   zerolinecolor='#000000', ticks='outside', showline=False, title="Wind speed @10m [km/h]"),
        xaxis2=dict(domain=[0.55, 1.], gridcolor="#ccc", showgrid=True, zeroline=True, zerolinewidth=1,
                   zerolinecolor='#000000', ticks='outside', showline=False, title="Wind speed @100m [km/h]"),
    )
    return go.Figure([trace_powercurve10, trace_powercurve100], layout)
