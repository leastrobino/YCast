import requests
import logging

from ycast import __version__
import ycast.vtuner as vtuner
import ycast.generic as generic

API_ENDPOINT = 'http://all.api.radio-browser.info'
MINIMUM_COUNT_COUNTRY = 5
MINIMUM_COUNT_LANGUAGE = 0
MINIMUM_COUNT_GENRE = 50
DEFAULT_STATION_LIMIT = 200
SHOW_BROKEN_STATIONS = False
ID_PREFIX = 'RB'


class Station:
    def __init__(self, station_json):
        self.id = generic.generate_stationid_with_prefix(station_json.get('stationuuid'), ID_PREFIX)
        self.name = station_json.get('name')
        self.url = station_json.get('url')
        self.icon = station_json.get('favicon')
        try:
            self.tags = [tag.capitalize() for tag in station_json['tags'].split(',')]
        except:
            self.tags = ['']
        try:
            self.countrycode = station_json['countrycode'].upper()
        except:
            self.countrycode = None
        try:
            self.language = station_json['language'].title()
        except:
            self.language = None
        self.votes = station_json.get('votes')
        self.codec = station_json.get('codec')
        self.bitrate = station_json.get('bitrate')

    def to_vtuner(self):
        return vtuner.Station(self.id, self.name, self.url, icon=self.icon, description=', '.join(self.tags),
                              genre=self.tags[0], location=self.countrycode, mime=self.codec, bitrate=self.bitrate)

    def get_playable_url(self):
        try:
            playable_url_json = request('url/' + generic.get_stationid_without_prefix(self.id))
            self.url = playable_url_json['url']
        except KeyError:
            logging.error("Could not retrieve first playlist item for station with ID '%s'", self.id)


def request(url):
    logging.debug("Radiobrowser API request: %s", url)
    headers = {'Content-Type': 'application/json', 'User-Agent': generic.USER_AGENT + '/' + __version__}
    try:
        response = requests.get(API_ENDPOINT + '/json/' + url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        logging.error("Connection to Radiobrowser API failed: %s", e)
        return {}
    if response.status_code != 200:
        logging.error("Could not fetch data from Radiobrowser API (HTTP status %s)", response.status_code)
        return {}
    return response.json()


def get_station_by_id(id):
    station_json = request('stations/byuuid/' + str(id))
    if station_json and len(station_json):
        return Station(station_json[0])
    else:
        return None


def search(name, limit=DEFAULT_STATION_LIMIT):
    apicall = 'stations/search?name=' + requests.utils.quote(name, safe='') + '&hidebroken=' + \
              str(not SHOW_BROKEN_STATIONS).lower() + '&order=name&reverse=false&limit=' + str(limit)
    stations_json = request(apicall)
    return [Station(station_json) for station_json in stations_json]


def get_country_directories(threshold=MINIMUM_COUNT_COUNTRY):
    country_directories = []
    apicall = 'countries?hidebroken=' + str(not SHOW_BROKEN_STATIONS).lower()
    countries_raw = request(apicall)
    countries_dict = {}
    for country_raw in countries_raw:
        if country_raw.get('iso_3166_1') and country_raw.get('stationcount'):
            # Merge duplicates with case folding
            country_code = country_raw['iso_3166_1'].lower()
            countries_dict[country_code] = countries_dict.get(country_code, 0) + country_raw['stationcount']
    for country_code, stationcount in countries_dict.items():
        if stationcount >= threshold:
            country_name = generic.get_country_name(country_code)
            country_directories.append(generic.Directory(country_code, stationcount, country_name))
    country_directories.sort(key=lambda directory: directory.displayname)
    return country_directories


def get_language_directories(threshold=MINIMUM_COUNT_LANGUAGE):
    language_directories = []
    apicall = 'languages?hidebroken=' + str(not SHOW_BROKEN_STATIONS).lower() + '&order=name&reverse=false'
    languages_raw = request(apicall)
    for language_raw in languages_raw:
        if (language_raw.get('name') and language_raw.get('stationcount') and
                int(language_raw['stationcount']) >= threshold and (language_raw.get('iso_639') or threshold)):
            language_directories.append(generic.Directory(language_raw['name'], language_raw['stationcount'],
                                                          language_raw['name'].title()))
    return language_directories


def get_genre_directories(threshold=MINIMUM_COUNT_GENRE):
    genre_directories = []
    apicall = 'tags?hidebroken=' + str(not SHOW_BROKEN_STATIONS).lower() + '&order=name&reverse=false'
    genres_raw = request(apicall)
    for genre_raw in genres_raw:
        if (genre_raw.get('name') and genre_raw.get('stationcount') and
                int(genre_raw['stationcount']) >= threshold):
            genre_directories.append(generic.Directory(genre_raw['name'], genre_raw['stationcount'],
                                                       genre_raw['name'].capitalize()))
    return genre_directories


def _get_stations(key, value, args=None):
    apicall = 'stations/' + key + '/' + requests.utils.quote(str(value), safe='') + \
              '?hidebroken=' + str(not SHOW_BROKEN_STATIONS).lower()
    if args:
        apicall += '&' + args
    stations_json = request(apicall)
    return [Station(station_json) for station_json in stations_json]


def get_stations_by_country(country):
    return _get_stations('bycountrycodeexact', country, 'order=name&reverse=false')


def get_stations_by_language(language):
    return _get_stations('bylanguageexact', language, 'order=name&reverse=false')


def get_stations_by_genre(genre):
    return _get_stations('bytagexact', genre, 'order=name&reverse=false')


def get_stations_by_clicks(limit=DEFAULT_STATION_LIMIT):
    return _get_stations('topclick', limit)


def get_stations_by_votes(limit=DEFAULT_STATION_LIMIT):
    return _get_stations('topvote', limit)
