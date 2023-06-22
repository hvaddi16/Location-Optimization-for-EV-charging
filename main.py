from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from dash_bootstrap_components import Row as R, Col as C
import geopandas as gpd
from urllib.request import urlopen
import json
import shapely.geometry
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import pandas as pd
import bisect

pio.renderers.default="chrome"
mapbox_access_token = "pk.eyJ1IjoidmFydW52YW5raW5lbmkiLCJhIjoiY2xiMnFtYmphMDcwcTNvcWVxYjA0aTZvOSJ9.-olc2j26zfM8Z51fjKpqzw"

TRAFFIC_BINS = [0,1000,5000,10000, np.inf]

def getColorForVolume(volume):
    colors = px.colors.sequential.YlOrBr[-7:]
    volume = volume.fillna(volume.median())
    volume = volume.round(0).astype(int)
    bins = TRAFFIC_BINS.copy()
    lz = len(bins)- 1
    lc = len(colors)
    colors = [colors[int(i * lc / lz)] for i in range(0,lz)]
    return volume, pd.cut(volume, bins, labels=colors), colors

def loadBaseRoads():
    #roads = pd.read_hdf("geojsons/maps.h5", "roads")
    roads = pd.read_csv("data/roads.csv")
    roads["volume"], roads["vol_color"], colors = getColorForVolume(roads.volume)
    return(roads, colors)

def loadChargingStationData():
    return(pd.read_csv('data/EV_data_capacity.csv'))

def loadNewStationData():
    return(pd.read_csv('data/new_cap.csv'))

GLOBAL_ROADS_DB_BASE, GLOBAL_ROADS_COLORS = loadBaseRoads()
GLOBAL_ROADS_DB = GLOBAL_ROADS_DB_BASE.copy()

def trafficVolumeStrings():
    while(1):
        strings = []
        for i,v in enumerate(TRAFFIC_BINS[:-2]):
            strings.append(f">={v} to <{TRAFFIC_BINS[i+1]}")
        strings.append(f">={TRAFFIC_BINS[-2]}")
        for s in strings:
            yield s

trafficVolumeGen = trafficVolumeStrings()

def topRowElements():
    title_elem = html.Div(
        "WHERE TO BARGE-IN FOR EV CHARGIN\'",
        style={"width": "100%", "height": "100%", "font-weight": "bold", "font-size": "48px"}
    )
    #     html.Img(
    #     src=r'data/Logo.png', alt='image',
    #     style={"width": "100%", "height": "100%", "font-weight": "bold", "font-size": "48px"}
    # )


    highways = dbc.Checklist(
        options=[
            {"label": "Primary HW", "value": "primary"},
            {"label": "Secondary HW", "value": "secondary"},
            {"label": "Others", "value": "others"},
        ],
        value=["primary","secondary", "others"],
        id="checklist-highways",
    )

    extra_elem = C([
        highways
    ])

    return [C(title_elem),C(extra_elem)]
#


def rightInfoPlots():
    top_plot = html.Div(
        dcc.Graph(id="top-graph", figure=sunburst()),
        style={"width": "300", "height": "300","font-weight": "bold", "font-size": "48px"},
        id = "top-plot"
    )
    top_text = html.Div(
        'State wise distribution of current EVStations Capacities',
        style={"width": "300", "height": "200", "font-size": "28px"},
        id = "top-text"
    )
    bot_plot = html.Div(
        dcc.Graph(id="bot-graph", figure=road_plot(24, 25)),
        style={"width": "300", "height": "160","font-weight": "bold", "font-size": "48px"},
        id = "bot-plot"
    )
    bot_text1 = html.Div(
        'Demand and Proposed Wattage Split',
        style={"width": "300", "height": "200", "font-size": "20px"},
        id = "bot-text1"
    )
    #top_plot = dcc.Graph(id="top_plot2", figure=sunburst())
    
    return [R(top_text),R(top_plot),R(bot_text1),R(bot_plot)]

def bottomRowElements():
    left_col = html.Div(
        "Legend and Filters",
        style = {"width": "240", "height": "900", "font-weight": "bold", "font-size": "48px"}
    )
    main_map = dcc.Graph(id="graph", figure=mainGraph())
    right_plots = rightInfoPlots()
    return [C(main_map),C(right_plots)]#C(left_col)


