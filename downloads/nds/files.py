import requests
import logging

def list_lod_filenames(bounds):
    lod_url = r"https://lod.stac.lgln.niedersachsen.de/search?bbox={}%2C{}%2C{}%2C{}".format(bounds[1], bounds[0], bounds[3], bounds[2])
    # Set the accept header
    headers = {'Accept': 'application/json'}
    response = requests.get(lod_url, headers=headers)

    if response.status_code != 200:
        return response.status_code, None
    
    filenames = {
        "type": "ressource",
        "url": None,
        "files": []
    }

    features = response.json()["features"]
    for feature in features:
        assets = feature["assets"]
        if "lod1-gml" in assets.keys():
            # Get the URL of the asset
            asset_url = assets["lod1-gml"]["href"]
            # Splitting the URL
            split_index = asset_url.index('/', 8)  # Find the first '/' after 'https://'
            url = asset_url[:split_index + 1]  # Include the '/'
            filename = asset_url[split_index + 1:]

            if filenames["url"] is None:
                filenames["url"] = url
            else:
                # Check if the URL is the same
                if filenames["url"] != url:
                    logging("URLs are not the same")
                    return 400, None
            filenames["files"].append(filename)
    return 200, filenames

def list_dgm_filenames(bounds):
    dgm_url = r"https://dgm.stac.lgln.niedersachsen.de/search?bbox={}%2C{}%2C{}%2C{}".format(bounds[1], bounds[0], bounds[3], bounds[2])
    # Set the accept header
    headers = {'Accept': 'application/json'}
    response = requests.get(dgm_url, headers=headers)

    if response.status_code != 200:
        return response.status_code, None
    
    filenames = {
        "type": "ressource",
        "url": None,
        "files": []
    }

    features = response.json()["features"]
    for feature in features:
        assets = feature["assets"]
        if "dgm1-tif" in assets.keys():
            # Get the URL of the asset
            asset_url = assets["dgm1-tif"]["href"]
            # Splitting the URL
            split_index = asset_url.index('/', 8)  # Find the first '/' after 'https://'
            url = asset_url[:split_index + 1]  # Include the '/'
            filename = asset_url[split_index + 1:]

            if filenames["url"] is None:
                filenames["url"] = url
            else:
                # Check if the URL is the same
                if filenames["url"] != url:
                    logging("URLs are not the same")
                    return 400, None
            filenames["files"].append(filename)
    return 200, filenames

def list_filenames(bounds4326, bounds25832):
    filenames = {}
    code, lod_filenames = list_lod_filenames(bounds4326)
    filenames["Gebäude"] = lod_filenames
    if code != 200:
        return None
    
    code, dgm_filenames = list_dgm_filenames(bounds4326)
    filenames["Gelände"] = dgm_filenames
    if code != 200:
        return None
    
    filenames["ALKIS"] = {
        "type": "WMS",
        "url": "https://opendata.lgln.niedersachsen.de/doorman/noauth/alkis_wms",
        "bbox": bounds25832,
        "layer_name": "ALKIS",
        "format": "image/png",
        "styles": "SW",
        "version": "1.3.0"
    }

    return filenames