import streamlit as st
from pyproj import Transformer
import requests
import shutil
import logging

st.header("Download von Geodaten für Ausbreitungsrechnungen")
st.markdown("Dieses Tool ermöglicht es, Geodaten für Ausbreitungsrechnungen herunterzuladen. Dazu wird eine Geodaten-Datei im GeoPackage-Format benötigt. Das Tool ermittelt das Bundesland, in dem sich das Polygon befindet, und lädt die entsprechenden Geodaten herunter.")

# Upload einer shp / gpkg Datei
uploaded_file = st.file_uploader("Datei hochladen", type=["gpkg"])

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

if uploaded_file is not None:

    # Erstelle einen temporären Ordner für die heruntergeladenen Dateien
    # Gebe dem Ordner einen eindeutigen Namen
    import os
    import uuid
    temp_dir = "temp_" + str(uuid.uuid4())
    os.makedirs(temp_dir)

    # Speichere die Datei im temporären Ordner
    # Ändere den Dateinamen in "data.shp" oder "data.gpkg"
    if uploaded_file.name.endswith(".shp"):
        fname = "data.shp"
    elif uploaded_file.name.endswith(".gpkg"):
        fname = "data.gpkg"
    geofile = os.path.join(temp_dir, fname)
    with open(geofile, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Erstelle polygon aus der shp / gpkg Datei
    import geopandas as gpd
    gdf = gpd.read_file(geofile)
    polygon = gdf.geometry[0]

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
    shutil.rmtree(temp_dir)

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
    spacing = st.number_input("Auflösung der Geländedatei", value=1)
    # Bestätige den Ladevorgang durch Klick auf einen Download Button
    st.write("Anzahl Dateien: {}".format(sum([len(dateienbeschreibung[key]["files"]) if dateienbeschreibung[key]["type"] == "ressource" else 1 for key in dateienbeschreibung.keys()])))
    starten = st.button("Download starten")

    if starten:
        temp_dir = "temp_" + str(uuid.uuid4())
        os.makedirs(temp_dir)
        # Lade Dateien herunter
        from downloads.get import files
        files(temp_dir, dateienbeschreibung)

        # Processing
        from processing import merge_tifs
        merge_tifs([temp_dir + "/Gelände/" + file_name.split("/")[-1] for file_name in dateienbeschreibung["Gelände"]["files"]], os.path.join(temp_dir, "Gelände", "Gelände_zusammen.tif"))
        #merge_tifs([temp_dir + "/ABK/" + file_name for file_name in dateienbeschreibung["ABK"]["files"]], os.path.join(temp_dir, "ABK", "abk_zusammen.tif"))

        from processing import tif_to_xyz
        
        tif_to_xyz(temp_dir + "/Gelände/Gelände_zusammen.tif", os.path.join(temp_dir, "Gelände", "dgm.xyz"), spacing=spacing)


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
