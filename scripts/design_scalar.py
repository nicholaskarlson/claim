"""Exact rational calculations for the design and binary-completion examples."""
from collections import defaultdict
from fractions import Fraction as F
from itertools import combinations, product
from math import sqrt

from design_io import run


def analyze(assigned, registry):
    observed = {row["student_id"]: row["withdrawal_label"] for row in registry}
    blocks = defaultdict(lambda: [[], []])
    for row in assigned:
        blocks[row["college_id"]][int(row["offer"])].append(observed[row["student_id"]])
    result = {"design/n": len(assigned), "design/colleges": len(blocks)}
    total = len(assigned)
    low, high, variance = F(0), F(0), F(0)
    for college, (control, offer) in blocks.items():
        n0, n1 = len(control), len(offer)
        y0, y1 = control.count("1"), offer.count("1")
        m0, m1 = control.count(""), offer.count("")
        size = n0 + n1
        weight = F(size, total)
        low += weight * (F(y1, n1) - F(y0 + m0, n0))
        high += weight * (F(y1 + m1, n1) - F(y0, n0))
        variance += weight**2 * F(size, 4*(size-1)) * (F(1, n0)+F(1, n1))
        for key, value in zip(("n0", "n1", "y0", "y1", "m0", "m1"), (n0, n1, y0, y1, m0, m1)):
            result[f"college/{college}/{key}"] = value
    radius = sqrt(20 * variance)
    result.update({"design/completion_lower": float(low), "design/completion_upper": float(high),
                   "design/variance_bound": float(variance), "design/radius": radius,
                   "design/confidence_lower": max(-1, float(low)-radius),
                   "design/confidence_upper": min(1, float(high)+radius)})
    return result


def fixture(rows):
    groups = [[r for r in rows if r["college_id"] == c] for c in ("A", "B")]
    legal = list(product(*(combinations(range(len(group)), 2) for group in groups)))
    result = {"toy/schedules": len(legal)}
    for outcome in (0, 1):
        ys = [[int(row["outcome"]) if row["outcome"] else outcome for row in group] for group in groups]
        actual = tuple(tuple(i for i, row in enumerate(group) if row["offer"] == "1") for group in groups)

        def difference(schedule):
            block_differences = []
            for values, offer in zip(ys, schedule):
                treated = sum(values[i] for i in offer)
                block_differences.append(F(2*treated - sum(values), 2))
            return sum(block_differences)/2

        observed = difference(actual)
        hits = sum(abs(difference(schedule)) >= abs(observed) for schedule in legal)
        tag = f"toy/if{outcome}/"
        result.update({tag+"stat": float(observed), tag+"extremes": hits, tag+"p": hits/len(legal)})
    result["toy/max_p"] = max(result["toy/if0/p"], result["toy/if1/p"])
    return result


if __name__ == "__main__":
    run(analyze, fixture)
