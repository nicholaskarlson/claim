"""Standard-library route using dictionaries, combinations and exact fractions."""
from fractions import Fraction
from itertools import combinations, product
from math import comb

from part1_io import arguments, read, write


def withdrawal(assigned_path, registry_path):
    assigned = sorted(read(assigned_path), key=lambda row: row["student_id"])
    registry = read(registry_path)
    lookup = {row["student_id"]:row for row in registry}
    joined = []
    for row in assigned:
        if row["student_id"] not in lookup:
            raise ValueError("Missing registry identity")
        record = lookup[row["student_id"]]
        if row["offer"] != record["offer"]:
            raise ValueError("Offer disagrees across files")
        joined.append(tuple(row[k] for k in ("student_id", "college_id", "offer"))+
                      tuple(record[k] for k in ("outcome_known", "withdrawal_label", "exit_type")))
    values = {"baseline_n":len(assigned), "registry_n":len(registry),
              "colleges_n":len({row["college_id"] for row in assigned})}
    for arm in ("0", "1"):
        rows = [row for row in joined if row[2] == arm]
        n = len(rows)
        known = sum(row[3] == "1" for row in rows)
        events = sum(row[4] == "1" for row in rows)
        unknown = n-known
        result = {"assigned":n, "known":known, "unknown":unknown, "events":events,
                  "recorded_rate":Fraction(events,n), "known_rate":Fraction(events,known) if known else None,
                  "lower":Fraction(events,n), "upper":Fraction(events+unknown,n)}
        values.update({f"arm/{arm}/{key}":value for key,value in result.items()})
    values["known_difference"] = values["arm/1/known_rate"]-values["arm/0/known_rate"] if all(
        values[f"arm/{arm}/known_rate"] is not None for arm in ("0", "1")) else None
    values["realized_difference_lower"] = values["arm/1/lower"]-values["arm/0/upper"]
    values["realized_difference_upper"] = values["arm/1/upper"]-values["arm/0/lower"]
    return {key:float(value) if isinstance(value,Fraction) else value for key,value in values.items()}, joined


def probability(root):
    sampling = read(root/"sampling.csv")
    estimates = []
    for selected in combinations(sampling, int(sampling[0]["sample_colleges"])):
        estimates.append(Fraction(sum(int(r["withdrawals"]) for r in selected),sum(int(r["size"]) for r in selected)))
    values = {"sampling/schedules":len(estimates), "sampling/population_rate":Fraction(
        sum(int(r["withdrawals"]) for r in sampling),sum(int(r["size"]) for r in sampling)),
        "sampling/mean":sum(estimates)/len(estimates), "sampling/min":min(estimates), "sampling/max":max(estimates)}
    rows = read(root/"assignment.csv")
    outcomes = [int(row["outcome"]) for row in rows]
    observed = {i for i,row in enumerate(rows) if row["offer"] == "1"}
    groups = sorted({row["college_id"] for row in rows})
    possible = [list(combinations([i for i,row in enumerate(rows) if row["college_id"] == group],
                                  int(rows[0]["offers_per_college"]))) for group in groups]
    blocked = [set().union(*selection) for selection in product(*possible)]
    pooled = [set(selection) for selection in combinations(range(len(rows)),len(observed))]
    def contrast(selected):
        return Fraction(sum(outcomes[i] for i in selected),len(selected))-Fraction(
            sum(outcomes[i] for i in range(len(rows)) if i not in selected),len(rows)-len(selected))
    observed_difference = contrast(observed)
    values["assignment/observed_difference"] = observed_difference
    for name,schedules in (("blocked",blocked),("pooled",pooled)):
        extremes = sum(abs(contrast(selected)) >= abs(observed_difference) for selected in schedules)
        values.update({f"assignment/{name}_schedules":len(schedules), f"assignment/{name}_extremes":extremes,
                       f"assignment/{name}_p":Fraction(extremes,len(schedules))})
    likelihoods = []
    for index,row in enumerate(read(root/"model.csv")):
        n,k,p = int(row["trials"]),int(row["events"]),Fraction(row["probability"])
        likelihood = comb(n,k)*p**k*(1-p)**(n-k)
        values[f"model/likelihood_{index}"] = likelihood
        likelihoods.append(likelihood)
    values["model/likelihood_ratio"] = likelihoods[0]/likelihoods[1]
    return {key:float(value) if isinstance(value,Fraction) else value for key,value in values.items()}, []


if __name__ == "__main__":
    args = arguments()
    values, joined = withdrawal(args.input,args.registry) if args.mode == "withdrawal" else probability(args.input)
    write(args.out,values,joined)
