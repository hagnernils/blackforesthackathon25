import os
import geopandas as gpd
import pandas as pd
from matplotlib import pyplot as plt
from shapely import wkt
from shapely.geometry import Point, Polygon
from pyproj import Transformer
import pickle
import h3
import seaborn as sns
import matplotlib.pyplot as plt


# Optional: Define transformer for EPSG:25832 -> EPSG:4326
transformer = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)

print("writing nexiga")
# Nexiga Daten laden
nexiga = gpd.read_file("daten/hackathon_daten/Datenquellen/Nexiga/nexiga_all.shp")
nexiga = nexiga.to_crs("EPSG:4326")
nexiga.to_file('nexiga.geojson', driver='GeoJSON')

print("writing pv data")
# PV daten
pv_df = pd.read_csv("daten/strom.csv", delimiter=";")
pv_df["Einbaudatum"] = pd.to_datetime(pv_df["Einbaudatum"], dayfirst=True, errors="coerce")
pv_df.rename(columns={'(Peak-)Leistung [kW]': 'kWp'}, inplace=True)
pv_df["kWp"] = pv_df["kWp"].astype(str).str.replace(",", ".", regex=False).astype(float)

pv_df["geometry"] = pv_df[pv_df["Position"].notnull()]["Position"].astype(str).apply(wkt.loads)
pv_gdf = gpd.GeoDataFrame(pv_df, geometry="geometry")
pv_gdf.set_crs("EPSG:4326", inplace=True)
pv_gdf.to_file("pv.geojson", driver="GeoJSON")

print("Getting addresses for heatpumps")
# Adressen haben positionen fuer Waermepumpen
#adressen = pd.read_csv("daten/hackathon_daten/Datenquellen/Hauskoordinaten/adressen_bw.txt", delimiter=";")

# Waermepumpen: position der adressen hinzufuegen
waerme = pd.read_csv("daten/Wärmepumpen.csv", delimiter=";")

# # Normalize and prepare key columns
# adressen["key"] = (
#     adressen["gmd"].str.strip().str.casefold() + "|" +
#     adressen["str"].str.strip().str.casefold() + "|" +
#     adressen["hnr"].astype(str).str.strip()
# )
#
# adressen = adressen[["key", "ostwert", "nordwert"]].copy()

waerme["key"] = (
    waerme["Gemeinde"].str.strip().str.casefold() + "|" +
    waerme["Straßenname"].str.strip().str.casefold() + "|" +
    waerme["Hausnummer"].astype(str).str.strip()
)

print("converting datetimes for geojson")
waerme["Einbaudatum"] = pd.to_datetime(waerme["Einbaudatum"], dayfirst=True, errors="coerce")
waerme["Leistung"] = waerme["Leistung"].astype(str).str.replace(",", ".", regex=False).astype(float)

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
        for _, row in [] # adressen.iterrows()
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

#### Cluster data in h3

RES = 12

def add_h3(df):
    df = df.copy()
    df["h3"] = None
    valid = df["geometry"].notnull()
    df.loc[valid, "h3"] = df.loc[valid, "geometry"].apply(lambda g: h3.latlng_to_cell(g.y, g.x, RES))
    return df

waerme_gdf = add_h3(waerme_gdf)
pv_gdf = add_h3(pv_gdf)
nexiga = add_h3(nexiga)


print("aggregating h3 cells")
# Heat pumps per hex
waerme_agg = waerme_gdf.groupby("h3").agg(heatpump_count=("geometry", "count"), avg_power=("Leistung", "mean"))

# PV systems per hex
pv_agg = pv_gdf.groupby("h3").agg(pv_count=("geometry", "count"), avg_peak=("kWp", "mean"))

# Demographic values per hex
nexiga_agg = nexiga.groupby("h3").agg(income_category=("kk_kat", "median"), pro_ev_attitude=("lceemob", "mean"))

merged = nexiga_agg.join(waerme_agg, how="left").join(pv_agg, how="left").fillna(0)
merged = merged.reset_index()

waerme_gdf.reset_index()
nexiga.reset_index()


nexiga_waerme_join_h3 = nexiga.join(waerme_gdf, lsuffix="_waerme", how="left")

all_data_joined_on_h3 = nexiga.join(waerme_gdf, lsuffix="_waerme", how="left").join(pv_gdf, lsuffix="_pv", how="left")


#nexiga_waerme_join_h3 = nexiga.set_index("h3").join(waerme_gdf.set_index("h3"), on="h3")
waerme_grouped_income = nexiga_waerme_join_h3.groupby("kk_kat").agg(heatpump_count=("geometry", "count"))
waerme_grouped_income.reset_index()

merged["geometry"] = merged["h3"].apply(lambda h: Polygon(h3.cell_to_boundary(h)))

pv_gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")
pv_gdf.to_file("h3.geojson", driver="GeoJSON")

kk_kat_totals = nexiga["kk_kat"].value_counts().sort_index()
waerme_grouped_income["kk_kat_total"] = waerme_grouped_income.index.map(kk_kat_totals)
waerme_grouped_income["rate_per_kk_kat"] = (
    waerme_grouped_income["heatpump_count"] / waerme_grouped_income["kk_kat_total"]
)

fig, ax = plt.subplots(1, 1, figsize=(10, 10))
plt.figure(figsize=(10, 6)) # Create a new figure for clarity
sns.barplot(data=waerme_grouped_income, x="kk_kat", y="rate_per_kk_kat")
plt.title('Probability of owning a Heatpump per Income Category')
plt.xlabel('Income Category')
plt.ylabel('Probability')
plt.show()

fig, ax = plt.subplots(1, 1, figsize=(10, 10))
plt.figure(figsize=(10, 6)) # Create a new figure for clarity
sns.barplot(data=waerme_grouped_income, x="kk_kat", y="pv_count")
plt.title('PV installations per Income Category')
plt.xlabel('Income Category')
plt.ylabel('Number of PV installs')
plt.show()

fig, ax = plt.subplots(1, 1, figsize=(10, 10))
plt.figure(figsize=(10, 6)) # Create a new figure for clarity
sns.barplot(data=waerme_grouped_income, x="kk_kat", y="heatpump_count")
plt.title('Heat pumps per Income Category')
plt.xlabel('Income Category')
plt.ylabel('Number of Heat pumps')
plt.show()

plt.figure(figsize=(10, 6)) # Create a new figure for clarity
sns.barplot(data=all_data_joined_on_h3.groupby("kk_kat").agg(pv_count=("geometry", "count")).reset_index(), x="kk_kat", y="pv_count")
plt.title('pv per Income Category')
plt.xlabel('Income Category')
plt.ylabel('Number of pv')
plt.show()