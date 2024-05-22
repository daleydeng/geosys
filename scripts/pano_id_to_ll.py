#!/usr/bin/env python
from geosys.maps import MAP_TYPES, QMAP_PANO_BY_ID_URL, qmap_parse_pano_info
from geosys.utils import request_data
import click

@click.command()
@click.argument("pid")
@click.option('-t', '--map_type', type=click.Choice(MAP_TYPES), default='qmap')
@click.option('-v', '--verbose', count=True)
def main(pid, map_type, verbose):
    if map_type == 'qmap':
        pano = request_data(QMAP_PANO_BY_ID_URL.format(id=pid))
        pano = qmap_parse_pano_info(pano)

        if verbose:
            print(pano)

        p = pano['pano']
        print(p['id'], *p['latlng'])

    else:
        raise


if __name__ == "__main__":
    main()
