"""Check S1 joins, exact probability fixtures and their printed results in three routes."""
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

from check_s5 import ROOT, require, sha
from part1_io import read

ASSIGNED = ["student_id","college_id","offer"]
REGISTRY = ["student_id","cohort","responded_baseline","offer","exit_month","exit_type",
            "withdrawal_label","outcome_known","observation_source"]
COUNT_KEYS = {"assigned","known","unknown","events"}


def validate(assigned, registry):
    for rows, columns, name in ((assigned,ASSIGNED,"assignment"),(registry,REGISTRY,"registry")):
        require(bool(rows) and list(rows[0]) == columns, f"Wrong {name} schema")
        require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
                f"Malformed {name} row")
        ids = [row["student_id"] for row in rows]
        require(all(ids) and len(ids) == len(set(ids)), f"Duplicate or empty {name} ID")
        require(all(row["offer"] in ("0","1") for row in rows), f"Invalid {name} offer")
    require({row["offer"] for row in assigned} == {"0","1"}, "Both offer arms are required")
    require(all(row["college_id"] for row in assigned), "Empty college")
    for row in registry:
        require(row["cohort"] == "anchor" and row["responded_baseline"] in ("0","1"), "Wrong registry cohort")
        require((row["outcome_known"],row["withdrawal_label"]) in (("0",""),("1","0"),("1","1")),
                "Unknown labels must remain blank")
        require(row["exit_type"] in ("none","withdrawal","transfer","consent_withdrawn"), "Invalid exit type")
        require((row["outcome_known"] == "0") == (row["exit_type"] == "consent_withdrawn"), "Consent observation rule differs")
        require((row["withdrawal_label"] == "1") == (row["exit_type"] == "withdrawal"), "Withdrawal label differs from exit")
        require(0 <= float(row["exit_month"]) <= 12, "Outcome is outside the horizon")
    lookup = {row["student_id"]:row for row in registry}
    for row in assigned:
        require(row["student_id"] in lookup, "Missing registry identity")
        record = lookup[row["student_id"]]
        require(record["offer"] == row["offer"], "Offer disagrees across files")
        require(record["responded_baseline"] == "1", "Assignment row is not a baseline respondent")


def values(path):
    rows = read(path)
    result = {row["key"]:float(row["value"]) if row["value"] else None for row in rows}
    require(len(result) == len(rows), "Duplicate result key")
    require(all(value is None or math.isfinite(value) for value in result.values()), "Nonfinite result")
    return result


def compare(mode, source, out, rscript, registry=None):
    if mode == "withdrawal":
        validate(read(source),read(registry))
    commands = {"numpy":[sys.executable,ROOT/"scripts/part1_numpy.py"],
                "scalar":[sys.executable,ROOT/"scripts/part1_scalar.py"],
                "base-r":[rscript,ROOT/"scripts/part1_base.R"]}
    result, sample, outputs = None, None, {}
    for route, prefix in commands.items():
        target = out/route
        command = [*prefix,mode,source,target]
        if registry is not None:
            command.append(registry)
        subprocess.run(list(map(str,command)),check=True,timeout=45)
        current = values(target/"values.csv")
        joined = read(target/"joined.csv")
        if result is not None:
            require(current.keys() == result.keys() and joined == sample, "Route inventory or joined rows differ")
            for key, value in result.items():
                other = current[key]
                if value is None or other is None:
                    require(value is None and other is None, f"Undefined status differs: {key}")
                elif key.endswith(("_n","_schedules","_extremes")) or key.split("/")[-1] in COUNT_KEYS:
                    require(value == other and value.is_integer(), f"Exact count differs: {key}")
                else:
                    require(math.isclose(value,other,rel_tol=0,abs_tol=1e-12), f"Numeric disagreement: {key}")
        result, sample = current, joined
        outputs[route] = current
    return result, sample, outputs


