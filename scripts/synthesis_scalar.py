"""Scalar Python synthesis of college-level grade moments."""
import csv
import math
from statistics import fmean, stdev
import sys

# The R route also computes these reference quantiles directly.
T95 = {2:4.30265272974946, 3:3.18244630528371, 14:2.14478668791693, 15:2.13144954555978}


def mean_weighted(values, weights):
    return math.fsum(x*w for x,w in zip(values,weights)) / math.fsum(weights)


def heterogeneity(d, weights):
    fixed = mean_weighted(d,weights)
    q = math.fsum(w*(x-fixed)**2 for x,w in zip(d,weights))
    total = math.fsum(weights)
    correction = total-math.fsum(w*w for w in weights)/total
    return fixed, q, max(0., (q-len(d)+1)/correction)


def main(path):
    with open(path,newline="") as handle:
        rows = list(csv.DictReader(handle))
    d, v, overlap = [], [], []
    for row in rows:
        n0,n1 = int(row["known_no"]),int(row["known_offer"])
        s0,s1 = int(row["sum_no"]),int(row["sum_offer"])
        q0,q1 = int(row["ss_no"]),int(row["ss_offer"])
        # Keep exact integer centered sums in the numerator before division.
        d.append((s1*n0-s0*n1)/(100*n0*n1))
        v.append(((n0*q0-s0*s0)/(n0*n0*(n0-1)) + (n1*q1-s1*s1)/(n1*n1*(n1-1)))/10000)
        overlap.append(n0*n1/(n0+n1))
    k = len(d)
    weights = [1/x for x in v]
    fixed,q,tau2 = heterogeneity(d,weights)
    random = [1/(x+tau2) for x in v]
    pooled = mean_weighted(d,random)
    se = 1/math.sqrt(math.fsum(random))
    mean_width = T95[k-1]*se
    prediction_width = T95[k-2]*math.hypot(se,math.sqrt(tau2))
    omitted = [heterogeneity(d[:i]+d[i+1:],weights[:i]+weights[i+1:])[2] for i in range(k)]
    n = sum(int(row[key]) for row in rows for key in ("assigned_no","assigned_offer"))
    known = sum(int(row[key]) for row in rows for key in ("known_no","known_offer"))
    output = {"colleges":k,"roster":n,"known":known,"missing":n-known,"low":min(d),"high":max(d),
              "equal_mean":fmean(d),"spread":stdev(d),"common_ols":mean_weighted(d,overlap),
              "fixed_iv":fixed,"q":q,"tau":math.sqrt(tau2),"pooled":pooled,"mean_se":se,
              "mean_lo":pooled-mean_width,"mean_hi":pooled+mean_width,
              "prediction_lo":pooled-prediction_width,"prediction_hi":pooled+prediction_width,
              "leaveout_lo":math.sqrt(min(omitted)),"leaveout_hi":math.sqrt(max(omitted))}
    for row,delta,var in zip(rows,d,v):
        output[f"{row['college']}_contrast"] = delta
        output[f"{row['college']}_se"] = math.sqrt(var)
    csv.writer(sys.stdout,lineterminator="\n").writerows(output.items())


if __name__ == "__main__":
    main(sys.argv[1])
