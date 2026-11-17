"""CSV input and output for the independent Chapter 6 routes."""
import argparse
import csv
from pathlib import Path
import sys

from part1_io import read


def run(analyze, fixture):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("registry", "fixture"))
    parser.add_argument("source", type=Path)
    parser.add_argument("registry", type=Path, nargs="?")
    args = parser.parse_args()
    rows = read(args.source)
    result = fixture(rows) if args.mode == "fixture" else analyze(rows, read(args.registry))
    csv.writer(sys.stdout, lineterminator="\n").writerows(sorted(result.items()))
