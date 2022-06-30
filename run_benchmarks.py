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
    "view_mainpage": {
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "reqs": 10000,
        "title": "View enwiki:Main Page",
    },
    "view_short": {
        "url": "https://it.wikipedia.org/wiki/Nemico_pubblico_(film_1998)",
        "reqs": 10000,
        "title": "View itwiki:Nemico pubblico (film_1998)",
    },
    "view_long": {
        "url": "https://en.wikipedia.org/wiki/Barack_Obama",
        "reqs": 10000,
        # Remember that views use ParserCache.
        "title": "View enwiki:Barack Obama",
    },
    "reparse_light": {
        "url": "https://nl.wikipedia.org/w/api.php?format=json&action=parse&title=Atoom&text={{:Atoom}}",
        "reqs": 500,
        "title": "Re-parse nlwiki:Atoom",
    },
    "reparse_heavy": {
        "url": "https://en.wikipedia.org/w/api.php?format=json&action=parse&title=Australia&text={{:Australia}}",
        "reqs": 500,
        "title": "Re-parse enwiki:Australia",
    },
    "rl_startup": {
        "url": "https://nl.wikipedia.org/w/load.php?lang=nl&modules=startup&only=scripts&raw=1&skin=vector",  # noqa
        "reqs": 30000,
        "title": "load.php startup JS for nlwiki",
    },
    "rl_css": {
        "url": "https://kk.wikipedia.org/w/load.php?lang=en&modules=ext.echo.styles.badge%7Cext.uls.interlanguage%7Cext.visualEditor.desktopArticleTarget.noscript%7Cext.wikimediaBadges%7Cmediawiki.ui.button%7Coojs-ui.styles.icons-alerts%7Cskins.vector.styles.legacy&only=styles&skin=vector",  # noqa
        "reqs": 30000,
        "title": "load.php styles for kkwiki",
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run MediaWiki benchmarks")
    parser.add_argument("host", help="Hostname to benchmark")
    parser.add_argument("label", help="Label to save data with")
    parser.add_argument("--scheme", dest="scheme", default="http", help="HTTPS/HTTP")
    parser.add_argument(
        "--timeout",
        dest="timeout",
        default=120,
        help="ab timeout (-s parameter). The default of ab, 30, is not enough. We default to 120",
    )

    return parser.parse_args()


def log(msg):
    ts = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
    print("[%s] %s" % (ts, msg))


def ab_req(host, run_label, conc, num_req, filename, url, scheme, timeout):
    _, netloc, path, qs, anchor = urlsplit(url)
    my_url = urlunsplit((scheme, host, path, qs, anchor))
    cmd = [
        "ab",
        "-s",
        str(timeout),
        "-c",
        str(conc),
        "-n",
        str(num_req),
        "-H",
        "Host: {}".format(netloc),
    ]
    # Tell mediawiki we are going over https even though we aren't to satisfy
    # it and avoid benchmarking redirects.
    # NOTE: This is brittle, but will do for now
    if scheme == "http":
        cmd.extend(["-H", "X-Forwarded-Proto: https"])

    # And add the rest now
    cmd.extend(["-g", "{}_{}_c{}.dat".format(run_label, filename, conc), my_url])
    log("Executing {}".format(" ".join(cmd)))
    subprocess.call(cmd)


def main():
    args = parse_args()
    for label, config in URLS.items():
        log("Performing requests for {}".format(label))
        for conc in STEPS:
            log("Starting run with c={}, n={}".format(conc, config["reqs"]))
            ab_req(
                args.host,
                args.label,
                conc,
                config["reqs"],
                label,
                config["url"],
                args.scheme,
                args.timeout,
            )


if __name__ == "__main__":
    main()
