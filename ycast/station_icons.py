import logging
import requests
import io
import os

from PIL import Image

import ycast.generic as generic
from ycast import __version__

MAX_SIZE = 290
CACHE_NAME = 'icons'


def get_icon(station):
    cache_path = generic.get_cache_path(CACHE_NAME)
    if not cache_path:
        return None
    station_icon_file = cache_path + '/' + station.id
    if not os.path.exists(station_icon_file):
        logging.debug("Station icon cache miss. Fetching and converting station icon for station with ID '%s'", station.id)
        headers = {'User-Agent': generic.USER_AGENT + '/' + __version__}
        try:
            response = requests.get(station.icon, headers=headers)
        except requests.exceptions.ConnectionError as e:
            logging.error("Connection to station icon URL failed: %s", e)
            return None
        if response.status_code != 200:
            logging.error("Could not get station icon data from '%s' (HTTP status %s)", station.icon, response.status_code)
            return None
        try:
            image = Image.open(io.BytesIO(response.content)).convert('RGBA')
            image = Image.alpha_composite(Image.new('RGBA', image.size, 'WHITE'), image).convert('RGB')
            if image.size[0] > image.size[1]:
                ratio = MAX_SIZE / image.size[0]
            else:
                ratio = MAX_SIZE / image.size[1]
            image = image.resize((int(image.size[0] * ratio), int(image.size[1] * ratio)), Image.LANCZOS)
            image.save(station_icon_file, format='JPEG')
        except Exception as e:
            logging.error("Station icon conversion error: %s", e)
            return None
    try:
        with open(station_icon_file, 'rb') as file:
            image_conv = file.read()
    except PermissionError:
        logging.error("Could not read cached station icon file '%s'",
                      station_icon_file)
        return None
    return image_conv
