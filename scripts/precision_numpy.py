"""Vectorized normal-reference intervals, tails and power."""
import csv
from math import erf, erfc, sqrt
import sys

import numpy as np

# Standard normal critical values to binary64 precision.
Z = np.asarray([1.959963984540054, 1.6448536269514722])


def scores(estimate, se, margin):
    width95, width90 = Z[:, None] * se
    lo95, hi95 = estimate - width95, estimate + width95
    lo90, hi90 = estimate - width90, estimate + width90
    sf = np.vectorize(erfc, otypes=[float])
    p_diff = sf(np.abs(estimate)/(se*sqrt(2)))
    p_lower = sf((estimate + margin)/(se*sqrt(2)))/2
    p_upper = sf((margin - estimate)/(se*sqrt(2)))/2
    power = np.vectorize(erf, otypes=[float])(np.maximum(0, margin/se - Z[1])/sqrt(2))
    return dict(estimate=estimate, se=se, margin=margin, lo95=lo95, hi95=hi95, lo90=lo90, hi90=hi90,
                p_difference=p_diff, p_lower=p_lower, p_upper=p_upper, p_equivalence=np.maximum(p_lower, p_upper),
                different=(p_diff < .05).astype(int), equivalent=(np.maximum(p_lower, p_upper) < .05).astype(int),
                benefit_beyond_margin=(hi90 < -margin).astype(int), power_zero=power)


if __name__ == "__main__":
    rows = np.atleast_1d(np.genfromtxt(sys.argv[1], names=True, delimiter=",", dtype=None, encoding="ascii"))
    results = scores(rows["estimate_pp"], rows["se_pp"], rows["margin_pp"])
    output = csv.writer(sys.stdout)
    for i, case in enumerate(rows["case"]):
        output.writerows((f"{case}/{key}",value[i]) for key,value in results.items())
