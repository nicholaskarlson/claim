"""Check the invitation roster, the exact weights fixture and pinned Book 8 results."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from check_part1 import validate
from check_s5 import ROOT, require, sha
from part1_io import read

FIXTURE = ROOT / "fixtures/observation"
UPSTREAM_ROUTES = {"numpy": "numpy", "standard-library Python": "stdlib", "base R": "base_r"}
GROUPS = {"all": "ALL", "respondents": "RESP", "nonrespondents": "NON"}


def read_json(path):
    return json.loads(path.read_text())


def commands(r):
    source = ROOT / "scripts"
    return {"numpy": [sys.executable, source/"observation_numpy.py"],
            "standard-library Python": [sys.executable, source/"observation_scalar.py"],
            "base R": [r, source/"observation_base.R"]}


def route(command, mode, source):
    raw = subprocess.check_output([*command, mode, source], text=True, timeout=30)
    rows = list(csv.reader(io.StringIO(raw)))
    result = {k: float(v) for k, v in rows}
    require(len(rows) == len(result), "Repeated observation summary key")
    return result


def compare(reference, result, tolerance, name):
    require(reference.keys() == result.keys(), f"{name}: observation keys differ")
    for key, value in result.items():
        require(math.isclose(value, reference[key], rel_tol=0, abs_tol=tolerance),
                f"{name}: {key} differs")


def verify_fixture(engines):
    source = FIXTURE/"two-strata.csv"
    expected = read_json(FIXTURE/"expected.json")
    rows = read(source)
    require([r["stratum"] for r in rows] == ["A", "B"], "Wrong fixture strata")
    for row in rows:
        events, known, eligible = (int(row[k]) for k in ("withdrawals", "known", "eligible"))
        require(0 <= events <= known <= eligible and eligible > 0, "Invalid fixture counts")
    with tempfile.TemporaryDirectory(prefix="claim-no-coverage-") as directory:
        invalid = Path(directory)/"no-known-in-B.csv"
        invalid.write_text("stratum,eligible,known,withdrawals\nA,10,8,1\nB,10,0,0\n")
        for name, command in engines.items():
            compare(expected, route(command, "fixture", source), 0, name)
            process = subprocess.run([*command, "fixture", invalid], capture_output=True, text=True, timeout=30)
            require(process.returncode and "A target stratum has no known outcomes" in process.stderr,
                    f"{name}: zero coverage must refuse weighting")
    return expected


def check_archive(path, reruns):
    require(sha(path) == reruns["public_archive_sha256"], "Wrong Book 8 public snapshot archive")
    with zipfile.ZipFile(path) as archive:
        require(archive.comment.decode().strip() == reruns["public_snapshot_commit"], "Wrong Book 8 commit")
        for name, digest in reruns["source_members"].items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest, f"Changed Book 8 member: {name}")


def validate_registry(registry_path):
    registry = read(registry_path)
    assignments = read(ROOT/"private/inputs/baseline-offer.csv")
    validate(assignments, registry)
    require({r["student_id"] for r in assignments} ==
            {r["student_id"] for r in registry if r["responded_baseline"] == "1"},
            "The registry respondent roster differs from baseline")
    for row in registry:
        if row["responded_baseline"] == "0":
            require(row["offer"] == "0" and row["outcome_known"] == "1"
                    and row["observation_source"] == "v1.1.0_admin_no_offer",
                    "The nonrespondent administrative observation rule differs")
        else:
            require(row["observation_source"] == "v1.0.0_respondent_registry",
                    "The respondent registry source differs")


def reconcile(result, unit08, unit10, tolerance, name):
    values8 = unit08["selected_values"]
    values10 = unit10["selected_values"]
    require(unit08["rows"]["status"] == unit10["rows"]["status"] == "success"
            and unit10["rows"]["raw_risk_reconstruction"], f"{name}: upstream row checks missing")
    for a, b in (("eligible","n"), ("withdrawals","withdrawals"), ("unknown","unknown")):
        require(result["all/"+a] == values10["pooled/"+b] and
                result["nonrespondents/"+a] == values10["nonrespondents/"+b] and
                result["respondents/"+a] == values10["control/"+b] + values10["offered/"+b],
                f"{name}: roster and Book 8 counts differ for {a}")
    require(result["all/transfers"] == values10["pooled/transfers"] and
            result["all/eligible"] == unit08["rows"]["people_rows"] == unit10["rows"]["person_rows"] and
            result["all/unknown"] == unit10["rows"]["unknown_outcomes_preserved"] and
            result["respondents/eligible"] == values8["observed/returned"] and
            values8["observed/complete"] == unit08["rows"]["complete_score_rows"],
            f"{name}: upstream scope differs")
    for bound in ("lower", "upper"):
        require(math.isclose(result["all/"+bound], values10["pooled/"+bound],
                             rel_tol=0, abs_tol=tolerance), f"{name}: bound differs")
    aj = values10["standardized/month/12/withdrawal"]
    require(result["all/lower"] <= aj <= result["all/upper"], "Book 8 AJ candidate outside support")
    return {**values8, "standardized_withdrawal": aj}


def print_tokens(registry, fixture, prior):
    result = {}
    def count(value):
        require(float(value).is_integer(), "Noninteger roster count")
        return f"{int(value):,}"

    for key, tag in GROUPS.items():
        for metric, ending in (("eligible", "N"), ("known", "KNOWN"), ("withdrawals", "EVENTS"), ("unknown", "UNKNOWN")):
            result[f"O5_{tag}_{ending}"] = count(registry[f"{key}/{metric}"])
        result[f"O5_{tag}_RATE"] = f"{registry[f'{key}/known_rate']:.2%}"
    result.update({
        "O5_TRANSFERS": count(registry["all/transfers"]),
        "O5_BOUNDS": f"{registry['all/lower']:.2%} to {registry['all/upper']:.2%}",
        "O5_AJ": f"{prior['standardized_withdrawal']:.2%}",
        "O5_OLD_BLEND": f"{registry['audit/old_response_blend']:.1%}",
        "O5_STRESS_COMPLETE": count(prior["observed/complete"]),
        "O5_STRESS_OBS": f"{prior['observed/complete_mean']:.3f}",
        "O5_STRESS_WEIGHTED": f"{prior['estimate/poststratified_mean']:.3f}",
        "O5_FIX_OBS": f"{fixture['fixture/known_rate']:.2%}",
        "O5_FIX_WEIGHTED": f"{fixture['fixture/weighted']:.2%}",
        "O5_FIX_BOUNDS": f"{fixture['fixture/lower']:.0%} to {fixture['fixture/upper']:.0%}",
        "O5_FIX_A_WEIGHT": f"{fixture['fixture/weight_A']:.2f}",
        "O5_FIX_B_WEIGHT": count(fixture["fixture/weight_B"]),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--book8-archive", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    r = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r, "Install actual base R or set CLAIM_RSCRIPT")
    engines = commands(r)
    fixture = verify_fixture(engines)
    if args.fixture_only:
        print("BOOK11_OBSERVATION_FIXTURE_OK routes=3 zero_coverage_refused=true")
        return

    require(args.out, "--out is required for the full check")
    contract_path = ROOT/"config/observation.json"
    spec = read_json(contract_path)
    for name, digest in spec["pinned"].items():
        require(sha(ROOT/name) == digest, f"Changed pinned Chapter 5 source: {name}")
    reruns_path = ROOT/spec["upstream_rerun_receipt"]
    reruns = read_json(reruns_path)
    unit08, unit10 = (read_json(ROOT/f"private/evidence/book8-unit{unit}-contract.json") for unit in ("08","10"))
    require(unit08["target_id"] == "B8-T01" and unit10["target_id"] == "B8-T03",
            "Book 8 stress and withdrawal targets differ from admitted scope")
    if args.book8_archive:
        check_archive(args.book8_archive, reruns)
    path = ROOT/"private/inputs/observed-registry.csv"
    validate_registry(path)
    routes, upstream, rendered = {}, {}, {}
    for name, command in engines.items():
        raw = route(command, "registry", path)
        routes[name] = raw
        key = UPSTREAM_ROUTES[name]
        prior = reconcile(raw, reruns["units"]["unit08"]["routes"][key],
                          reruns["units"]["unit10"]["routes"][key], spec["tolerance"], name)
        upstream[name] = prior
        rendered[name] = print_tokens(raw, fixture, prior)
        compare(routes["numpy"], raw, spec["tolerance"], name)
        compare(upstream["numpy"], prior, spec["tolerance"], name)
        require(rendered["numpy"] == rendered[name], f"{name}: printed values differ")
    data = {"contract": spec["id"], "contract_sha256": sha(contract_path), "frame": spec["frame"],
            "book8_snapshot_commit": reruns["public_snapshot_commit"], "book8_archive_checked": bool(args.book8_archive),
            "upstream_rerun_sha256": sha(reruns_path), "registry_values_by_route": routes,
            "book8_rerun_values_by_route": upstream, "fixture": fixture, "zero_coverage_refused": True,
            "printed": rendered["numpy"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n")
    print("BOOK11_OBSERVATION_OK routes=3 invitees="+rendered["numpy"]["O5_ALL_N"]+
          " unknown="+rendered["numpy"]["O5_ALL_UNKNOWN"]+" book8_units=08,10")


if __name__ == "__main__":
    main()