def fixture_checks(out, rscript):
    root = ROOT/"fixtures/part1"
    probability_contract = json.loads((ROOT/"config/probability-contract.json").read_text())
    for name,digest in probability_contract["inputs"].items():
        require(sha(ROOT/name) == digest, f"Probability fixture changed: {name}")
    result, sample, _ = compare("withdrawal",root/"assigned.csv",out/"withdrawal",rscript,root/"registry.csv")
    require(result["baseline_n"] == 6 and result["registry_n"] == 8 and len(sample) == 6, "Fixture frame differs")
    for arm in ("0","1"):
        for key,expected in {"assigned":3,"known":2,"unknown":1,"events":1,
                             "recorded_rate":1/3,"known_rate":1/2,"lower":1/3,"upper":2/3}.items():
            require(math.isclose(result[f"arm/{arm}/{key}"],expected,abs_tol=1e-12), "Wrong exact withdrawal fixture")
    assigned,registry = read(root/"assigned.csv"),read(root/"registry.csv")
    refusals = {}
    for name,changed_a,changed_r,message in (
        ("duplicate_id",assigned+[assigned[0]],registry,"Duplicate or empty assignment ID"),
        ("unknown_as_zero",assigned,[{**r,"withdrawal_label":"0"} if r["outcome_known"] == "0" else r for r in registry],
         "Unknown labels must remain blank"),
        ("missing_id",assigned,registry[1:],"Missing registry identity"),
        ("offer_mismatch",assigned,[{**r,"offer":"1"} if r["student_id"] == "A" else r for r in registry],
         "Offer disagrees across files"),
    ):
        try:
            validate(changed_a,changed_r)
        except ValueError as error:
            require(str(error) == message, f"Wrong refusal for {name}")
        else:
            raise ValueError(f"Accepted invalid fixture: {name}")
        refusals[name] = True
    zero_known = out/"zero-known.csv"
    with zero_known.open("w",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=REGISTRY)
        writer.writeheader()
        for row in registry:
            if row["offer"] == "0" and row["responded_baseline"] == "1":
                row = {**row,"withdrawal_label":"","outcome_known":"0","exit_type":"consent_withdrawn"}
            writer.writerow(row)
    zero,_,_ = compare("withdrawal",root/"assigned.csv",out/"zero-known",rscript,zero_known)
    require(zero["arm/0/known_rate"] is None and zero["known_difference"] is None,
            "A zero known-label denominator must remain undefined")
    p,_,_ = compare("probability",root,out/"probability",rscript)
    expected = {"sampling/schedules":6,"sampling/population_rate":3/8,"sampling/mean":3/8,
                "sampling/min":1/8,"sampling/max":5/8,"assignment/observed_difference":-1,
                "assignment/blocked_schedules":36,"assignment/blocked_extremes":2,"assignment/blocked_p":1/18,
                "assignment/pooled_schedules":70,"assignment/pooled_extremes":2,"assignment/pooled_p":1/35,
                "model/likelihood_0":27/64,"model/likelihood_1":1/4,"model/likelihood_ratio":27/16}
    require(p.keys() == expected.keys(), "Probability fixture result inventory differs")
    require(all(math.isclose(p[key],value,rel_tol=0,abs_tol=1e-12) for key,value in expected.items()),
            "Probability fixture differs from exact rational answers")
    return p,refusals


def projection(data):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer,fieldnames=ASSIGNED,lineterminator="\n")
    writer.writeheader()
    for row in csv.DictReader(io.StringIO(data.decode("utf-8"))):
        writer.writerow({key:row[key] for key in ASSIGNED})
    return buffer.getvalue().encode("utf-8")


