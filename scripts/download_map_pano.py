#!/usr/bin/env python
from pathlib import Path
import math as M
from io import BytesIO
from functools import partial
from PIL import Image
import yaml
from geosys.maps import (
    QMAP_PANO_IMG_URL,
    BMAP_PANO_IMG_URL,
    GMAP_PANO_IMG_URL,
    AMAP_PANO_IMG_URL
)
from geosys.utils import request_retry
import click

map_types = 'gmap', 'bmap', 'amap', 'qmap'
TILE_W = 512

class MapPanoDownloader:
    def __init__(self, server_nr, url, w, zoom, z_off=0):
        self.url = url
        self.w = w
        self.z_off = z_off
        self.server_nr = server_nr
        self.server_ids = list(range(server_nr))
        self.cur_server = 0
        self.zoom = zoom
        assert self.zoom + self.z_off >= 0

    def get_url(self, pid, ti, pi):
        if hasattr(self, 'change_id'):
            pid = self.change_id(pid)
        kws = {'id': pid, 'tilt': ti, 'pan': pi, 'zoom': self.zoom + self.z_off}

        if self.server_nr > 1:
            out = self.url.format(server=self.server_ids[self.cur_server],
                                  **kws)
            self.cur_server = (self.cur_server + 1) % self.server_nr
            return out

        return self.url.format(**kws)

class GMapPanoDownloader(MapPanoDownloader):
    def __init__(self, zoom):
        super().__init__(4, GMAP_PANO_IMG_URL, 13312, zoom=zoom)

class BMapPanoDownloader(MapPanoDownloader):
    def __init__(self, zoom):
        # bmap's zoom is incorrect
        super().__init__(2, BMAP_PANO_IMG_URL, 8192, zoom=zoom, z_off=1)

class QMapPanoDownloader(MapPanoDownloader):
    def __init__(self, zoom):
        super().__init__(9, QMAP_PANO_IMG_URL, 8192, zoom=zoom, z_off=-3)

class AMapPanoDownloder(MapPanoDownloader):
    def __init__(self, zoom):
        super().__init__(1, AMAP_PANO_IMG_URL, 8192, zoom=zoom, z_off=-2)

    def change_id(self, i):
        return i.replace('_', '/')


MapPanoDownloaders = {
    'gmap': GMapPanoDownloader,
    'bmap': BMapPanoDownloader,
    'qmap': QMapPanoDownloader,
    'amap': AMapPanoDownloder,
}

def align(x, dx):
    return M.ceil(x / dx) * dx

def get_tile_grid(w, h):
    return [(ti, pi) for ti in range(int(h / TILE_W))
            for pi in range(int(w / TILE_W))]


click.option = partial(click.option, show_default=True)
@click.command()
@click.argument("src")
@click.option('-o', '--out', default='')
@click.option('-t', '--map_type', type=click.Choice(map_types), default='qmap')
@click.option('-z', '--zoom', default=3, help='needed zoom')
def main(src, out, map_type, zoom):
    src = Path(src)
    if src.exists():
        pids = list(yaml.load(open(src)).keys())
        if not out:
            out = src.parent / src.stem
            out.mkdir(exist_ok=True)
    else:
        pids = [src]
        if not out:
            out = src.parent

    mpd = MapPanoDownloaders[map_type](zoom)

    real_w = mpd.w
    while real_w > TILE_W * 2**zoom:
        real_w /= 2
    real_w = int(real_w)
    real_h = int(real_w / 2)
    w, h = align(real_w, TILE_W), align(real_h, TILE_W)
    need_crop = real_w < w or real_h < h
    tile_grid = get_tile_grid(w, h)

    canvas = Image.new('RGB', (int(w), int(h)))

    for pid in pids:
        out_f = (out / pid).with_suffix('.jpg')
        print(f"proessing {out_f}")
        if out_f.exists():
            print(f"{out_f} exists")
            continue

        keys, urls = [], []
        for ti, pi in tile_grid:
            keys.append((ti, pi))
            urls.append(mpd.get_url(pid, ti, pi))

        content0 = request_retry(urls[0])
        try:
            b = BytesIO(content0)
            img = Image.open(b)
            img_w, img_h = img.size
            if img_w != TILE_W:
                print('img_w({}) !='.format(img_w), TILE_W)
                exit()

        except OSError:
            print('OSError, set white')
            exit()

        contents = [request_retry(i) for i in urls[1:]]
        contents = [content0] + contents
        for (ti, pi), content in zip(keys, contents):
            try:
                b = BytesIO(content)
                img = Image.open(b)

            except OSError:
                print('OSError, set white')
                exit()

            canvas.paste(img, (pi * TILE_W, ti * TILE_W))

        if need_crop:
            canvas = canvas.crop((0, 0, real_w, real_h))

        canvas.save(out_f)


if __name__ == "__main__":
    main()
