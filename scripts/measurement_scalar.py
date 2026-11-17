"""Standard-library computation for Chapter 4."""
import csv
import math
from pathlib import Path
import statistics as st
import sys

from measurement_io import ITEMS


def rows(path):
    with Path(path).open(newline="") as stream:
        return {row["student_id"]: row for row in csv.DictReader(stream)}


def score(row):
    keyed = [6 - int(row[key]) if key == "st4" else int(row[key])
             for key in ITEMS if row[key]]
    return sum(keyed) * (20 // len(keyed)) if len(keyed) >= 4 else None


def analyze(baseline, assignment, followup, observed_r):
    before, offers, after = (rows(path) for path in (baseline, assignment, followup))
    eligible = []
    for identity, row in before.items():
        if offers[identity]["offer"] != "0":
            continue
        x = score(row)
        if x is not None:
            y = score(after[identity]) if after[identity]["responded"] == "1" else None
            eligible.append((x, identity, y))
    eligible.sort()
    paired = [(x, identity, y) for x, identity, y in eligible if y is not None]
    m = len(paired) // 4
    low, high = paired[:m], paired[-m:]
    xs, ys = [x for x, _, _ in paired], [y for _, _, y in paired]
    mx, my = st.mean(xs), st.mean(ys)
    slope = st.covariance(xs, ys) / st.variance(xs)
    selected = eligible[-(len(eligible) // 4):]
    threshold = [y for x, _, y in paired if x >= 80]
    values = {
        "arm0/n": len(paired), "arm0/baseline_mean": mx / 20, "arm0/month3_mean": my / 20,
        "arm0/change": (my - mx) / 20, "arm0/correlation": st.correlation(xs, ys),
        "arm0/slope": slope, "threshold/n": len(threshold),
        "threshold/remain": sum(y >= 80 for y in threshold),
        "baseline_selected/eligible": len(eligible), "baseline_selected/top/n": len(selected),
        "baseline_selected/top/paired": sum(y is not None for _, _, y in selected),
        "top/ties": xs.count(high[0][0]),
        "top/prediction": (my + slope * (st.mean(x for x, _, _ in high) - mx)) / 20,
    }
    for name, group in (("bottom", low), ("top", high),
                        ("top_inclusive", [row for row in paired if row[0] >= high[0][0]])):
        values.update({f"{name}/n": len(group),
                       f"{name}/baseline": st.mean(x for x, _, _ in group) / 20,
                       f"{name}/month3": st.mean(y for _, _, y in group) / 20,
                       f"{name}/change": st.mean(y - x for x, _, y in group) / 20})
    for name, rx, ry, delta in (("negative", .70, .85, -.25), ("zero", .70, .85, 0),
                                ("positive", .70, .85, .25), ("impossible", .10, .10, 0)):
        error_cov = delta * math.sqrt((1 - rx) * (1 - ry))
        implied = (observed_r - error_cov) / math.sqrt(rx * ry)
        values[f"error/{name}/rho"] = implied
        values[f"error/{name}/feasible"] = int(abs(implied) <= 1)
    return values, eligible


if __name__ == "__main__":
    values, identities = analyze(*sys.argv[1:4], float(sys.argv[4]))
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerows(sorted(values.items()))
    writer.writerows((identity, x, "" if y is None else y) for x, identity, y in identities)