def getRoadGO(roads, color):
    rdf = roads[roads.vol_color == color]
    rdf = rdf.sort_values(["road num","index"])
    return go.Scattermapbox(
        lat=rdf.lat,
        lon=rdf.lon,
        mode="lines",
        line=dict(width=1, color=rdf.vol_color.iloc[0]),
        hovertemplate= '<b>Traffic Volume: '+ rdf["volume"].astype(str) +
        '<br>Highway Num: '+ rdf["name"] +
        '<br>Road Length: ' + rdf["length_km"].astype(str) +
        '<extra></extra>',
        customdata=rdf,
        name=next(trafficVolumeGen),
        hoverinfo="none",
        legendgroup = "Roads",
        legendgrouptitle = {"text": "Traffic Volume"},
    )

def mainGraph():
    fig = createBaseFig()
    fig = displayRoads(fig)
    fig = displayChargingSt(fig)
    fig = displayNewSt(fig)
    return fig

def createBaseFig():
    fig = go.Figure()
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), width=1200, height=800,
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=dict(lat=37.8283, lon=-99.5795),
            pitch=0,
            zoom=3.75
        ),
        legend_x=0
    )
    return fig

def displayRoads(fig):
    global GLOBAL_ROADS_DB
    roads = GLOBAL_ROADS_DB
    for c in GLOBAL_ROADS_COLORS:
        fig.add_trace(getRoadGO(roads, c))
    return fig

def displayChargingSt(fig):
    stats = loadChargingStationData()
    fig.add_trace(
        go.Scattermapbox(
            lat=stats.Latitude,
            lon=stats.Longitude,
            mode="markers",
            marker = dict(symbol = 'circle', size = 5, color = '#0e9901'),
            opacity = 0.7 ,
            hovertemplate = stats['Station Name']+'<br>'+ 
                            #'Capacity: '+stats['capacity'] +'<br>'+
                            'Open'+' : ' + stats['Access Days Time'] + '<br>' +
                            #'Port Types: ' + stats['EV Connector Types'] + '<br>' +
                            #'Number of Ports: ' + stats['ports'].astype(int).astype(str) +
                            '<extra></extra>',
            hoverinfo="none",
            customdata=stats,
            name="Existing Station",
            legendgroup="Stations",
            legendgrouptitle={"text": "EV Stations"},
        )
    )
    return fig

def road_plot(tot, prop):
    #tot = cur + prop
    if tot >= prop:
        fig = go.Figure(go.Indicator(
        mode = "gauge", value = 0,
        domain = {'x': [0, 1], 'y': [0, 1]},
        #delta = {'reference': 150, 'position': "top"},
        title = {'text':"<b>Demand</b><br><b>Split</b><br><span style='color: gray; font-size:0.8em'>kWH</span>", 'font': {"size": 14}},
        gauge = {
        'shape': "bullet",
        'axis': {'range': [None, tot]},
        'bgcolor': "white",
        'steps': splits(prop,tot)
        }))
    
    else:
        fig = go.Figure(go.Indicator(
        mode = "gauge", value = 0,
        domain = {'x': [0, 1], 'y': [0, 1]},
        #delta = {'reference': 150, 'position': "top"},
        title = {'text':"<b>Demand</b><br><b>Split</b><br><span style='color: gray; font-size:0.8em'>kWH</span>", 'font': {"size": 14}},
        gauge = {
        'shape': "bullet",
        'axis': {'range': [None, prop]},
        'bgcolor': "white",
        'steps': splits(tot,prop),
        }))
    fig.update_layout(height = 200)
    return fig

def stat_plot(cap, road):
    fig = go.Figure(go.Indicator(
    mode = "gauge",
    value = cap,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text':"<b>Demand</b><br><b>Per Road</b><br><span style='color: gray; font-size:0.8em'>kWH</span>", 'font': {"size": 12}},
    gauge = {
        'shape': "bullet",
        'axis': {'range': [None, road]},
        'bgcolor': "white",
        }))
    fig.update_layout(height = 200)
    return fig

def splits(cur, prop):
    cur = int(cur)
    prop = int(prop)
    if int(prop /12) > 0 and prop >cur:
        if int(prop / 12) > 1:
            x = int((prop)*0.07)
            y = prop*0.02
        else:
            x = 1
            y = prop*0.02
        a = [[i, i + x - y ] if i+x-y <=cur else [i, cur]for i in range(0, cur, x)]
        s = [[i, i + x - y] if i+x-y <=prop else [i, prop] for i in range(cur, prop, x)]
        b = [{'range': i, 'color': '#0e9901'} for i in a]
        for i in s:
            d = {'range': i, 'color': "#6efd61"}
            b.append(d)
    elif int(cur /12) == 0:
        b = [{'range': [0,cur], 'color': '#FFFFFF'}]

    return b

