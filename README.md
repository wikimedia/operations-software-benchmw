benchmw
=======

benchmw is a set of scripts to make benchmarking MediaWiki and then sharing
results easier.

You need a server configured to serve MediaWiki, tuned to whatever you want to
benchmark. From a server with `ab` installed (like deploy1001), run:

```
python3 run_benchmarks.py mw1234.eqiad.wmnet label
```

`label` should be an internal identifier that describes the configuration of
what you're testing.

Repeat with different labels for whatever else you want to compare to.

Move all the `*.dat` files into a folder named `data` on your machine
and make sure you have `gnuplot` installed.

First, create a `config.yaml` file based on the sample one provided. Specify
the human-readable descriptions for the labels used and then what comparisons
should be charted.

```
python3 filter_and_plot.py data config.yaml
```

That will clean the data and generate images in `data/images/`.
