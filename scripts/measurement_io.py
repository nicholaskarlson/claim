"""Load the frozen score inputs and derive the month-three projection."""
import csv
import io
import re

ITEMS = [f"st{i}" for i in range(1, 6)]
FOLLOWUP = ["student_id", "responded", *ITEMS]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def project_month3(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    require(reader.fieldnames == ["student_id", "wave_month", "responded", "mode", "form",
                                  "wb1", "wb2", "wb3", "wb4", "wb5", *ITEMS, "intention_leave"],
            "Book 10 follow-up columns differ")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FOLLOWUP, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        require(None not in row and None not in row.values(), "Malformed Book 10 follow-up row")
        if row["wave_month"] == "3":
            writer.writerow({key: row[key] for key in FOLLOWUP})
    return stream.getvalue().encode()


def validate_month3(raw, identities):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    require(reader.fieldnames == FOLLOWUP, "Month-three columns differ")
    seen = set()
    for row in reader:
        require(None not in row and None not in row.values(), "Malformed month-three row")
        identity = row["student_id"]
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", identity)), "Invalid month-three ID")
        require(identity not in seen, "Duplicate month-three ID")
        seen.add(identity)
        require(row["responded"] in {"0", "1"}, "Invalid month-three response flag")
        require(all(row[key] in ("", "1", "2", "3", "4", "5") for key in ITEMS), "Invalid stress item")
        require(row["responded"] == "1" or all(not row[key] for key in ITEMS),
                "Nonresponse row contains stress answers")
    require(seen == identities, "Month-three roster differs from baseline")
