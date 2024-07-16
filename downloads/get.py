import os
import requests
import logging
from PIL import Image
from io import BytesIO
from owslib.wms import WebMapService
import rasterio
from rasterio.transform import from_bounds
import numpy as np

def get_ressource(temp_dir, dateienbeschreibung, key):
    url = dateienbeschreibung[key]["url"]
    for datei in dateienbeschreibung[key]["files"]:          
        fname = key
        folder_path = os.path.join(temp_dir, fname)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, datei.split("/")[-1])
        response = requests.get(url + "/" + datei)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
        else:
            logging.error("Fehler beim Download von: " + url)

def get_wms(temp_dir, dateienbeschreibung, key):
    def calculate_dimensions(bbox, max_width=4096, max_height=3072):
        minx, miny, maxx, maxy = bbox
        bbox_width = maxx - minx
        bbox_height = maxy - miny
        aspect_ratio = bbox_width / bbox_height

        if aspect_ratio > 1:
            width = max_width
            height = int(max_width / aspect_ratio)
        else:
            height = max_height
            width = int(max_height * aspect_ratio)

        return width, height
    
    beschreibung = dateienbeschreibung[key]
    bbox = beschreibung["bbox"] 

    # Vergrößere die Bounding Box in jede Richtung um 500m
    minx, miny, maxx, maxy = bbox
    miny -= (maxy - miny)*0.2
    minx -= (maxx - minx)*0.2
    maxy += (maxy - miny)*0.2
    maxx += (maxx - minx)*0.2
    bbox = (minx, miny, maxx, maxy)

    width, height = calculate_dimensions(bbox)

    # Connect to the WMS service
    wms = WebMapService(beschreibung["url"], version=beschreibung["version"])
   
    # Define the parameters for the WMS request
    wms_params = {
        'service': 'WMS',
        'version': beschreibung["version"],
        'request': 'GetMap',
        'layers': beschreibung["layer_name"],
        'styles': beschreibung["styles"],
        'crs': 'EPSG:25832',  # Coordinate reference system
        'bbox': "{},{},{},{}".format(bbox[0],bbox[1],bbox[2],bbox[3]),  # Bounding box
        'width': width,     # Width of the output image in pixels
        'height': height,    # Height of the output image in pixels
        'format': 'image/png'  # Output format
    }

    # Make the WMS request
    response = requests.get(beschreibung["url"], params=wms_params)
    
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        folder_path = os.path.join(temp_dir, key)
        os.makedirs(folder_path, exist_ok=True)
        output_png = os.path.join(temp_dir, key, key + ".png")
        image.save(output_png)

        # Define the transform (georeferencing) based on the bounding box and dimensions
        transform = from_bounds(*bbox, width, height)

        # Open the PNG file and read its contents
        with Image.open(output_png) as image:
            image_data = image.convert('RGB')  # Ensure the image is in RGB mode
            image_array = np.array(image_data)

        # Create the georeferenced TIFF file
        output_tif = output_png.replace(".png", ".tif")
        with rasterio.open(
            output_tif,
            'w',
            driver='GTiff',
            height=image_array.shape[0],
            width=image_array.shape[1],
            count=3,  # Number of bands (RGB)
            dtype=image_array.dtype,
            crs='EPSG:25832',
            transform=transform,
        ) as dst:
            dst.write(image_array[:, :, 0], 1)  # Red channel
            dst.write(image_array[:, :, 1], 2)  # Green channel
            dst.write(image_array[:, :, 2], 3)  # Blue channel
    else:
        logging.error("Fehler beim Download von: " + beschreibung["url"])

def files(temp_dir, dateienbeschreibung):
    for key in dateienbeschreibung.keys():
        if dateienbeschreibung[key]["type"] == "ressource":
            get_ressource(temp_dir, dateienbeschreibung, key)
        elif dateienbeschreibung[key]["type"] == "WMS":
            get_wms(temp_dir, dateienbeschreibung, key)
        else:
            # Unknown type
            logging.error("Unknown type: " + dateienbeschreibung[key]["type"])
