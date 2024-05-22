from setuptools import setup

def build(kws):
    kws.update(
        cffi_modules=["geosys/compile.py:builder"],
    )
