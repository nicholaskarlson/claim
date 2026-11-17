"""Verify the randomized roster, completion bounds and exact assignment fixture."""
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
import zipfile

from check_observation import compare, validate_registry
from check_s5 import ROOT, require, sha
from part1_io import read

ROUTES = {"numpy": "numpy", "standard-library Python": "stdlib", "base R": "base_r"}
FIXTURE = ROOT/"fixtures/design"


def read_json(path):
    return json.loads(path.read_text())


def calculate(command, mode, *sources):
    text = subprocess.check_output([*command, mode, *sources], text=True, timeout=30)
    rows = list(csv.reader(io.StringIO(text)))
    values = {key: float(value) for key, value in rows}
    require(len(values) == len(rows), "Repeated design result key")
    return values


def verify_fixture(engines):
    path = FIXTURE/"one-unknown.csv"
    rows = read(path)
    require([r["student_id"] for r in rows if r["outcome"] == ""] == ["B4"],
            "Fixture must preserve the one unknown outcome")
    require(len({r["student_id"] for r in rows}) == len(rows) == 8 and
            all(r["outcome"] in {"0", "1", ""} for r in rows), "Invalid fixture label or identity")
    require(set(r["college_id"] for r in rows) == {"A", "B"}, "Fixture colleges changed")
    for college in ("A","B"):
        offers = sorted(r["offer"] for r in rows if r["college_id"] == college)
        require(offers == ["0", "0", "1", "1"], "Fixture assignments differ")
    expected = read_json(FIXTURE/"expected.json")
    for route, command in engines.items():
        compare(expected, calculate(command, "fixture", path), 1e-12, route)
    return expected


def check_archive(archive_path, prior):
    require(sha(archive_path) == prior["archive_sha256"], "Wrong Book 9 archive")
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.comment.decode().strip() == prior["book9_commit"], "Wrong Book 9 snapshot commit")
        for name, digest in prior["source_members"].items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest, f"Changed Book 9 member: {name}")


def reconcile(raw, upstream, tolerance, alpha):
    colleges = sorted({key.split("/")[1] for key in raw if key.startswith("college/")})
    require(raw["design/colleges"] == len(colleges) == 16, "College inventory changed")
    for c in colleges:
        n0, n1 = (raw[f"college/{c}/n{z}"] for z in (0, 1))
        require(min(n0, n1) >= 1 and abs(n0-n1) <= 1, f"{c}: unsupported conditional allocation")
    for z in (0,1):
        n, y, m = (sum(raw[f"college/{c}/{key}{z}"] for c in colleges) for key in ("n","y","m"))
        require((n,n-m,m,y) == tuple(upstream[f"arm/{z}/{key}"] for key in ("N","known","unknown","w")),
                f"Arm {z} roster or label counts differ from Book 9")
    require(raw["design/n"] == upstream["arm/0/N"] + upstream["arm/1/N"], "Roster size changed")
    radius = raw["design/radius"]
    lo, hi = raw["design/completion_lower"], raw["design/completion_upper"]
    require(lo <= hi and math.isclose(radius**2*alpha,raw["design/variance_bound"],abs_tol=tolerance),
            "Invalid completion range or design radius")
    require(math.isclose(max(-1,lo-radius),raw["design/confidence_lower"],abs_tol=tolerance)
            and math.isclose(min(1,hi+radius),raw["design/confidence_upper"],abs_tol=tolerance),
            "Wrong conservative confidence envelope")


