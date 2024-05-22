#!/usr/bin/env python
from pathlib import Path
import math as M
import numpy as np
import numpy.linalg as npl
import yaml
from shapely.geometry import Polygon, Point
from pprint import pformat
import click

from geosys.maps import (
    QMAP_PANO_BY_ID_URL,
    QMAP_PANO_BY_YX_URL,
    qmap_parse_pano_info,
    qmap_ll2yx,
    AMAP_PANO_BY_ID_URL,
    AMAP_PANO_BY_YX_URL,
)

from geosys.utils import request_data
from geosys.cvt_geosys import (
    geo_dist, in_china, is_latlng, gcj02_to_wgs84,
    wgs84_to_gcj02, unit_ll_meter)
from geosys.io_ import load_txt, save_txt

def PR2ptr(R):
    return (M.atan2(R[2, 0], R[2, 2]),
            -M.asin(R[2, 1]),
            M.atan2(R[0, 1], R[1, 1]))

def mcross(a):
    return np.array([[0, -a[2], a[1]],
                     [a[2], 0, -a[0]],
                     [-a[1], a[0], 0]])

def axisangle2R(v, t=0):
    if not t:
        t = npl.norm(v)
        if t > 0:
            v = v / t
        else:
            v = v
    else:
        if npl.norm(v) == 0:
            v = [0, 0, 0]
        else:
            v = np.array(v) / npl.norm(v)

    cos_t = M.cos(t)
    return cos_t * np.eye(3) + M.sin(t) * mcross(v) + (1 - cos_t) * np.outer(v, v)

def axisangle2PR(v, t):
    return axisangle2R(v, -t)


class MapPanoGrabber:
    def __init__(self, cache, server_nr, by_id, by_yx, pano_data_fmt='.json'):
        self.cache = cache
        self.failed_panos_f = cache / 'failed_panos.yaml'
        if self.failed_panos_f.exists():
            self.failed_panos = set(yaml.save_load(open(self.failed_panos_f)))
        else:
            self.failed_panos = set()

        self.server_nr = server_nr
        self.by_id = by_id
        self.by_yx = by_yx
        self.pano_data_fmt = pano_data_fmt

        self.total = 0
        self.server_nr = server_nr
        self.cur_server = 0

    def pano_id(self, p):
        raise

    def inc_server(self):
        out = self.cur_server
        self.cur_server = (self.cur_server + 1) % self.server_nr
        return out

    def get_by_id_url(self, q):
        if self.server_nr <= 1:
            return self.by_id.format(id=q)

        return self.by_id.format(server=self.inc_server(), id=q)

    def get_by_yx_url(self, q):
        y, x = q
        if self.server_nr <= 1:
            return self.by_yx.format(y=y, x=x)
        return self.by_yx.format(server=self.inc_server(), y=y, x=x)

    def cache_info_f(self, name):
        return (self.cache / name).with_suffix(self.pano_data_fmt)

    def add_failed_pano(self, n):
        print("add failed_pano", len(self.failed_panos), n)
        self.failed_panos.add(n)

    def request_pano_data(self, q):
        self.total += 1
        print('current request', self.total)
        if isinstance(q, str):
            if q in self.failed_panos:
                return

            info_f = self.cache_info_f(q)
            if info_f.exists():
                return load_txt(info_f)

            pano = request_data(self.get_by_id_url(q), verbose=True)
            if not pano:
                print('pano is None')
                self.add_failed_pano(q)
                return

            if not info_f.exists():
                save_txt(pano, info_f)

        elif is_latlng(q):
            pano = request_data(self.get_by_yx_url(q))
            if not pano:
                print('pano is None')
                return

            i = self.pano_id(pano)
            if not i:
                print('no pano_id\n', pformat(pano))
                return

        else:
            raise

        return pano

    def cache_infos(self, ids):
        for i in ids:
            self.request_pano_data(i)

    def grab_region(self, seeds, bnd):
        done = {}
        queue = set()
        for i in seeds:
            pano = self.get_pano_by_latlng(i)
            if pano:
                queue.add(self.pano_id(pano))

        cur_nr = 0
        visited = set()
        while queue:
            print('queue len', len(queue))
            queue2 = set()
            for i in queue:
                if i in visited:
                    continue
                visited.add(i)
                queue2.add(i)

            if not queue2:
                break

            rets = [self.get_pano(i, bnd=bnd) for i in queue2]
            queue = set()
            for ret in rets:
                if not ret:
                    continue

                # for multi floor case in gmap, pano may not exist
                # when in incorrect floor
                p = ret.get('pano', None)
                if p:
                    pid, (lat, lng) = p['id'], p['latlng']
                    # when i is latlng, pid is missed, we need to add it again
                    if pid not in visited:
                        visited.add(pid)

                    if not bnd.contains(Point(lat, lng)):
                        continue

                    lat, lng = round(lat, 6), round(lng, 6)
                    done[pid] = p
                    cur_nr += 1
                    print('add', cur_nr, pid, done[pid])

                links = ret['links']
                queue |= set(i for i in links if i not in done)

        if self.failed_panos:
            yaml.dump(list(self.failed_panos), open(self.failed_panos_f, 'w'))

        return done

    def grab_panos(self, a):
        panos = {}
        for i in a:
            p = self.get_pano(i)
            if not p or not p.get('pano', None):
                continue

            p = p['pano']
            panos[p['id']] = p

        return panos

