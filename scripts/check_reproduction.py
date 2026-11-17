"""Trace the S5 aggregate and repeat the public fixture from pinned bytes."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile

from check_s5 import ROOT, compare, render_tokens, require, sha

FIXTURE_CONFIG = ROOT/"config/reproduction-fixture.json"
TRACE_CONFIG = ROOT/"config/reproduction.json"


def load(path):
    return json.loads(path.read_text())


def checked_fixture(path, expected_digest):
    require(sha(path) == expected_digest, "Changed public fixture bytes")


def fixture_audit(rscript):
    spec = load(FIXTURE_CONFIG)
    path = ROOT/"companion-src/fixture.csv"
    if not path.is_file():
        path = ROOT/"fixtures/exact.csv"
    require(spec["id"] == "B11-V10-FIXTURE-v1", "Wrong fixture contract")
    checked_fixture(path, spec["fixture_sha256"])
    for name, digest in spec["code_sha256"].items():
        require(sha(ROOT/name) == digest, f"Changed public route or dependency: {name}")
    tolerance = spec["absolute_tolerance"]
    expected = spec["inputs"]
    pairs, routes = compare(path, rscript, expected, tolerance)
    require([list(pair) for pair in pairs] == spec["keyed_sums"], "Fixture scores differ")
    rendered = render_tokens(routes["numpy"], expected)
    require(all(render_tokens(value, expected) == rendered for value in routes.values()),
            "Fixture editions would print different values")

    with tempfile.TemporaryDirectory(prefix="claim-reorder-") as directory:
        changed = Path(directory)/"reordered.csv"
        rows = path.read_bytes().splitlines(keepends=True)
        rows[1:3] = reversed(rows[1:3])
        changed.write_bytes(b"".join(rows))
        try:
            checked_fixture(changed, spec["fixture_sha256"])
        except ValueError as error:
            require(str(error) == "Changed public fixture bytes", "Wrong fixture refusal")
        else:
            raise ValueError("Reordered bytes were accepted as the frozen fixture")
        reordered_pairs, reordered_routes = compare(changed, rscript, expected, tolerance)
        require(sorted(reordered_pairs) == sorted(pairs), "Reordering changed the identity-keyed sums")
        require(all(math.isclose(routes[name], value, rel_tol=0, abs_tol=tolerance)
                    for name,value in reordered_routes.items()), "Reordering changed the correlation")

    return {"contract":spec["id"],"contract_sha256":sha(FIXTURE_CONFIG),
            "data_sha256":spec["fixture_sha256"],"code_sha256":spec["code_sha256"],
            "absolute_tolerance":tolerance,"counts":{key:expected[key] for key in ("baseline","colleges","paired")},
            "raw_r_by_route":routes,"keyed_sums":spec["keyed_sums"],
            "r_print":rendered["S5_R"],"reordered_bytes_refused":True,"reordered_result_agreed":True}


def normalized(text):
    return re.sub(r"(?<=\w)-\s+(?=\w)", "-", " ".join(text.split()))


def check_sentence(text, label, sentence, format_name):
    value = normalized(text)
    require(value.count(label) == 1 and normalized(f"{label} {sentence}") in value,
            f"{format_name}: traced sentence changed at {label}")


def test_sentence_check(sentence, label):
    wrong = sentence.replace("scores had", "traits had")
    require(wrong != sentence, "Sentence control needs the recorded-score noun")
    check_sentence(f"{label} {sentence}",label,sentence,"integrity control")
    try:
        check_sentence(f"{label} {wrong} Elsewhere: {sentence}",label,sentence,"integrity control")
    except ValueError as error:
        require(str(error) == f"integrity control: traced sentence changed at {label}", "Wrong sentence refusal")
    else:
        raise ValueError("Changed claim passed with its digits and the correct sentence elsewhere")


def trace_s5(path, fixture):
    spec = load(TRACE_CONFIG)
    source = ROOT/"config/s5.json"
    require(sha(source) == spec["source_contract_sha256"] and
            fixture["contract_sha256"] == spec["public_fixture_contract_sha256"], "Changed reproduction contract inputs")
    source_spec = load(source)
    upstream = load(path)
    require(upstream["contract"] == source_spec["id"] == spec["source_contract"] and
            upstream["contract_sha256"] == sha(source) and
            upstream["upstream_commit"] == source_spec["upstream_commit"] and
            upstream["baseline_projection_sha256"] == source_spec["projection_sha256"] ==
            sha(ROOT/"private/inputs/baseline-items.csv"), "S5 source receipt differs from the pinned inputs")
    counts = upstream["counts"]
    require(counts == {key:source_spec["expected"][key] for key in ("baseline","colleges","paired")} and
            upstream["exact_pair_agreement"] == counts["paired"], "Wrong S5 counts or keyed sum check")
    by_route = upstream["raw_r_by_route"]
    require(set(by_route) == set(fixture["raw_r_by_route"]), "S5 route missing")
    expected = source_spec["expected"]
    print_forms = {name:render_tokens(value, expected) for name,value in by_route.items()}
    require(all(value == upstream["printed"] == source_spec["print"] for value in print_forms.values()) and
            all(math.isclose(value, expected["r"], rel_tol=0, abs_tol=source_spec["absolute_tolerance"])
                for value in by_route.values()), "S5 unrounded value or print differs")
    tokens = upstream["printed"]
    sentence = spec["target_sentence"].format(paired=tokens["S5_N"], r=tokens["S5_R"])
    test_sentence_check(sentence, spec["reader_labels"]["chapter_1"])
    return {"contract":spec["id"],"contract_sha256":sha(TRACE_CONFIG),"source_claim":spec["source_claim"],
            "source_contract":source_spec["id"],"source_contract_sha256":sha(source),
            "source_upstream_commit":source_spec["upstream_commit"],"source_receipt_sha256":sha(path),
            "projection_sha256":upstream["baseline_projection_sha256"],"counts":counts,"raw_r_by_route":by_route,
            "runtime":{key:upstream[key] for key in ("python","numpy","r")},
            "absolute_tolerance":source_spec["absolute_tolerance"],"print_rule":source_spec["print_rule"],
            "reader_labels":spec["reader_labels"],"sentence_control_refused":True,
            "fixture":fixture,"printed":{"R10_SENTENCE":sentence,"R10_FIX_R":fixture["r_print"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s5",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--fixture-only",action="store_true")
    args = parser.parse_args()
    rscript = os.environ.get("CLAIM_RSCRIPT") or shutil.which("Rscript")
    require(rscript, "Actual base R is required. Install Rscript or set CLAIM_RSCRIPT.")
    fixture = fixture_audit(rscript)
    if args.fixture_only:
        print(f"BOOK11_REPRODUCTION_FIXTURE_OK routes=3 paired={fixture['counts']['paired']} "
              f"r={fixture['r_print']} reordered_bytes_refused=true reordered_result_agreed=true")
        return
    require(args.s5 and args.out, "--s5 and --out are required for a full trace")
    receipt = trace_s5(args.s5,fixture)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print("BOOK11_REPRODUCTION_OK source=S5 routes=3 sentence_control_refused=true")


if __name__ == "__main__":
    main()
