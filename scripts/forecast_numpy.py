"""Vectorized scores for frozen binary forecasts."""
import csv
import sys

import numpy as np


def score(z):
    y = z["outcome"]
    n, events = len(y), int(y.sum())
    values = {"n": n, "events": events}
    for key in ("forecast", "baseline"):
        p = z[key]
        order = np.argsort(p)
        _, starts = np.unique(p[order], return_index=True)
        sizes = np.diff(np.append(starts, n))
        yes = np.add.reduceat(y[order], starts)
        no = sizes - yes
        pairs2 = int(yes @ (2 * np.cumsum(no) - no))
        clipped = np.clip(p, 1e-12, 1 - 1e-12)
        values.update({key+"/mean": p.mean(), key+"/brier": np.mean((p-y)**2),
                       key+"/auc_pairs2": pairs2, key+"/auc": pairs2/(2*events*(n-events)),
                       key+"/log_loss": -np.mean(y*np.log(clipped)+(1-y)*np.log1p(-clipped))})
    for i in range(5):
        p = z["forecast"]
        select = (p >= i/5) & ((p < (i+1)/5) if i < 4 else (p <= 1))
        count = np.count_nonzero(select)
        values.update({f"bin/{i+1}/n": count, f"bin/{i+1}/events": int(y[select].sum())})
        if count:
            values[f"bin/{i+1}/mean"] = p[select].mean()
    return values


if __name__ == "__main__":
    arr = np.genfromtxt(sys.argv[1], delimiter=",", names=True, dtype=None, encoding="ascii")
    writer = csv.writer(sys.stdout, lineterminator="\n")
    for group in ("all", *sorted(set(arr["group"]))):
        current = arr if group=="all" else arr[arr["group"]==group]
        writer.writerows((f"{group}/{key}", value) for key,value in sorted(score(current).items()))
