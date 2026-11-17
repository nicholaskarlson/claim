"""Select only the primary outcome and released forecasts for scoring."""
import csv
import hashlib
import io
import json

PREFIX = "predict-main/open-materials/predictive-reasoning-with-statistics/"
PROTOCOL = PREFIX + "model-specs/sealed_envelope.json"
DEPLOYMENT = PREFIX + "source/sealed-envelope/deployment_c2.csv"
PREDICTIONS = PREFIX + "expected-results/sealed_predictions.csv"
FIELDS = ["group", "outcome", "forecast", "baseline"]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def project(archive, out):
    plan = json.loads(archive.read(PROTOCOL))
    pool = {college: g for g, colleges in plan["college_groups"].items() for college in colleges}
    events, size = (plan["comparator"][k] for k in ("events", "n"))
    constant = events / size
    seen = set()
    codes = {"withdrawal": ("1", "0"), "transfer": ("0", "1"), "none": ("0", "0")}
    transfers = 0
    with archive.open(DEPLOYMENT) as data, archive.open(PREDICTIONS) as preds:
        rows = csv.DictReader(io.TextIOWrapper(data, newline=""))
        predictions = csv.DictReader(io.TextIOWrapper(preds, newline=""))
        writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row, p in zip(rows, predictions, strict=True):
            sid = row["student_id"]
            college = row["college_id"]
            exit_type = row["exit_type"]
            labels = (row["withdrawn_12"], row["transferred_12"])
            if (sid in seen or sid != p["student_id"] or college != p["college_id"]
                    or pool[college] != p["population"] or labels != codes.get(exit_type)):
                raise ValueError("Frozen forecast, roster or primary label disagree")
            if abs(float(p["comparator_probability"]) - constant) > 2e-15:
                raise ValueError("Development comparator changed")
            seen.add(sid)
            transfers += labels[1] == "1"
            writer.writerow(dict(zip(FIELDS, (pool[college], labels[0], p["frame_probability"],
                                              p["comparator_probability"]))))
    if len(seen) != plan["expected_rows"]:
        raise ValueError("Deployment inventory changed")
    return transfers
