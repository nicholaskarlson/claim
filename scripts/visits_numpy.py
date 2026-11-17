"""NumPy visit summaries and working college covariance."""
import numpy as np

from visits_io import run


def analyze(rows, beta):
    z, y, t = (np.array([float(r[key]) for r in rows]) for key in ("offer","visits","months"))
    if np.any(t <= 0):
        raise ValueError("Exposure must be positive")
    values = {"raw/zeros":np.count_nonzero(y==0)}
    for arm in (0,1):
        mask = z==arm
        n, months, visits = mask.sum(), t[mask].sum(), y[mask].sum()
        summaries = {"n":n,"months":months,"visits":visits,"mean_count":visits/n,
                     "aggregate_rate":visits/months,"mean_individual_rate":np.mean(y[mask]/t[mask])}
        values.update({f"arm{arm}/{key}":v for key,v in summaries.items()})
    values.update({"raw/count_difference":values["arm1/mean_count"]-values["arm0/mean_count"],
                   "raw/rate_ratio":values["arm1/aggregate_rate"]/values["arm0/aggregate_rate"]})
    if not beta:
        return values
    n = len(rows)
    colleges, idx = np.unique([r["college_id"] for r in rows],return_inverse=True)
    g = len(colleges)
    counts = np.bincount(idx*2+z.astype(int),minlength=2*g).reshape(-1,2)
    visits = np.bincount(idx*2+z.astype(int),weights=y,minlength=2*g).reshape(-1,2)
    means = visits/counts
    estimate = (counts.sum(axis=1)/n) @ (means[:,1]-means[:,0])
    x = np.column_stack((np.ones(n),z,[float(r["prior_grade"])-3 for r in rows],
                         [float(r["part_time"]) for r in rows],[float(r["first_gen"]) for r in rows]))
    k = x.shape[1]
    mu = t*np.exp(x@beta)
    scores = x*(y-mu)[:,None]
    info = x.T @ (mu[:,None]*x)
    contrast = np.linalg.solve(info,[0,1,0,0,0])
    influence = scores @ contrast
    grouped = np.bincount(idx,weights=influence)
    row_se = np.sqrt((influence@influence)*n/(n-k))
    college_se = np.sqrt((grouped@grouped)*(g/(g-1))*((n-1)/(n-k)))
    crit = 2.131449545559323
    values.update({"design/colleges":g,"design/difference":estimate,"model/row_se":row_se,
                   "model/college_se":college_se,"model/score_max_per_row":np.max(np.abs(scores.sum(axis=0)))/n,
                   "model/college_lower":np.exp(beta[1]-crit*college_se),
                   "model/college_upper":np.exp(beta[1]+crit*college_se)})
    return values


if __name__ == "__main__":
    run(analyze)
