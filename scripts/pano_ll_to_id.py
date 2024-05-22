#!/usr/bin/env python
import click
from geosys.maps import MAP_TYPES, QMAP_PANO_BY_YX_URL, qmap_ll2yx

from geosys.utils import request_data

@click.command()
@click.argument("ll", type=(float, float))
@click.option('-t', '--map_type', type=click.Choice(MAP_TYPES), default='qmap')
@click.option('-v', '--verbose', count=True)
def main(ll, map_type, verbose):
    if map_type == 'qmap':
        y, x = qmap_ll2yx(*ll)
        pano = request_data(QMAP_PANO_BY_YX_URL.format(y=y, x=x))
        if verbose:
            print(pano)
        if pano['info']['errno']:
            print(f'get {ll} errno ({pano["info"]["errno"]})')
            exit()

        p = pano['detail']
        print(p['svid'], *ll)

    else:
        raise


if __name__ == "__main__":
    main()
