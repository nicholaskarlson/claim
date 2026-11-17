"""Verify the invented synthesis and the Book 9 ordinary aggregate projection."""
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
from zipfile import ZipFile

from check_s5 import ROOT, require, sha
from synthesis_source import BASELINE, FIELDS, PREFIX, REGISTRY, projection

FIXTURE = ROOT/"fixtures/synthesis/four-colleges.csv"
COUNTS = ("colleges","roster","known","missing")


def load(path):
    return json.loads(path.read_text())


def validate(path, colleges):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames) == FIELDS, "Synthesis aggregate schema differs")
        rows = list(reader)
    require([row["college"] for row in rows] == [chr(65+i) for i in range(colleges)], "Wrong college inventory")
    for row in rows:
        variances = []
        for arm in ("no","offer"):
            assigned,n,total,ss = (int(row[f"{key}_{arm}"]) for key in ("assigned","known","sum","ss"))
            require(2 <= n <= assigned and 0 <= total <= 400*n and 0 <= ss <= 400*total and
                    n*ss >= total**2, "Impossible grade moments or unsupported arm size")
            variances.append(n*ss-total**2)
        require(any(variances), "Zero working variance in a college")
    return rows


def compare(reference, value, tolerance):
    require(reference.keys() == value.keys(), "Synthesis route inventory differs")
    for key,wanted in reference.items():
        got = value[key]
        if key in COUNTS:
            require(got == wanted and got.is_integer(), f"Exact synthesis count differs: {key}")
        else:
            require(math.isclose(got,wanted,rel_tol=0,abs_tol=tolerance), f"Synthesis routes differ: {key}")


def calculate(commands, path, tolerance):
    outputs = {}
    for name,command in commands.items():
        raw = subprocess.check_output([*command,path],text=True,timeout=40)
        rows = list(csv.reader(io.StringIO(raw)))
        value = {name:float(x) for name,x in rows}
        require(len(rows)==len(value),"Duplicate synthesis output")
        outputs[name] = value
        compare(outputs["numpy"],value,tolerance)
    return outputs


def fixture_check(commands):
    rows = validate(FIXTURE,4)
    runs = calculate(commands,FIXTURE,2e-10)
    exact = {"roster":32,"known":32,"missing":0,"equal_mean":.2,"pooled":.2,"q":30,
             "tau":math.sqrt(.24),"mean_se":math.sqrt(1/15),"A_se":math.sqrt(2/75)}
    for run in runs.values():
        compare(exact,{key:run[key] for key in exact},2e-10)
    with tempfile.TemporaryDirectory(prefix="claim-synthesis-") as directory:
        homogeneous = Path(directory)/"common.csv"
        with homogeneous.open("w",newline="") as out:
            writer = csv.DictWriter(out,fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(dict(rows[0],college=row["college"]) for row in rows)
        common = calculate(commands,homogeneous,2e-10)
        require(all(run["tau"] == 0 for run in common.values()), "Zero boundary changed")
    return runs["numpy"]


def verify_archive(path, pinned, expected_projection):
    require(sha(path)==pinned["book9_archive_sha256"], "Wrong Book 9 archive")
    with ZipFile(path) as archive:
        require(archive.comment.decode().strip()==pinned["book9_commit"], "Wrong Book 9 snapshot")
        data = {name:archive.read(PREFIX+name) for name in pinned["member_sha256"]}
        require(all(hashlib.sha256(raw).hexdigest() == pinned["member_sha256"][name] for name,raw in data.items()),
                "Book 9 synthesis source changed")
        require(projection(data[BASELINE],data[REGISTRY]) == expected_projection.read_bytes(),
                "Book 9 grade projection differs")


def printed(values, fixture):
    def points(x):
        return f"{x:+.3f}".replace("-","−")

    def interval(prefix):
        return f"{points(values[prefix+'_lo'])} to {points(values[prefix+'_hi'])}"

    text = {f"Y12_{key.upper()}":f"{int(values[key]):,}" for key in COUNTS}
    text.update({f"Y12_{key.upper()}":points(values[key])
                 for key in ("low","high","equal_mean","common_ols","fixed_iv","pooled")})
    text.update({f"Y12_{key.upper()}":f"{values[key]:.3f}" for key in ("spread","tau","mean_se")})
    text.update(Y12_MEAN_INTERVAL=interval("mean"),Y12_PREDICTION=interval("prediction"),
                Y12_OMIT_MIN=f"{values['leaveout_lo']:.3f}",Y12_OMIT_MAX=f"{values['leaveout_hi']:.3f}",
                Y12_FIX_Q=f"{fixture['q']:.0f}",Y12_FIX_TAU2=f"{fixture['tau']**2:.2f}",
                Y12_FIX_MEAN=f"{fixture['pooled']:+.2f}")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--book9-archive",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args = parser.parse_args()
    r = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(r, "Install base R or set CLAIM_RSCRIPT")
    commands = {label:[r if label=="base_r" else sys.executable,ROOT/"scripts"/filename] for label,filename in
                (("numpy","synthesis_numpy.py"),("stdlib","synthesis_scalar.py"),("base_r","synthesis_base.R"))}
    fixture = fixture_check(commands)
    if args.fixture_only:
        print("BOOK11_SYNTHESIS_FIXTURE_OK routes=3 exact_q=30 zero_boundary=true")
        return
    require(args.out,"--out is required")
    config = ROOT/"config/synthesis.json"
    spec = load(config)
    for name,digest in spec["pinned"].items():
        require(sha(ROOT/name)==digest,f"Changed synthesis source: {name}")
    pin = load(ROOT/"private/evidence/book9-synthesis-rerun.json")
    require(pin["rerun_routes"]==3 and pin["case"]==spec["upstream_contract"],"Book 9 rerun scope differs")
    data = ROOT/"private/inputs/synthesis-colleges.csv"
    validate(data,16)
    if args.book9_archive:
        verify_archive(args.book9_archive,pin,data)
    routes = calculate(commands,data,spec["tolerance"])
    expected = pin["expected_gpa12"]
    tokens = printed(routes["numpy"],fixture)
    for values in routes.values():
        require(values["known"]==expected["n"] and values["missing"]==expected["missing"]
                and math.isclose(values["common_ols"],expected["estimate"],rel_tol=0,abs_tol=spec["tolerance"]),
                "Book 9 GPA reference differs")
        require(printed(values,fixture)==tokens, "Printed synthesis results differ")
    result = {"contract":spec["id"],"contract_sha256":sha(config),"source_commit":pin["book9_commit"],
              "upstream_contract":pin["case"],"scope":spec["target"],"method":spec["method"],
              "source_archive_checked":bool(args.book9_archive),"all_routes":routes,"fixture":fixture,"printed":tokens}
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(f"BOOK11_SYNTHESIS_OK routes=3 colleges={tokens['Y12_COLLEGES']} tau={tokens['Y12_TAU']} "
          f"prediction={tokens['Y12_PREDICTION']}")


if __name__=="__main__":
    main()
