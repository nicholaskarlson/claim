"""Verify visits, exposure, archived model reruns and college uncertainty sensitivity."""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal
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
import tempfile
import zipfile

from check_observation import compare
from check_s5 import ROOT, require, sha
from part1_io import read
from visits_io import FIELDS, project

FIXTURE = ROOT/"fixtures/visits"
ROUTES = {"numpy":"numpy","standard-library Python":"stdlib","base R":"base_r"}
METHODS = {"POISSON":("poisson_adjusted","model"),"QUASI":("poisson_adjusted","quasi"),
           "HC1":("poisson_adjusted","hc1"),"NB2":("nb_adjusted","model"),
           "NB2_HC1":("nb_adjusted","hc1")}


def json_at(path):
    return json.loads(path.read_text())


def calculate(command,*args):
    stdout=subprocess.check_output([*command,*map(str,args)],text=True,timeout=30)
    rows=list(csv.reader(io.StringIO(stdout)))
    values={key:float(value) for key,value in rows}
    require(len(values)==len(rows),"Duplicate visits result")
    return values


def verify_fixture(engines):
    path=FIXTURE/"exposure.csv"
    expected=json_at(FIXTURE/"expected.json")
    require([r["offer"] for r in read(path)]==["0","0","1","1"],"Incorrect fixture arms")
    with tempfile.TemporaryDirectory(prefix="claim-visits-") as directory:
        invalid=Path(directory)/"zero-exposure.csv"
        invalid.write_text(path.read_text().replace("0,0,1","0,0,0"))
        for name,command in engines.items():
            compare(expected,calculate(command,"fixture",path),1e-12,name)
            result=subprocess.run([*command,"fixture",invalid],capture_output=True,text=True,timeout=30)
            require(result.returncode and "Exposure must be positive" in result.stderr,
                    f"{name}: zero exposure must be refused")
    return expected


def verify_archive(archive_path,prior,projected):
    require(sha(archive_path)==prior["archive_sha256"],"Wrong Book 9 archive")
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.comment.decode().strip()==prior["book9_commit"],"Wrong Book 9 commit")
        for name,digest in prior["source_members"].items():
            require(hashlib.sha256(archive.read(name)).hexdigest()==digest,f"Changed Book 9 member: {name}")
        inputs={key:archive.read(member) for key,member in prior["input_members"].items()}
    require(project(**inputs)==projected.read_bytes(),"Book 9 visits projection differs")


def verify_input(source,assignment):
    rows=read(source)
    assigned=read(assignment)
    require(len(rows)==len(assigned)==1219 and list(rows[0])==FIELDS,"Unexpected visit roster or schema")
    ids={row["student_id"] for row in rows}
    require(len(ids)==len(rows) and ids=={row["student_id"] for row in assigned},"Visit/assignment identity differs")
    colleges=defaultdict(set)
    for row in assigned:
        colleges[row["college_id"]].add(row["offer"])
    require(len(colleges)==16 and all(arms=={"0","1"} for arms in colleges.values()),
            "Both assigned arms must occur in each of sixteen colleges")
    for row in rows:
        require(None not in row and None not in row.values(),"Malformed projected visit row")
        require(re.fullmatch(r"[0-9]+",row["visits"]) and int(row["visits"])<=10000,"Invalid archived count")
        require(re.fullmatch(r"[0-9]+(?:\.[0-9]{1,3})?",row["months"])
                and 0<Decimal(row["months"])<=12,"Invalid enrolled-month exposure")
        require(all(row[k] in {"0","1"} for k in ("part_time","first_gen")),"Invalid baseline indicator")
        require(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?",row["prior_grade"])
                and 0<=Decimal(row["prior_grade"])<=4,"Invalid prior grade")


def reconcile(raw,unit1,unit6,tolerance,name):
    paired={}
    for a in (0,1):
        for key in ("n","visits","months","mean_count","aggregate_rate","mean_individual_rate"):
            paired[f"arm{a}/{key}"]=unit6[f"arm/{a}/{key}"]
    paired.update({key:unit6[key] for key in ("raw/count_difference","raw/rate_ratio")})
    paired["raw/zeros"]=round(unit6["raw/zero_share"]*unit1["n"])
    paired["design/colleges"]=unit1["colleges"]
    paired["design/difference"]=unit1["design/difference"]
    paired["model/row_se"]=unit6["offer/poisson_adjusted/hc1/se"]
    compare(paired,{k:raw[k] for k in paired},tolerance,name+" Book 9 reconciliation")
    require(raw["model/score_max_per_row"]<=1e-10,f"{name}: projected mean score is not stationary")
    for arm in (0,1):
        for key in ("n","visits"):
            require(raw[f"arm{arm}/{key}"]==unit6[f"arm/{arm}/{key}"],f"{name}: exact count differs")
    for key in ("quasi","hc1"):
        require(unit6[f"offer/poisson_adjusted/{key}/irr"]==unit6["offer/poisson_adjusted/model/irr"],
                "Poisson uncertainty variants changed the mean estimate")


