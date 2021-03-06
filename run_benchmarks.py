#!/usr/bin/env python3
"""
Copyright (C) 2018 Giuseppe Lavagetto <glavagetto@wikimedia.org>
Copyright (C) 2021 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import argparse
import datetime
import subprocess
import time

from urllib.parse import urlsplit, urlunsplit

MIN_CONCURRENCY = 10
MAX_CONCURRENCY = 40
STEPS = list(range(MIN_CONCURRENCY, MAX_CONCURRENCY + 1))[::5]
URLS = {
    'main_page': {
        'url': 'https://en.wikipedia.org/wiki/Main_Page',
        'reqs': 10000,
        'title': 'enwiki:Main Page'
    },
    'light_page': {
        'url': 'https://it.wikipedia.org/wiki/Nemico_pubblico_(film_1998)',
        'reqs': 10000,
        'title': 'itwiki:Nemico Pubblico (film 1998)'
    },
    'heavy_page': {
        'url': 'https://en.wikipedia.org/wiki/Barack_Obama',
        'reqs': 10000,
        'title': 'enwiki:Barack Obama (no re-parsing)'
    },
    're-parse': {
        'url': 'https://en.wikipedia.org/w/api.php?action=parse&text={{:Australia}}',
        'reqs': 500,
        'title': 'Re-parsing of enwiki:Australia'
    },
    'load': {
        'url': 'https://kk.wikipedia.org/w/load.php?debug=false&lang=kk&modules=ext.3d.styles%7Cext.cite.styles%7Cext.uls.interlanguage%7Cext.visualEditor.desktopArticleTarget.noscript%7Cext.wikimediaBadges%7Cmediawiki.legacy.commonPrint%2Cshared%7Cmediawiki.page.gallery.styles%7Cmediawiki.skinning.interface%7Cmediawiki.toc.styles%7Cskins.vector.styles%7Cwikibase.client.init&only=styles&skin=vector', # noqa
        'reqs': 30000,
        'title': 'Re-parsing of enwiki:Australia'
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run MediaWiki benchmarks")
    parser.add_argument("host", help="Hostname to benchmark")
    parser.add_argument("label", help="Label to save data with")
    return parser.parse_args()


def log(msg):
    ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print("[%s] %s" % (ts, msg))


def ab_req(host, run_label, conc, num_req, filename, url):
    _, netloc, path, qs, anchor = urlsplit(url)
    my_url = urlunsplit(('http', host, path, qs, anchor))
    cmd = [
            'ab',
            '-c', str(conc),
            '-n', str(num_req),
            '-H', 'Host: {}'.format(netloc),
            '-H', 'X-Forwarded-Proto: https',
            '-g', '{}_{}_c{}.dat'.format(run_label, filename, conc),
            my_url
    ]
    log("Executing {}".format(" ".join(cmd)))
    subprocess.call(cmd)


def main():
    args = parse_args()
    for label, config in URLS.items():
        log("Performing requests for {}".format(label))
        for conc in STEPS:
            log("Starting run with c={}, n={}".format(conc, config['reqs']))
            ab_req(args.host, args.label, conc, config['reqs'], label, config['url'])


if __name__ == "__main__":
    main()
