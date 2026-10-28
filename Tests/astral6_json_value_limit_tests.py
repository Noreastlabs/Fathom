#!/usr/bin/env python3
"""CLI-only finite JSON budget regressions; all generated evidence goes to scratch.

Run with --validator <built fathom_content_validate> --scratch <fresh Build path>.
The synthetic boundary inputs are deliberately schema-invalid: a later schema
refusal proves parsing completed without weakening reference or admission rules.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


CLI_VALUES = 1_100_000
JSON_BYTES = 32 * 1024 * 1024


def array_values(total):
    # The array itself counts as one value; object keys do not count as values.
    return b"[" + b"null," * (total - 2) + b"null]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validator", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    validator = args.validator.resolve(strict=True)
    scratch = args.scratch.resolve()
    scratch.relative_to(root / "Build")
    scratch.mkdir(parents=True, exist_ok=False)
    fixtures = root / "Tests/fixtures/canonical_controls"
    original = {
        "package": (fixtures / "examples.json").read_bytes(),
        "registry": (fixtures / "identity-registry.json").read_bytes(),
        "profile": (fixtures / "expected-profile.json").read_bytes(),
    }
    measurements = []

    def run(label, changes=None, code=None, field=None, exit_code=1, bad_hash=False):
        case = scratch / label
        case.mkdir()
        inputs = dict(original, **(changes or {}))
        for name, data in inputs.items():
            (case / (name + ".json")).write_bytes(data)
        command = [str(validator)]
        for name in inputs:
            command += ["--" + name, str(case / (name + ".json"))]
        profile_hash = hashlib.sha256(inputs["profile"]).hexdigest()
        command += ["--profile-sha256", "0" * 64 if bad_hash else profile_hash,
                    "--source-root", str(root), "--report", str(case / "report.json")]
        start = time.monotonic()
        with (case / "stdout.log").open("wb") as out, (case / "time.log").open("wb") as err:
            process = subprocess.run(["/usr/bin/time", "-l", *command], stdout=out, stderr=err)
        measurement = {"case": label, "command": command, "exit_code": process.returncode,
                       "wall_seconds": time.monotonic() - start}
        measurements.append(measurement)
        (scratch / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")
        assert process.returncode == exit_code, (label, process.returncode, exit_code)
        if exit_code == 74:
            assert not (case / "report.json").exists(), label
            assert "Read exceeds byte limit" in (case / "time.log").read_text(), label
        else:
            report = json.loads((case / "report.json").read_text())
            config = report["configuration"]
            assert config["json_values"] == CLI_VALUES, (label, config)
            assert {key: config[key] for key in ("json_bytes", "json_depth", "string_bytes", "number_bytes")} == {
                "json_bytes": JSON_BYTES, "json_depth": 64,
                "string_bytes": 1024 * 1024, "number_bytes": 128}, (label, config)
            assert not report["curriculum_playback_authorized"], label
            if code:
                assert not report["valid_reference"], label
                assert any(issue["code"] == code and (field is None or issue["field"] == field)
                           for issue in report["issues"]), (label, report["issues"])
                if code != "JSON_VALUE_LIMIT":
                    assert all(issue["code"] != "JSON_VALUE_LIMIT" for issue in report["issues"]), label
            else:
                assert report["valid_reference"] and len(report["records"]) == 13, label
        print("PASS", label, flush=True)

    run("existing-13-record-reference", exit_code=2)
    at_limit = array_values(CLI_VALUES)
    over_limit = array_values(CLI_VALUES + 1)
    for document in ("profile", "package", "registry"):
        code, field = ("REQUIRED_FIELD", "/package/schema_version") if document == "package" else ("TYPE_OBJECT", "/" + document)
        run(document + "-exact-value-boundary", {document: at_limit}, code, field)
        run(document + "-oversize-value-refusal", {document: over_limit}, "JSON_VALUE_LIMIT")
    # A map-heavy boundary exercises per-node/key allocation, unlike a null array.
    dense_object = ("{" + ",".join('"k%d":null' % i for i in range(CLI_VALUES - 1)) + "}").encode()
    run("map-exact-value-boundary", {"profile": dense_object}, "REQUIRED_FIELD", "/profile/profile_version")
    run("profile-hash-before-oversize-parse", {"profile": over_limit}, "PROFILE_HASH", "/profile", bad_hash=True)
    run("decoded-duplicate-key", {"profile": b'{"x":1,"\\u0078":2}'}, "JSON_DUPLICATE_KEY")
    run("depth-boundary", {"profile": b"[" * 64 + b"0" + b"]" * 64}, "TYPE_OBJECT", "/profile")
    run("depth-oversize", {"profile": b"[" * 65 + b"0" + b"]" * 65}, "JSON_DEPTH_LIMIT")
    run("string-boundary", {"profile": b'"' + b"a" * (1024 * 1024) + b'"'}, "TYPE_OBJECT", "/profile")
    run("string-oversize", {"profile": b'"' + b"a" * (1024 * 1024 + 1) + b'"'}, "JSON_STRING_LIMIT")
    run("number-oversize", {"profile": b"1" * 129}, "JSON_NUMBER_LIMIT")
    run("nonfinite", {"profile": b"1e309"}, "JSON_NONFINITE")
    run("malformed-trailing", {"profile": b"{} false"}, "JSON_TRAILING")
    run("byte-boundary", {"profile": b"{}" + b" " * (JSON_BYTES - 2)}, "REQUIRED_FIELD")
    run("byte-oversize", {"profile": b"{}" + b" " * (JSON_BYTES - 1)}, exit_code=74)
    print(f"{len(measurements)} CLI checks passed; no runtime admission")


if __name__ == "__main__":
    main()
