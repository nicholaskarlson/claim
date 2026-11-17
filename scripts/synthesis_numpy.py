"""Array-based independent reconstruction of the college synthesis."""
import csv
import sys
import numpy as np

T95 = {2:4.30265272974946, 3:3.18244630528371, 14:2.14478668791693, 15:2.13144954555978}


def fit_moments(means, var):
    w = np.reciprocal(var)
    p = w / w.sum()
    location = p @ means
    q = np.sum(w*np.square(means-location))
    return location, q, np.maximum(0,(q-(means.size-1))/(w.sum()*(1-(p @ p))))


def main(path):
    known_and_moments = np.loadtxt(path, dtype=np.int64, delimiter=",", skiprows=1, usecols=range(1,9))
    assigned, n, sums, squares = np.hsplit(known_and_moments,4)
    sample_variance = (squares - np.square(sums)/n) / (n-1)
    var = np.sum(sample_variance/n, axis=1) / 10000
    diff = (sums / n) @ np.array([-.01,.01])
    k = len(diff)
    fixed,q,tau2 = fit_moments(diff,var)
    w = 1/(var+tau2)
    center = np.average(diff, weights=w)
    se = np.sqrt(1/w.sum())
    predicted = T95[k-2]*np.sqrt(se**2+tau2)
    mean_half = T95[k-1]*se
    omitted = np.array([fit_moments(np.delete(diff,i),np.delete(var,i))[2] for i in range(k)])
    overlap = np.prod(n,axis=1)/n.sum(axis=1)
    output = {"colleges":k,"roster":assigned.sum(),"known":n.sum(),"missing":(assigned-n).sum(),
              "low":diff.min(),"high":diff.max(),"equal_mean":diff.mean(),"spread":diff.std(ddof=1),
              "common_ols":np.average(diff,weights=overlap),"fixed_iv":fixed,"q":q,"tau":np.sqrt(tau2),
              "pooled":center,"mean_se":se,"mean_lo":center-mean_half,"mean_hi":center+mean_half,
              "prediction_lo":center-predicted,"prediction_hi":center+predicted,
              "leaveout_lo":np.sqrt(omitted.min()),"leaveout_hi":np.sqrt(omitted.max())}
    with open(path,newline="") as handle:
        names = [row["college"] for row in csv.DictReader(handle)]
    for name,delta,v in zip(names,diff,var):
        output[f"{name}_contrast"] = delta
        output[f"{name}_se"] = np.sqrt(v)
    csv.writer(sys.stdout,lineterminator="\n").writerows(output.items())


if __name__ == "__main__":
    main(sys.argv[1])
