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
import math
import re
import subprocess

from pathlib import Path

import yaml

from run_benchmarks import STEPS, URLS


def parse_args():
    parser = argparse.ArgumentParser(description="Filter data and plot it into charts")
    parser.add_argument("data_dir", type=Path, help="Directory of data files")
    parser.add_argument("config", type=Path, help="Configuration of comparisons to make")
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        raise ValueError("{} is not a directory".format(args.data))
    if not args.config.exists():
        raise ValueError("{} does not exist".format(args.config))

    return args


def clean(clean_dir: Path, filename: Path) -> Path:
    print("cleaning file {}".format(filename))
    # read all the file, extract response time and timestamp, and sort by timestamp.
    # NOT optimized on purpose.
    clean_filename = clean_dir / filename.name
    results = []
    content = filename.read_text().splitlines()
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
    with clean_filename.open('w') as f:
        for duration, ts in clean_results:
            f.write("{}\t{}\n".format(duration, ts))
    return clean_filename


def parse_filename(config, filename: Path):
    bn = filename.name
    all_configs = list(config['configurations'])
    all_tests = list(URLS)
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


def latency_plot(config, images_dir: Path, clean_dir: Path, classifier, name, labels, test, c):
    filenames = []
    for label in labels:
        filename = "{}_{}_c{}.dat".format(label, test, c)
        try:
            clean_file = classifier[filename]['clean_file']
            filenames.append(clean_file)
        except KeyError:
            raise RuntimeError("Unable to find {}".format(filename))
    label_descrs = map(lambda x: config['configurations'][x], labels)
    percentiles = ['Percentile\t' + '\t'.join(label_descrs)]
    for percentile in config['percentiles']:
        data = [str(percentile)]
        for filename in filenames:
            with open(filename, 'r') as f:
                lines = f.readlines()
                p = lines[round(percentile*len(lines))]
                data.append(p.split('\t')[0])
        data = '\t'.join(data)
        percentiles.append(data)
    pfile = '{}_{}_{}.percentiles'.format('+'.join(labels), test, c)
    print('Saving to ', clean_dir / pfile)
    percentiles = map(lambda x: x + '\n', percentiles)
    with open(clean_dir / pfile, 'w') as f:
        f.writelines(percentiles)

    # And now let's draw it
    outfile = images_dir / "{}_{}_c{}.png".format(name, test, c)
    gpfile = clean_dir / "{}_{}_c{}.gpl".format(name, test, c)
    tpl = """
set title '{title} (c={conc})'
set term png size 1800,1600
set key left top vertical samplen 4 spacing 1 font ",20"
set xtics rotate out
set out '{outfile}'
set style data histogram
set style fill solid border
set style histogram clustered gap 3
plot for [COL=2:{last_label}] '{infile}' using COL:xticlabels(1) title columnheader
"""
    content = tpl.format(
            title=URLS[test]['title'],
            conc=c,
            outfile=outfile,
            infile=clean_dir / pfile,
            last_label=len(labels) + 1,
            )
    gpfile.write_text(content)
    subprocess.check_call(['gnuplot', str(gpfile)])
    print('Created {}'.format(outfile))


def gnuplot(config, images_dir: Path, clean_dir: Path, classifier, name, labels, test, c):
    plot_line = []
    for label in labels:
        filename = "{}_{}_c{}.dat".format(label, test, c)
        try:
            clean_file = classifier[filename]['clean_file']
        except KeyError:
            raise RuntimeError("Unable to find {}".format(filename))
        plot_line.append("'{}' using 1 title '{}' with lines smooth csplines linewidth 4".format(
            clean_file, config['configurations'][label]))
    # remove the trailing comma and space
    outfile = images_dir / "{}_{}_c{}.png".format(name, test, c)
    gpfile = clean_dir / "{}_{}_c{}.gpl".format(name, test, c)
    tpl = """
set title '{title} (c={conc})'
set term png size 800,600
set key left
set out '{outfile}'
plot {plotline}
"""
    content = tpl.format(title=URLS[test]['title'], conc=c, outfile=outfile,
                         plotline=", ".join(plot_line))
    gpfile.write_text(content)
    subprocess.check_call(['gnuplot', str(gpfile)])
    print('Created {}'.format(outfile))


def main():
    args = parse_args()
    clean_dir = args.data_dir / 'clean'
    images_dir = args.data_dir / 'images'
    with args.config.open() as f:
        config = yaml.safe_load(f)
    print(config)
    classifier = {}
    if not clean_dir.is_dir():
        clean_dir.mkdir()
    if not images_dir.is_dir():
        images_dir.mkdir()
    # find interesting files
    for filename in sorted(args.data_dir.glob("*.dat")):
        classifier[filename.name] = parse_filename(config, filename)

    # now clean them
    for filename in sorted(classifier):
        classifier[filename]['clean_file'] = clean(clean_dir, args.data_dir / filename)

    # Now let's process the comparisons we want and create the graphs
    for name, configs in config['comparisons'].items():
        for test in URLS:
            for c in STEPS:
                # TODO: Make this good, not hardcoded
                if name == 'percentiles':
                    latency_plot(config, images_dir, clean_dir, classifier,
                            name, configs, test, c)
                else:
                    # Create a graph series including the configs we picked
                    gnuplot(config, images_dir, clean_dir, classifier, name, configs, test, c)


if __name__ == '__main__':
    main()
