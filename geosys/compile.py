#!/usr/bin/env python
from pathlib import Path
import cffi

cur_d = Path(__file__).parent

builder = cffi.FFI()
builder.set_source("geosys._cvt_geosys", open(cur_d / "cvt_geosys_mpl.c").read())
builder.cdef("""
void wgs84_to_gcj02 (double y, double x, double *out);
void wgs84_to_gcj02_jac (double y, double x, double *out);
void bd09_to_gcj02 (double y, double x, double *out);
""")

if __name__ == "__main__":
    builder.compile(verbose=True)
