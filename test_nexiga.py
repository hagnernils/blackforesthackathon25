import os

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from pyproj import Transformer
import pickle

# Optional: Define transformer for EPSG:25832 -> EPSG:4326
transformer = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)

# print("writing nexiga")
# # Nexiga Daten laden
# nexiga = gpd.read_file("daten/hackathon_daten/Datenquellen/Nexiga/nexiga_all.shp")
# nexiga = nexiga.to_crs("EPSG:4326")
# nexiga.to_file('nexiga.geojson', driver='GeoJSON')
#
# print("writing pv data")
# # PV daten
# pv_df = pd.read_csv("daten/strom.csv", delimiter=";")
# pv_df["geometry"] = pv_df[pv_df["Position"].notnull()]["Position"].astype(str).apply(wkt.loads)
# gdf = gpd.GeoDataFrame(pv_df, geometry="geometry")
# gdf.set_crs("EPSG:4326", inplace=True)
# gdf.to_file("pv.geojson", driver="GeoJSON")

print("Getting addresses for heatpumps")
# Adressen haben positionen fuer Waermepumpen
adressen = pd.read_csv("daten/hackathon_daten/Datenquellen/Hauskoordinaten/adressen_bw.txt", delimiter=";")

# Waermepumpen: position der adressen hinzufuegen
waerme = pd.read_csv("daten/Wärmepumpen.csv", delimiter=";")

# Normalize and prepare key columns
adressen["key"] = (
    adressen["gmd"].str.strip().str.casefold() + "|" +
    adressen["str"].str.strip().str.casefold() + "|" +
    adressen["hnr"].astype(str).str.strip()
)

adressen = adressen[["key", "ostwert", "nordwert"]].copy()

waerme["key"] = (
    waerme["Gemeinde"].str.strip().str.casefold() + "|" +
    waerme["Straßenname"].str.strip().str.casefold() + "|" +
    waerme["Hausnummer"].astype(str).str.strip()
)

print("converting datetimes for geojson")
waerme["timestamp"] = pd.to_datetime(waerme["Einbaudatum"], dayfirst=True, errors="coerce")

def to_wgs84_wkt(row):
    try:
        x, y = float(row["ostwert"]), float(row["nordwert"])
        lon, lat = transformer.transform(x, y)
        return Point(lon, lat).wkt
    except:
        return None

print("creating address dictionary")
coord_dict = None

if not os.path.isfile("address_dict.pkl"):
    coord_dict = {
        row["key"]: to_wgs84_wkt(row)
        for _, row in adressen.iterrows()
    }
    with open("address_dict.pkl", "wb") as f:
        pickle.dump(coord_dict, f)
else:
    with open("address_dict.pkl", "rb") as f:
        coord_dict = pickle.load(f)

print("mapping heatpump address to location")
waerme["Position"] = waerme["key"].map(coord_dict)

waerme["Einbaudatum"] = pd.to_datetime(waerme["Einbaudatum"], dayfirst=True, errors="coerce")

waerme["geometry"] = waerme[waerme["Position"].notnull()]["Position"].astype(str).apply(wkt.loads)

waerme_gdf = gpd.GeoDataFrame(waerme, geometry="geometry", crs="EPSG:4326")
waerme_gdf = waerme_gdf.dropna(subset=["geometry"])

waerme_gdf.to_file("waerme.geojson", driver="GeoJSON")

def address_to_Point(stadt, strasse, hausnummer):
    adressen["street"] = strasse
    result = adressen.loc[
        (adressen['gmd'].str.casefold() == stadt.casefold()) &
        (adressen['str'].str.casefold() == strasse.casefold()) &
        (adressen['hnr'].astype(str) == str(hausnummer))
        ]
    return Point(float(result["ostwert"]), float(result["nordwert"])).wkt

#print(address_to_Point("Weisweil", "Friedhofstraße", 11))

# adressen["gmd"] = adressen["gmd"].str.strip().str.casefold()
# adressen["str"] = adressen["str"].str.strip().str.casefold()
# adressen["hnr"] = adressen["hnr"].astype(str).str.strip()
#
# waerme["Gemeinde"] = waerme["Gemeinde"].str.strip().str.casefold()
# waerme["Straßenname"] = waerme["Straßenname"].str.strip().str.casefold()
# waerme["Hausnummer"] = waerme["Hausnummer"].astype(str).str.strip()
#
# df["timestamp"] = pd.to_datetime(df["datum"], dayfirst=True, errors="coerce")
#
# # Merge based on city, street, and house number
# merged = pd.merge(
#     waerme,
#     adressen,
#     how="right",
#     left_on=["Gemeinde", "Straßenname", "Hausnummer"],
#     right_on = ["gmd", "str", "hnr"]
# )
#
# # Convert to WKT format using shapely
# def to_wkt(row):
#     if pd.notnull(row['ostwert']) and pd.notnull(row['nordwert']):
#         # Assumes coordinates are in EPSG:4326 or already lat/lon (check if not!)
#         point = Point(float(row['ostwert']), float(row['nordwert']))
#         return point.wkt
#     return None
#
# merged["Position"] = merged.apply(to_wkt, axis=1)