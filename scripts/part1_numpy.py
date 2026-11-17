"""NumPy route using sorted joins and vectorized finite enumerations."""
import numpy as np

from part1_io import arguments, read, write


def withdrawal(assigned_path, registry_path):
    assigned = read(assigned_path)
    registry = read(registry_path)
    a = np.array([[r[k] for k in ("student_id", "college_id", "offer")] for r in assigned])
    r = np.array([[row[k] for k in ("student_id", "offer", "outcome_known", "withdrawal_label", "exit_type")]
                  for row in registry])
    a = a[np.argsort(a[:, 0])]
    r = r[np.argsort(r[:, 0])]
    positions = np.searchsorted(r[:, 0], a[:, 0])
    if np.any(positions >= len(r)) or not np.array_equal(r[positions, 0], a[:, 0]):
        raise ValueError("Missing registry identity")
    r = r[positions]
    if not np.array_equal(a[:, 2], r[:, 1]):
        raise ValueError("Offer disagrees across files")
    values = {"baseline_n": len(a), "registry_n": len(registry), "colleges_n": len(np.unique(a[:, 1]))}
    for arm in ("0", "1"):
        selected = r[a[:, 2] == arm]
        n = len(selected)
        known = int(np.count_nonzero(selected[:, 2] == "1"))
        events = int(np.count_nonzero(selected[:, 3] == "1"))
        unknown = n-known
        for key, value in {"assigned":n, "known":known, "unknown":unknown, "events":events,
                           "recorded_rate":events/n, "known_rate":events/known if known else None,
                           "lower":events/n, "upper":(events+unknown)/n}.items():
            values[f"arm/{arm}/{key}"] = value
    values["known_difference"] = values["arm/1/known_rate"]-values["arm/0/known_rate"] if all(
        values[f"arm/{arm}/known_rate"] is not None for arm in ("0", "1")) else None
    values["realized_difference_lower"] = values["arm/1/lower"]-values["arm/0/upper"]
    values["realized_difference_upper"] = values["arm/1/upper"]-values["arm/0/lower"]
    joined = np.column_stack((a, r[:, 2:])).tolist()
    return values, joined


def probability(root):
    sampling = read(root/"sampling.csv")
    sizes = np.array([int(row["size"]) for row in sampling])
    events = np.array([int(row["withdrawals"]) for row in sampling])
    sample_size = int(sampling[0]["sample_colleges"])
    schedules = ((np.arange(2**len(sizes))[:, None] >> np.arange(len(sizes))) & 1).astype(bool)
    schedules = schedules[schedules.sum(axis=1) == sample_size]
    estimates = (schedules@events)/(schedules@sizes)
    values = {"sampling/schedules":len(schedules), "sampling/population_rate":events.sum()/sizes.sum(),
              "sampling/mean":estimates.mean(), "sampling/min":estimates.min(), "sampling/max":estimates.max()}
    rows = read(root/"assignment.csv")
    groups = np.array([row["college_id"] for row in rows])
    outcomes = np.array([int(row["outcome"]) for row in rows])
    observed = np.array([int(row["offer"]) for row in rows], dtype=bool)
    quota = int(rows[0]["offers_per_college"])
    all_schedules = ((np.arange(2**len(rows))[:, None] >> np.arange(len(rows))) & 1).astype(bool)
    blocked = np.ones(len(all_schedules), dtype=bool)
    for group in np.unique(groups):
        blocked &= all_schedules[:, groups == group].sum(axis=1) == quota
    total_offers = int(observed.sum())
    observed_difference = outcomes[observed].mean()-outcomes[~observed].mean()
    values["assignment/observed_difference"] = observed_difference
    for name, keep in (("blocked", blocked), ("pooled", all_schedules.sum(axis=1) == total_offers)):
        eligible = all_schedules[keep]
        differences = (eligible@outcomes)/total_offers-((~eligible)@outcomes)/(len(rows)-total_offers)
        extremes = int(np.count_nonzero(np.abs(differences) >= abs(observed_difference)-1e-14))
        values[f"assignment/{name}_schedules"] = len(eligible)
        values[f"assignment/{name}_extremes"] = extremes
        values[f"assignment/{name}_p"] = extremes/len(eligible)
    likelihoods = []
    for index, row in enumerate(read(root/"model.csv")):
        p, n, k = float(row["probability"]), int(row["trials"]), int(row["events"])
        likelihood = float(np.polynomial.polynomial.polypow([1-p, p], n)[k])
        values[f"model/likelihood_{index}"] = likelihood
        likelihoods.append(likelihood)
    values["model/likelihood_ratio"] = likelihoods[0]/likelihoods[1]
    return values, []


if __name__ == "__main__":
    args = arguments()
    values, joined = withdrawal(args.input, args.registry) if args.mode == "withdrawal" else probability(args.input)
    write(args.out, values, joined)
