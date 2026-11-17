"""Copy only the ID, college and ten item fields from the pinned upstream member."""
import csv
import io

FIELDS = ["student_id", "college_id", *(f"{scale}{i}" for scale in ("st", "wb") for i in range(1, 6))]


def project(data):
    records = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in records:
        writer.writerow({key: row[key] for key in FIELDS})
    return buffer.getvalue().encode("utf-8")
