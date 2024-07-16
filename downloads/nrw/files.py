# Kacheln ermitteln
# Die Kacheln werden durch die untere linke Ecke definiert
# Der Parameter kachelMeter gibt die Kantenlänge der Kacheln in Metern an
# Die untere linke wird in EPSG 25832 angegeben
# Die Kacheln werden in einer Liste von URLs definiert
# x Koordinate hat 7 Stellen, die y Koordinate hat 8 Stellen
# Die Anzahl der Stellen wird durch kachelMeter reduziert, d.h. kachelMeter=1000 -> X Koordinate hat 3 und y Koordinate hat 4 Stellen
# Es müssen alle unteren linken Ecken der Kacheln ermittelt werden, die das Polygon schneiden
# Die Bounds werden direkt als Parameter übergeben
def get_kacheln(bounds):
    kachel_meter = 1000
    kacheln = []
    x1, y1, x2, y2 = bounds
    x1 = int(x1 / kachel_meter) * kachel_meter
    y1 = int(y1 / kachel_meter) * kachel_meter
    x2 = int(x2 / kachel_meter) * kachel_meter
    y2 = int(y2 / kachel_meter) * kachel_meter
    for x in range(x1, x2 + kachel_meter, kachel_meter):
        for y in range(y1, y2 + kachel_meter, kachel_meter):
            kacheln.append((x/kachel_meter, y/kachel_meter))
    return kacheln

dateien = [{
    "url": "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod1_gml/lod1_gml/",
    "datei": r"LoD1_32_{}_{}_1_NW.gml",
    "fname": "Gebäude"
},
{
    "url": "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tiff/dgm1_tiff/",
    "fname": "Gelände"
},
{
    "url": "https://www.opengeodata.nrw.de/produkte/geobasis/lk/akt/abk_tiff/abk_sw_tiff/",
    "fname": "ABK",
    "datei": r"abk_sw_32{}_{}_1.tif",
}]

def dgm_filename_aus_metadata(x, y):
    # Lese die Datei dgm1_tiff.csv in einen Dataframe ein
    import pandas as pd
    df = pd.read_csv("downloads/nrw/dgm1_tiff.csv", skiprows=5, delimiter=";")
    # Finde die Zeile in der Spalte "Kachelnamen", die die übergebene x und y Koordinate enthält
    # Gebe den gefundenen Kachelnamen als Ergebnis der Funktion zurück
    return df[(df["Kachelname"].str.contains(str(x))) & (df["Kachelname"].str.contains(str(y)))].iloc[0]["Kachelname"] + ".tif"


def list_filenames(bounds):
    kacheln = get_kacheln(bounds)
    filenames = {}
    for kachel in kacheln:
        for datei in dateien:
            if datei["fname"] not in filenames:
                filenames[datei["fname"]] = {
                    "type": "ressource",
                    "url": datei["url"],
                    "files": []
                }
            x, y = kachel
            if datei["fname"] == "Gelände":
                datei_name = dgm_filename_aus_metadata(int(x), int(y))
            else:
                datei_name = datei["datei"].format(int(x), int(y))
            filenames[datei["fname"]]["files"].append(datei_name)

    

    filenames["ALKIS"] = {
        "type": "WMS",
        "url": "https://www.wms.nrw.de/geobasis/wms_nw_alkis",
        "bbox": bounds,
        "layer_name": ['adv_alkis_flurstuecke', 'adv_alkis_flurstuecke'],
        "format": "image/png",
        "styles": "Grau",
        "version": "1.3.0"
    }
    return filenames