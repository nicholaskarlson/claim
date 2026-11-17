"""Check the normal-reference margin exercise and the pinned Book 9 model."""
import argparse
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from check_s5 import ROOT, require, sha

FIXTURE = ROOT/"fixtures/precision"
FIELDS = ("case", "estimate_pp", "se_pp", "margin_pp")
ROUTES = {"numpy":"precision_numpy.py", "stdlib":"precision_scalar.py", "base_r":"precision_base.R"}
FLAGS = ("different", "equivalent", "benefit_beyond_margin")
MODEL = "standardized/adjusted/all/hc1/rd/"


def load(path):
    return json.loads(path.read_text())


def fixture_rows(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        require(tuple(reader.fieldnames) == FIELDS, "Wrong precision fixture schema")
        rows = list(reader)
    require(len(rows) == 4 and len({row["case"] for row in rows}) == len(rows), "Wrong fixture cases")
    for row in rows:
        estimate, se, margin = (float(row[key]) for key in FIELDS[1:])
        require(all(map(math.isfinite, (estimate,se,margin))) and se > 0 and margin > 0,
                "A normal comparison requires finite values, a positive standard error and a positive margin")
    return rows


def calculate(command, path):
    raw = subprocess.check_output([*command,path], text=True, timeout=30)
    pairs = list(csv.reader(io.StringIO(raw)))
    values = {key:float(value) for key,value in pairs}
    require(len(values) == len(pairs), "Duplicate precision result")
    return values


def compare(reference, values, tolerance):
    require(reference.keys() == values.keys(), "Precision result inventory differs")
    require(all(math.isclose(reference[key], value, rel_tol=0, abs_tol=tolerance)
                for key,value in values.items()), "Precision results disagree")


def decisions(values, case):
    result = [values[f"{case}/{key}"] for key in FLAGS]
    require(all(flag in (0,1) for flag in result), "Invalid precision decision")
    return list(map(int,result))


def audit_fixture(engines):
    path = FIXTURE/"normal.csv"
    rows = fixture_rows(path)
    expected = load(FIXTURE/"expected-decisions.json")
    require(set(expected) == {row["case"] for row in rows}, "Wrong fixture decision inventory")
    runs = {route:calculate(command,path) for route,command in engines.items()}
    for values in runs.values():
        compare(runs["numpy"],values,2e-14)
        require(all(decisions(values,case) == flags for case,flags in expected.items()),
                "Incorrect difference, equivalence or minimum-benefit decision")
        require(values["undecided/power_zero"] == 0 and values["both/power_zero"] > .99,
                "Wrong model-based power limits")
    return runs["numpy"], rows


def compare_model(engines, prior, z, margin, tolerance):
    values = {}
    with tempfile.TemporaryDirectory(prefix="claim-precision-") as temp:
        path = Path(temp)/"book9-wald.csv"
        for route,command in engines.items():
            source = prior["routes"][route]["selected"]
            estimate, lower, upper = (100*source[MODEL+key] for key in ("estimate","lower","upper"))
            require(math.isclose(lower+upper,2*estimate,rel_tol=0,abs_tol=tolerance) and lower < upper,
                    "Book 9 reported interval does not identify a single symmetric Wald SE")
            se = (upper-lower)/(2*z)
            path.write_text(",".join(FIELDS)+f"\nmodel,{estimate:.17g},{se:.17g},{margin}\n")
            result = calculate(command,path)
            compare({"model/lo95":lower,"model/hi95":upper},
                    {key:result[key] for key in ("model/lo95","model/hi95")},tolerance)
            require(decisions(result,"model") == [0,0,0], "Book 9 decisions changed")
            values[route] = result
    for result in values.values():
        compare(values["numpy"],result,tolerance)
    return values


def printed(model, fixture, margin):
    def pp(value):
        return f"{value:+.2f}".replace("-", "−")

    def interval(values, case, level):
        return f"{pp(values[f'{case}/lo{level}'])} to {pp(values[f'{case}/hi{level}'])}"

    result = {"U9_MARGIN":f"{margin:g}","U9_ESTIMATE":pp(model["model/estimate"]),
              "U9_SE":f"{model['model/se']:.2f}",
              "U9_MODEL95":interval(model,"model",95),"U9_MODEL90":interval(model,"model",90),
              "U9_P_DIFF":f"{model['model/p_difference']:.3f}",
              "U9_P_LOWER":f"{model['model/p_lower']:.3f}","U9_P_UPPER":f"{model['model/p_upper']:.3f}",
              "U9_P_TOST":f"{model['model/p_equivalence']:.3f}",
              "U9_EQ_POWER":f"{100*fixture['equivalent/power_zero']:.1f}%"}
    for case in ("different","equivalent","both","undecided"):
        for level in (95,90):
            result[f"U9_{case.upper()}{level}"] = interval(fixture,case,level)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args = parser.parse_args()
    r = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r,"Install actual base R or set CLAIM_RSCRIPT")
    engines = {route:[r if route=="base_r" else sys.executable,ROOT/"scripts"/name]
               for route,name in ROUTES.items()}
    fixture, rows = audit_fixture(engines)
    if args.fixture_only:
        print("BOOK11_PRECISION_FIXTURE_OK routes=3 decisions=4")
        return
    require(args.out,"--out is required")
    spec_path = ROOT/"config/precision.json"
    spec = load(spec_path)
    for name,digest in spec["pinned"].items():
        require(sha(ROOT/name)==digest,f"Changed precision source: {name}")
    margin = spec["teaching_margin_pp"]
    require(all(float(row["margin_pp"]) == margin for row in rows) and
            spec["two_sided_difference_alpha"] == spec["one_sided_equivalence_alpha"] == .05,
            "Declared margin or alpha differs from computation")
    prior_path = ROOT/"private/evidence/book9-design-rerun.json"
    prior = load(prior_path)
    contract = load(ROOT/"private/evidence/book9-unit04-contract.json")
    z = contract["settings"]["z"]
    values = compare_model(engines,prior,z,margin,spec["absolute_tolerance"])
    tokens = printed(values["numpy"],fixture,margin)
    require(all(printed(result,fixture,margin) == tokens for result in values.values()),
            "Printed precision results disagree")
    result = {"contract":spec["id"],"contract_sha256":sha(spec_path),"book9_commit":prior["book9_commit"],
              "book9_rerun_sha256":sha(prior_path),"scope":spec["reference"],"margin_pp":margin,
              "margin_source":spec["margin_source"],
              "model_by_route":{route:{key:value for key,value in run.items() if key != "model/power_zero"}
                                for route,run in values.items()},"fixture":fixture,"printed":tokens}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(f"BOOK11_PRECISION_OK routes=3 model_95={tokens['U9_MODEL95']} model_90={tokens['U9_MODEL90']}")


if __name__ == "__main__":
    main()
