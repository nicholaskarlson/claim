"""Command-line and CSV plumbing for the Chapter 5 calculation routes."""
import argparse
import csv
from pathlib import Path
import sys

from part1_io import read


def run(analyze):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("registry", "fixture"))
    parser.add_argument("source")
    args = parser.parse_args()
    values = analyze(args.mode, read(Path(args.source)))
    csv.writer(sys.stdout, lineterminator="\n").writerows(sorted(values.items()))
