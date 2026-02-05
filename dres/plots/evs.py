import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta



#--------------------------------------- EVs ---------------------------------------

def plot_departure_histogram(dres, bin_minutes=1, ev_id=None, include_heatmap=True):
    """
    Plot histogram of EV departure and arrival times across 24 hours.
    
    Args:
        df: DataFrame with 'datetime_on_departure' and 'datetime_on_arrival' columns
        bin_minutes: Resolution of histogram bins in minutes (default: 1)
        include_heatmap: If True, adds journey duration heatmap as third subplot
    
    Returns:
        plotly Figure object with multiple subplots
    """

    # Extract EV schedule data
    df = dres.ev.schedule_data
    if ev_id is not None:
        df = dres.ev.schedule_data[dres.ev.schedule_data['ev_id'] == ev_id]
    
    if dres.ev.schedule_type not in ["journey_events", "charge_events"]:
        raise ValueError("EV schedule type must be 'journey_events' or 'charge_events'.")
    
    # Normalize times to reference date for histogram
    reference_date = datetime(2019, 1, 1)
    
    if dres.ev.schedule_type == "charge_events":
        # Extract time component and normalize to reference date
        departure_times = [datetime.combine(reference_date.date(), t.time()) 
                          for t in pd.to_datetime(df['datetime_charge_start'])]
        arrival_times = [datetime.combine(reference_date.date(), t.time()) 
                        for t in pd.to_datetime(df['dateime_charge_end'])]
    elif dres.ev.schedule_type == "journey_events":
        ## LEGACY EV DATASET HANDLING >>>
        # Ensure datetime objects (extract time component only, normalized to a reference date)
        departure_times = [datetime.combine(reference_date.date(), t.time()) 
                        for t in pd.to_datetime(df["datetime_on_departure"])]
        arrival_times = [datetime.combine(reference_date.date(), t.time()) 
                        for t in pd.to_datetime(df["datetime_on_arrival"])]
        ## <<< LEGACY EV DATASET HANDLING


    # Create time bins as datetime objects
    n_bins = int(1440 / bin_minutes)
    bin_edges_minutes = np.linspace(0, 1440, n_bins + 1)
    bin_edges_dt = [reference_date + timedelta(minutes=int(m)) for m in bin_edges_minutes]
    
    # Manual histogram calculation
    dep_hist = np.zeros(n_bins)
    arr_hist = np.zeros(n_bins)
    
    for dt in departure_times:
        minutes = (dt - reference_date).total_seconds() / 60
        bin_idx = int(minutes / bin_minutes)
        if 0 <= bin_idx < n_bins:
            dep_hist[bin_idx] += 1
    
    for dt in arrival_times:
        minutes = (dt - reference_date).total_seconds() / 60
        bin_idx = int(minutes / bin_minutes)
        if 0 <= bin_idx < n_bins:
            arr_hist[bin_idx] += 1
    
    # Bin centers as datetime
    bin_centers = [(bin_edges_dt[i] + timedelta(minutes=bin_minutes/2)) for i in range(n_bins)]
    
    # Calculate common y-axis range for histograms
    max_count = max(dep_hist.max(), arr_hist.max())
    y_range = [0, max_count * 1.05]  # Add 5% padding
    
    # Common x-axis settings with dynamic formatting based on zoom
    xaxis_config = dict(
        tickformatstops=[
            dict(dtickrange=[None, 60000], value="%H:%M:%S"),
            dict(dtickrange=[60000, 3600000], value="%H:%M"),
            dict(dtickrange=[3600000, None], value="%H:%M")
        ],
        showgrid=True,
        gridcolor='lightgray',
        gridwidth=1
    )
    
    traces = []
    annotations = []
    
    # Three subplots with heatmap
    # Departure histogram (top)
    traces.append(go.Bar(
        x=bin_centers,
        y=dep_hist,
        marker=dict(color='steelblue', line=dict(width=0)),
        name='Departures',
        width=bin_minutes * 60000,
        showlegend=False,
        xaxis='x',
        yaxis='y'
    ))
    
    # Arrival histogram (middle)
    traces.append(go.Bar(
        x=bin_centers,
        y=arr_hist,
        marker=dict(color='coral', line=dict(width=0)),
        name='Arrivals',
        width=bin_minutes * 60000,
        showlegend=False,
        xaxis='x2',
        yaxis='y2'
    ))
    
    # 
    if dres.ev.schedule_type == "charge_events":
        departure_datetime = pd.to_datetime(df['datetime_charge_start'])
        arrival_datetime = pd.to_datetime(df['dateime_charge_end'])
        color_bar_text = 'Hours per day, charging'

    elif dres.ev.schedule_type == "journey_events":
        departure_datetime = pd.to_datetime(df['datetime_on_departure'])
        arrival_datetime = pd.to_datetime(df['datetime_on_arrival'])
        color_bar_text = 'Hours per day, unplugged'

    # Prepare heatmap data
    df_copy = df.copy()
    df_copy['Duration_hours'] = (arrival_datetime - departure_datetime).dt.total_seconds() / 3600
    df_copy['DayOfWeek'] = departure_datetime.dt.dayofweek
    df_copy['Week'] = departure_datetime.dt.isocalendar().week
    df_copy['Year'] = departure_datetime.dt.year
    df_copy['YearWeek'] = df_copy['Year'].astype(str) + '-W' + df_copy['Week'].astype(str).str.zfill(2)
    
    heatmap_data = df_copy.groupby(['DayOfWeek', 'YearWeek'])['Duration_hours'].mean().reset_index()
    pivot_data = heatmap_data.pivot(index='DayOfWeek', columns='YearWeek', values='Duration_hours')
    pivot_data = pivot_data.reindex(sorted(pivot_data.columns), axis=1)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Heatmap (bottom)
    traces.append(go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=day_names,
        colorscale='Viridis',
        reversescale=True,
        colorbar=dict(
            orientation='h',
            x=0.0,
            xanchor='left',
            y=0.33,
            yanchor='top',
            len=1.0,
        ),
        hoverongaps=False,
        hovertemplate='Week: %{x}<br>Day: %{y}<br>Duration: %{z:.2f} hours<extra></extra>',
        xaxis='x3',
        yaxis='y3'
    ))
    
    # Subplot annotations (titles)
    annotations = [
        dict(text=color_bar_text, x=0.04, y=0.265, xref='paper', yref='paper',
                xanchor='left', yanchor='bottom', showarrow=False,
                font=dict(size=14, color='#000')),
        
    ]
    
    layout = go.Layout(
        title=f'EV Data Analysis (single vehicle)',
        template='plotly_white',
        height=750,
        width=800,
        bargap=0.05,
        margin=dict(t=100, b=120, l=80, r=120),
        annotations=annotations,
        dragmode='zoom',
        font=dict(family="Cambria", size=12),
        # Top histogram (departures)
        xaxis=dict(domain=[0, 1], anchor='y', matches='x2', **xaxis_config),
        yaxis=dict(domain=[0.76, 1.0], anchor='x', title='Number of Departures',
                    range=y_range, fixedrange=True),
        # Middle histogram (arrivals)
        xaxis2=dict(domain=[0, 1], anchor='y2', title='Time of Day', **xaxis_config),
        yaxis2=dict(domain=[0.48, 0.72], anchor='x2', title='Number of Arrivals',
                    range=y_range, fixedrange=True),
        # Bottom heatmap
        xaxis3=dict(domain=[0, 1.0], anchor='y3', tickangle=-45),
        yaxis3=dict(domain=[0, 0.20], anchor='x3', autorange='reversed')
    )
    
    fig = go.Figure(data=traces, layout=layout)

    return fig

