"""CSV plumbing for independent visits and exposure computations."""
import argparse
import csv
import io
from pathlib import Path
import sys

from part1_io import read


FIELDS = ["student_id","visits","months","prior_grade","part_time","first_gen"]


def project(baseline, participants, registry):
    def records(data):
        return list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))

    people = records(participants)
    histories = records(registry)
    p = {r["student_id"]:r for r in people}
    h = {r["student_id"]:r for r in histories}
    b = records(baseline)
    ids = {r["student_id"] for r in b}
    if len(ids)!=len(b) or len(p)!=len(people) or len(h)!=len(histories) or ids != set(h) or not ids <= set(p):
        raise ValueError("Book 9 visit/participant identity sets differ")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in b:
        sid=row["student_id"]
        if row["college_id"] != p[sid]["college_id"] or p[sid]["responded_baseline"] != "1":
            raise ValueError("Book 9 college or baseline membership differs")
        writer.writerow({"student_id":sid,"visits":h[sid]["visits_12"],"months":h[sid]["months_enrolled"],
                         **{key:p[sid][key] for key in FIELDS[3:]}})
    return stream.getvalue().encode()


def run(analyze):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("ordinary","fixture"))
    parser.add_argument("source", type=Path)
    parser.add_argument("assignment", type=Path, nargs="?")
    parser.add_argument("beta", nargs="*", type=float)
    args = parser.parse_args()
    rows = read(args.source)
    if args.mode == "ordinary":
        assignments = read(args.assignment)
        by_id = {r["student_id"]:r for r in rows}
        rows = [{**a, **by_id[a["student_id"]]} for a in assignments]
    result = analyze(rows, args.beta)
    csv.writer(sys.stdout, lineterminator="\n").writerows(sorted(result.items()))
