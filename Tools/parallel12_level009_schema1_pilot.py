#!/usr/bin/env python3
"""Detached Level 9 schema1 proposal pinned to reviewed candidate C; no import."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("Build/parallel-10/2.3-legacy-id-reconciliation-r01/candidate-c")
AGG = Path("Build/parallel-11/2.3.1.1.1-level009-whole-r01/aggregate-final-a.json")
TXT = Path("Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt")
PDF = Path("Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf")
OUT = Path("Build/parallel-12/level009-schema1-pilot-r01")
OVERLAY = Path("Build/parallel-12/level009-schema1-overlay-r02b")
PDF_PAGES = Path("Build/parallel-12/level009-schema1-overlay-r02/pdf-pages.json")
CURRENT = Path("Content/controls/curriculum-v1")
REPORT = Path("Build/parallel-02/551-baseline-r01/current-native-report.json")
ALLOCATION_551 = Path("Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence/allocation01/cumulative-allocation.json")
OVERLAY_PINS = {
    CURRENT / "package.json": "224e4b6eeed97ed3a695ce94f207bcd5436e39dbfaed5b20cbda702ab8c98d90",
    CURRENT / "identity-registry.json": "baad2ee9fc8c4bdb98a948f8064480bee4b2f509ae62132aea15f886f7eda776",
    CURRENT / "expected-profile.json": "19b2cd3c04e150bfa41dcff559627062bbfd7850568ed53f81543b2f4e0f7a7a",
    OUT / "proposal.json": "f1cfd7cf8e00ac31584346159f7f6232d025d00c6b3fd7a591ad8ea3dc27cf07",
    OUT / "transaction.json": "8bf0b3558742c1366acab37b05287c030e1d53c6821eed02ecf77ac549855fd8",
    PDF_PAGES: "aa16c74a939ae8405df7efef930f4aa6b6429b04034762a7fc81e9f5eec8344c",
    REPORT: "0ce8213a599c13758bcd5a24b78d5324812fc9b74cc6160b9cb1fa4618200d26",
    ALLOCATION_551: "c3af58329f0b7ad1cfa9252eae05d7dfafe27218bfdb4b693eb0b2be2794c73f",
}
PINS = {
    BASE / "package.json": "224e4b6eeed97ed3a695ce94f207bcd5436e39dbfaed5b20cbda702ab8c98d90",
    BASE / "identity-registry.json": "baad2ee9fc8c4bdb98a948f8064480bee4b2f509ae62132aea15f886f7eda776",
    BASE / "expected-profile.json": "19b2cd3c04e150bfa41dcff559627062bbfd7850568ed53f81543b2f4e0f7a7a",
    BASE / "generation.json": "7d22dcebbc63aafd2fcfcfd014d7c542e7dadc1f56f3560d3454924b49ff8c61",
    AGG: "bf3744f105814d986dee84cb6742a1809698c7d97010a6cfde92b561cdf2f9d4",
    TXT: "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105",
    PDF: "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f",
}
STRINGS = {"E": (1, 40), "A": (2, 45), "D": (3, 50), "G": (4, 55), "B": (5, 59), "e": (6, 64)}


class ProposalError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialized(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def pin_inputs(root=ROOT):
    for path, expected in PINS.items():
        actual = digest((root / path).read_bytes())
        if actual != expected:
            raise ProposalError(f"BASELINE_MISMATCH {path}: {actual} != {expected}; rebase required")


def pin_overlay_inputs(root=ROOT):
    for path, expected in {**PINS, **OVERLAY_PINS}.items():
        actual = digest((root / path).read_bytes())
        if actual != expected:
            raise ProposalError(f"BASELINE_MISMATCH {path}: {actual} != {expected}; rebase required")


def require(condition, code):
    if not condition:
        raise ProposalError(code)


def suffix(identifier):
    return int(identifier.rsplit(":", 1)[1])


def source_check(row, text_lines):
    number, code = row["exercise_number"], row["code"]
    ref = row["source_refs"]["txt"]
    match = re.fullmatch(r"L9-TXT1-(\d+)-(\d+)", ref)
    require(match is not None, "SOURCE_REF_SHAPE")
    first, last = map(int, match.groups())
    require(1 <= first <= last <= len(text_lines), "SOURCE_SPAN")
    passage = text_lines[first - 1:last]
    require(passage[0] == f"Exercise {number:03d}: {code}", "SOURCE_HEADING")
    for direction in row["directions"]:
        require(all(route["source_tab_row"] in passage for route in direction["sequential_one_string_routes"]), "SOURCE_TAB_ROW")
    require(re.fullmatch(r"L9-PDF1-p\d+", row["source_refs"]["pdf"]) is not None, "PDF_REF_SHAPE")
    return {"txt": ref, "pdf": row["source_refs"]["pdf"], "passage_sha256": digest("\n".join(passage).encode())}


def build(root=ROOT):
    pin_inputs(root)
    base = json.loads((root / BASE / "package.json").read_text())
    registry = json.loads((root / BASE / "identity-registry.json").read_text())
    aggregate = json.loads((root / AGG).read_text())
    lines = (root / TXT).read_text().splitlines()
    require(lines[5] == "MOVEMENT RULE" and lines[18] == "PRACTICE RULE", "SOURCE_RULES")
    require(len(base["records"]) == 551 and not any(r["legacy_level"] == 9 for r in base["records"]), "BASELINE_SCOPE")
    require(len(aggregate["records"]) == 108, "AGGREGATE_SCOPE")
    existing = {e["id"] for e in registry["entities"]}
    require("fg:workbook:000009" not in existing, "WORKBOOK_ALREADY_ALLOCATED")
    next_module = max(suffix(x) for x in existing if x.startswith("fg:module:")) + 1
    next_item = max(suffix(x) for x in existing if x.startswith("fg:item:")) + 1
    next_variant = max(suffix(x) for x in existing if x.startswith("fg:variant:")) + 1
    entities = [{"id": "fg:workbook:000009", "kind": "workbook", "label": "Legacy Level9 mid-pattern position transfer", "parent": "fg:course:000001"}]
    records, allocations, source_map = [], {}, []
    for index, row in enumerate(aggregate["records"]):
        number = index + 1
        require(row["exercise_number"] == number and row["source_local_key"] == f"L9-set{(index // 12) + 1:02d}-ex{number:03d}", "AGGREGATE_ORDER")
        require(row["fixed_bpm"] is None and row["note_per_click"] is None and row["onset_q"] is None and row["duration_q"] is None, "UNSUPPORTED_TIMING")
        require(row["canonical_item_id"] is None and row["canonical_variant_id"] is None and not row["admitted"] and not row["runtime_eligible"], "INVALID_AUTHORITY")
        source = source_check(row, lines)
        module = f"fg:module:{next_module + index:06d}"
        item = f"fg:item:{next_item + index:06d}"
        entities.extend([
            {"id": module, "kind": "module", "label": f"Level9 Exercise {number:03d} {row['code']}", "parent": "fg:workbook:000009"},
            {"id": item, "kind": "item", "label": f"Exercise {number:03d} {row['code']} position transfer", "parent": module},
        ])
        refs = [source["txt"], source["pdf"], "L9-TXT1-1-26"]
        events, variants, occurrence_map, variant_map = [], [], {}, {}
        require(len(row["directions"]) == 2, "DIRECTION_COUNT")
        for direction_index, direction in enumerate(row["directions"]):
            name = ("shift_up", "shift_down")[direction_index]
            require(direction["direction"] == name, "DIRECTION_ORDER")
            expected_route = ["E", "A", "D", "G", "B", "e"] if name == "shift_up" else ["e", "B", "G", "D", "A", "E"]
            require(direction["route_order"] == expected_route and direction["position_order"] == (["P5", "P7"] if name == "shift_up" else ["P7", "P5"]), "ROUTE_POSITION")
            start = len(events)
            for route_index, route in enumerate(direction["sequential_one_string_routes"]):
                string_name = expected_route[route_index]
                require(route["string"] == string_name and route["shift_after_note"] == 2 and route["whole_hand_frame_shift_frets"] == (2 if name == "shift_up" else -2) and route["melodic_interval_inferred"] is False, "SHIFT_SEMANTICS")
                require(len(route["notes"]) == 4, "ROUTE_NOTES")
                for ordinal, note in enumerate(route["notes"], 1):
                    require(note["ordinal"] == ordinal and note["string"] == string_name and note["position"] == direction["position_order"][(ordinal - 1) // 2], "NOTE_ORDER")
                    require(note["onset_q"] is None and note["duration_q"] is None, "UNSUPPORTED_TIMING")
                    require(note["finger_digit"] == row["code"][ordinal - 1] and note["fret"] == (5 if name == "shift_up" else 7) + (0 if ordinal <= 2 else (2 if name == "shift_up" else -2)) + int(note["finger_digit"]) - 1, "FRET_FINGER")
                    event_id = f"{item}:event:{len(events) + 1:04d}"
                    string_number, open_midi = STRINGS[string_name]
                    events.append({"kind": "note", "string": string_number, "fret": note["fret"], "midi": open_midi + note["fret"], "spelling": None, "degree_contexts": {}, "finger": int(note["finger_digit"]), "onset_q": None, "duration_q": None, "attack": "picked", "tie_from": None, "event_id": event_id})
                    occurrence_map[f"{name}:{string_name}:{ordinal}"] = event_id
            selected = [e["event_id"] for e in events[start:]]
            require(len(selected) == 24, "DIRECTION_EVENTS")
            for pick_index, pick in enumerate(("D", "U")):
                variant_id = f"fg:variant:{next_variant + index * 4 + direction_index * 2 + pick_index:06d}"
                label = f"{name}-{pick}"
                entities.append({"id": variant_id, "kind": "variant", "label": label, "parent": item})
                variant_map[label] = variant_id
                variants.append({"id": variant_id, "label": label, "event_ids": selected, "source_refs": refs, "route": name, "pick_start": pick, "pick_start_origin": "learner_configuration", "accent_policy": "source_unspecified", "role": "notation_practice", "grouping": {"kind": "unresolved", "notes_per_beat": None, "beat_unit_q": None, "marking_factor": [1, 1], "source_label": "Straight eighths/sixteenths and click pacing are practice directions without a fixed quarter-note event mapping"}, "tail_pause": None, "unresolved": ["Metrical beat and event duration are not fixed by source."]})
        require(len(events) == 48 and len(variants) == 4, "RECORD_COVERAGE")
        timing_exception = "No fixed BPM, metrical beat unit, onset or duration: start 8–12 BPM below Level 8 is relative to an unknown learner tempo; straight eighths/sixteenths and D/U starts are practice choices."
        practice_rules = ["Pass 1 stops after notes 1–2, releases and relocates before notes 3–4; no authored stop duration.", "Pass 2 removes the stop, uses straight eighths, lightly accents note 3, removes that accent, then converts to sixteenths; no fixed quarter-note grid.", "After three clean loops add 2 BPM next session; after two missed landings, slides or rising tension reduce 4–6 BPM; these are relative progression rules, not fixed record BPM.", "Advance after a full clean set in both directions on two separate days; no automatic mastery inference."]
        record = {"id": item, "workbook_id": "fg:workbook:000009", "module_id": module, "legacy_level": 9,
                  "title": f"Exercise {number:03d}: {row['code']} — mid-pattern position transfer", "kind": "notation", "content_revision": 1,
                  "status": "converted_candidate", "runtime_eligible": False, "source_refs": refs, "authored_text_refs": refs,
                  "normalization": [{"kind": "representation_metadata", "basis": "P11 whole-Level9 source mapping and original TXT/PDF; position change is a whole-hand frame shift", "text": "Two distinct directions, each six sequential one-string routes. The bar after note two marks a 2-fret position shift, not a melodic interval; D/U starts are learner choices. Candidate only."}],
                  "context": {"local_code": row["code"], "route": "shift_up E-A-D-G-B-e; shift_down e-B-G-D-A-E", "position": "P5 to P7 and P7 to P5; shift after note 2", "pick_start": "D or U selected by learner", "pick_start_variants": ["D", "U"], "source_tempo_rules_ref": "L9-TXT1-1-26", "tuning_open_midi": [40, 45, 50, 55, 59, 64], "capo": 0},
                  "events": events, "timing": {"status": "unresolved", "unit": "quarter", "basis": "ASCII spacing and relative tempo directions do not define quarter-note spans", "other_source_requirements": [timing_exception, *practice_rules]},
                  "rubric": None, "resource_requirements": [], "ambiguities": [timing_exception],
                  "control_scope": {"local_case": f"Exercise {number:03d} {row['code']} whole printed case", "extent": "complete_selected_case", "whole_workbook_complete": False, "source_event_count": 48, "basis_refs": refs, "unresolved": [timing_exception]},
                  "variants": variants, "lineage": {"kind": "new"}}
        records.append(record)
        allocations[item] = {"legacy_level": 9, "occurrences": occurrence_map, "variants": variant_map}
        source_map.append({"item_id": item, "source_local_key": row["source_local_key"], "exercise_number": number, "code": row["code"], **source})
    require(not existing.intersection(e["id"] for e in entities), "ALLOCATION_COLLISION")
    require(len({e["id"] for e in entities}) == len(entities), "ALLOCATION_DUPLICATE")
    proposal = {"proposal_version": "parallel12-level009-schema1-pilot.1", "classification": "detached_nonadmitted_schema1_record_proposals", "schema_version": "1.0.0-curriculum-candidate", "baseline": {str(k): v for k, v in PINS.items()}, "records": records}
    transaction = {"version": "parallel12-provisional-allocation-transaction.1", "baseline_package_sha256": PINS[BASE / "package.json"], "baseline_registry_sha256": PINS[BASE / "identity-registry.json"], "rebase_if_baseline_changes": True, "mode": "append_only_new_lineage", "existing_record_count": 551, "existing_entity_count": len(existing), "new_entities": entities, "records": allocations, "source_map": source_map}
    verify(proposal, transaction)
    return proposal, transaction


def verify(proposal, transaction):
    require(proposal["baseline"][str(BASE / "package.json")] == transaction["baseline_package_sha256"] == PINS[BASE / "package.json"], "INVALID_AUTHORITY")
    require(proposal["baseline"][str(BASE / "identity-registry.json")] == transaction["baseline_registry_sha256"] == PINS[BASE / "identity-registry.json"], "INVALID_AUTHORITY")
    require(transaction["mode"] == "append_only_new_lineage" and transaction["rebase_if_baseline_changes"] is True and transaction["existing_record_count"] == 551, "INVALID_AUTHORITY")
    records = proposal["records"]
    require(len(records) == 108 and len(transaction["records"]) == 108 and len(transaction["new_entities"]) == 649, "COVERAGE")
    ids = [r["id"] for r in records]
    require(len(set(ids)) == 108 and set(ids) == set(transaction["records"]), "IDENTITY_COVERAGE")
    for r in records:
        require(r["status"] == "converted_candidate" and r["runtime_eligible"] is False and r["lineage"] == {"kind": "new"} and r["content_revision"] == 1, "INVALID_AUTHORITY")
        require(r["timing"]["status"] == "unresolved" and len(r["events"]) == 48 and len(r["variants"]) == 4, "RECORD_SHAPE")
        require(all(e["onset_q"] is None and e["duration_q"] is None for e in r["events"]), "UNSUPPORTED_TIMING")
        require(all(v["grouping"]["kind"] == "unresolved" and v["grouping"]["notes_per_beat"] is None and v["grouping"]["beat_unit_q"] is None for v in r["variants"]), "UNSUPPORTED_TIMING")
        require("fixed_bpm" not in r and len(transaction["records"][r["id"]]["occurrences"]) == 48 and len(transaction["records"][r["id"]]["variants"]) == 4, "ALLOCATION_COVERAGE")
    return {"records": len(records), "events": sum(len(r["events"]) for r in records), "variants": sum(len(r["variants"]) for r in records), "new_entities": len(transaction["new_entities"]), "timing_status": "unresolved", "authority": "provisional"}


def allocation_floor(registry, kind):
    current = max(suffix(e["id"]) for e in registry["entities"] if e["kind"] == kind)
    plural = {"item": "items", "module": "modules", "variant": "variants"}[kind]
    ranges = []
    for entry in registry["workbook_catalog"]["entries"]:
        bounds = entry.get("reserved_playable_identity_ranges", {}).get(plural)
        if bounds is not None:
            require(len(bounds) == 2 and all(x.startswith(f"fg:{kind}:") for x in bounds), "RESERVATION_SHAPE")
            first, last = map(suffix, bounds)
            require(first <= last, "RESERVATION_SHAPE")
            ranges.append((first, last, entry["workbook_id"]))
    return max([current, *(last for _, last, _ in ranges)]) + 1, ranges


def assert_not_reserved(entities, registry):
    for kind in ("item", "module", "variant"):
        floor, ranges = allocation_floor(registry, kind)
        current = max(suffix(e["id"]) for e in registry["entities"] if e["kind"] == kind)
        for entity in entities:
            if entity["kind"] != kind:
                continue
            number = suffix(entity["id"])
            require(number > current, f"CURRENT_ID_COLLISION {kind} {entity['id']}")
            require(all(not first <= number <= last for first, last, _ in ranges), f"RESERVED_ID_COLLISION {kind} {entity['id']}")
            require(number >= floor, f"RESERVED_HIGH_WATER {kind} {entity['id']}")


def rebase_reserved_ids(proposal, transaction, registry):
    proposal = json.loads(json.dumps(proposal))
    transaction = json.loads(json.dumps(transaction))
    mapping = {}
    for kind in ("module", "item", "variant"):
        old = sorted((e["id"] for e in transaction["new_entities"] if e["kind"] == kind), key=suffix)
        floor, _ = allocation_floor(registry, kind)
        mapping.update({identity: f"fg:{kind}:{floor + index:06d}" for index, identity in enumerate(old)})
    for entity in transaction["new_entities"]:
        entity["id"] = mapping.get(entity["id"], entity["id"])
        entity["parent"] = mapping.get(entity["parent"], entity["parent"])
    rebased = {}
    for record in proposal["records"]:
        old_item = record["id"]
        record["id"] = mapping[old_item]
        record["module_id"] = mapping[record["module_id"]]
        event_mapping = {}
        for event in record["events"]:
            old = event["event_id"]
            event["event_id"] = record["id"] + old[len(old_item):]
            event_mapping[old] = event["event_id"]
        for variant in record["variants"]:
            variant["id"] = mapping[variant["id"]]
            variant["event_ids"] = [event_mapping[x] for x in variant["event_ids"]]
        allocated = transaction["records"][old_item]
        allocated["occurrences"] = {k: event_mapping[v] for k, v in allocated["occurrences"].items()}
        allocated["variants"] = {k: mapping[v] for k, v in allocated["variants"].items()}
        rebased[record["id"]] = allocated
    transaction["records"] = rebased
    for source in transaction["source_map"]:
        source["item_id"] = mapping[source["item_id"]]
    assert_not_reserved(transaction["new_entities"], registry)
    verify(proposal, transaction)
    return proposal, transaction


def overlay_build(root=ROOT):
    pin_overlay_inputs(root)
    baseline_package = json.loads((root / CURRENT / "package.json").read_text())
    baseline_registry = json.loads((root / CURRENT / "identity-registry.json").read_text())
    baseline_profile = json.loads((root / CURRENT / "expected-profile.json").read_text())
    proposal = json.loads((root / OUT / "proposal.json").read_text())
    transaction = json.loads((root / OUT / "transaction.json").read_text())
    report = json.loads((root / REPORT).read_text())
    allocation_551 = json.loads((root / ALLOCATION_551).read_text())
    pdf_pages = json.loads((root / PDF_PAGES).read_text())
    require(pdf_pages["source_pdf_sha256"] == PINS[PDF] and len(pdf_pages["pages"]) == 10, "PDF_EXTRACT_AUTHORITY")
    require(report["valid_reference"] is True and report["exit_code"] == 2 and len(report["records"]) == 551, "PREDECESSOR_AUTHORITY")
    require(report["package_sha256"] == OVERLAY_PINS[CURRENT / "package.json"] and report["registry_sha256"] == OVERLAY_PINS[CURRENT / "identity-registry.json"], "PREDECESSOR_AUTHORITY")
    require([r["preserved_record"] for r in report["records"]] == baseline_package["records"], "PREDECESSOR_RECORDS")
    require(len(allocation_551["records"]) == 551 and set(allocation_551["records"]) == {r["id"] for r in baseline_package["records"]}, "ALLOCATION_BASELINE")
    verify(proposal, transaction)
    proposal, transaction = rebase_reserved_ids(proposal, transaction, baseline_registry)
    require(len(baseline_registry["entities"]) == transaction["existing_entity_count"], "IDENTITY_BASELINE")
    package = json.loads(json.dumps(baseline_package))
    registry = json.loads(json.dumps(baseline_registry))
    profile = json.loads(json.dumps(baseline_profile))
    package["content_version"] = "curriculum-v1-level009-659-build-only-candidate.1"
    package["records"].extend(proposal["records"])
    registry["entities"].extend(transaction["new_entities"])
    lines = (root / TXT).read_text().splitlines()
    def passage(first, last):
        require(1 <= first <= last <= len(lines), "SOURCE_SPAN")
        value = "\n".join(lines[first - 1:last])
        return {"path": str(TXT), "sha256": PINS[TXT], "format": "txt", "first_line": first, "last_line": last, "text": value, "text_sha256": digest(value.encode())}
    package["sources"]["L9-TXT1-1-26"] = passage(1, 26)
    for source in transaction["source_map"]:
        ref = source["txt"]
        match = re.fullmatch(r"L9-TXT1-(\d+)-(\d+)", ref)
        require(match is not None, "SOURCE_REF_SHAPE")
        first, last = map(int, match.groups())
        package["sources"][ref] = passage(first, last)
        pdf_ref = source["pdf"]
        page = int(pdf_ref.rsplit("p", 1)[1])
        pdf_text = pdf_pages["pages"][str(page)]
        require(re.search(rf"\b{source['exercise_number']:03d}\b\s+{source['code']}\b", pdf_text) is not None, "PDF_EXTRACT_FIDELITY")
        package["sources"][pdf_ref] = {"path": str(PDF), "sha256": PINS[PDF], "format": "pdf", "page": page, "text": pdf_text, "text_sha256": digest(pdf_text.encode())}
    require(len(package["records"]) == 659 and len(registry["entities"]) == 6336 and len(package["sources"]) == 775, "OVERLAY_COVERAGE")
    identity_baseline = {k: baseline_registry[k] for k in ("identity_version", "entities", "rules")}
    lineage_baseline = {"version": "lineage-baseline.1", "records": {r["id"]: {"content_revision": r["content_revision"], "record_sha256": r["record_sha256"]} for r in report["records"]}}
    candidate_allocation = {"version": "control-allocation.1", "authority": "P12 Build-only Level9 append-only proposal bound to P02 adopted 551 reference; no import or admission", "records": {**allocation_551["records"], **transaction["records"]}}
    artifact_payloads = {
        OVERLAY / "identity-baseline.json": identity_baseline,
        OVERLAY / "lineage-baseline.json": lineage_baseline,
        OVERLAY / "candidate-allocation.json": candidate_allocation,
    }
    # The frozen validator's 32 MiB JSON limit excludes the 107 MiB aggregate
    # 551-record report. Retain the exact r13/r14 authority chain that native
    # validation already used for current Content; append only the new allocation.
    removed_roles = {"candidate_identity_allocation"}
    profile["authority_artifacts"] = [a for a in profile["authority_artifacts"] if a["role"] not in removed_roles]
    for path, role in [(OVERLAY / "candidate-allocation.json", "candidate_identity_allocation")]:
        sha = digest(serialized(artifact_payloads[path])) if path in artifact_payloads else OVERLAY_PINS[path]
        profile["authority_artifacts"].append({"path": str(path), "role": role, "sha256": sha})
    profile["reference_package"] = {k: v for k, v in package.items() if k != "workbook_catalog"}
    profile["reference_registry"] = {k: v for k, v in registry.items() if k != "workbook_catalog"}
    profile["event_sources"].update({e["event_id"]: r["source_refs"][0] for r in proposal["records"] for e in r["events"]})
    summary = {"status": "build_only_nonadmitted", "baseline_records": 551, "new_records": 108, "total_records": 659, "baseline_entities": 5687, "new_entities": 649, "total_entities": 6336, "sources": len(package["sources"]), "new_event_sources": 5184, "baseline_package_sha256": OVERLAY_PINS[CURRENT / "package.json"], "native_lineage_authority": "existing r13 515-record baseline plus r14 allocation chain", "proposed_next_baselines_bound_to_native": False, "rebase_if_baseline_changes": True, "native_admission_claim": False}
    artifacts = {**artifact_payloads, OVERLAY / "corrected-proposal.json": proposal, OVERLAY / "corrected-transaction.json": transaction, OVERLAY / "package.json": package, OVERLAY / "identity-registry.json": registry, OVERLAY / "expected-profile.json": profile, OVERLAY / "overlay-summary.json": summary}
    overlay_verify(artifacts, baseline_package, baseline_registry, proposal, transaction)
    return artifacts


def overlay_verify(artifacts, baseline_package, baseline_registry, proposal, transaction):
    package, registry = artifacts[OVERLAY / "package.json"], artifacts[OVERLAY / "identity-registry.json"]
    require(package["records"][:551] == baseline_package["records"] and registry["entities"][:5687] == baseline_registry["entities"], "BASELINE_REMAP")
    require(all(r["timing"]["status"] == "unresolved" and all(e["onset_q"] is None and e["duration_q"] is None for e in r["events"]) for r in package["records"][551:]), "UNSUPPORTED_TIMING")
    require(all(r["runtime_eligible"] is False and r["lineage"] == {"kind": "new"} for r in package["records"][551:]), "INVALID_AUTHORITY")
    require(package["records"][551:] == proposal["records"] and registry["entities"][5687:] == transaction["new_entities"], "PROPOSAL_DRIFT")
    require(artifacts[OVERLAY / "corrected-proposal.json"] == proposal and artifacts[OVERLAY / "corrected-transaction.json"] == transaction, "TRANSACTION_DRIFT")
    require(len(artifacts[OVERLAY / "candidate-allocation.json"]["records"]) == 659, "ALLOCATION_COVERAGE")
    return artifacts[OVERLAY / "overlay-summary.json"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify", "overlay-build", "overlay-verify"])
    args = parser.parse_args()
    out = ROOT / OUT
    if args.command == "overlay-build":
        artifacts = overlay_build()
        (ROOT / OVERLAY).mkdir(parents=True, exist_ok=True)
        for path, value in artifacts.items():
            (ROOT / path).write_bytes(serialized(value))
        print(json.dumps(artifacts[OVERLAY / "overlay-summary.json"], sort_keys=True))
        return
    if args.command == "overlay-verify":
        expected = overlay_build()
        for path, value in expected.items():
            require((ROOT / path).read_bytes() == serialized(value), f"OUTPUT_DRIFT {path}")
        print(json.dumps(expected[OVERLAY / "overlay-summary.json"], sort_keys=True))
        return
    if args.command == "build":
        proposal, transaction = build()
        out.mkdir(parents=True, exist_ok=True)
        (out / "proposal.json").write_bytes(serialized(proposal))
        (out / "transaction.json").write_bytes(serialized(transaction))
    else:
        pin_inputs()
        proposal = json.loads((out / "proposal.json").read_text())
        transaction = json.loads((out / "transaction.json").read_text())
        expected = build()
        require(serialized(proposal) == serialized(expected[0]) and serialized(transaction) == serialized(expected[1]), "OUTPUT_DRIFT")
    print(json.dumps(verify(proposal, transaction), sort_keys=True))


if __name__ == "__main__":
    main()
