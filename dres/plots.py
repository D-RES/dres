import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import plotly.express as px
from geographiclib.geodesic import Geodesic

from .nemo import load_yaml
from .api import openmeteo

geod = Geodesic.WGS84

# KQ


def storm_conditions(storm_wind_speeds):
    plt.figure(figsize=(10, 6))
    plt.plot(np.arange(0, 24), storm_wind_speeds)
    plt.title('Wind Speed Variation over 24 Hours during a Storm')
    plt.xlabel('Hours')
    plt.ylabel('Wind Speed (m/s)')
    plt.grid(True)
    plt.show()

    return plt


# PM

# WIND
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


# EV
def ev_charge_rate(df):

    dt_minutes = (df['Arrival DateTime'] - df['Departure DateTime']).dt.total_seconds()/60

    ev_charge_rate = (df['SOC on Departure'] - df['SOC on Arrival']) / dt_minutes
    max_ev_charge_rate = np.max(ev_charge_rate)
    max_ev_charge_rate

    trace = go.Histogram(
        x=ev_charge_rate,
        xbins=dict( # bins used for histogram
            size=0.0000001
        ),
    )

    layout = go.Layout(
        title='EV charge rate',
        xaxis_title='SoC charge rage [SoC{UNIT?}/min]',
        yaxis_title='freq.',
    )

    fig = go.Figure(trace, layout)
    fig.show()


# EV
def ev_soc_timeline(df, max_ev_charge_rate):

    ev_batt_capacity = max(df['SOC on Departure'])

    ev_timeline_dt = []
    ev_timeline_soc = []

    ev_timeline_dt.append(pd.to_datetime('2019-01-01 00:00'))
    ev_timeline_soc.append(df['SOC on Departure'][0])

    for (i,row) in df.iterrows():
        dt = row['Departure DateTime'] - ev_timeline_dt[-1]
        
        time_to_max_charge = (ev_batt_capacity - ev_timeline_soc[-1]) / max_ev_charge_rate
        time_to_max_charge = pd.Timedelta(minutes=time_to_max_charge)
        time_at_max_charge = time_to_max_charge + ev_timeline_dt[-1]

        # Conditional logic to achieve constant charing ramp
        full_charge_achieved_before_departure = time_at_max_charge < row['Departure DateTime']
        if full_charge_achieved_before_departure and i!=0:
            # Evaluate the point in time during charge that capacity is reached (i.e. before 'Departure DateTime')
            ev_timeline_dt.append(time_at_max_charge)
            # Ensure the 'SOC on Departure' is not exceded during charge
            ev_timeline_soc.append(np.min([ev_batt_capacity,row['SOC on Departure']]))

        ev_timeline_dt.append(row['Departure DateTime'])
        ev_timeline_soc.append(row['SOC on Departure'])
        ev_timeline_dt.append(row['Departure DateTime']+pd.Timedelta(seconds=1))
        ev_timeline_soc.append(0)
        ev_timeline_dt.append(row['Arrival DateTime']-pd.Timedelta(seconds=1))
        ev_timeline_soc.append(0)
        ev_timeline_dt.append(row['Arrival DateTime'])
        ev_timeline_soc.append(row['SOC on Arrival'])

    ev_timeline = pd.DataFrame({
        'datetime': ev_timeline_dt,
        'soc': ev_timeline_soc,
    })
    ev_timeline.set_index('datetime', inplace=True)


    trace = go.Scatter(
        x=ev_timeline.index,
        y=ev_timeline.soc,
        mode='lines',
        fill='tozeroy',
    )
    layout = go.Layout(
        title="EV SoC timeline",
        yaxis=dict(title="SoC [UNITS TBC]")
    )
    fig = go.Figure(trace, layout)
    fig.show()

    return ev_timeline


# Network Map

def network_map(network, radii=None):

    
        
    traces = []

    network.buses['Bus'] = network.buses.index
    mapping = dict(network.buses[['Bus', 'x']].values)
    network.lines['x0'] = network.lines.bus0.map(mapping)
    network.lines['x1'] = network.lines.bus1.map(mapping)
    mapping = dict(network.buses[['Bus', 'y']].values)
    network.lines['y0'] = network.lines.bus0.map(mapping)
    network.lines['y1'] = network.lines.bus1.map(mapping)


    if radii:
        
        regions = []
        
        for i in range(len(radii)):
            
            radius = radii[i] 
            line = network.lines.loc[(network.lines.bus0==radius[0]) & (network.lines.bus1==radius[1])]

            cntr = (line['y0'].to_list()[0], line['x0'].to_list()[0])
            s = line['length'].to_list()[0] * 1000 #Distance (m)

            #Define the ellipsoid
            geod = Geodesic.WGS84

            #Solve the Direct problem
            azimuths = np.linspace(start=0,stop=360,num=181)
            xs = []
            ys = []
            for i in range(len(azimuths)):
                dir = geod.Direct(cntr[0],cntr[1],azimuths[i],s)
                xs.append(dir['lon2'])
                ys.append(dir['lat2'])

            regions.append({'name':f"{radius[0]}-{radius[1]}",'xs': xs,'ys': ys})


        for i in range(len(regions)):
            traces.append(go.Scattermap(
                lat=regions[i]['ys'],
                lon=regions[i]['xs'],
                mode='lines',
                line=dict(width=0.1),
                showlegend=False,
                fill="toself",
                fillcolor='rgba(0.5,0.5,0.5,0.1)',
                text=regions[i]['name'],
            ))


    for (i,row) in network.lines.iterrows():
        traces.append(go.Scattermap(
            lat=[row['y0'], row['y1']],
            lon=[row['x0'], row['x1']],
            mode='lines',
            marker=go.scattermap.Marker(
                size=14
            ),
            # showlegend=False,
            name=f"{row['bus0']} - {row['bus1']}",
            text=f"{row['bus0']} - {row['bus1']}",
        ))

    traces.append(go.Scattermap(
        lat=network.buses['y'].to_list(),
        lon=network.buses['x'].to_list(),
        mode='markers',
        marker=go.scattermap.Marker(
            color='#000000',
            size=8
        ),
        showlegend=False,
        text=network.buses.index.to_list()
    ))

    fig = go.Figure(traces)

    fig.update_layout(
        height=1000,
        margin=dict(t=0),
        hovermode='closest',
        map=dict(
            bearing=0,
            center=go.layout.map.Center(
                lat=59,
                lon=-3
            ),
            pitch=0,
            zoom=8.5
        )
    )

    fig.show()


# IO FILES
def from_df(df, x_title="", y_title="", type="lines+markers"):

    traces = []

    for col in df.columns:
        traces.append(go.Scatter(
            x=df[col].index,
            y=df[col].values,
            mode=type,
            name=col
        ))

    layout = go.Layout(
        height=450,
        width=1450,
        margin=dict(t=10,b=50,l=50,r=10),
        xaxis=dict(title=x_title),
        yaxis=dict(title=y_title),
        legend_orientation='h',
        )
    fig = go.Figure(traces,layout)
    fig.show()



