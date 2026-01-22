import plotly.graph_objects as go


#--------------------------------------- IO FILES ---------------------------------------

def from_df(df, y_title=""):

    traces = []

    for col in df.columns:
        traces.append(go.Scatter(
            x=df[col].index,
            y=df[col].values,
            name=col
        ))

    layout = go.Layout(
        height=450,
        width=1450,
        margin=dict(t=10,b=50,l=50,r=10),
        yaxis=dict(title=y_title),
        legend_orientation='h',
        )
    fig = go.Figure(traces,layout)
    fig.show()