def tokens(raw,unit1,unit6,fixture):
    def n(value):
        require(value==int(value),"Noninteger count")
        return f"{int(value):,}"

    def d(value, digits=3):
        return f"{value:.{digits}f}".replace("-","−")

    def bounds(lo,hi):
        return f"{d(lo)} to {d(hi)}"

    out={"M7_N":n(unit1["n"]),"M7_COLLEGES":n(unit1["colleges"]),
         "M7_DESIGN_DIFF":d(raw["design/difference"]),
         "M7_DESIGN_CI":bounds(unit1["design/normal_lower"],unit1["design/normal_upper"]),
         "M7_RAW_RATIO":d(raw["raw/rate_ratio"]),"M7_ZEROS":n(raw["raw/zeros"]),
         "M7_UNADJUSTED_P":d(unit6["offer/poisson_unadjusted/model/p"],4),
         "M7_COLLEGE_CI":bounds(raw["model/college_lower"],raw["model/college_upper"]),
         "M7_PHI":d(unit6["model/poisson_adjusted/phi"]),
         "M7_POISSON_ZEROS":d(unit6["model/poisson_adjusted/expected_zeros"],1),
         "M7_NB2_ZEROS":d(unit6["model/nb_adjusted/expected_zeros"],1),
         "M7_ELASTICITY":d(unit6["diagnostic/exposure_total_elasticity"]),
         "M7_ELASTICITY_CI":bounds(unit6["diagnostic/exposure_lower"],unit6["diagnostic/exposure_upper"]),
         "M7_COMMON_MONTHS_DIFF":d(unit6["standardized/poisson_adjusted/hc1/count_diff12/estimate"]),
         "M7_FIX_COUNT_RATIO":d(fixture["arm1/mean_count"]/fixture["arm0/mean_count"],2),
         "M7_FIX_RATE_RATIO":d(fixture["raw/rate_ratio"],2)}
    for a in (0,1):
        for key,tag in (("n","N"),("visits","VISITS"),("months","MONTHS"),
                        ("mean_count","PER_STUDENT"),("aggregate_rate","PER_MONTH"),
                        ("mean_individual_rate","MEAN_INDIV_RATE")):
            value=raw[f"arm{a}/{key}"]
            out[f"M7_{a}_{tag}"]=n(value) if key in {"n","visits"} else f"{value:,.3f}" if key=="months" else d(value)
    for tag,(model,method) in METHODS.items():
        group=f"offer/{model}/{method}/"
        out["M7_"+tag+"_IRR"]=d(unit6[group+"irr"])
        out["M7_"+tag+"_CI"]=bounds(unit6[group+"lower"],unit6[group+"upper"])
        out["M7_"+tag+"_P"]=d(unit6[group+"p"],4)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--book9-archive",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args=parser.parse_args()
    r=os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r,"Install actual base R or set CLAIM_RSCRIPT")
    scripts=ROOT/"scripts"
    engines={"numpy":[sys.executable,scripts/"visits_numpy.py"],
             "standard-library Python":[sys.executable,scripts/"visits_scalar.py"],
             "base R":[r,scripts/"visits_base.R"]}
    fixture=verify_fixture(engines)
    if args.fixture_only:
        print("BOOK11_VISITS_FIXTURE_OK routes=3 zero_exposure_refused=true")
        return
    require(args.out,"--out is required for the full check")
    config_path=ROOT/"config/visits.json"
    config=json_at(config_path)
    for name,digest in config["pinned"].items():
        require(sha(ROOT/name)==digest,f"Changed pinned visits source: {name}")
    prior_path=ROOT/"private/evidence/book9-visits-rerun.json"
    prior=json_at(prior_path)
    units=prior["units"]
    require(units["01"]["summary_keys"]==112 and units["06"]["summary_keys"]==367
            and all(u["people"]==1219 and set(u["routes"])==set(ROUTES.values()) for u in units.values()),
            "Book 9 visits reruns incomplete")
    source=ROOT/"private/inputs/visits-exposure.csv"
    assignment=ROOT/"private/inputs/baseline-offer.csv"
    verify_input(source,assignment)
    if args.book9_archive:
        verify_archive(args.book9_archive,prior,source)
    raw,models,printed={},{},{}
    for name,command in engines.items():
        key=ROUTES[name]
        unit1=units["01"]["routes"][key]["selected"]
        unit6=units["06"]["routes"][key]["selected"]
        beta=units["06"]["routes"][key]["beta"]
        require(len(beta)==5 and all(math.isfinite(x) for x in beta),"Wrong Book 9 coefficient vector")
        result=calculate(command,"ordinary",source,assignment,*beta)
        reconcile(result,unit1,unit6,config["tolerance"],name)
        raw[name]=result
        models[name]={"unit01":unit1,"unit06":unit6}
        compare(raw["numpy"],result,config["tolerance"],name)
        for unit,values in models[name].items():
            compare(models["numpy"][unit],values,config["tolerance"],name+" upstream "+unit)
        printed[name]=tokens(result,unit1,unit6,fixture)
        require(printed[name]==printed["numpy"],f"{name}: printed visit values differ")
    result={"contract":config["id"],"contract_sha256":sha(config_path),"roster":config["roster"],
            "endpoint":config["endpoint"],"working_mean":config["working_mean"],
            "college_sensitivity":config["college_sensitivity"],"book9_commit":prior["book9_commit"],
            "book9_rerun_sha256":sha(prior_path),"book9_archive_checked":bool(args.book9_archive),
            "archive_results_by_route":raw,"book9_models_by_route":models,"fixture":fixture,
            "zero_exposure_refused":True,"printed":printed["numpy"]}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("BOOK11_VISITS_OK routes=3 adjusted_poisson="+printed["numpy"]["M7_POISSON_IRR"]+
          " college_interval="+printed["numpy"]["M7_COLLEGE_CI"])


if __name__=="__main__":
    main()
