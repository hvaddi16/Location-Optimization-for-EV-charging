import pandas as pd
import re
import bisect
import geopandas  as gpd
from shapely.geometry.linestring import LineString
from shapely.geometry.multilinestring import MultiLineString
import numpy as np
from scipy.spatial.distance import cdist
from geopy.distance import geodesic as GD

def roadsIntoFastJson():
    zipfile = "geojsons/ne_10m_roads.zip"
    roads = gpd.read_file(zipfile)
    volx = pd.read_csv("data/2020.csv")
    sel_columns = [
        "type",
        "name",
        "length_km",
        "toll",
        "geometry"
    ]

    roads = roads[
        (roads["continent"]=="North America") &
        (roads["sov_a3"]=="USA") &
        (roads["featurecla"]=="Road")
    ]
    roads = roads[sel_columns]

    def getxy(x):
        if isinstance(x, LineString):
            linestrings = [x]
        elif isinstance(x, MultiLineString):
            linestrings = x.geoms
        out = {}
        out["lat"] = np.array([np.append(ls.xy[1],None) for ls in linestrings])
        #out["lat"] = out["lat"].flatten()
        out["lon"] = np.array([np.append(ls.xy[0],None) for ls in linestrings])
        #out["lon"] = out["lon"].flatten()
        return pd.Series(out)

    roads[["lat", "lon"]] = roads["geometry"].apply(getxy)
    roads.drop("geometry", axis=1, inplace=True)
    roads = pd.DataFrame(roads)

    vol = volx[volx["month"]==1]
    vol = vol[["lat", "long"]].values
    vol[:,1] = -vol[:,1]

    def distCross(x, p):
        lats = np.concatenate(x["lat"])
        lats = lats[lats != None]
        lons = np.concatenate(x["lon"])
        lons = lons[lons != None]

        v = np.vstack([lats,lons]).T
        try:
            if v.shape[0] == 0:
                d = np.full((p.shape[0],1),np.nan)
            else:
                d = cdist(v.astype(np.float64),p).min(axis=0)
        except:
            print("hehe")
        return d

    
    dists = roads.apply(lambda x: distCross(x, vol), axis=1)
    dists = np.vstack(dists)
    roads["arg_min"] = dists.argmin(axis=1)
    roads["arg_min"] = np.where(dists.min(axis=1)>2, np.nan, roads["arg_min"])
    roads["volume"] = roads["arg_min"].apply(lambda x: np.nan if np.isnan(x) else volx["dailytraffic"].loc[x])
    roads["demandfactor"] = roads["arg_min"].apply(lambda x: np.nan if np.isnan(x) else volx["demandfactor"].loc[x])
    roads["state"] = roads["arg_min"].apply(lambda x: np.nan if np.isnan(x) else volx["state"].loc[x])
    roads["lat"] = roads["lat"].apply(lambda x: np.concatenate(x).flatten())
    roads["lon"] = roads["lon"].apply(lambda x: np.concatenate(x).flatten())
    with pd.HDFStore('geojsons/maps.h5') as store:
        store['roads'] = roads  # save it

    return 0

def add_cap():
    stats = pd.read_csv('data/EVStations_data_cleaned.csv')
    stats["capacity"] = 0
    stats['capacity'] = np.where(~stats['EV Level1 EVSE Num'].isna(), 1.2 * stats['EV Level1 EVSE Num'], stats['capacity'])
    stats['capacity'] = np.where(~stats['EV Level2 EVSE Num'].isna(),  7.6* stats['EV Level2 EVSE Num'] + stats['capacity'], stats['capacity'])
    stats['capacity'] = np.where(~stats['EV DC Fast Count'].isna(),  50* stats['EV DC Fast Count'] + stats['capacity'], stats['capacity'])
    stats['capacity'] = ((stats['capacity'].astype(int)).astype(str)) + 'kW'
    stats['EV Connector Types'] = stats['EV Connector Types'].str.replace(' ', ', ')
    stats['ports'] = stats['EV Level1 EVSE Num'] + stats['EV Level2 EVSE Num'] + stats['EV DC Fast Count']
    stats['ports'] = np.where(stats['ports'].isna(), 0, stats['ports'])
    df = pd.read_csv('data/sorted_roads.csv')
    stats_new = stats.apply(lambda x : dist(x, df), axis = 1)
    stats_new.columns = [ "r_"+i for i in stats_new.columns.tolist()]
    stats = pd.concat([stats, stats_new], axis=1)
    stats.to_csv('data/EV_data_capacity.csv', index = False)

