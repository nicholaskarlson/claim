"""Verify Book 7 aggregate forecast evidence and a runnable scoring fixture."""
import argparse
from collections import Counter
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
import zipfile

from check_s5 import ROOT, require, sha
from forecast_source import FIELDS, digest, project
from part1_io import read

FIXTURE = ROOT/"fixtures/forecast"
POPS = ("all", "continuing", "previously_new", "unseen")
ROUTES = {"numpy":"numpy", "standard-library Python":"stdlib", "base R":"base_r"}


def load(path):
    return json.loads(path.read_text())


def validate(path):
    rows = read(path)
    classes = {}
    for row in rows:
        require(list(row)==FIELDS and None not in row.values(), "Forecast scoring schema differs")
        require(row["group"] and row["group"]!="all", "Invalid scoring group")
        require(row["outcome"] in {"0","1"}, "Every scoring row needs a known binary outcome")
        for key in ("forecast","baseline"):
            require(0 <= float(row[key]) <= 1, "Forecast lies outside [0,1]")
        classes.setdefault(row["group"],Counter())[row["outcome"]]+=1
    require(bool(classes) and all(len(count)==2 for count in classes.values()),
            "This scoring comparison requires both classes in each group")


def calculate(command, path):
    raw = subprocess.check_output([*command,path],text=True,timeout=45)
    rows = list(csv.reader(io.StringIO(raw)))
    values = {key:float(value) for key,value in rows}
    require(len(rows)==len(values), "Duplicate scoring output")
    return values


def compare(reference, values, tolerance, name):
    require(reference.keys()==values.keys(), f"{name}: scoring inventory changed")
    for key, value in values.items():
        if key.rsplit("/",1)[1] in {"n","events","auc_pairs2"}:
            require(value==reference[key] and value==int(value), f"{name}: exact count differs: {key}")
        else:
            require(math.isclose(value,reference[key],rel_tol=0,abs_tol=tolerance), f"{name}: {key} differs")


def fixture_check(engines):
    path=FIXTURE/"scoring.csv"
    validate(path)
    expected=load(FIXTURE/"expected.json")
    for name,command in engines.items():
        compare(expected,calculate(command,path),2e-12,name)
    with tempfile.TemporaryDirectory(prefix="forecast-missing-") as directory:
        invalid=Path(directory)/"missing.csv"
        invalid.write_text(path.read_text().replace("A,1,0.3","A,,0.3"))
        try:
            validate(invalid)
        except ValueError as exc:
            require(str(exc)=="Every scoring row needs a known binary outcome", "Wrong missing-outcome refusal")
        else:
            raise ValueError("Missing scoring label was accepted")
    return expected


def check_archive(path, prior, engines, tolerance):
    require(sha(path)==prior["archive_sha256"], "Wrong Book 7 companion snapshot")
    with tempfile.TemporaryDirectory(prefix="forecast-primary-") as directory:
        csv_path=Path(directory)/"scoring.csv"
        with zipfile.ZipFile(path) as archive, csv_path.open("w",newline="") as out:
            require(archive.comment.decode().strip()==prior["snapshot"], "Wrong Book 7 snapshot commit")
            for member, value in prior["source_members"].items():
                require(digest(archive.read(member))==value, f"Book 7 member changed: {member}")
            transfers=project(archive,out)
        require(sha(csv_path)==prior["scoring_projection_sha256"] and transfers==prior["transfers"],
                "Primary score projection differs")
        validate(csv_path)
        for name,command in engines.items():
            # Upstream re-prediction can perturb exact floating ties. Re-score released
            # probabilities against the pinned NumPy reference, which is byte-identical.
            compare(prior["routes"]["numpy"]["metrics"],calculate(command,csv_path),tolerance,name)


def verify_links(values, spec):
    total=values["all/n"]
    require(total==sum(values[g+"/n"] for g in POPS[1:]), "Later groups do not partition the cohort")
    require(values["all/events"]==sum(values[g+"/events"] for g in POPS[1:]), "Later group events disagree")
    q=spec["comparator"]["events"]/spec["comparator"]["n"]
    for group in POPS:
        n,e=values[group+"/n"],values[group+"/events"]
        require(0<e<n, "Both classes must be represented")
        require(math.isclose(q,values[group+"/baseline/mean"],abs_tol=2e-12)
                and values[group+"/baseline/auc"]==.5, "The constant comparator changed")
        require(math.isclose((e*(1-q)**2+(n-e)*q*q)/n,values[group+"/baseline/brier"],abs_tol=2e-12),
                "The constant comparator Brier score differs")
        for key, total_value in (("n",n),("events",e)):
            require(sum(values[f"{group}/bin/{i}/{key}"] for i in range(1,6))==total_value,
                    "Calibration bins do not partition the scoring rows")


