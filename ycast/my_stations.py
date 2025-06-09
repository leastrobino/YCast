import base64
import hashlib
import logging

import yaml

import ycast.vtuner as vtuner
import ycast.generic as generic

ID_PREFIX = 'MY'

config_file = 'stations.yml'


class Station:
    def __init__(self, id, name, url, tag):
        self.id = generic.generate_stationid_with_prefix(id, ID_PREFIX)
        self.name = name
        self.url = url
        self.icon = None
        self.tag = tag

    def to_vtuner(self):
        return vtuner.Station(self.id, self.name, self.url, icon=self.icon,
                              description=self.tag, genre=self.tag)


def set_config(config):
    global config_file
    if config:
        config_file = config
    if get_stations_yaml():
        return True
    else:
        return False


def get_station_by_id(id):
    my_stations_yaml = get_stations_yaml()
    if my_stations_yaml:
        for category in my_stations_yaml:
            for station in get_stations_by_category(category):
                if id == generic.get_stationid_without_prefix(station.id):
                    return station
    return None


def get_stations_yaml():
    try:
        with open(config_file, 'r') as f:
            my_stations = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("Station configuration file '%s' not found", config_file)
        return None
    except PermissionError:
        logging.error("Could not read station configuration file '%s'", config_file)
        return None
    except yaml.YAMLError as e:
        logging.error("Station configuration file format error: %s", e)
        return None
    return my_stations


def get_category_directories():
    my_stations_yaml = get_stations_yaml()
    categories = []
    if my_stations_yaml:
        for category in my_stations_yaml:
            categories.append(generic.Directory(category, len(get_stations_by_category(category))))
    return categories


def get_stations_by_category(category):
    my_stations_yaml = get_stations_yaml()
    stations = []
    if my_stations_yaml and category in my_stations_yaml:
        for station_name in my_stations_yaml[category]:
            station_url = my_stations_yaml[category][station_name]
            station_id = get_checksum(station_name + station_url)
            stations.append(Station(station_id, station_name, station_url, category))
    return stations


def get_checksum(data):
    digest = hashlib.md5(data.encode()).digest()
    xor_fold = bytes(digest[i] ^ digest[i+8] for i in range(8))
    return base64.urlsafe_b64encode(xor_fold).decode()[:11]
