"""Scalar scores and exact tied-pair counts for frozen forecasts."""
from collections import Counter, defaultdict
import csv
from math import fsum, log, log1p
from pathlib import Path
import sys

from part1_io import read


def score(rows):
    y = [int(row["outcome"]) for row in rows]
    n, events = len(y), sum(y)
    result = {"n": n, "events": events}
    for key in ("forecast", "baseline"):
        p = [float(row[key]) for row in rows]
        groups = defaultdict(Counter)
        for probability, outcome in zip(p,y):
            groups[probability][outcome]+=1
        below = pairs2 = 0
        for probability in sorted(groups):
            counts = groups[probability]
            pairs2 += counts[1]*(2*below+counts[0])
            below += counts[0]
        clipped = [min(1-1e-12,max(1e-12,value)) for value in p]
        losses = (-log(value) if outcome else -log1p(-value) for value,outcome in zip(clipped,y))
        result.update({key+"/mean": fsum(p)/n, key+"/brier": fsum((a-b)**2 for a,b in zip(p,y))/n,
                       key+"/auc_pairs2": pairs2,key+"/auc":pairs2/(2*events*(n-events)),
                       key+"/log_loss": fsum(losses)/n})
    bins = [[] for _ in range(5)]
    for row,outcome in zip(rows,y):
        p = float(row["forecast"])
        i = sum(p >= edge/5 for edge in range(1,5))
        bins[i].append((p,outcome))
    for i,group in enumerate(bins,1):
        result[f"bin/{i}/n"] = len(group)
        result[f"bin/{i}/events"] = sum(y for _,y in group)
        if group:
            result[f"bin/{i}/mean"] = fsum(p for p,_ in group)/len(group)
    return result


if __name__ == "__main__":
    rows=read(Path(sys.argv[1]))
    writer=csv.writer(sys.stdout,lineterminator="\n")
    for group in ("all",*sorted({row["group"] for row in rows})):
        current=rows if group=="all" else [row for row in rows if row["group"]==group]
        writer.writerows((f"{group}/{key}",value) for key,value in sorted(score(current).items()))
