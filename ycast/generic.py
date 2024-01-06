import logging
import os

import yaml

USER_AGENT = 'YCast'
VAR_PATH = os.path.expanduser('~') + '/.ycast'
CACHE_PATH = VAR_PATH + '/cache'

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'countries.yml'), 'r') as f:
    country_names = yaml.safe_load(f)


class Directory:
    def __init__(self, name, item_count, displayname=None):
        self.name = name
        self.item_count = item_count
        if displayname:
            self.displayname = displayname
        else:
            self.displayname = name


def generate_stationid_with_prefix(id, prefix):
    if not prefix or len(prefix) != 2:
        logging.error("Invalid station prefix length (must be 2)")
        return None
    if not id:
        logging.error("Missing station id for full station id generation")
        return None
    return str(prefix) + '_' + str(id)


def get_stationid_prefix(id):
    if len(id) < 4:
        logging.error("Could not extract stationid (Invalid station id length)")
        return None
    return id[:2]


def get_stationid_without_prefix(id):
    if len(id) < 4:
        logging.error("Could not extract stationid (Invalid station id length)")
        return None
    return id[3:]


def get_cache_path(cache_name):
    cache_path = CACHE_PATH + '/' + cache_name
    try:
        os.makedirs(cache_path)
    except FileExistsError:
        pass
    except PermissionError:
        logging.error("Could not create cache folders (%s) because of access permissions", cache_path)
        return None
    return cache_path


def get_country_name(code):
    return country_names.get(code.upper(), code.upper())
