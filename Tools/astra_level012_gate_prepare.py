#!/usr/bin/env python3
"""Immutable Rung02 integration closure. This tool cannot issue admission."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CASE = "Build/parallel-02/level012-rung02-vertical-r01"
BASE = "Content/controls/representative-v1"
MANIFEST = "Content/runtime/representative-v1-manifest.json"
ITEM = "fg:item:001141"
VARIANTS = ["fg:variant:007404", "fg:variant:007405"]
PINS = {
    MANIFEST: "f57b3c6e1adddd3699bb27c8c0c35f356fbbcb2808f409f87bcca531afa75a8e",
    f"{CASE}/package.json": "3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc",
    f"{CASE}/identity-registry.json": "1541b508787cf87d61a917da89e8933fdc85aedf5f0b38abbc8d85d6be70cf87",
    f"{CASE}/expected-profile.json": "346db033dac7bad2d601a8b782facd48ff9feac779a930102608c0bc065bb74c",
    f"{CASE}/native-report.json": "5f02bda35bebdc0ba6931109bf9986d3d4d2a24fa01aa9d5e5be26803cb51d91",
    f"{BASE}/package.json": "0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b",
    f"{BASE}/expected-profile.json": "22c82db322f36d78e744b3445173f7d0a3f4f686ead209293c2416f0db308aed",
    f"{BASE}/identity-registry.json": "fa64b6d9e0a937415c5c52ff96e050de89f5eb31b989e0fd3e4b97eb9adfb6a8",
}
SCOPE = {
    "item_id": ITEM, "variant_ids": VARIANTS, "content_revision": 1,
    "cell": "Level12 Rung02 Bb major", "events": 16,
    "timing": "connected even eighths", "optional_inter_cell_pause": False,
    "fixed_authored_bpm": False, "whole_ladder": False,
    "mastery": False, "automatic_credit": False,
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, "DUPLICATE_KEY " + key)
        out[key] = value
    return out


def parse(data):
    return json.loads(data, object_pairs_hook=unique_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("NONFINITE " + x)))


def source_file(root, rel):
    parts = PurePosixPath(rel).parts
    need(parts and not rel.startswith("/") and not {".", ".."}.intersection(rel.split("/")) and "\\" not in rel,
         "UNSAFE_PATH")
    path = root / rel
    if len(parts) > 1 and parts[0] == "Results" and parts[1] != "primary":
        relocated = root / "Results/primary" / Path(*parts[1:])
        if relocated.exists():
            path = relocated
    need(path.resolve().is_relative_to(root.resolve()), "SOURCE_ESCAPE")
    need(not any(p.is_symlink() for p in [path, *path.parents]), "SOURCE_SYMLINK")
    return path


def pinned(root, rel, digest):
    raw = source_file(root, rel).read_bytes()
    need(sha(raw) == digest, "HASH_DRIFT " + rel)
    return raw


def pending_decision():
    return {
        "version": "rung02-curriculum-decision.1", "status": "Pending",
        "package_sha256": PINS[f"{CASE}/package.json"],
        "profile_sha256": PINS[f"{CASE}/expected-profile.json"],
        "registry_sha256": PINS[f"{CASE}/identity-registry.json"],
        "scope": copy.deepcopy(SCOPE), "authority_name": None, "recorded_utc": None,
        "owner_response_evidence": None,
        "notes_fingerings_picking_timing_accepted": False,
        "stable_identities_accepted": False, "single_cell_runtime_eligible": False,
    }


def validate_decision(value):
    """Structural gate only: P02 must separately bind the real owner response.

    No field or test result can manufacture human authority. Production loading
    must additionally pin this entire disposition by a reviewed manifest hash.
    """
    expected = pending_decision()
    need(set(value) == set(expected), "DECISION_FIELDS")
    need(value["status"] == "ACCEPTED", "CURRICULUM_DECISION_PENDING_OR_REJECTED")
    for key in ("version", "package_sha256", "profile_sha256", "registry_sha256", "scope"):
        need(encode(value[key]) == encode(expected[key]), "DECISION_BINDING " + key)
    for key in ("notes_fingerings_picking_timing_accepted", "stable_identities_accepted",
                "single_cell_runtime_eligible"):
        need(value[key] is True, "DECISION_ACCEPTANCE " + key)
    for key in ("authority_name", "recorded_utc", "owner_response_evidence"):
        need(isinstance(value[key], str) and value[key].strip(), "DECISION_ATTRIBUTION " + key)


def verify_case(package, registry, profile, old_package, old_registry):
    need(package == profile["reference_package"] and registry == profile["reference_registry"],
         "PROFILE_BINDING")
    need(len(package["records"]) == 1, "CASE_COUNT")
    record = package["records"][0]
    need(record["id"] == ITEM and record["content_revision"] == 1 and
         record["module_id"] == "fg:module:001141" and
         record["runtime_eligible"] is False, "CASE_ID_OR_ELIGIBILITY")
    need(len(old_package["records"]) == 13 and
         sum(len(r["variants"]) for r in old_package["records"]) == 49, "BASE_SCOPE")
    old_ids = {e["id"] for e in old_registry["entities"]}
    entities = registry["entities"]
    need(len({e["id"] for e in entities}) == len(entities), "DUPLICATE_ENTITY")
    need(not old_ids.intersection(e["id"] for e in entities if e["kind"] in ("item", "module", "variant")),
         "IDENTITY_COLLISION")
    need([v["id"] for v in record["variants"]] == VARIANTS, "VARIANT_IDS")
    need(len(record["events"]) == 16 and len(profile["event_sources"]) == 16, "EVENT_COVERAGE")
    event_ids = [e["event_id"] for e in record["events"]]
    need(len(set(event_ids)) == 16 and set(event_ids) == set(profile["event_sources"]), "EVENT_IDENTITIES")
    from fractions import Fraction
    for i, event in enumerate(record["events"]):
        onset = Fraction(i, 2)
        need(event["onset_q"] == [onset.numerator, onset.denominator] and
             event["duration_q"] == [1, 2], "CONNECTED_EIGHTHS")
    need(all(v["event_ids"] == event_ids and v["tail_pause"] is None for v in record["variants"]),
         "SINGLE_CELL_SCOPE")


def derive(root=ROOT):
    raw = {p: pinned(root, p, digest) for p, digest in PINS.items()}
    package, registry, profile = [parse(raw[f"{CASE}/{name}.json"])
                                  for name in ("package", "identity-registry", "expected-profile")]
    verify_case(package, registry, profile, parse(raw[f"{BASE}/package.json"]),
                parse(raw[f"{BASE}/identity-registry.json"]))
    report = parse(raw[f"{CASE}/native-report.json"])
    need(report["exit_code"] == 2 and report["valid_reference"] is True and
         report["curriculum_playback_authorized"] is False, "NATIVE_BASELINE")
    # Preserve all original manifest bytes and files. Never merge schema0.2/1.
    base_manifest = raw[MANIFEST]
    base = parse(base_manifest)
    need(base["entries"]["package"] == f"{BASE}/package.json", "MANIFEST_ENTRY_DRIFT")
    closure = {MANIFEST: base_manifest}
    for entry in base["files"]:
        data = pinned(root, entry["path"], entry["sha256"])
        need(len(data) == entry["bytes"], "SIZE_DRIFT")
        closure[entry["path"]] = data
    closure.update(raw)
    for entry in [*profile["authority_artifacts"], profile["resource_plan"], *package["sources"].values()]:
        data = pinned(root, entry["path"], entry["sha256"])
        need(entry["path"] not in closure or closure[entry["path"]] == data, "CLOSURE_COLLISION")
        closure[entry["path"]] = data
    # A directly runnable original13 bundle is retained separately for regressions.
    output = {"closure/" + name: data for name, data in closure.items()}
    output["original13/manifest.json"] = base_manifest
    for entry in base["files"]:
        output["original13/" + entry["path"]] = closure[entry["path"]]
    output["decision-needed.json"] = encode(pending_decision())
    output["integration-plan.json"] = encode({
        "version": "rung02-integration-preparation.1", "status": "Pending real Curriculum decision",
        "installable": False, "source_production_released": False,
        "base_manifest_sha256": sha(base_manifest), "scope": SCOPE,
        "base_entry": "original13/manifest.json", "extension_root": "closure",
        "extension_entries": {name: f"{CASE}/{name}.json" for name in ("package", "identity-registry", "expected-profile")},
        "decision": "decision-needed.json", "authority_owner": "Human Curriculum/owner; P02 records and applies",
        "required_order": ["prepare", "real exact-case disposition", "P02 version-bound integration",
                           "fresh installed Learn/Practice/history proof", "independent closure", "P02 small assigned batch"],
    })
    output["inventory.json"] = encode({"version": "astra-preparation-inventory.1", "files": [
        {"path": p, "bytes": len(data), "sha256": sha(data)} for p, data in sorted(output.items())]})
    return output


def write_new(destination, files):
    need(not destination.exists(), "OUTPUT_EXISTS")
    destination.mkdir(parents=True)
    for name, data in sorted(files.items()):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    need(destination.is_relative_to(ROOT / "Build/astra-admission-gate"), "LANE_OUTPUT_ONLY")
    files = derive()
    if args.command == "prepare":
        write_new(destination, files)
    else:
        actual = {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()}
        need(actual == set(files), "OUTPUT_FILE_SET_DRIFT")
        for name, data in files.items():
            need((destination / name).read_bytes() == data, "OUTPUT_DRIFT " + name)
    print(json.dumps({"status": "PREPARED_PENDING_AUTHORITY", "files": len(files),
                      "bytes": sum(map(len, files.values())), "admitted": False, "installed": False}))


if __name__ == "__main__":
    main()