# havent add date
class GMapPanoGrabber(MapPanoGrabber):
    def __init__(self, cache, floor=0):
        server_url = "https://cbks{server}.googleapis.com/cbk?"
        by_id_url = server_url + "output=json&panoid={id}"
        by_yx_url = server_url + "output=json&ll={y},{x}&radius=50"
        super().__init__(cache, 4, by_id_url, by_yx_url)
        self.floor = floor

    def pano_id(self, pano):
        if pano:
            return pano['Location']['panoId']

    def get_pano_by_latlng(self, latlng):
        return self.request_pano_data(latlng)

    def get_pano(self, q, bnd=None):
        pano = self.request_pano_data(q)
        if not pano:
            return
        if pano['Data']['imagery_type'] != 1:
            return

        pl = pano['Location']
        has_level = ('level_id' in pl
                     and pl['level_id'] != '0000000000000000'
                     and 'levels' in pano)

        if has_level:
            cur_ord = -1
            for l in pano['levels']['level']:
                if pl['level_id'] == l['level_id']:
                    cur_ord = int(l['ordinal'])
                    break

            if cur_ord != self.floor:
                # correct floor
                for l in pano['levels']['level']:
                    if int(l['ordinal']) == self.floor:
                        return {'links': [l['pano_id']]}

        if 'image_date' in pano['Data']:
            date = pano['Data']['image_date']
            date = date[2: 4] + date[5: 7]
        else:
            date = 'N/A'

        return {
            'pano': {
                'id': pl['panoId'],
                'latlng': [float(pl['lat']), float(pl['lng'])],
                'date': date,
                'ori': self.get_pano_ori(pano),
            },
            'links': [i['panoId'] for i in pano.get('Links', [])]
        }

    @staticmethod
    def get_pano_ori(p):
        p = p['Projection']
        pan = M.radians(float(p['pano_yaw_deg']))
        R0 = axisangle2PR([0, 1, 0], pan)
        tilt = M.radians(float(p['tilt_pitch_deg']))
        theta = -M.radians(float(p['tilt_yaw_deg']))

        R1 = axisangle2PR([M.cos(theta), 0, -M.sin(theta)], tilt)

        return PR2ptr(R1.dot(R0))


AMAP_K = 0.00274658203125

class AMapPanoGrabber(MapPanoGrabber):
    def __init__(self, cache, floor=0):
        super().__init__(cache, 1, AMAP_PANO_BY_ID_URL, AMAP_PANO_BY_YX_URL)

    @staticmethod
    def rename_id(i):
        return i.replace('/', '_')

    def pano_id(self, p):
        return self.rename_id(next(iter(p.values()))["StreetInfo"]['panoid'])

    def get_by_id_url(self, q):
        q1 = q.replace('_', '/')
        return super().get_by_id_url(q1)

    def get_pano_by_latlng(self, latlng):
        lat, lng = wgs84_to_gcj02(*latlng)
        q = lat / AMAP_K, lng / AMAP_K
        pano = self.request_pano_data(q)
        if pano is None or ('result' in pano and pano['result'] == 'nodata'):
            return
        return pano

    def get_pano(self, q):
        pano = self.request_pano_data(q)
        if pano is None:
            return
        pos, topo = pano['PosInfo'], pano['TopoInfo']
        lat, lng = gcj02_to_wgs84(pos['lat'], pos['lon'])

        return {
            'pano': {'id': q, 'lat': lat, 'lng': lng},
            'links': [self.rename_id(i['id']) for i in topo],
        }

