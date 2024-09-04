import streamlit as st
from pyproj import Transformer
import requests
import shutil
import logging
import pydeck as pdk
import pandas as pd
from shapely.geometry import Polygon

st.header("Download von Geodaten für Ausbreitungsrechnungen")
st.markdown("Dieses Tool ermöglicht es, Geodaten für Ausbreitungsrechnungen herunterzuladen. Dazu wird eine Geodaten-Datei im GeoPackage-Format benötigt. Das Tool ermittelt das Bundesland, in dem sich das Polygon befindet, und lädt die entsprechenden Geodaten herunter.")

select_with_gpkg = not st.toggle("Koordinaten eingeben", value=False)
# Upload einer shp / gpkg Datei
if select_with_gpkg:
    uploaded_file = st.file_uploader("Datei hochladen", type=["gpkg"])
else:
    st.caption("Eingabe der Koordinaten im EPSG:25832 Format")
    st.caption("Untere linke Ecke:")
    c1, c2 = st.columns(2)
    with c1:
        x_ule = st.number_input("X-Koordinate", key="xule", value=0.00, step=0.01, format="%.2f")
    with c2:
        y_ule = st.number_input("Y-Koordinate", key="yule", value=0.00, step=0.01, format="%.2f")
    st.caption("Obere rechte Ecke:")

    c3, c4 = st.columns(2)
    with c3:
        x_ore = st.number_input("X-Koordinate", key="xore", value=0.00, step=0.01, format="%.2f")
    with c4:
        y_ore = st.number_input("Y-Koordinate", key="yore", value=0.00, step=0.01, format="%.2f")
    uploaded_file = None


def show_map(polygon):
    polygon_coordinates = [[point[1], point[0]] for point in polygon.exterior.coords]    

    # Define GeoJSON data structure
    polygon_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_coordinates]
                },
                "properties": {
                    "name": "Sample Polygon"
                }
            }
        ]
    }

    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        polygon_geojson,
        pickable=True,
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
        get_fill_color=[255, 0, 0, 100],  # Red color with some transparency
        get_line_color=[0, 0, 0, 255]     # Black outline        
    )   

    view_state = pdk.ViewState(
        latitude=polygon.centroid.x,
        longitude=polygon.centroid.y,
        zoom=12,
        #pitch=50
    )

    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=view_state
    )

    # Render the map in Streamlit
    st.pydeck_chart(deck)

# Rechne EPSG:25832 in lat und lon um
def epsg25832_to_latlon(x, y):
    transformer = Transformer.from_crs("epsg:25832", "epsg:4326")
    return transformer.transform(x, y)

# Nutze einen Webservice um für eine geokoordinate das zugehörige Bundesland zu ermitteln
@st.cache_data
def get_state(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon
    }

    header = { "User-Agent": "RichtersHuels", "Referrer": "info@richtershuels.de", "From": "info@richtershuels.de" }
    
    response = requests.get(url, params=params, headers=header)
    if response.status_code != 200:
        logging.error("Fehler beim Abrufen des Bundeslandes. Fehler Code: {}".format(response.status_code) + " Inhalt: " + response.text)
        return response.status_code, None
    data = response.json()    
    return response.status_code, data["address"]["state"]