def tokens(v, fixture, spec, plan, transfers):
    def n(x): return f"{int(x):,}"
    def pct(x): return f"{100*x:.2f}%"
    def metric(key, digits=4): return f"{v[key]:.{digits}f}"
    out={"P8_N":n(v["all/n"]),"P8_EVENTS":n(v["all/events"]),"P8_TRANSFERS":n(transfers),
         "P8_SITES":n(sum(map(len,plan["college_groups"].values()))),
         "P8_BASE_EVENTS":n(spec["comparator"]["events"]),"P8_BASE_N":n(spec["comparator"]["n"]),
         "P8_BASE_PROB":pct(v["all/baseline/mean"]),"P8_EVENT_FRAC":pct(v["all/events"]/v["all/n"]),
         "P8_MEAN_PROB":pct(v["all/forecast/mean"]),
         "P8_BRIER":metric("all/forecast/brier"),"P8_BASE_BRIER":metric("all/baseline/brier"),
         "P8_AUC":metric("all/forecast/auc",3),"P8_LOG":metric("all/forecast/log_loss"),
         "P8_BASE_LOG":metric("all/baseline/log_loss"),
         "P8_FIX_BRIER":f"{fixture['all/forecast/brier']:.4f}","P8_FIX_AUC":f"{fixture['all/forecast/auc']:.3f}"}
    for g,tag in (("continuing","CONT"),("previously_new","PREV"),("unseen","NEW")):
        out.update({f"P8_{tag}_N":n(v[g+"/n"]),f"P8_{tag}_SITES":n(len(plan["college_groups"][g])),
                    f"P8_{tag}_BRIER":metric(g+"/forecast/brier",4),
                    f"P8_{tag}_BASE":metric(g+"/baseline/brier",4),
                    f"P8_{tag}_AUC":metric(g+"/forecast/auc",3)})
    for i in range(1,6):
        k=f"all/bin/{i}/"
        count=v[k+"n"]
        out.update({f"P8_BIN{i}_N":n(count),f"P8_BIN{i}_P":pct(v[k+"mean"]),
                    f"P8_BIN{i}_Y":pct(v[k+"events"]/count)})
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--book7-archive",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args=parser.parse_args()
    r=os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r, "Install actual base R or set CLAIM_RSCRIPT")
    script=ROOT/"scripts"
    engines={"numpy":[sys.executable,script/"forecast_numpy.py"],
             "standard-library Python":[sys.executable,script/"forecast_scalar.py"],
             "base R":[r,script/"forecast_base.R"]}
    fixture=fixture_check(engines)
    if args.fixture_only:
        print("BOOK11_FORECAST_FIXTURE_OK routes=3 ties=half missing_refused=true")
        return
    require(args.out,"--out is required")
    spec_path=ROOT/"config/forecast.json"
    spec=load(spec_path)
    for name, value in spec["pinned"].items():
        require(sha(ROOT/name)==value, f"Changed forecast input: {name}")
    evidence=ROOT/"private/evidence"
    plan=load(evidence/"book7-forecast-contract.json")
    prior=load(evidence/"book7-forecast-rerun.json")
    require(not prior["new_world_draws"] and plan["no_model_refit"] and plan["no_threshold_selection"]
            and plan["outcome_field"]=="withdrawn_12" and not plan["simulator_reference"]["matches_primary_target"],
            "Book 7 evaluation contract changed")
    if args.book7_archive:
        check_archive(args.book7_archive,prior,engines,spec["tolerance"])
    values=prior["routes"]["numpy"]["metrics"]
    printed=tokens(values,fixture,spec,plan,prior["transfers"])
    for name,key in ROUTES.items():
        metrics=prior["routes"][key]["metrics"]
        verify_links(metrics,spec)
        compare(values,metrics,spec["tolerance"],name)
        require(tokens(metrics,fixture,spec,plan,prior["transfers"])==printed, f"{name}: rendered forecast differs")
    result={"contract":spec["id"],"contract_sha256":sha(spec_path),"book7_snapshot":prior["snapshot"],
            "target":spec["target"],"scope":spec["scope"],"comparator":spec["comparator"],
            "observation":spec["observation"],"metrics":values,
            "upstream_rerun_sha256":sha(evidence/"book7-forecast-rerun.json"),
            "book7_archive_rescored":bool(args.book7_archive),"fixture":fixture,"printed":printed}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(f"BOOK11_FORECAST_OK routes=3 later={printed['P8_N']} brier={printed['P8_BRIER']} auc={printed['P8_AUC']}")


if __name__=="__main__":
    main()
