"""Project pinned Book 9 ordinary GPA to alias-only college-by-arm moments."""
import csv
from decimal import Decimal
import io

from check_s5 import require

PREFIX = "nekpress-model-based-reasoning-with-statistics-private-main/"
BASELINE = "ordinary/data/anchor_baseline.csv"
REGISTRY = "ordinary/data/anchor_registry.csv"
FIELDS = ("college", "assigned_no", "assigned_offer", "known_no", "known_offer",
          "sum_no", "sum_offer", "ss_no", "ss_offer")


def projection(baseline_bytes, registry_bytes):
    baseline = list(csv.DictReader(io.StringIO(baseline_bytes.decode("utf-8"))))
    grades = {}
    for row in csv.DictReader(io.StringIO(registry_bytes.decode("utf-8"))):
        identity = row["student_id"]
        require(identity not in grades, "Repeated source grade key")
        grades[identity] = row["gpa12"]
    keys = {row["student_id"] for row in baseline}
    require(len(keys) == len(baseline) and keys == grades.keys(), "Book 9 GPA roster differs")
    college_names = sorted({row["college_id"] for row in baseline})
    require(len(college_names) == 16, "Unexpected Book 9 college inventory")
    moments = {(college,arm):[0,0,0,0] for college in college_names for arm in ("0","1")}
    for row in baseline:
        count = moments[(row["college_id"],row["offer"])]
        count[0] += 1
        raw = grades[row["student_id"]]
        if raw == "":
            continue
        cents = Decimal(raw) * 100
        require(cents.is_finite() and 0 <= cents <= 400 and cents == int(cents), "Unexpected GPA precision or range")
        grade = int(cents)
        count[1] += 1
        count[2] += grade
        count[3] += grade**2
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer,lineterminator="\n")
    writer.writerow(FIELDS)
    for i,college in enumerate(college_names):
        no, offer = (moments[college,arm] for arm in ("0","1"))
        interleaved = [value for pair in zip(no,offer) for value in pair]
        writer.writerow([chr(ord("A")+i), *interleaved])
    return buffer.getvalue().encode("utf-8")