def get_roads():
    df = pd.read_hdf("geojsons/maps.h5", "roads")
    df = pd.concat(df.apply(data_add, axis = 1).tolist())
    df = df.sort_values(['lat', 'lon'], ascending=[True, True])
    df.to_csv('data/sorted_roads.csv', index = False)

def data_add(r1):
    latlon = np.vstack(r1[['lat','lon']].values).T
    new_df = pd.DataFrame( latlon, columns = ['lat', 'lon'] )
    new_df['road num'] = r1.name
    for c in r1.index.tolist():
        if c not in ['lat', 'lon']:
            new_df[c] = r1[c]
    return new_df.reset_index()

def dist(r, df):
    a = bisect.bisect_left(df['lat'], r['Latitude'])
    b = df['lat'].iloc[a] + 0.02
    mx = bisect.bisect_left(df['lat'], b)
    c = df['lat'].iloc[a] - 0.02
    mn = bisect.bisect_left(df['lat'], b)
    df2 = df.iloc[mn:mx+1,:][['lat','lon']] 
    Y = cdist(r[['Latitude', 'Longitude']].values.reshape(1,-1).astype(np.float64), df2.values, 'euclidean')
    armin, min_dis = Y.argmin(axis = 1), Y.min(axis = 1)
    res = df2.iloc[armin,:]
    res = df.iloc[res.index.tolist()[0], :]
    res['min dis'] = min_dis
    return res

def merged_roads():
    df = pd.read_csv('data/sorted_roads.csv')
    stats = pd.read_csv('data/EV_data_capacity.csv')
    merged = df.merge(stats, how="left", left_on=["lat", "lon"], right_on=["r_lat", "r_lon"])
    merged.to_csv('data/merged.csv', index = False)

def getGD(r):
    p1 = (r["lat"], r["lon"])
    p2 = (r["xlat"], r["xlon"])
    return GD(p1,p2)

def scaledPoint(r,t):
    p1 = np.array((r["lat"], r["lon"]))
    p2 = np.array((r["xlat"], r["xlon"]))
    d = r["Dist"]
    return ((p1*t) + (p2*(d-t)))/d

def optimalStations():
    df = pd.read_csv("data/new_ev.csv")
    nxtdf = df["new_ev"].str.split("_", expand=True).iloc[:, 2:].astype(int)
    nxtdf.columns = ["road num", "candidate index"]
    df = pd.concat([nxtdf, df["capacity"]], axis=1)
    roads = pd.read_csv('data/sorted_roads.csv')
    odfl, rdfl = [], []
    for rnum in sorted(set(df["road num"])):
        odf, rdf = getAssignments(rnum, roads, df)
        odfl.append(odf)
        rdfl.append(rdf)

    df = pd.concat(odfl)
    roads = pd.concat(rdfl)
    df.to_csv('data/new_cap.csv', index=False)
    roads.to_csv('data/roads.csv', index=False)

def getAssignments(rnum, roads, df):
    node_gap = 25
    rdf = roads[roads["road num"] == rnum].sort_values(["index"])
    odf = df[df["road num"]== rnum].sort_values(["candidate index"])
    odf["candidate index"] *= node_gap
    odf["candidate index"] += node_gap
    rdf1 = rdf[["lat", "lon"]]
    rdf2 = rdf[["lat", "lon"]].shift(-1)
    rdf2.columns = ["x"+i for i in rdf2.columns.tolist()]
    rdfn = pd.concat([rdf1, rdf2], axis=1).dropna()
    rdfn["Dist"] = rdfn.apply(getGD, axis=1)
    rdfn["Dist"] = rdfn["Dist"]*rdf.length_km.iloc[0]/rdfn["Dist"].sum()
    candidate_points = []
    for i,r in enumerate(rdfn.T.items()):
        r = r[1]
        if i==0:
            traversed = 0
            distance_to_node = node_gap
        while(1):
            if (r['Dist']-traversed)<(distance_to_node - 1e-6):
                distance_to_node -= (r['Dist'] -traversed)
                traversed = 0
                break
            else:
                traversed += distance_to_node
                candidate_points.append(scaledPoint(r, traversed))
                distance_to_node = node_gap
    try:
        cdf = pd.DataFrame(candidate_points)
        cdf.index = odf.index
        cdf.columns = ["lat", "lon"]
        odf = pd.concat([odf,cdf], axis=1)
    except:
        pass
    rdf["e_capacity"] = odf["capacity"].sum()
    return odf, rdf



#roadsIntoFastJson()
#get_roads()
#add_cap()
#merged_roads()
optimalStations()




