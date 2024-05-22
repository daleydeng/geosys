import os
import json
from lxml import etree
from .utils import fix_xml_error

def load_xml(f, fix_err=False):
    f = str(f)
    if not fix_err:
        return etree.parse(f)

    s = open(f).read()
    s = fix_xml_error(s)
    return etree.fromstring(s)

def load_txt(f):
    if os.stat(f).st_size == 0:
        return
    if f.suffix == '.json':
        return json.load(open(f))
    elif f.suffix == '.xml':
        return load_xml(f)

def save_xml(a, f):
    open(f, 'wb').write(etree.tostring(
        a, pretty_print=True, xml_declaration=True))

def save_txt(a, f, *args, **kws):
    if f.suffix == '.json':
        json.dump(a, open(f, 'w'))

    elif f.suffix == '.xml':
        save_xml(a, f)

    else:
        raise
