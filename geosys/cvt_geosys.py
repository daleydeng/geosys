from pathlib import Path
import json
import math as M
from Polygon import Polygon
from geopy.distance import geodesic
from scipy.optimize import leastsq
from ._cvt_geosys import ffi, lib

cur_d = Path(__file__).parent

pi2 = M.pi * 2
# borrowed from geopy
EARTH_R_MAJOR = 6378137.0
EARTH_R_MINOR = 6356752.3142
EARTH_FLATTENING = 1 / 298.257223563

def wgs84_to_gcj02(y, x):
    out = ffi.new('double[2]')
    lib.wgs84_to_gcj02(y, x, out)
    return tuple(out)

def wgs84_to_gcj02_jac(y, x):
    out = ffi.new('double[4]')
    lib.wgs84_to_gcj02_jac(y, x, out)
    return [[out[0], out[2]], [out[1], out[3]]]

def transform_point(T, X):
    return T[:, :-1].dot(X) + T[:, -1]

def geo_dist(lat0, lng0, lat1, lng1):
    return geodesic((lat0, lng0), (lat1, lng1)).meters

def geo_coord(lat, lng, clat=0, clng=0):
    return ((1 if lat > clat else -1) * geo_dist(lat, lng, clat, lng),
            (1 if lng > clng else -1) * geo_dist(lat, lng, lat, clng))


cache = {}
def in_china(y, x):
    if 'china_borders' not in cache:
        cache['china_borders'] = json.load(open(cur_d / 'china_borders.json'))

    return any(Polygon(b).isInside(y, x) for b in cache['china_borders'])

def check_in_china_fn(fn):
    def __fn(y, x):
        if in_china(y, x):
            return fn(y, x)
        else:
            return y, x
    return __fn


wgs84_to_gcj02 = check_in_china_fn(wgs84_to_gcj02)

def __gcj02_to_wgs84(y0, x0):
    """
    >>> gcj02, wgs84 = (39.906961, 116.397555), (39.905560, 116.391314)
    >>> ok(__gcj02_to_wgs84(*gcj02), wgs84, 1e-6)
    """
    def wgs84_to_gcj02_fvec(x):
        y1, x1 = wgs84_to_gcj02(*x)
        return y1 - y0, x1 - x0

    def wgs84_to_gcj02_fjac(x):
        return wgs84_to_gcj02_jac(*x)

    x, flag = leastsq(wgs84_to_gcj02_fvec, (y0, x0), Dfun=wgs84_to_gcj02_fjac)
    return x.tolist()


gcj02_to_wgs84 = check_in_china_fn(__gcj02_to_wgs84)

EARTH_CIRCUM = 2 * M.pi * EARTH_R_MAJOR

def _check_lat(lat):
    assert abs(lat) < 85

# mercator projection use gudermannian function
def ll2merc(lat, lng, meter=True):
    _check_lat(lat)
    lat, lng = M.radians(lat), M.radians(lng)
    x = lng / pi2
    siny = M.sin(lat)
    # north is positive, else y *= -1
    y = 0.5 * M.log((1 + siny) / (1 - siny)) / pi2
    if meter:
        x *= EARTH_CIRCUM
        y *= EARTH_CIRCUM
    return y, x

def merc2ll(y, x, meter=True):
    if meter:
        y /= EARTH_CIRCUM
        x /= EARTH_CIRCUM
    return M.degrees(2 * M.atan(M.exp(pi2 * y)) - M.pi / 2), M.degrees(x * pi2)


_geo_decodes = {
    'beijing': (39.9, 116.3),
    'shanghai': (31.2323076784, 121.4691562490),
    'washington': (47.5, -120.5),
}

def get_latlng(s):
    if type(s) == str:
        return _geo_decodes[s]
    return s

def is_latlng(x):
    return (type(x) == tuple and len(x) == 2
            and isinstance(x[0], float) and isinstance(x[1], float))


INVALID_ELEV = 10000

def apply_ll2xyz(trans, lat, lng, elev=0):
    anchor, T = trans
    z, x = geo_coord(lat, lng, *anchor)
    return transform_point(T, (x, -elev, z))


EPSG3857_K0 = 0.15915494309189535
EPSG3857_K1 = 0.5
EPSG3857_K2 = 2**18

def ll2merc_epsg3857(lat, lng):
    _check_lat(lat)
    x = M.radians(lng)
    y = M.log(M.tan(M.pi / 4 + M.radians(lat) / 2))
    # scale = 2**18
    y = EPSG3857_K2 * (-y * EPSG3857_K0 + EPSG3857_K1)
    x = EPSG3857_K2 * (x * EPSG3857_K0 + EPSG3857_K1)
    return y, x

def merc2ll_epsg3857(y, x):
    x = (x / EPSG3857_K2 - EPSG3857_K1) / EPSG3857_K0
    y = - (y / EPSG3857_K2 - EPSG3857_K1) / EPSG3857_K0
    lng = M.degrees(x)
    lat = M.degrees(2 * M.atan(M.exp(y)) - M.pi / 2)
    return lat, lng

def unit_ll_meter(lat, lng):
    dy = geo_dist(lat, lng, lat + 1, lng)
    dx = geo_dist(lat, lng, lat, lng + 1)
    return dy, dx
