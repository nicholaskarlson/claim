"""Validate frozen source, three independent routes, exact fixture and refusal."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from project_baseline import FIELDS, project

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    require(reader.fieldnames == FIELDS, "Baseline columns changed")
    identities = set()
    for row in reader:
        require(None not in row and all(v is not None for v in row.values()), "Malformed row")
        identity = row["student_id"]
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", identity)), "Invalid ID")
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", row["college_id"])), "Invalid college")
        require(identity not in identities, "Duplicate student ID")
        identities.add(identity)
        require(all(row[k] in ("", "1", "2", "3", "4", "5") for k in FIELDS[2:]), "Invalid item")
    require(bool(identities), "Empty input")


def compare(path, rscript, expected, tolerance):
    validate(path.read_bytes())
    routes = {
        "numpy": [sys.executable, ROOT/"scripts/s5_numpy.py"],
        "standard-library Python": [sys.executable, ROOT/"scripts/s5_scalar.py"],
        "base R": [rscript, ROOT/"scripts/s5_base.R"],
    }
    reference = None
    values = {}
    for name, command in routes.items():
        lines = subprocess.check_output([*command, path], text=True, timeout=30).splitlines()
        n, g, pairs, r = lines[0].split(",")
        counts = dict(zip(("baseline", "colleges", "paired"), map(int, (n, g, pairs))))
        sums = [(i, int(x), int(y)) for i, x, y in csv.reader(lines[1:])]
        require(counts == {k: expected[k] for k in counts} and len(sums) == counts["paired"],
                f"{name}: wrong count or row inventory")
        require(math.isclose(float(r), expected["r"], rel_tol=0, abs_tol=tolerance),
                f"{name}: correlation disagrees with independent target")
        require(reference is None or sums == reference, f"{name}: keyed pairs differ")
        reference = sums
        values[name] = float(r)
    require(max(values.values()) - min(values.values()) <= tolerance, "Route disagreement")
    return reference, values


def render_tokens(value, expected):
    return {"S5_BASE": f"{expected['baseline']:,}", "S5_COLLEGES": f"{expected['colleges']:,}",
            "S5_N": f"{expected['paired']:,}", "S5_R": f"{value:.3f}".replace("-", "−")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--book10-archive", type=Path)
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args()
    rscript = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(rscript, "Actual base R is required. Install Rscript or set CLAIM_RSCRIPT.")
    fixture = ROOT/"companion-src/fixture.csv"
    if not fixture.is_file():
        fixture = ROOT/"fixtures/exact.csv"
    fixture_expected = {"baseline": 4, "colleges": 2, "paired": 3, "r": -1.0}
    exact, fixture_values = compare(fixture, rscript, fixture_expected, 1e-12)
    require(exact == [("A", 5, 15), ("B", 10, 10), ("C", 15, 5)], "Exact keyed sums differ")
    raw = fixture.read_bytes()
    try:
        validate(raw + raw.splitlines(keepends=True)[1])
    except ValueError as error:
        require(str(error) == "Duplicate student ID", f"Wrong refusal: {error}")
    else:
        raise ValueError("A duplicate student should have been refused")
    if args.fixture_only:
        print("BOOK11_FIXTURE_OK routes=3 duplicate_refused=true")
        return
    require(args.out is not None, "--out is required for the full check")
    config = ROOT/"config/s5.json"
    spec = json.loads(config.read_text())
    data = ROOT/"private/inputs/baseline-items.csv"
    require(sha(data) == spec["projection_sha256"], "Frozen baseline projection changed")
    for key, member in (
        ("upstream_contract_sha256", "book10-unit03-contract.json"),
        ("upstream_rerun_receipt_sha256", "book10-unit03-rerun.json"),
    ):
        require(sha(ROOT/"private/evidence"/member) == spec[key], f"Pinned evidence changed: {member}")
    if args.book10_archive:
        require(sha(args.book10_archive) == spec["upstream_archive_sha256"], "Wrong Book 10 archive")
        with zipfile.ZipFile(args.book10_archive) as archive:
            require(archive.comment.decode().strip() == spec["upstream_commit"], "Wrong upstream commit")
            member = archive.read(spec["upstream_member"])
        require(hashlib.sha256(member).hexdigest() == spec["upstream_member_sha256"], "Wrong source member")
        require(project(member) == data.read_bytes(), "Projection does not match accepted upstream bytes")
    pairs, values = compare(data, rscript, spec["expected"], spec["absolute_tolerance"])
    printed = render_tokens(values["numpy"], spec["expected"])
    require(printed == spec["print"] and all(render_tokens(r, spec["expected"]) == printed
                                              for r in values.values()), "Printed digits disagree")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"contract": spec["id"], "contract_sha256": sha(config), "upstream_commit": spec["upstream_commit"],
               "baseline_projection_sha256": sha(data), "projection_rebuilt_from_archive": bool(args.book10_archive),
               "counts": {k: spec["expected"][k] for k in ("baseline", "colleges", "paired")},
               "raw_r_by_route": values, "printed": printed,
               "exact_pair_agreement": len(pairs), "fixture_r_by_route": fixture_values,
               "duplicate_refused": True, "python": sys.version.split()[0],
               "numpy": subprocess.check_output([sys.executable, "-c", "import numpy; print(numpy.__version__)"],
                                                text=True, timeout=30).strip(),
               "r": subprocess.check_output([rscript, "--version"], text=True, timeout=30,
                                            stderr=subprocess.STDOUT).splitlines()[0]}
    args.out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(f"BOOK11_S5_OK routes=3 paired={len(pairs)} r={printed['S5_R']}")


if __name__ == "__main__":
    main()
