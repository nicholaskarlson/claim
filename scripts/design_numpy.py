"""Vectorized group counts and assignment matrices for Chapter 6."""
import numpy as np

from design_io import run


def analyze(assigned, registry):
    ids = np.array([r["student_id"] for r in registry])
    order = np.argsort(ids)
    joined = order[np.searchsorted(ids[order], [r["student_id"] for r in assigned])]
    labels = np.array([r["withdrawal_label"] for r in registry])[joined]
    college, inv = np.unique([r["college_id"] for r in assigned], return_inverse=True)
    arm = np.array([int(r["offer"]) for r in assigned])
    index = inv*2 + arm
    size = 2*len(college)
    n = np.bincount(index, minlength=size).reshape(-1, 2)
    y = np.bincount(index[labels=="1"], minlength=size).reshape(-1, 2)
    m = np.bincount(index[labels==""], minlength=size).reshape(-1, 2)
    nc = n.sum(axis=1)
    w = nc / nc.sum()
    rates = y/n
    minimum = w @ (rates[:, 1] - rates[:, 0] - m[:, 0]/n[:, 0])
    maximum = w @ (rates[:, 1] - rates[:, 0] + m[:, 1]/n[:, 1])
    var = np.sum((w*w) * (nc/(nc-1)) * np.sum(1/n, axis=1) / 4)
    radius = np.sqrt(var/.05)
    result = {"design/n": nc.sum(), "design/colleges": len(nc), "design/completion_lower": minimum,
              "design/completion_upper": maximum, "design/variance_bound": var, "design/radius": radius,
              "design/confidence_lower": max(-1, minimum-radius),
              "design/confidence_upper": min(1, maximum+radius)}
    for i, c in enumerate(college):
        for tag, tab in (("n", n), ("y", y), ("m", m)):
            for z in (0, 1):
                result[f"college/{c}/{tag}{z}"] = tab[i,z]
    return result


def fixture(rows):
    college = np.array([r["college_id"] for r in rows])
    offer = np.array([int(r["offer"]) for r in rows])
    patterns = (np.arange(1 << len(rows))[:, None] >> np.arange(len(rows))) & 1
    masks = patterns[(patterns[:, college=="A"].sum(axis=1)==2) &
                     (patterns[:, college=="B"].sum(axis=1)==2)]
    result = {"toy/schedules": len(masks)}
    for value in (0,1):
        y = np.array([int(r["outcome"]) if r["outcome"] else value for r in rows])
        scale = len(y)//2
        stats = (2*(masks @ y)-y.sum())/scale
        observed = (2*(offer @ y)-y.sum())/scale
        hits = np.count_nonzero(abs(stats)>=abs(observed))
        tag = f"toy/if{value}/"
        result.update({tag+"stat": observed, tag+"extremes": hits, tag+"p": hits/len(masks)})
    result["toy/max_p"] = max(result["toy/if0/p"], result["toy/if1/p"])
    return result


if __name__ == "__main__":
    run(analyze, fixture)