def ev_charge_rate(dres, ev_id=None):

    # Extract EV schedule data
    if ev_id is not None:
        df = dres.ev.schedule_data[dres.ev.schedule_data['ev_id'] == ev_id]
    else:
        df = dres.ev.schedule_data

    if dres.ev.schedule_type == "journey_events":
        dt_minutes = (df['datetime_on_arrival'] - df['datetime_on_departure']).dt.total_seconds()/60

        ev_charge_rate = (df['soc_on_departure'] - df['soc_on_arrival']) / dt_minutes
        max_ev_charge_rate = np.max(ev_charge_rate)
        bin_size=0.0000005
    elif dres.ev.schedule_type == "charge_events":
        dt_minutes = (df['dateime_charge_end'] - df['datetime_charge_start']).dt.total_seconds()/60

        ev_charge_rate = (df['soc_end'] - df['soc_start']) / dt_minutes
        max_ev_charge_rate = np.max(ev_charge_rate)
        bin_size=0.00005

    trace = go.Histogram(
        x=ev_charge_rate,
        xbins=dict( # bins used for histogram
            size=bin_size
        ),
        marker=dict(
            line=dict(color='rgba(200, 200, 200, 0.5)', width=0.5)
        ),
    )

    layout = go.Layout(
        title='EV charge rate',
        xaxis_title='SoC charge rage [SoC{UNIT?}/min]',
        yaxis_title='freq.',
    )

    fig = go.Figure(trace, layout)
    fig.show()

    return