def tokens(raw, fixture, upstream):
    def pp(value):
        return f"{100*value:+.2f}".replace("-", "−")

    def range_pp(lo, hi):
        return f"{pp(lo)} to {pp(hi)}"

    def outward(value, rounding):
        return rounding(value*10000)/10000

    prefix = "standardized/adjusted/all/hc1/rd/"
    return {
        "D6_N": f"{int(raw['design/n']):,}",
        "D6_BLOCKS": str(int(raw["design/colleges"])),
        "D6_COMPLETION": range_pp(raw["design/completion_lower"],raw["design/completion_upper"]),
        "D6_RADIUS": f"{100*raw['design/radius']:.2f}",
        "D6_INTERVAL": range_pp(outward(raw["design/confidence_lower"], math.floor),
                                 outward(raw["design/confidence_upper"], math.ceil)),
        "D6_B9_ESTIMATE": pp(upstream[prefix+"estimate"]),
        "D6_B9_INTERVAL": range_pp(upstream[prefix+"lower"],upstream[prefix+"upper"]),
        "D6_TOY_SCHEDULES": str(int(fixture["toy/schedules"])),
        "D6_TOY_STAT_ZERO": pp(fixture["toy/if0/stat"]),
        "D6_TOY_STAT_ONE": pp(fixture["toy/if1/stat"]),
        "D6_TOY_TAIL_ZERO": f"{int(fixture['toy/if0/extremes'])}/{int(fixture['toy/schedules'])}",
        "D6_TOY_TAIL_ONE": f"{int(fixture['toy/if1/extremes'])}/{int(fixture['toy/schedules'])}",
        "D6_TOY_P_ZERO": f"{fixture['toy/if0/p']:.4f}",
        "D6_TOY_P_ONE": f"{fixture['toy/if1/p']:.4f}",
        "D6_TOY_MAX_P": f"{fixture['toy/max_p']:.4f}",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--book9-archive", type=Path)
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args()
    r = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r, "Install actual base R or set CLAIM_RSCRIPT")
    script = ROOT/"scripts"
    engines = {"numpy": [sys.executable,script/"design_numpy.py"],
               "standard-library Python": [sys.executable,script/"design_scalar.py"],
               "base R": [r,script/"design_base.R"]}
    fixture = verify_fixture(engines)
    if args.fixture_only:
        print("BOOK11_DESIGN_FIXTURE_OK routes=3 legal_allocations=36 completions=2")
        return

    require(args.out, "--out is required for the full check")
    config_path = ROOT/"config/design.json"
    spec = read_json(config_path)
    for name, digest in spec["pinned"].items():
        require(sha(ROOT/name) == digest, f"Changed pinned Chapter 6 source: {name}")
    prior_path = ROOT/"private/evidence/book9-design-rerun.json"
    prior = read_json(prior_path)
    require(prior["summary_keys"] == 621 and prior["unknown_labels_preserved"] == 11 and
            set(prior["routes"]) == set(ROUTES.values()), "Incomplete Book 9 Unit 4 audit")
    if args.book9_archive:
        check_archive(args.book9_archive, prior)
    registry = ROOT/"private/inputs/observed-registry.csv"
    assigned = ROOT/"private/inputs/baseline-offer.csv"
    validate_registry(registry)
    routes, upstream, prints = {}, {}, {}
    for name, command in engines.items():
        raw = calculate(command, "registry", assigned, registry)
        reference = prior["routes"][ROUTES[name]]["selected"]
        reconcile(raw, reference, spec["tolerance"], spec["confidence_alpha"])
        routes[name] = raw
        upstream[name] = reference
        prints[name] = tokens(raw, fixture, reference)
        compare(routes["numpy"], raw, spec["tolerance"], name)
        compare(upstream["numpy"], reference, spec["tolerance"], name+" Book 9 rerun")
        require(prints[name] == prints["numpy"], f"{name}: printed design results differ")

    result = {"contract": spec["id"], "contract_sha256": sha(config_path),
              "target": spec["target"], "assignment_law": spec["conditional_assignment_law"],
              "assumptions": spec["assumptions"], "book9_commit": prior["book9_commit"],
              "book9_rerun_sha256": sha(prior_path), "book9_archive_checked": bool(args.book9_archive),
              "registry_values_by_route": routes, "book9_model_values_by_route": upstream,
              "fixture": fixture, "printed": prints["numpy"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("BOOK11_DESIGN_OK routes=3 colleges="+prints["numpy"]["D6_BLOCKS"]+
          " interval="+prints["numpy"]["D6_INTERVAL"]+" conditional_design=true")


if __name__ == "__main__":
    main()
