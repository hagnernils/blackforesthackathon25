import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from pyproj import Transformer

# Optional: Define transformer for EPSG:25832 -> EPSG:4326
transformer = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)


# Nexiga Daten laden
nexiga = gpd.read_file("daten/hackathon_daten/Datenquellen/Nexiga/nexiga_all.shp")
nexiga = nexiga.to_crs("EPSG:4326")
nexiga.to_file('nexiga.geojson', driver='GeoJSON')

gdf2 = gpd.read_file("daten/hackathon_daten/Datenquellen/ALKIS/ALKIS-oE_085310_Ihringen_shp/flurstueck.shp")
gdf2.to_file('ihringen.geojson', driver='GeoJSON')
gdf2 = gdf2.to_crs("EPSG:4326")

# Strom / Photovoltaik
df = pd.read_csv("daten/strom.csv", delimiter=";")
# Convert WKT column to geometry
#df["geometry"] = df[df["Position"].notnull()]["Position"].astype(str).apply(wkt.loads)
#gdf = gpd.GeoDataFrame(df, geometry="geometry")
# Set CRS to WGS84 (EPSG:4326), common for GPS coordinates
#gdf.set_crs("EPSG:4326", inplace=True)
#gdf.to_file("strom.geojson", driver="GeoJSON")

adressen = pd.read_csv("daten/hackathon_daten/Datenquellen/Hauskoordinaten/adressen_bw.txt", delimiter=";")

# Waermepumpen
waerme = pd.read_csv("daten/Wärmepumpen.csv", delimiter=";")

def address_to_Point(stadt, strasse, hausnummer):
    adressen["street"] = strasse
    result = adressen.loc[
        (adressen['gmd'].str.casefold() == stadt.casefold()) &
        (adressen['str'].str.casefold() == strasse.casefold()) &
        (adressen['hnr'].astype(str) == str(hausnummer))
        ]
    return Point(float(result["ostwert"]), float(result["nordwert"])).wkt

print(address_to_Point("Weisweil", "Friedhofstraße", 11))

# Normalize and prepare key columns
adressen["key"] = (
    adressen["gmd"].str.strip().str.casefold() + "|" +
    adressen["str"].str.strip().str.casefold() + "|" +
    adressen["hnr"].astype(str).str.strip()
)

waerme["key"] = (
    waerme["Gemeinde"].str.strip().str.casefold() + "|" +
    waerme["Straßenname"].str.strip().str.casefold() + "|" +
    waerme["Hausnummer"].astype(str).str.strip()
)

waerme["timestamp"] = pd.to_datetime(waerme["Einbaudatum"], dayfirst=True, errors="coerce")
adressen = adressen[["key", "ostwert", "nordwert"]].copy()

def to_wgs84_wkt(row):
    try:
        x, y = float(row["ostwert"]), float(row["nordwert"])
        lon, lat = transformer.transform(x, y)
        return Point(lon, lat).wkt
    except:
        return None

coord_dict = {
    row["key"]: to_wgs84_wkt(row)
    for _, row in adressen.iterrows()
}

waerme["Position"] = waerme["key"].map(coord_dict)

waerme["geometry"] = waerme["Position"].apply(wkt.loads)
waerme_gdf = gpd.GeoDataFrame(waerme, geometry="geometry", crs="EPSG:4326")
waerme_gdf = waerme_gdf.dropna(subset=["geometry"])
waerme_gdf.to_file("waerme.geojson", driver="GeoJSON")

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