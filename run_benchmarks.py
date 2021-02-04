#!/usr/bin/env python3
import time
import subprocess
import sys
import datetime

from urllib.parse import urlsplit, urlunsplit

HOST_TO_TEST = 'mw1277.eqiad.wmnet'
run_label = sys.argv[1]
min_concurrency = 10
max_concurrency = 40
URLS = {
    'main_page': ('https://en.wikipedia.org/wiki/Main_Page', 10000),
    'light_page': ('https://it.wikipedia.org/wiki/Nemico_pubblico_(film_1998)', 10000),
    'heavy_page': ('https://en.wikipedia.org/wiki/Barack_Obama', 10000),
    're-parse': ('https://en.wikipedia.org/w/api.php?action=parse&text={{:Australia}}', 500),
    'load': ('https://kk.wikipedia.org/w/load.php?debug=false&lang=kk&modules=ext.3d.styles%7Cext.cite.styles%7Cext.uls.interlanguage%7Cext.visualEditor.desktopArticleTarget.noscript%7Cext.wikimediaBadges%7Cmediawiki.legacy.commonPrint%2Cshared%7Cmediawiki.page.gallery.styles%7Cmediawiki.skinning.interface%7Cmediawiki.toc.styles%7Cskins.vector.styles%7Cwikibase.client.init&only=styles&skin=vector', 30000)
}


def log(msg):
    ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print("[%s] %s" % (ts, msg))


def ab_req(c, n, filename, url):
    _, netloc, path, qs, anchor = urlsplit(url)
    my_url = urlunsplit(('http', HOST_TO_TEST, path, qs, anchor))
    cmd = [
            'ab',
            '-c', str(c),
            '-n', str(n),
            '-H', 'Host: {}'.format(netloc),
            '-H', 'X-Forwarded-Proto: https',
            '-g', '{}_{}_c{}.dat'.format(run_label, filename, c),
            my_url
    ]
    log("Executing {}".format(" ".join(cmd)))
    subprocess.call(
        cmd
    )


for label, data in URLS.items():
    url, num_req = data
    conc = min_concurrency
    log("Performing requests for {}".format(label))
    while conc <= max_concurrency:
        my_run_label = "{}_{}".format(run_label, label)
        log("Starting run with c={}, n={}".format(conc, num_req))
        ab_req(conc, num_req, label, url)
        conc += 5
