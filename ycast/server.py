import logging
import re

from flask import Flask, request, url_for, redirect, abort, make_response

import ycast.vtuner as vtuner
import ycast.radiobrowser as radiobrowser
import ycast.my_stations as my_stations
import ycast.generic as generic
import ycast.station_icons as station_icons


PATH_ROOT = 'ycast'
PATH_PLAY = 'play'
PATH_STATION = 'station'
PATH_SEARCH = 'search'
PATH_ICON = 'icon'
PATH_MY_STATIONS = 'my_stations'
PATH_RADIOBROWSER = 'radiobrowser'
PATH_RADIOBROWSER_COUNTRY = 'country'
PATH_RADIOBROWSER_LANGUAGE = 'language'
PATH_RADIOBROWSER_GENRE = 'genre'
PATH_RADIOBROWSER_POPULAR = 'popular'

station_tracking = True
my_stations_enabled = False
app = Flask(__name__)


def run(config, address='0.0.0.0', port=80):
    check_my_stations_feature(config)
    try:
        app.run(host=address, port=port)
    except PermissionError:
        logging.error("No permission to create socket. Are you trying to use ports below 1024 without elevated rights?")


def check_my_stations_feature(config):
    global my_stations_enabled
    my_stations_enabled = my_stations.set_config(config)


def get_directories_page(subdir, directories):
    page = vtuner.Page()
    if len(directories) == 0:
        page.add(vtuner.Display("No entries found"))
        page.set_count(1)
        return page
    for directory in get_paged_elements(directories):
        vtuner_directory = vtuner.Directory(directory.displayname,
                                            url_for(subdir, directory=directory.name, _external=True),
                                            directory.item_count)
        page.add(vtuner_directory)
    page.set_count(len(directories))
    return page


def get_stations_page(stations):
    page = vtuner.Page()
    if len(stations) == 0:
        page.add(vtuner.Display("No stations found"))
        page.set_count(1)
        return page
    for station in get_paged_elements(stations):
        vtuner_station = station.to_vtuner()
        if station_tracking:
            vtuner_station.url = url_for('get_stream_url', id=vtuner_station.id, _external=True)
        else:
            vtuner_station.url = strip_https(vtuner_station.url)
        vtuner_station.icon = url_for('get_station_icon', id=vtuner_station.id, _external=True)
        page.add(vtuner_station)
    page.set_count(len(stations))
    return page


def get_paged_elements(items):
    try:
        if request.args.get('startitems'):
            offset = int(request.args.get('startitems')) - 1
        elif request.args.get('startItems'):
            offset = int(request.args.get('startItems')) - 1
        elif request.args.get('start'):
            offset = int(request.args.get('start')) - 1
        else:
            offset = 0
    except:
        logging.error("Invalid paging offset. The query string was: %s", request.query_string.decode())
        abort(400)
    if offset < 0:
        offset = 0
    if offset >= len(items):
        logging.warning("Paging offset larger than item count")
        return []
    try:
        if request.args.get('enditems'):
            limit = int(request.args.get('enditems'))
        elif request.args.get('endItems'):
            limit = int(request.args.get('endItems'))
        elif request.args.get('howmany'):
            limit = offset + int(request.args.get('howmany'))
        else:
            limit = len(items)
    except:
        logging.error("Invalid paging limit. The query string was: %s", request.query_string.decode())
        abort(400)
    if limit < 0:
        limit = 0
    if limit <= offset:
        logging.warning("Paging limit smaller than offset")
        return []
    return items[offset:limit]


def get_station_by_id(stationid, additional_info=False):
    station_id_prefix = generic.get_stationid_prefix(stationid)
    if station_id_prefix == my_stations.ID_PREFIX:
        return my_stations.get_station_by_id(generic.get_stationid_without_prefix(stationid))
    elif station_id_prefix == radiobrowser.ID_PREFIX:
        station = radiobrowser.get_station_by_id(generic.get_stationid_without_prefix(stationid))
        if station and additional_info:
            station.get_playable_url()
        return station
    return None


def strip_https(url):
    if url.startswith('https://'):
        url = 'http://' + url[8:]
    return url


def vtuner_redirect(url):
    if request.host and not re.search('^[A-Za-z0-9]+\.vtuner\.com$', request.host):
        logging.warning("You are not accessing a YCast redirect with a whitelisted host URL (*.vtuner.com). "
                        "Some AVRs have problems with this. The requested host was: %s", request.host)
    return redirect(url, code=302)


@app.route('/setupapp/<path:path>',
           methods=['GET', 'POST'])
def upstream(path):
    path = path.lower()
    if request.args.get('token') == '0':
        return vtuner.get_init_token()
    if request.args.get('search'):
        return station_search()
    if 'statxml.asp' in path and request.args.get('id'):
        return get_station_info()
    if 'navxml.asp' in path:
        return radiobrowser_landing()
    if 'favxml.asp' in path:
        return my_stations_landing()
    if 'loginxml.asp' in path:
        return landing()
    logging.error("Unhandled upstream query: /setupapp/%s", path)
    abort(404)


@app.route('/',
           methods=['GET', 'POST'])
@app.route('/' + PATH_ROOT + '/',
           methods=['GET', 'POST'])
