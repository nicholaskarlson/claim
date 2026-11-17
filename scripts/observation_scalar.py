"""Exact-count and rational-weight summaries using standard-library Python."""
from fractions import Fraction

from observation_io import run


def rates(n, known, events):
    unknown = n - known
    return {"eligible": n, "known": known, "withdrawals": events, "unknown": unknown,
            "known_rate": events / known, "lower": events / n, "upper": (events + unknown) / n}


def analyze(mode, rows):
    if mode == "fixture":
        weights = {}
        n = known = events = 0
        total_weight = weighted_events = Fraction()
        for row in rows:
            size, used, cases = (int(row[k]) for k in ("eligible", "known", "withdrawals"))
            if used == 0:
                raise ValueError("A target stratum has no known outcomes")
            w = Fraction(size, used)
            weights["weight_" + row["stratum"]] = float(w)
            n += size
            known += used
            events += cases
            total_weight += used * w
            weighted_events += cases * w
        result = {**rates(n, known, events), **weights,
                  "weighted": float(weighted_events / total_weight), "weight_sum": float(total_weight)}
        return {"fixture/" + key: value for key, value in result.items()}

    result = {}
    for name, response in (("all", None), ("respondents", "1"), ("nonrespondents", "0")):
        group = [row for row in rows if response is None or row["responded_baseline"] == response]
        known = sum(row["outcome_known"] == "1" for row in group)
        events = sum(row["withdrawal_label"] == "1" for row in group)
        stats = rates(len(group), known, events)
        stats["transfers"] = sum(row["exit_type"] == "transfer" for row in group)
        result.update({name + "/" + key: value for key, value in stats.items()})
    control = [r for r in rows if r["responded_baseline"] == "1" and r["offer"] == "0"]
    result["audit/old_response_blend"] = (
        result["respondents/eligible"] * sum(r["withdrawal_label"] == "1" for r in control)
        / sum(r["outcome_known"] == "1" for r in control) + result["nonrespondents/withdrawals"]
    ) / result["all/eligible"]
    return result


if __name__ == "__main__":
    run(analyze)