if uploaded_file is not None or not select_with_gpkg:

    # Erstelle einen temporären Ordner für die heruntergeladenen Dateien
    # Gebe dem Ordner einen eindeutigen Namen
    import os
    import uuid
    import geopandas as gpd

    temp_dir = None
    if uploaded_file is not None:
        # Speichere die Datei im temporären Ordner
        # Ändere den Dateinamen in "data.shp" oder "data.gpkg"
        temp_dir = "temp_" + str(uuid.uuid4())
        os.makedirs(temp_dir)
        if uploaded_file.name.endswith(".shp"):
            fname = "data.shp"
        elif uploaded_file.name.endswith(".gpkg"):
            fname = "data.gpkg"
        geofile = os.path.join(temp_dir, fname)
        with open(geofile, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Erstelle polygon aus der shp / gpkg Datei
        gdf = gpd.read_file(geofile)
        polygon = gdf.geometry[0]
        shutil.rmtree(temp_dir)
    else:
        polygon = Polygon([(x_ule, y_ule), (x_ule, y_ore), (x_ore, y_ore), (x_ore, y_ule)])
        gdf = None
        
    
    p4326 = Polygon([epsg25832_to_latlon(x, y) for x, y in polygon.exterior.coords])
    for point in p4326.exterior.coords:
        if point[0]<=0 or point[1]<=0:
            st.error("Kein valides Polygon angegeben.")
            st.stop()
    with st.expander("Ausdehnung kontrollieren"):
        show_map(p4326)
    st.markdown("---")
    st.caption("Download")
    
    if len(gdf) > 1:
        st.error("Es wurde mehr als ein Polygon erkannt. Bitte laden Sie nur eine Datei hoch, die ein Polygon enthält.")
        shutil.rmtree(temp_dir)
        st.stop()
    

    code, bundesland = get_state(*epsg25832_to_latlon(polygon.bounds[0], polygon.bounds[1]))
    if code != 200:
        st.error("Fehler beim Abrufen des Bundeslandes.")
        st.error("Status Code: ", code)
        shutil.rmtree(temp_dir)
        st.stop()

    st.write("Bundesland: ", bundesland)

    if bundesland == "Nordrhein-Westfalen":
        from downloads.nrw.files import list_filenames
        dateienbeschreibung = list_filenames(polygon.bounds)
    elif bundesland == "Niedersachsen":
        from downloads.nds.files import list_filenames
        ulx, uly = epsg25832_to_latlon(polygon.bounds[0], polygon.bounds[1])
        orx, ory = epsg25832_to_latlon(polygon.bounds[2], polygon.bounds[3])
        dateienbeschreibung = list_filenames((ulx, uly, orx, ory), polygon.bounds)
    else:
        st.error("Das Bundesland wird noch nicht unterstützt.")
        shutil.rmtree(temp_dir)
        st.stop()

    # Bestätige den Ladevorgang durch Klick auf einen Download Button

    st.caption("Dateien zum Download:")
    download_keys = []
    for key in dateienbeschreibung.keys():
        v = st.checkbox(f"{key} (Anzahl: {len(dateienbeschreibung[key]['files']) if dateienbeschreibung[key]['type'] == 'ressource' else 1})", value=True)
        if v:
            download_keys.append(key)
            if key == "Gelände":
                spacing = st.number_input("Auflösung der Geländedatei", value=1) 

    download_dateienbeschreibung = {}
    for k in download_keys:
        download_dateienbeschreibung[k] = dateienbeschreibung[k]

    if len(download_dateienbeschreibung) == 0:
        st.warning("Keine Dateien ausgewählt.")
        starten = False
    else:
        starten = st.button("Download starten")

    if starten:
        temp_dir = "temp_" + str(uuid.uuid4())
        os.makedirs(temp_dir)
        # Lade Dateien herunter
        from downloads.get import files
        files(temp_dir, download_dateienbeschreibung)

        # Processing
        from processing import merge_tifs
        if "Gelände" in download_dateienbeschreibung:
            merge_tifs([temp_dir + "/Gelände/" + file_name.split("/")[-1] for file_name in dateienbeschreibung["Gelände"]["files"]], os.path.join(temp_dir, "Gelände", "Gelände_zusammen.tif"))
            from processing import tif_to_xyz
            tif_to_xyz(temp_dir + "/Gelände/Gelände_zusammen.tif", os.path.join(temp_dir, "Gelände", "dgm.xyz"), spacing=spacing)
        #if "ABK" in download_dateienbeschreibung:
        #    merge_tifs([temp_dir + "/ABK/" + file_name for file_name in dateienbeschreibung["ABK"]["files"]], os.path.join(temp_dir, "ABK", "abk_zusammen.tif"))

        # Erstelle zip Datei
        import zipfile
        import io
        with io.BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))

            zip_data = zip_buffer.getvalue()

            st.download_button(
            label="Download",
            data=zip_data,
            file_name="dateien.zip",
            mime="application/zip"
        )


        # Entferne temporären Ordner
        shutil.rmtree(temp_dir)