def ev_soc_timeline(dres, max_ev_charge_rate, ev_id=None):

    # Extract EV schedule data
    if ev_id is not None:
        df = dres.ev.schedule_data[dres.ev.schedule_data['ev_id'] == ev_id]
    else:
        df = dres.ev.schedule_data

    if dres.ev.schedule_type == "journey_events":
        ev_batt_capacity = max(df['soc_on_departure'])

        ev_timeline_dt = []
        ev_timeline_soc = []

        ev_timeline_dt.append(pd.to_datetime('2019-01-01 00:00'))
        ev_timeline_soc.append(df['soc_on_departure'].iloc[0])

        for (i, row) in df.iterrows():
            dt = row['datetime_on_departure'] - ev_timeline_dt[-1]
            
            time_to_max_charge = (ev_batt_capacity - ev_timeline_soc[-1]) / max_ev_charge_rate
            time_to_max_charge = pd.Timedelta(minutes=time_to_max_charge)
            time_at_max_charge = time_to_max_charge + ev_timeline_dt[-1]

            # Conditional logic to achieve constant charging ramp
            full_charge_achieved_before_departure = time_at_max_charge < row['datetime_on_departure']
            if full_charge_achieved_before_departure and i != 0:
                # Evaluate the point in time during charge that capacity is reached (i.e. before 'datetime_on_departure')
                ev_timeline_dt.append(time_at_max_charge)
                # Ensure the 'soc_on_departure' is not exceeded during charge
                ev_timeline_soc.append(np.min([ev_batt_capacity, row['soc_on_departure']]))

            ev_timeline_dt.append(row['datetime_on_departure'])
            ev_timeline_soc.append(row['soc_on_departure'])
            ev_timeline_dt.append(row['datetime_on_departure'] + pd.Timedelta(seconds=1))
            ev_timeline_soc.append(0)
            ev_timeline_dt.append(row['datetime_on_arrival'] - pd.Timedelta(seconds=1))
            ev_timeline_soc.append(0)
            ev_timeline_dt.append(row['datetime_on_arrival'])
            ev_timeline_soc.append(row['soc_on_arrival'])

    elif dres.ev.schedule_type == "charge_events":
        # Check for NaN values in critical columns
        if df[['datetime_charge_start', 'dateime_charge_end', 'soc_start', 'soc_end']].isna().any().any():
            print("DataFrame contains NaN values in critical columns. Please clean the data before proceeding.")
        df = df.dropna(subset=['datetime_charge_start', 'dateime_charge_end', 'soc_start', 'soc_end'])
        
        ev_batt_capacity = max(df['soc_end'])

        ev_timeline_dt = []
        ev_timeline_soc = []

        ev_timeline_dt.append(df['datetime_charge_start'].iloc[0])
        ev_timeline_soc.append(df['soc_start'].iloc[0])

        for (i, row) in df.iterrows():
            # If there's a gap between events, show constant SoC
            if i > 0 and ev_timeline_dt[-1] < row['datetime_charge_start']:
                # Hold previous SoC until next event starts
                ev_timeline_dt.append(row['datetime_charge_start'] - pd.Timedelta(seconds=1))
                ev_timeline_soc.append(ev_timeline_soc[-1])

            # Add charging event
            ev_timeline_dt.append(row['datetime_charge_start'])
            ev_timeline_soc.append(row['soc_start'])
            
            # Calculate charging with max rate
            time_to_max_charge = (ev_batt_capacity - row['soc_start']) / max_ev_charge_rate
            time_to_max_charge = pd.Timedelta(minutes=time_to_max_charge)
            time_at_max_charge = time_to_max_charge + row['datetime_charge_start']

            # Check if full charge achieved before event end
            full_charge_achieved_before_end = time_at_max_charge < row['dateime_charge_end']
            if full_charge_achieved_before_end:
                ev_timeline_dt.append(time_at_max_charge)
                ev_timeline_soc.append(np.min([ev_batt_capacity, row['soc_end']]))
            
            ev_timeline_dt.append(row['dateime_charge_end'])
            ev_timeline_soc.append(row['soc_end'])

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

    return