def print_values(result, probability):
    out = {}
    for arm,name in (("0","NO"),("1","YES")):
        n,known,events,unknown = (int(result[f"arm/{arm}/{key}"]) for key in ("assigned","known","events","unknown"))
        out.update({f"S1_{name}_N":str(n),f"S1_{name}_KNOWN":str(known),f"S1_{name}_EVENTS":str(events),
                    f"S1_{name}_UNKNOWN":str(unknown),
                    f"S1_{name}_RECORDED":f"{events}/{n} ({100*events/n:.1f}%)",
                    f"S1_{name}_KNOWN_RATE":f"{events}/{known} ({100*events/known:.1f}%)",
                    f"S1_{name}_BOUNDS":f"{100*result[f'arm/{arm}/lower']:.1f}% to {100*result[f'arm/{arm}/upper']:.1f}%"})
    out["S1_SENTENCE"] = (f"Among {out['S1_NO_N']} baseline respondents assigned no mentoring offer, "
                          f"{out['S1_NO_EVENTS']} had a recorded withdrawal before transfer or month 12, "
                          f"and {out['S1_NO_UNKNOWN']} outcome labels were unknown after consent withdrawal.")
    out["S1_KNOWN_DIFFERENCE"] = f"{100*result['known_difference']:.1f}".replace("-","−")
    out["S1_DIFFERENCE_BOUNDS"] = (f"{100*result['realized_difference_lower']:.2f} to "
                                  f"{100*result['realized_difference_upper']:.2f}").replace("-","−")
    out["P3_BLOCKED_P"] = f"{probability['assignment/blocked_p']:.4f}"
    out["P3_POOLED_P"] = f"{probability['assignment/pooled_p']:.4f}"
    out["P3_MODEL_QUARTER"] = f"{100*probability['model/likelihood_0']:.1f}%"
    out["P3_MODEL_HALF"] = f"{100*probability['model/likelihood_1']:.1f}%"
    out["P3_LIKELIHOOD_RATIO"] = f"{probability['model/likelihood_ratio']:.4f}"
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--book10-archive",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args = parser.parse_args()
    rscript = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(rscript,"Actual base R is required")
    with tempfile.TemporaryDirectory(prefix="claim-part1-") as directory:
        area = Path(directory)
        p,refusals = fixture_checks(area,rscript)
        if args.fixture_only:
            print("BOOK11_PART1_FIXTURES_OK routes=3 refusals=4 zero_known=undefined probability=exact")
            return
        require(args.out is not None,"--out is required")
        config = ROOT/"config/part1.json"
        spec = json.loads(config.read_text())
        for path,digest in spec["input_hashes"].items():
            require(sha(ROOT/path) == digest,f"Pinned Part I input changed: {path}")
        if args.book10_archive:
            require(sha(args.book10_archive) == spec["upstream_archive_sha256"],"Wrong upstream Book 10 archive")
            with zipfile.ZipFile(args.book10_archive) as archive:
                require(archive.comment.decode().strip() == spec["upstream_commit"],"Wrong Book 10 commit")
                for name,source in spec["sources"].items():
                    raw = archive.read(source["member"])
                    require(hashlib.sha256(raw).hexdigest() == source["sha256"],"Wrong upstream member")
                    expected = projection(raw) if source["mode"] == "project_id_college_offer" else raw
                    require(expected == (ROOT/"private/inputs"/name).read_bytes(),"Projection differs from accepted source")
        result,sample,routes = compare("withdrawal",ROOT/"private/inputs/baseline-offer.csv",area/"ordinary",rscript,
                                      ROOT/"private/inputs/observed-registry.csv")
        require(result["baseline_n"] == 1219 and result["colleges_n"] == 16 and result["registry_n"] == 1600,
                "Ordinary frame differs from the accepted source")
        require(result["arm/0/assigned"] == 610 and result["arm/1/assigned"] == 609,"Assignment inventory differs")
        printed = print_values(result,p)
        require(all(print_values(current,p) == printed for current in routes.values()),"Printed values differ by route")
        joined = "\n".join(",".join(row.values()) for row in sample).encode()
        receipt = {"contract":spec["id"],"probability_contract":"B11-P3-EXACT-v1",
                   "probability_contract_sha256":sha(ROOT/"config/probability-contract.json"),"contract_sha256":sha(config),"raw":result,"printed":printed,
                   "raw_by_route":routes,"joined_records":len(sample),"joined_sha256":hashlib.sha256(joined).hexdigest(),
                   "probability":p,"refusals":refusals,"zero_known":"undefined",
                   "source_projection_rebuilt":bool(args.book10_archive),"input_hashes":spec["input_hashes"],
                   "r":subprocess.check_output([rscript,"--version"],text=True,stderr=subprocess.STDOUT,timeout=30).splitlines()[0]}
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
        print("BOOK11_PART1_OK routes=3 joined=1219 refusals=4 probability=exact")


if __name__ == "__main__":
    main()
