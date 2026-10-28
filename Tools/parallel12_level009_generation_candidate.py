#!/usr/bin/env python3
"""Build-only Level9 generation metadata and exact four-file adoption preflight."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = Path("Content/controls/curriculum-v1")
OVERLAY = Path("Build/parallel-12/level009-schema1-overlay-r02b")
OUT = Path("Build/parallel-12/level009-generation-preflight-r03")
REVIEW = Path("Results/parallel-02/review/20260923T154000Z-2.3-level009-schema1-overlay-r02b-independent-review-results.md")
PINS = {
    CURRENT / "package.json": "224e4b6eeed97ed3a695ce94f207bcd5436e39dbfaed5b20cbda702ab8c98d90",
    CURRENT / "identity-registry.json": "baad2ee9fc8c4bdb98a948f8064480bee4b2f509ae62132aea15f886f7eda776",
    CURRENT / "expected-profile.json": "19b2cd3c04e150bfa41dcff559627062bbfd7850568ed53f81543b2f4e0f7a7a",
    CURRENT / "generation.json": "7d22dcebbc63aafd2fcfcfd014d7c542e7dadc1f56f3560d3454924b49ff8c61",
    CURRENT / "workbook-coverage.json": "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb",
    OVERLAY / "package.json": "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
    OVERLAY / "identity-registry.json": "5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
    OVERLAY / "expected-profile.json": "21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
    OVERLAY / "native-report.json": "4e3972a5278ad2e76bfaf20cbd6451c1759c323ba6612fbfc8f81a14eecf38f1",
    REVIEW: "c72333a4d9f6a55030dff8c115f8c51d5f852e5662958f6f0edd5c1e9f400c35",
}
FOUR = ("package.json", "identity-registry.json", "expected-profile.json", "generation.json")


class PreflightError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise PreflightError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def check_pins(root=ROOT):
    for path, expected in PINS.items():
        actual = sha((root / path).read_bytes())
        require(actual == expected, f"PIN_DRIFT {path}: {actual} != {expected}")


def load(root, path):
    return json.loads((root / path).read_text())


def workbook_numbers(package, registry):
    from_records = {record["legacy_level"] for record in package["records"]}
    from_registry = {int(e["id"].rsplit(":", 1)[1]) for e in registry["entities"] if e["kind"] == "workbook"}
    require(from_records == from_registry, "WORKBOOK_IDENTITY_MISMATCH")
    return sorted(from_records)


def check_reservations(current_registry, new_entities):
    for kind, plural in (("module", "modules"), ("item", "items"), ("variant", "variants")):
        current = max(int(e["id"].rsplit(":", 1)[1]) for e in current_registry["entities"] if e["kind"] == kind)
        reserved = []
        for entry in current_registry["workbook_catalog"]["entries"]:
            bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
            if bounds:
                require(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds), "RESERVED_RANGE_SHAPE")
                reserved.append(tuple(int(x.rsplit(":", 1)[1]) for x in bounds))
        floor = max([current, *(last for _, last in reserved)]) + 1
        numbers = [int(e["id"].rsplit(":", 1)[1]) for e in new_entities if e["kind"] == kind]
        require(all(number >= floor and all(not first <= number <= last for first, last in reserved) for number in numbers), f"RESERVED_ID_COLLISION {kind}")


def derive(root=ROOT):
    check_pins(root)
    current = {name: load(root, CURRENT / name) for name in FOUR}
    package = load(root, OVERLAY / "package.json")
    registry = load(root, OVERLAY / "identity-registry.json")
    profile = load(root, OVERLAY / "expected-profile.json")
    report = load(root, OVERLAY / "native-report.json")
    current_package, current_registry, current_profile, current_gen = (current[name] for name in FOUR)
    require(len(current_package["records"]) == 551 and len(current_registry["entities"]) == 5687, "CURRENT_SCOPE")
    require(current_gen["records"] == 551 and current_gen["current_entities"] == 5687 and current_gen["variants"] == 4569 and current_gen["events"] == 21661 and current_gen["passages"] == 657, "CURRENT_GENERATION_DRIFT")
    require(workbook_numbers(current_package, current_registry) == current_gen["workbooks"], "CURRENT_WORKBOOK_DRIFT")
    require(len(package["records"]) == 659 and len(registry["entities"]) == 6336 and len(package["sources"]) == 775, "CANDIDATE_SCOPE")
    require(package["records"][:551] == current_package["records"] and registry["entities"][:5687] == current_registry["entities"], "BASELINE_VALUE_DRIFT")
    require(all(package["sources"].get(k) == v for k, v in current_package["sources"].items()), "SOURCE_DRIFT")
    require(package["workbook_catalog"] == registry["workbook_catalog"] == profile["workbook_catalog"] == current_gen["workbook_catalog"], "CATALOG_DRIFT")
    require(len(current_gen["workbook_catalog"]["entries"]) == 105, "CATALOG_COUNT")
    require(profile["reference_package"] == {k: v for k, v in package.items() if k != "workbook_catalog"}, "PROFILE_PACKAGE_DRIFT")
    require(profile["reference_registry"] == {k: v for k, v in registry.items() if k != "workbook_catalog"}, "PROFILE_REGISTRY_DRIFT")
    require(all(profile["event_sources"].get(k) == v for k, v in current_profile["event_sources"].items()), "EVENT_SOURCE_DRIFT")
    new_records = package["records"][551:]
    new_entities = registry["entities"][5687:]
    require(len(new_records) == 108 and len(new_entities) == 649 and all(r["legacy_level"] == 9 and r["runtime_eligible"] is False and r["timing"]["status"] == "unresolved" for r in new_records), "LEVEL9_SCOPE")
    require(all(e["onset_q"] is None and e["duration_q"] is None for r in new_records for e in r["events"]), "INVENTED_TIMING")
    require(len({e["id"] for e in registry["entities"]}) == len(registry["entities"]), "DUPLICATE_ENTITY")
    check_reservations(current_registry, new_entities)
    counts = {"records": len(package["records"]), "current_entities": len(registry["entities"]), "variants": sum(len(r["variants"]) for r in package["records"]), "events": sum(len(r["events"]) for r in package["records"]), "passages": len(package["sources"])}
    require(counts == {"records": 659, "current_entities": 6336, "variants": 5001, "events": 26845, "passages": 775}, "DERIVED_COUNT")
    require(len(profile["event_sources"]) == counts["events"], "EVENT_SOURCE_COVERAGE")
    workbooks = workbook_numbers(package, registry)
    require(workbooks == sorted(current_gen["workbooks"] + [9]), "WORKBOOK_SCOPE")
    level9_catalog = next(e for e in current_gen["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000009")
    level12_catalog = next(e for e in current_gen["workbook_catalog"]["entries"] if e["workbook_id"] == "fg:workbook:000012")
    require(level9_catalog["admitted"] is False and level9_catalog["runtime_eligible"] is False and level9_catalog["imported"] is False, "CATALOG_ADMISSION")
    require(level9_catalog["conversion_status"] == "not_converted" and level12_catalog["conversion_status"] == "not_converted" and 12 in current_gen["workbooks"], "CATALOG_STATUS_PRECEDENT")
    require(report["valid_reference"] is True and report["exit_code"] == 2 and report["curriculum_playback_authorized"] is False and len(report["records"]) == 659, "NATIVE_REFERENCE")
    require(report["package_sha256"] == PINS[OVERLAY / "package.json"] and report["registry_sha256"] == PINS[OVERLAY / "identity-registry.json"] and report["profile_sha256"] == PINS[OVERLAY / "expected-profile.json"], "NATIVE_IDENTITY")
    require(not any(issue["severity"] == "error" for issue in report["issues"]), "NATIVE_ERRORS")
    generation = json.loads(json.dumps(current_gen))
    generation.update(counts)
    generation["workbooks"] = workbooks
    generation["identities"] = {name: PINS[OVERLAY / name] for name in ("package.json", "identity-registry.json", "expected-profile.json")}
    generation["classification"] = "Build-only Level9 659-record nonadmitted reference candidate; no human/runtime admission"
    require(generation["reconciliation"] == current_gen["reconciliation"] and generation["bundle_status"] == current_gen["bundle_status"], "HISTORY_DRIFT")
    require(set(generation) == set(current_gen), "GENERATION_SHAPE")
    require(generation["workbook_catalog"] == current_gen["workbook_catalog"], "CATALOG_DRIFT")
    gen_path = OUT / "generation.json"
    candidate = {name: {"path": str((OVERLAY / name) if name != "generation.json" else gen_path), "sha256": PINS[OVERLAY / name] if name != "generation.json" else sha(encoded(generation)), "bytes": (root / OVERLAY / name).stat().st_size if name != "generation.json" else len(encoded(generation))} for name in FOUR}
    baseline = {name: {"path": str(CURRENT / name), "sha256": PINS[CURRENT / name], "bytes": (root / CURRENT / name).stat().st_size} for name in FOUR}
    preflight = {
        "version": "parallel12-level009-four-file-preflight.1",
        "status": "ready_for_P02_review_only_no_content_write",
        "baseline": baseline,
        "candidate": candidate,
        "rollback_inputs": baseline,
        "unchanged_workbook_coverage": {"path": str(CURRENT / "workbook-coverage.json"), "sha256": PINS[CURRENT / "workbook-coverage.json"], "bytes": (root / CURRENT / "workbook-coverage.json").stat().st_size},
        "review": {"path": str(REVIEW), "sha256": PINS[REVIEW]},
        "native_reference": {"path": str(OVERLAY / "native-report.json"), "sha256": PINS[OVERLAY / "native-report.json"], "valid_reference": True, "runtime_admitted": False},
        "checks": {"baseline_prefix_exact": True, "candidate_counts_derived": counts, "catalog_105_value_identical": True, "workbooks_from_records_and_registry": workbooks, "reserved_identity_ranges_clear": True, "native_valid_reference": True, "generation_reconciliation_history_preserved": True, "generation_shape_preserved": True},
        "catalog_status_distinction": {"workbook_id": "fg:workbook:000009", "status": "Generation workbooks denotes candidate record/entity presence; the unchanged catalog row remains source-inventory metadata, not_converted and explicitly empty for playable projection. Current Level12 is the precedent: it appears in generation.workbooks while its catalog row remains not_converted. No catalog status change is proposed.", "level12_precedent_checked": True, "catalog_change_proposed": False},
        "required_next_step": "P02 independent four-file review, then P02-owned staged atomic adoption/rollback and post-write native/catalog checks; no admission claim",
    }
    return generation, preflight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    command = parser.parse_args().command
    generation, preflight = derive()
    if command == "build":
        (ROOT / OUT).mkdir(parents=True, exist_ok=True)
        (ROOT / OUT / "generation.json").write_bytes(encoded(generation))
        (ROOT / OUT / "adoption-preflight.json").write_bytes(encoded(preflight))
    else:
        require((ROOT / OUT / "generation.json").read_bytes() == encoded(generation), "GENERATION_OUTPUT_DRIFT")
        require((ROOT / OUT / "adoption-preflight.json").read_bytes() == encoded(preflight), "PREFLIGHT_OUTPUT_DRIFT")
    print(json.dumps({"status": preflight["status"], "counts": preflight["checks"]["candidate_counts_derived"], "workbooks": generation["workbooks"], "catalog_status_distinction_recorded": True}, sort_keys=True))


if __name__ == "__main__":
    main()
