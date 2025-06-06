import xml.etree.ElementTree as ET

XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def get_init_token():
    return '<EncryptedToken>0000000000000000</EncryptedToken>'


def add_bogus_parameter(url):
    """
    We need this bogus parameter because some (if not all) AVRs blindly append additional request parameters
    with an ampersand. E.g.: '&mac=<REDACTED>&dlang=eng&fver=1.2&startitems=1&enditems=100'.
    The original vTuner API hacks around that by adding a specific parameter or a bogus parameter like '?empty=' to
    the target URL.
    """
    return url + '?vtuner=true'


class Page:
    def __init__(self):
        self.items = []
        self.count = -1
        self.dontcache = False

    def add(self, item):
        self.items.append(item)

    def set_count(self, count):
        self.count = count

    def to_xml(self):
        xml = ET.Element('ListOfItems')
        ET.SubElement(xml, 'ItemCount').text = str(self.count)
        if self.dontcache:
            ET.SubElement(xml, 'NoDataCache').text = 'Yes'
        for item in self.items:
            xml.append(item.to_xml())
        return xml

    def to_string(self):
        return XML_HEADER + ET.tostring(self.to_xml(), encoding='unicode')


class Previous:
    def __init__(self, url):
        self.url = url

    def to_xml(self):
        item = ET.Element('Item')
        ET.SubElement(item, 'ItemType').text = 'Previous'
        ET.SubElement(item, 'UrlPrevious').text = add_bogus_parameter(self.url)
        ET.SubElement(item, 'UrlPreviousBackUp').text = add_bogus_parameter(self.url)
        return item


class Display:
    def __init__(self, text):
        self.text = text

    def to_xml(self):
        item = ET.Element('Item')
        ET.SubElement(item, 'ItemType').text = 'Display'
        ET.SubElement(item, 'Display').text = self.text
        return item


class Search:
    def __init__(self, caption, url):
        self.caption = caption
        self.url = url

    def to_xml(self):
        item = ET.Element('Item')
        ET.SubElement(item, 'ItemType').text = 'Search'
        ET.SubElement(item, 'SearchURL').text = add_bogus_parameter(self.url)
        ET.SubElement(item, 'SearchURLBackUp').text = add_bogus_parameter(self.url)
        ET.SubElement(item, 'SearchCaption').text = self.caption
        ET.SubElement(item, 'SearchTextbox').text = None
        ET.SubElement(item, 'SearchButtonGo').text = 'Search'
        ET.SubElement(item, 'SearchButtonCancel').text = 'Cancel'
        return item


class Directory:
    def __init__(self, title, url, item_count=-1):
        self.title = title
        self.url = url
        self.item_count = item_count

    def to_xml(self):
        item = ET.Element('Item')
        ET.SubElement(item, 'ItemType').text = 'Dir'
        ET.SubElement(item, 'Title').text = self.title
        ET.SubElement(item, 'UrlDir').text = add_bogus_parameter(self.url)
        ET.SubElement(item, 'UrlDirBackUp').text = add_bogus_parameter(self.url)
        ET.SubElement(item, 'DirCount').text = str(self.item_count)
        return item


class Station:
    def __init__(self, id, name, url, icon=None, description=None, genre=None,
                 location=None, mime=None, bitrate=None, bookmark=None):
        self.id = id
        self.name = name
        self.url = url
        self.icon = icon
        self.description = description
        self.genre = genre
        self.location = location
        self.mime = mime
        self.bitrate = bitrate
        self.bookmark = bookmark

    def to_xml(self):
        item = ET.Element('Item')
        ET.SubElement(item, 'ItemType').text = 'Station'
        ET.SubElement(item, 'StationId').text = self.id
        ET.SubElement(item, 'StationName').text = self.name
        ET.SubElement(item, 'StationUrl').text = self.url
        ET.SubElement(item, 'Logo').text = self.icon
        ET.SubElement(item, 'StationDesc').text = self.description
        ET.SubElement(item, 'StationFormat').text = self.genre
        ET.SubElement(item, 'StationLocation').text = self.location
        ET.SubElement(item, 'StationMime').text = self.mime
        ET.SubElement(item, 'StationBandWidth').text = str(self.bitrate) if self.bitrate else None
        ET.SubElement(item, 'Bookmark').text = self.bookmark
        ET.SubElement(item, 'Relia').text = '3'
        return item
