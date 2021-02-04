#!/usr/bin/env python3
import glob
import math
import os
import re
import subprocess
import sys

DATA_DIR = sys.argv[1]
CLEAN_DIR = os.path.join(DATA_DIR, 'clean')
IMAGES_DIR = os.path.join(CLEAN_DIR, 'images')

# test we ran / description
TESTS = {
    'main_page': 'Enwiki main page',
    'light_page': 'itwiki:Nemico Pubblico (film 1998)',
    're-parse': 'Re-parsing of enwiki:Australia',
    'load': 'load.php css stylesheet',
    'heavy_page': 'Enwiki Obama page (no re-parsing)'
}

CONFIGURATIONS = {
    'buster16': 'buster (2016)',
    'stretch16': 'stretch (2016)',
    'buster19': 'buster (2019)',
    'stretch19': 'stretch (2019)',
    'mw1381': 'stretch (4.19 kernel, 2019 hw)'
    # 'hhvm': 'HHVM',
    # 'maxch40': '40 workers',
    # 'maxch40_static': '40 workers (static)',
    # 'maxch80': '80 workers',
    # 'maxch80_static': '80 workers (static)',
    # 'opcache_1': 'Opcache (basic)',
    # 'opcache_2': 'Opcache (optimal)',
    # 'opcache_3': 'Opcache (no refesh)',
    # 'sock': 'Unix socket proxying',
    # 'sock60': 'Unix socket, 60 workers',
    # 'sock60lb': 'Unix socket, 60w, load-balanced'
}

COMPARISONS = {
    'distro': ['stretch16', 'buster16', 'stretch19', 'mw1381', 'buster19'],
    '2019': ['stretch19', 'buster19'],
    '2016': ['stretch16', 'buster16'],
    'kernel419': ['mw1381', 'buster19'],
    'stretch19': ['stretch19', 'mw1381', 'buster19']
    # 'workers': ['hhvm', 'maxch40', 'maxch40_static'],
    # 'opcache': ['hhvm', 'opcache_1', 'opcache_2', 'opcache_3'],
    # 'high_workers': ['hhvm', 'opcache_2', 'maxch80', 'maxch80_static', 'sock', 'sock60']
}


def clean(filename):
    print("cleaning file {}".format(filename))
    # read all the file, extract response time and timestamp, and sort by timestamp.
    # NOT optimized on purpose.
    clean_filename = os.path.join(CLEAN_DIR, os.path.basename(filename))
    results = []
    with open(filename, 'r') as f:
        content = f.readlines()
    for line in content[1:]:
        fields = re.split(r'\t+', line)
        # add a tuple with ts, ttime
        try:
            results.append((fields[1], fields[4]))
        except Exception:
            print(fields)
    # sort results by timestamp, then remove the first records:
    # either 5% or 10 seconds
    results.sort(key=lambda x: int(x[0]))
    to_remove = math.floor(len(results) * 0.05)
    start_time = results[0][0]
    clean_results = []
    for ts, duration in results:
        if to_remove > 0:
            dt = int(ts) - int(start_time)
            if dt >= 10:
                to_remove = 0
            else:
                to_remove -= 1
                continue
        clean_results.append((duration, ts))
    # re-sort by response time
    clean_results.sort(key=lambda x: int(x[0]))
    # remove the top 1% of the results for graph reasons
    to_remove = math.ceil(len(clean_results) * 0.01)
    clean_results = clean_results[:-to_remove]
    print("Saving cleaned file to {}".format(clean_filename))
    with open(clean_filename, 'w') as f:
        for duration, ts in clean_results:
            f.write("{}\t{}\n".format(duration, ts))
    return clean_filename


def parse_filename(filename):
    bn = os.path.basename(filename)
    all_configs = CONFIGURATIONS.keys()
    all_tests = TESTS.keys()
    configuration = None
    test = None
    concurrency = None
    to_remove = 0
    # iteratively check the filename
    for conf in all_configs:
        if not bn.startswith(conf + '_'):
            continue
        # if we already found a longer match, do nothing
        if configuration is not None and \
                configuration > conf:
            continue
        configuration = conf
        to_remove = len(conf) + 1
    bn = bn[to_remove:]

    if configuration is None:
        raise ValueError("No configuration found for filename {}".format(filename))
    # here we don't need to check for repeated strings.
    for t in all_tests:
        if not bn.startswith(t + '_'):
            continue
        test = t
        to_remove = len(t) + 1
        bn = bn[to_remove:]
        break
    if test is None:
        raise ValueError("No test found for filename {}".format(filename))

    match = re.search(r'c(\d+)', bn)
    if match is None:
        raise ValueError("No concurrency value found in {}".format(filename))
    concurrency = match.group(1)
    return {'conf': configuration, 't': test, 'c': concurrency}


def gnuplot(classifier, name, configs, test, c):
    plot_line = []
    for config in configs:
        filename = "{}_{}_c{}.dat".format(config, test, c)
        try:
            clean_file = classifier[filename]['clean_file']
            plot_line.append("'{}' u 1 title '{}' w l s c lw 4".format(
                clean_file, CONFIGURATIONS[config]))
        except Exception:
            raise
            print('WARNING: file {} not found'.format(filename))
    # remove the trailing comma and space
    outfile = os.path.join(IMAGES_DIR, "{}_{}_c{}.png".format(name, test, c))
    gpfile = os.path.join(CLEAN_DIR, "{}_{}_c{}.gpl".format(name, test, c))
    tpl = """
set title '{title} (c={conc})'
set term png size 800,600
set key left
set out '{outfile}'
p {plotline}
"""
    with open(gpfile, 'w') as f:
        content = tpl.format(title=TESTS[test], conc=c, outfile=outfile,
                             plotline=", ".join(plot_line))
        f.write(content)
    subprocess.check_call(['gnuplot', gpfile])
    print('Created {}'.format(outfile))


if __name__ == '__main__':
    classifier = {}
    if not os.path.isdir(CLEAN_DIR):
        os.mkdir(CLEAN_DIR)
    if not os.path.isdir(IMAGES_DIR):
        os.mkdir(IMAGES_DIR)
    # find interesting files
    for filename in sorted(glob.glob("{}/*.dat".format(DATA_DIR))):
        try:
            classifier[os.path.basename(filename)] = parse_filename(filename)
        except Exception as e:
            print(e)

    # now clean them
    for filename in sorted(classifier.keys()):
        classifier[filename]['clean_file'] = clean(os.path.join(DATA_DIR, filename))

    # Now let's process the comparisons we want and create the graphs
    for name, configs in COMPARISONS.items():
        for test in TESTS.keys():
            for c in [10, 15, 20, 25, 30, 35, 40]:
                # Create a graph series including the configs we picked
                gnuplot(classifier, name, configs, test, c)