def landing():
    page = vtuner.Page()
    page.add(vtuner.Directory('Radio Browser', url_for('radiobrowser_landing', _external=True), 4))
    if my_stations_enabled:
        page.add(vtuner.Directory('My Stations', url_for('my_stations_landing', _external=True),
                                  len(my_stations.get_category_directories())))
    else:
        page.add(vtuner.Display("'My Stations' feature not configured"))
    page.set_count(2)
    return page.to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_MY_STATIONS + '/',
           methods=['GET', 'POST'])
def my_stations_landing():
    directories = my_stations.get_category_directories()
    return get_directories_page('my_stations_category', directories).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_MY_STATIONS + '/<directory>',
           methods=['GET', 'POST'])
def my_stations_category(directory):
    stations = my_stations.get_stations_by_category(directory)
    return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/',
           methods=['GET', 'POST'])
def radiobrowser_landing():
    page = vtuner.Page()
    page.add(vtuner.Directory('Countries', url_for('radiobrowser_countries', _external=True),
                              len(radiobrowser.get_country_directories())))
    page.add(vtuner.Directory('Languages', url_for('radiobrowser_languages', _external=True),
                              len(radiobrowser.get_language_directories())))
    page.add(vtuner.Directory('Genres', url_for('radiobrowser_genres', _external=True),
                              len(radiobrowser.get_genre_directories())))
    page.add(vtuner.Directory('Most Popular', url_for('radiobrowser_popular', _external=True),
                              radiobrowser.DEFAULT_STATION_LIMIT))
    page.set_count(4)
    return page.to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_COUNTRY + '/',
           methods=['GET', 'POST'])
def radiobrowser_countries():
    directories = radiobrowser.get_country_directories()
    return get_directories_page('radiobrowser_country_stations', directories).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_COUNTRY + '/<directory>',
           methods=['GET', 'POST'])
def radiobrowser_country_stations(directory):
    stations = radiobrowser.get_stations_by_country(directory)
    return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_LANGUAGE + '/',
           methods=['GET', 'POST'])
def radiobrowser_languages():
    directories = radiobrowser.get_language_directories()
    return get_directories_page('radiobrowser_language_stations', directories).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_LANGUAGE + '/<directory>',
           methods=['GET', 'POST'])
def radiobrowser_language_stations(directory):
    stations = radiobrowser.get_stations_by_language(directory)
    return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_GENRE + '/',
           methods=['GET', 'POST'])
def radiobrowser_genres():
    directories = radiobrowser.get_genre_directories()
    return get_directories_page('radiobrowser_genre_stations', directories).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_GENRE + '/<directory>',
           methods=['GET', 'POST'])
def radiobrowser_genre_stations(directory):
    stations = radiobrowser.get_stations_by_genre(directory)
    return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_POPULAR + '/',
           methods=['GET', 'POST'])
def radiobrowser_popular():
    stations = radiobrowser.get_stations_by_clicks()
    return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_SEARCH + '/',
           methods=['GET', 'POST'])
def station_search():
    query = request.args.get('search')
    if not query or len(query) < 3:
        page = vtuner.Page()
        page.add(vtuner.Display("Search query too short"))
        page.set_count(1)
        return page.to_string()
    else:
        # TODO: we also need to include 'my station' elements
        stations = radiobrowser.search(query)
        return get_stations_page(stations).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_PLAY,
           methods=['GET', 'POST'])
def get_stream_url():
    stationid = request.args.get('id')
    if not stationid:
        logging.error("Stream URL without station ID requested")
        abort(400)
    station = get_station_by_id(stationid, additional_info=True)
    if not station:
        logging.error("Could not get station with ID '%s'", stationid)
        abort(404)
    logging.debug("Station with ID '%s' requested", station.id)
    return vtuner_redirect(strip_https(station.url))


@app.route('/' + PATH_ROOT + '/' + PATH_STATION,
           methods=['GET', 'POST'])
def get_station_info():
    stationid = request.args.get('id')
    if not stationid:
        logging.error("Station info without station ID requested")
        abort(400)
    station = get_station_by_id(stationid, additional_info=(not station_tracking))
    if not station:
        logging.error("Could not get station with ID '%s'", stationid)
        page = vtuner.Page()
        page.add(vtuner.Display("Station not found"))
        page.set_count(1)
        return page.to_string()
    vtuner_station = station.to_vtuner()
    if station_tracking:
        vtuner_station.url = url_for('get_stream_url', id=vtuner_station.id, _external=True)
    else:
        vtuner_station.url = strip_https(vtuner_station.url)
    vtuner_station.icon = url_for('get_station_icon', id=vtuner_station.id, _external=True)
    page = vtuner.Page()
    page.add(vtuner_station)
    page.set_count(1)
    return page.to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_ICON,
           methods=['GET', 'POST'])
def get_station_icon():
    stationid = request.args.get('id')
    if not stationid:
        logging.error("Station icon without station ID requested")
        abort(400)
    station = get_station_by_id(stationid)
    if not station:
        logging.error("Could not get station with ID '%s'", stationid)
        abort(404)
    if not hasattr(station, 'icon') or not station.icon:
        logging.warning("No icon information found for station with ID '%s'", stationid)
        abort(404)
    station_icon = station_icons.get_icon(station)
    if not station_icon:
        logging.error("Could not get station icon for station with ID '%s'", stationid)
        abort(404)
    response = make_response(station_icon)
    response.headers.set('Content-Type', 'image/jpeg')
    return response
