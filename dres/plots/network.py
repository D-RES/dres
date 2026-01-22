import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from geographiclib.geodesic import Geodesic

#--------------------------------------- Network Map ---------------------------------------

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

