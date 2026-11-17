"""NumPy route for the scoped observed-score check."""
import csv
import sys

import numpy as np

with open(sys.argv[1], newline="") as stream:
    data = list(csv.reader(stream))[1:]
rows = np.array(data)
items = rows[:, 2:]
keep = np.all(items != "", axis=1)
keyed = items[keep].astype(np.int64)
keyed[:, [3, 8]] = 6 - keyed[:, [3, 8]]
sums = keyed.reshape(-1, 2, 5).sum(axis=2)
print(f"{len(rows)},{len(np.unique(rows[:, 1]))},{len(sums)},{np.corrcoef(sums.T)[0, 1]:.17g}")
for identity, pair in zip(rows[keep, 0], sums):
    print(f"{identity},{pair[0]},{pair[1]}")
