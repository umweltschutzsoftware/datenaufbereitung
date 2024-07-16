# Kobiniere eine mehrere tif Dateien zu einer tif Datei

from PIL import Image
import numpy as np
import rasterio
from rasterio.merge import merge
import csv

def merge_tifs(tif_files, output_file):
    """
    Merges multiple TIFF files into one and preserves the original georeferencing information of each file.

    Args:
    tif_files (list of str): List of paths to the TIFF files.
    output_file (str): Path to the output merged TIFF file.

    Returns:
    None
    """
    src_files_to_mosaic = []
    for tif in tif_files:
        src = rasterio.open(tif, crs='EPSG:25832')
        src_files_to_mosaic.append(src)

    mosaic, out_trans = merge(src_files_to_mosaic, method='first', nodata=-9999)

    # Update the metadata with the merged mosaic information
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "crs": src_files_to_mosaic[0].crs
    })

    # Write the mosaic to a new file
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(mosaic)

    # Close the source files
    for src in src_files_to_mosaic:
        src.close()

def tif_to_xyz(tif_file, xyz_file, spacing=1):
    """
    Tastet die Höhenwerte eines TIFF-Rasters in regelmäßigen Abständen ab und speichert die X- und Y-Koordinaten sowie die Höhe in einer XYZ-Datei.

    Parameters:
    tiff_datei (str): Pfad zur TIFF-Datei.
    abstand (int): Der Abstand zwischen den Abtastpunkten.
    output_datei (str): Pfad zur Ausgabe-XYZ-Datei.
    """
    with rasterio.open(tif_file) as dataset:
        # Lesen der Rasterdaten
        raster = dataset.read(1)
        
        # Bestimmen der Rastertransformation
        transform = dataset.transform
        
        # Öffnen der Ausgabe-XYZ-Datei
        xyz_file_without_extension = xyz_file[:-4]
        with open(xyz_file, mode='w', newline='') as file:
            with open(xyz_file_without_extension + "32.xyz", mode='w', newline='') as file32:
                writer = csv.writer(file, delimiter=' ')
                writer32 = csv.writer(file32, delimiter=' ')
                # Abtastung in regelmäßigen Abständen
                for row in range(0, raster.shape[0], spacing):
                    for col in range(0, raster.shape[1], spacing):
                        # Berechnung der x- und y-Koordinaten
                        x, y = transform * (col, row)
                        höhe = raster[row, col]
                        # Schreiben der Werte in die Datei (X, Y ohne Nachkommastellen, Z mit zwei Nachkommastellen)
                        writer.writerow([int(x), int(y), f"{höhe:.2f}"])
                        writer32.writerow([32000000+ int(x), int(y), f"{höhe:.2f}"])