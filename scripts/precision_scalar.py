"""Scalar normal-reference intervals, tails and power."""
import csv
from math import erfc, sqrt
from statistics import NormalDist
import sys


def score(estimate, se, margin):
    reference = NormalDist()
    z95 = reference.inv_cdf(0.975)
    z90 = reference.inv_cdf(0.95)
    lo95, hi95 = estimate - z95*se, estimate + z95*se
    lo90, hi90 = estimate - z90*se, estimate + z90*se
    lower_p = erfc((estimate + margin)/se/sqrt(2))/2
    upper_p = erfc((margin - estimate)/se/sqrt(2))/2
    p = erfc(abs(estimate)/se/sqrt(2))
    acceptance_edge = margin/se - z90
    power_zero = max(0, reference.cdf(acceptance_edge) - reference.cdf(-acceptance_edge))
    return dict(estimate=estimate, se=se, margin=margin, lo95=lo95, hi95=hi95, lo90=lo90, hi90=hi90,
                p_difference=p, p_lower=lower_p, p_upper=upper_p, p_equivalence=max(lower_p, upper_p),
                different=int(lo95 > 0 or hi95 < 0), equivalent=int(lo90 > -margin and hi90 < margin),
                benefit_beyond_margin=int(hi90 < -margin), power_zero=power_zero)


if __name__ == "__main__":
    output = csv.writer(sys.stdout)
    with open(sys.argv[1], newline="") as stream:
        for row in csv.DictReader(stream):
            args = (float(row[key]) for key in ("estimate_pp", "se_pp", "margin_pp"))
            output.writerows((row["case"]+"/"+key,value) for key,value in score(*args).items())