def soc_timeline(dres, asset_id):

    # Template for annotations
    annotations = []

    # Set rules based on schedule type
    schedule_type = dres.simulation_config['EV_schedule_data']['schedule_type']
    if schedule_type == 'soc_timeline':
        asset_id_tag = 'ev_id'
        plot_title = 'EV SoC Timeline for EV:'
    elif schedule_type == 'station_timeline':
        asset_id_tag = 'station_id'
        plot_title = 'Charging Station SoC Timeline for Station:'
    
    # Get base date for datetime conversion
    base_date = pd.Timestamp(dres.simulation_config['EV_schedule_data']['include_date_datum'])
    
    # Extract relevant schedule data based on asset_id
    df = dres.ev.schedule_data
    df = df[df[asset_id_tag] == asset_id].copy()

    # Check if dataframe is empty
    try:
        
    
        # Convert datetime column to proper datetime format
        if pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])
        else:
            df['datetime'] = base_date + pd.to_timedelta(df['datetime'], unit='s')

        # Prepare data for plotting
        df = df.sort_values('datetime').set_index('datetime')
        x_min = df.index.min().normalize()
        x_max = df.index.max().normalize() + pd.Timedelta(days=1)
        full_index = pd.date_range(start=x_min, end=x_max, freq='s')
        df = df.reindex(full_index)
        df['soc'] = pd.to_numeric(df['soc'], errors='coerce').fillna(0)
        df[asset_id_tag] = asset_id
        df = df.reset_index().rename(columns={'index': 'datetime'})

        # Build trace object
        trace_soc = go.Scatter(
            x=df['datetime'], y=df['soc'],
            mode='lines+markers', name='SoC Over Time',
            fill='tozeroy'
        )

        datetime_range = [x_min, x_max]


        # Evaluate annotations for charging sessions (if station timeline)
        if schedule_type == 'station_timeline':
            charge_starts = ((df["soc"].shift(1) == 0) & (df["soc"] > 0)).to_numpy().nonzero()[0]
            charge_ends = ((df["soc"].shift(1) > 0) & (df["soc"] == 0)).to_numpy().nonzero()[0]
            charge_midpoints = np.floor((charge_starts + charge_ends) / 2)
            annot_plot_context = zip(
                df['datetime'][charge_midpoints].to_list(), 
                df['ev_id'][charge_midpoints].to_list()
            )
            annotations = [
                dict(
                    x=t,
                    y=0.975,
                    yref='paper',
                    text=str(ev_id),
                    showarrow=False,
                    font=dict(size=10, color='#333')
                )
                for t, ev_id in annot_plot_context
            ]
        
        

    except Exception as e:
        print(f"No data available for {asset_id_tag} '{asset_id}'. Error: {e}")
        
        # Build dummy trace object
        trace_soc = go.Scatter(
            x=[], y=[],
            mode='lines+markers', name='SoC Over Time',
            fill='tozeroy'
        )

        datetime_range = [pd.Timestamp(base_date), pd.Timestamp(base_date + pd.Timedelta(days=1))]
    
    # Define layout
    layout = go.Layout(
        title=f"{plot_title}'{asset_id}'",
        xaxis_title='Time',
        yaxis_title='State of Charge (Wh)',
        xaxis=dict(type='date', range=datetime_range),
        yaxis=dict(range=[0, 60000]),
        annotations=annotations,
    )

    # Plot figure (show)
    go.Figure(data=[trace_soc], layout=layout).show()