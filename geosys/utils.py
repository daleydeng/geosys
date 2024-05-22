import re
import json
from time import sleep
from urllib.request import urlopen
from urllib.error import HTTPError
from lxml import etree

_xml_formatter = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&apos;',
    '"': '&quot;',
}
_xml_re = re.compile('&....')
def fix_xml_error(s):
    for i in _xml_re.findall(s):
        if any(i.startswith(j) for j in _xml_formatter.values()):
            continue
        s = re.sub(i, '&amp;' + i[1:], s)
    return s


TIMEOUT_BASE = 4  # seconds

def request_retry(url, retry=8, verbose=False):
    timeout = TIMEOUT_BASE
    for i in range(retry):
        try:
            print('requesting', url)
            return urlopen(url, timeout=timeout).read()
        except HTTPError as e:
            print(url, str(e))
            return
        except Exception as e:
            print('{} {}. retry {}'.format(url, str(e), i + 1))
            sleep(timeout)
            timeout *= 2
    print("request_retry failed on url", url)
    return

def request_data(url, retry=10, verbose=False):
    bs = request_retry(url, retry=retry, verbose=verbose)
    s = bs.decode('utf8', errors='ignore')
    if 'fn' in url or 'cb' in url:
        off = s.find('(')
        if off and s[-2:] == ');':
            s = s[off + 1:-2]

    if s.startswith('<?xml'):
        try:
            s = fix_xml_error(s)
            return etree.fromstring(s.encode())
        except etree.XMLSyntaxError:
            print('xml syntax error for', url)
            return
    elif s.startswith('{'):
        return json.loads(s)

    raise