class QMapPanoGrabber(MapPanoGrabber):
    def __init__(self, cache, floor=0):
        super().__init__(cache, 1, QMAP_PANO_BY_ID_URL, QMAP_PANO_BY_YX_URL,
                         pano_data_fmt='.xml')

    def pano_id(self, p):
        return p['detail']['svid']

    def get_pano_by_latlng(self, latlng):
        y, x = qmap_ll2yx(*latlng)
        pano = self.request_pano_data((y, x))
        if 'svid' not in pano['detail']:
            return
        return pano

    def get_pano(self, q, bnd=None):
        pano = self.request_pano_data(q)
        return qmap_parse_pano_info(pano, bnd=bnd)

def gen_loc_grid1(x0, x1, nr):
    if nr <= 1:
        return (x0 + x1) / 2,
    if nr == 2:
        return (x0 + x1) / 2, x0, x1
    return np.linspace(x0, x1, num=nr, endpoint=True)

def make_region(r):
    tp = r['type']
    if tp == 'square':
        cy, cx = r['center']
        radius = r['radius']
        dy, dx = unit_ll_meter(cy, cx)

        ry = radius / dy
        rx = radius / dx

        y0 = cy - ry
        y1 = cy + ry
        x0 = cx - rx
        x1 = cx + rx

        return Polygon([(y0, x0), (y0, x1), (y1, x1), (y1, x0)])
    else:
        raise

def gen_seed_grid(region, margin, gap=0):
    lat0, lng0, lat1, lng1 = region.bounds
    if gap:
        dlng, dlat = lat1 - lat0, lng1 - lng0
        lat0 += dlat * gap
        lat1 -= dlat * gap
        lng0 += dlng * gap
        lng1 -= dlng * gap

    nr = M.ceil(geo_dist(lat0, lng0, lat1, lng0) / margin)
    lats = gen_loc_grid1(lat0, lat1, nr)
    nr = M.ceil(geo_dist(lat0, lng0, lat0, lng1) / margin)
    lngs = gen_loc_grid1(lng0, lng1, nr)

    return [(lat, lng) for lat in lats for lng in lngs
            if region.contains(Point(lat, lng))]


#    'bmap': BMapPanoGrabber,
MapPanoGrabbers = {
    'gmap': GMapPanoGrabber,
    'qmap': QMapPanoGrabber,
    'amap': AMapPanoGrabber,
}

@click.command()
@click.argument('regions')
@click.option('-o', '--out', default='')
@click.option('-t', '--map_type', type=click.Choice(MapPanoGrabbers.keys()),
              default='qmap')
@click.option('--floor', default=0, help='for multi floors in gmap')
@click.option('--cache_dir', default='info_cache')
def main(regions, out, map_type, floor, cache_dir):
    regions = Path(regions)
    if not out:
        out = (regions.parent / str(regions.stem + '_panos')).with_suffix('.yaml')

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True)
    mpg = MapPanoGrabbers[map_type](cache_dir, floor=floor)

    pi = yaml.full_load(open(regions))
    seed_gap = pi['seed_gap']
    regions = pi['regions']

    for r in regions:
        region = make_region(r)
        c = region.centroid

        is_in_china = in_china(c.x, c.y)
        assert((is_in_china and map_type != 'gmap')
               or (not is_in_china and map_type == 'gmap'))

        seeds = gen_seed_grid(region, seed_gap)
        panos = mpg.grab_region(seeds, region)

        print(f"generated {len(panos)} panos to {out}")
        with open(out, 'w') as fp:
            print(f"# size {len(panos)}", file=fp)
            yaml.dump(panos, fp)


if __name__ == "__main__":
    main()
