import geopandas as gpd

# Datei laden
gdf = gpd.read_file("daten/hackathon_daten/Datenquellen/Nexiga/nexiga_all.shp")
gdf2 = gpd.read_file("daten/hackathon_daten/Datenquellen/ALKIS/ALKIS-oE_085310_Ihringen_shp/flurstueck.shp")

# In WGS84 (lat/lon) umprojizieren, falls noch nicht in EPSG:4326
gdf = gdf.to_crs("EPSG:4326")
gdf2 = gdf2.to_crs("EPSG:4326")

gdf.to_file('nexiga.geojson', driver='GeoJSON')
gdf2.to_file('ihringen.geojson', driver='GeoJSON')
