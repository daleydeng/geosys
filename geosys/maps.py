import math as M
from shapely.geometry import Point
from .cvt_geosys import gcj02_to_wgs84, wgs84_to_gcj02

MAP_TYPES = ['qmap']
QMAP_PANO_ADDR = 'http://sv.map.qq.com'
QMAP_PANO_BY_ID_URL = QMAP_PANO_ADDR + '/sv?svid={id}'
QMAP_PANO_BY_YX_URL = QMAP_PANO_ADDR + '/xf?x={x}&y={y}&r=500&cb=0'
QMAP_PANO_IMG_URL = \
    'http://sv{server}.map.qq.com/tile?svid={id}&x={pan}&y={tilt}&level={zoom}'

AMAP_PANO_ADDR = "http://wsv.amap.com"
AMAP_PANO_BY_ID_URL = AMAP_PANO_ADDR + "/AnGeoPanoramaServer?data=vector&id={id}"
AMAP_PANO_BY_YX_URL = (
    AMAP_PANO_ADDR
    + "AnGeoPoitopanoServer?xys={x},{y}&radius=150&type=nearestpanos"
)
AMAP_PANO_IMG_URL = \
    "http://wsv.amap.com/AnGeoPanoramaServer?" \
    "data=image&id={id}&level={zoom}&x={pan}&y={tilt}"


BMAP_PANO_IMG_URL = \
    "http://mapsv{server}.bdimg.com/scape/?"\
    "qt=pdata&sid={id}&pos={tilt}_{pan}&z={zoom}"

GMAP_PANO_IMG_URL = \
    "http://geo{server}.ggpht.com/cbk?"\
    "output=tile&panoid={id}&x={pan}&y={tilt}&zoom={zoom}"

QMAP_K0 = 111319.49077777778
QMAP_K1 = 0.008726646259971648
QMAP_K2 = 0.017453292519943295

def qmap_ll2yx(lat, lng, is_gcj02=True):
    if is_gcj02:
        lat, lng = wgs84_to_gcj02(lat, lng)
    x = QMAP_K0 * lng
    y = QMAP_K0 * M.log(M.tan(QMAP_K1 * (90 + lat))) / QMAP_K2
    return y, x

def qmap_yx2ll(y, x, is_gcj02=True):
    lng = x / QMAP_K0
    lat = M.atan(M.exp(QMAP_K2 * y / QMAP_K0)) / QMAP_K1 - 90
    if is_gcj02:
        lat, lng = gcj02_to_wgs84(lat, lng)
    return lat, lng

def qmap_parse_pano_info(pano, bnd=None):
    if pano is None or pano.find('error') is not None:
        return

    addr = pano.xpath('addr')
    if len(addr) == 0:
        return
    addr = addr[0]

    basic_info = pano.xpath('basic')[0]
    pid = basic_info.get('svid')

    this_lat, this_lng = gcj02_to_wgs84(
        float(addr.get('y_lat')), float(addr.get('x_lng')))
    dir_ = M.radians(float(basic_info.get('dir')))

    links = []
    for i in pano.xpath('all_scenes/all_scene'):
        if bnd:
            lat, lng = qmap_yx2ll(float(i.get('y')), float(i.get('x')))
            if bnd.contains(Point(lat, lng)):
                links.append(i.get('svid'))
        else:
            links.append(i.get('svid'))

    return {
        'pano': {
            'id': pid, 'latlng': [this_lat, this_lng], 'date': pid[8:14],
            'ori': [dir_, 0, 0],
        },
        'links': links
    }
