"""CSV input and output for independent Part I calculations."""
import argparse
import csv
from pathlib import Path


def read(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("withdrawal", "probability"))
    parser.add_argument("input", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("registry", type=Path, nargs="?")
    return parser.parse_args()


def write(out, values, joined=()):
    out.mkdir(parents=True, exist_ok=False)
    with (out/"values.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("key", "value"))
        writer.writerows(sorted(values.items()))
    with (out/"joined.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("student_id", "college_id", "offer", "outcome_known", "withdrawal_label", "exit_type"))
        writer.writerows(joined)
