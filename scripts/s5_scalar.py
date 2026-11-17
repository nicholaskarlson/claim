"""Standard-library Python route, using centered cross-products of keyed means."""
import csv
import math
import sys

with open(sys.argv[1], newline="") as stream:
    records = list(csv.DictReader(stream))
pairs = []
for row in records:
    scales = [[row[f"{name}{i}"] for i in range(1, 6)] for name in ("st", "wb")]
    if all(all(items) for items in scales):
        stress, wellbeing = (sum(int(x) if i != 3 else 6 - int(x)
                                 for i, x in enumerate(items)) for items in scales)
        pairs.append((row["student_id"], stress, wellbeing))
x = [row[1] / 5 for row in pairs]
y = [row[2] / 5 for row in pairs]
dx = [v - math.fsum(x) / len(x) for v in x]
dy = [v - math.fsum(y) / len(y) for v in y]
r = math.fsum(a*b for a, b in zip(dx, dy)) / math.sqrt(
    math.fsum(a*a for a in dx) * math.fsum(b*b for b in dy))
print(f"{len(records)},{len({row['college_id'] for row in records})},{len(pairs)},{r:.17g}")
for row in pairs:
    print(",".join(map(str, row)))
