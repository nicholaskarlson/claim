"""NumPy computation for Chapter 4."""
import csv
import sys

import numpy as np

from measurement_io import ITEMS


def table(path):
    return np.atleast_1d(np.genfromtxt(path, delimiter=",", names=True, dtype=None,
                                      encoding="ascii", missing_values="", filling_values=-1))


def scores(table):
    items = np.column_stack([table[key] for key in ITEMS])
    valid = items > 0
    items[:, 3] = 6 - items[:, 3]
    n = valid.sum(axis=1)
    totals = np.where(valid, items, 0).sum(axis=1)
    return np.select([n == 4, n == 5], [5 * totals, 4 * totals], default=-1)


def analyze(baseline, assignment, followup, observed_r):
    b, a, f = (np.sort(table(path), order="student_id") for path in (baseline, assignment, followup))
    assert np.array_equal(b["student_id"], a["student_id"]) and np.array_equal(b["student_id"], f["student_id"])
    x, y = scores(b), scores(f)
    y[f["responded"] != 1] = -1
    ix = np.flatnonzero((a["offer"] == 0) & (x >= 0))
    ix = ix[np.lexsort((b["student_id"][ix], x[ix]))]
    pair = ix[y[ix] >= 0]
    m = len(pair) // 4
    low, high = pair[:m], pair[-m:]
    high_inclusive = pair[x[pair] >= x[high[0]]]
    selected = ix[-(len(ix) // 4):]
    xp, yp = x[pair] / 20, y[pair] / 20
    design = np.column_stack((np.ones(len(xp)), xp))
    intercept, slope = np.linalg.lstsq(design, yp, rcond=None)[0]
    threshold = yp[xp >= 4]
    values = {
        "arm0/n": len(pair), "arm0/baseline_mean": xp.mean(), "arm0/month3_mean": yp.mean(),
        "arm0/change": (yp - xp).mean(), "arm0/correlation": np.corrcoef(xp, yp)[0, 1],
        "arm0/slope": slope, "threshold/n": len(threshold),
        "threshold/remain": np.count_nonzero(threshold >= 4),
        "baseline_selected/eligible": len(ix), "baseline_selected/top/n": len(selected),
        "baseline_selected/top/paired": np.count_nonzero(y[selected] >= 0),
        "top/ties": np.count_nonzero(x[pair] == x[high[0]]),
        "top/prediction": intercept + slope * x[high].mean() / 20,
    }
    for name, group in (("bottom", low), ("top", high), ("top_inclusive", high_inclusive)):
        values.update({f"{name}/n": len(group), f"{name}/baseline": x[group].mean() / 20,
                       f"{name}/month3": y[group].mean() / 20,
                       f"{name}/change": (y[group] - x[group]).mean() / 20})
    reliabilities = np.array([[.70, .85], [.70, .85], [.70, .85], [.10, .10]])
    rho = ((observed_r - np.array([-.25, 0, .25, 0]) * np.sqrt((1 - reliabilities).prod(axis=1)))
           / np.sqrt(reliabilities.prod(axis=1)))
    for name, implied in zip(("negative", "zero", "positive", "impossible"), rho):
        values[f"error/{name}/rho"] = implied
        values[f"error/{name}/feasible"] = int(abs(implied) <= 1)
    identities = [(b["student_id"][i], x[i], "" if y[i] < 0 else y[i]) for i in ix]
    return values, identities


if __name__ == "__main__":
    values, identities = analyze(*sys.argv[1:4], float(sys.argv[4]))
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerows(sorted(values.items()))
    writer.writerows(identities)
