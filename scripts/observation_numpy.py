"""Vectorized counts and normalized weights for the Chapter 5 examples."""
import numpy as np

from observation_io import run


def analyze(mode, rows):
    if mode == "fixture":
        sizes, used, cases = (np.array([int(row[key]) for row in rows])
                              for key in ("eligible", "known", "withdrawals"))
        if np.any(used == 0):
            raise ValueError("A target stratum has no known outcomes")
        weights = sizes / used
        total = sizes.sum()
        observed = used.sum()
        events = cases.sum()
        unknown = total - observed
        weight_sum = weights @ used
        values = {"eligible": total, "known": observed, "withdrawals": events, "unknown": unknown,
                  "known_rate": events / observed, "lower": events / total,
                  "upper": (events + unknown) / total,
                  "weighted": (weights @ cases) / weight_sum, "weight_sum": weight_sum}
        values.update({"weight_" + row["stratum"]: w for row, w in zip(rows, weights)})
        return {"fixture/" + key: value for key, value in values.items()}

    keys = ("responded_baseline", "outcome_known", "withdrawal_label", "exit_type")
    response, known, event, exit_type = (np.array([r[key] for r in rows]) for key in keys)
    is_known, withdrew, transfer = known == "1", event == "1", exit_type == "transfer"
    result = {}
    for name, mask in (("all", np.ones(len(rows), dtype=bool)), ("respondents", response == "1"),
                       ("nonrespondents", response == "0")):
        n = np.count_nonzero(mask)
        k = np.count_nonzero(mask & is_known)
        y = np.count_nonzero(mask & withdrew)
        summary = {"eligible": n, "known": k, "withdrawals": y, "unknown": n-k,
                   "known_rate": y/k, "lower": y/n, "upper": (y+n-k)/n,
                   "transfers": np.count_nonzero(mask & transfer)}
        result.update({name + "/" + key: value for key, value in summary.items()})
    offer = np.array([r["offer"] for r in rows])
    control = (response == "1") & (offer == "0")
    shares = np.array([result[f"{g}/eligible"] for g in ("respondents", "nonrespondents")]) / len(rows)
    group_rates = np.array([withdrew[control].sum() / is_known[control].sum(),
                            result["nonrespondents/known_rate"]])
    result["audit/old_response_blend"] = shares @ group_rates
    return result


if __name__ == "__main__":
    run(analyze)