def displayNewSt(fig):
    stats = loadNewStationData()
    stats = stats[stats["capacity"]>0]

    fig.add_trace(
        go.Scattermapbox(
            lat=stats.lat,
            lon=stats.lon,
            mode="markers",
            marker = dict(symbol = 'circle', size = 5, color = '#FF0000'),
            opacity = 0.7 ,
            hovertemplate = 'Capacity' +' : '+ stats['capacity'].astype(int).astype(str) + 'kWh' +'<br>'+
                            '<extra></extra>',
            hoverinfo="none",
            name="Proposed Station",
            customdata=stats,
            legendgroup="Stations",
            legendgrouptitle={"text": "EV Stations"},
        )
    )
    return fig


def sunburst():
    dt = pd.read_csv("data/state_top4_capacity.csv")
    dt['City'] = np.where(dt['City']=='Others', dt['State']+ ' Others', dt['City'])
    dt2 = dt.groupby('State').sum()
    a = dt['State'].unique()
    fig =go.Figure(go.Sunburst( 
        labels= a.tolist() + dt['City'].tolist(),
        parents=[""]*len(a) + dt['State'].tolist(),
        values= dt2['total_capacity'].tolist() + dt["total_capacity"].tolist()
        ))
    fig.update_layout(margin = dict(t=5, l=0, r=0, b=5))

    return fig

def mainChildren():
    return [
        R(topRowElements(), id = "top_row"),
        R(bottomRowElements(), id = "bot_row")
    ]

def mainLayout():
    return html.Div(mainChildren(), id="main", style={"width": "100%", "height": "100%"})

app = Dash(__name__, external_stylesheets=[dbc.themes.LITERA])
app.layout = mainLayout()

@app.callback(
    Output("graph", "figure"),
    Input("checklist-highways", "value"),
)
def filterPrimaryHighways(values):
    global GLOBAL_ROADS_DB
    roads = GLOBAL_ROADS_DB_BASE.copy()
    if "primary" not in values:
        roads = roads[roads["type"]!="Major Highway"]
    if "secondary" not in values:
        roads = roads[roads["type"] != "Secondary Highway"]
    if "others" not in values:
        roads = roads[(roads["type"] == "Major Highway") | (roads["type"] == "Secondary Highway")]
    GLOBAL_ROADS_DB = roads.copy()
    return mainGraph()

@app.callback(
    Output("bot-graph", "figure"),
    Output("bot-text1", 'children'),
    Input("graph", "hoverData"),
)
def display_hover(hoverData):
    global GLOBAL_ROADS_DB
    roads = GLOBAL_ROADS_DB.copy()
    if hoverData is not None:
        if 'points' in hoverData:
            hoverData = hoverData['points'][0]
            if "Traffic Volume" in hoverData['hovertemplate']:
                cd = hoverData["customdata"]
                tot_cap = cd[6]*cd[10]
                prop_cap = cd[12]
                s = C([
                    R('The Demand for road: ' + str(prop_cap)),
                    R('Road capacity with new stations: '+ str(int(tot_cap)) + "kWH.")])
                return road_plot(tot_cap, prop_cap), s
            elif "Open" in hoverData['hovertemplate']:
                cd = hoverData["customdata"]
                tot_curr = int(cd[33][:-2])
                if cd[41] is None or cd[45] is None:
                    prop = 0
                else:
                    prop = cd[41] * cd[45]
                s = C([
                    R('Name : '+ cd[1]),
                    R('Capacity: '+ str(tot_curr)+'kWH'),
                    R('Port Types: ' + str(cd[25])),
                ])

                return stat_plot(tot_curr,prop), s
            elif "Capacity" in hoverData['hovertemplate']:

                cd = hoverData["customdata"]
                rc = roads[roads['road num'] == cd[0]].iloc[0,:]

                rcap = rc['demandfactor'] * rc['length_km']
                cap = cd[2]

                s = C([
                    R('New Proposed Station on road: ' + str(cd[0])),
                    R('Proposed Capacity: ' + str(cap)+'kWH'),
                    R('Total Demand of the Road: '+str(rcap.round(2))+'kWH'),
                    R("Proposed station fulfillment: "+ str(((cap/rcap)*100).round(2)) +'%'),
                ])

                return stat_plot(cap,rcap), s


    return road_plot(0, 1), ""

app.run_server(host='127.0.0.1', port=3000, debug=True)

#%%
