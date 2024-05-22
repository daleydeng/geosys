from geosys import __version__
from geosys.cvt_geosys import *

def test_version():
    assert __version__ == '0.1.0'

def test_wgs84():
    # at tiananmen square
    gcj02, wgs84 = (39.906961, 116.397555), (39.905560, 116.391314)
    wgs84_1 = wgs84_to_gcj02(*gcj02_to_wgs84(*gcj02))
    assert wgs84_1 == gcj02

if __name__ == "__main__":
    test_wgs84()
