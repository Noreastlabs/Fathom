#!/usr/bin/env python3
"""Seal the exact Level 44 private exercise contracts from pinned source and prior work."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESERVATION = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-a44-reservation.json"
PRIOR = ROOT / "Build/fullscope-private-a-r01/level044-r08/packet.jsonl"
INDEX = ROOT / "Build/fullscope-private-a-r01/semantic-overlay-index-r13/effective-range-index.jsonl"
OUT = ROOT / "Build/exercise-impl-shard-a44-r01"
RESULTS = ROOT / "Results/exercise-impl-shard-a44-r01"

PINS = {
    "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-a44-full-template-prompt.md": "5cc1934cf36a3fb593e0988b57c55d17351aa8be89db3d1f72f3ed6761f9689d",
    "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-a44-reservation.json": "e1c54a9a14b5c784677d3ad3853ae7173d0a51dd9ca696da3edb03dd182168d1",
    "Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl": "dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c",
    "Planning/Fathom-Exercise-WBS-Annex-v1.json": "a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1",
    "Build/fullscope-private-a-r01/semantic-overlay-index-r13/effective-range-index.jsonl": "6786cbcbf1982207ad0d0a815ff96b44426c88c442548f1a8d0a8661bb255945",
    "Build/fullscope-private-a-r01/level044-r08/packet.jsonl": "2ebdce031b7ddf40f8702147def889cfb75f12b7ca94f71ce97840036d2aabb7",
    "Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_44_A_Blues_Resolution_Vocabulary_Lick_Construction_and_Functional_Turnarounds_Fixed_Key_A.txt": "fcbc0712e7e874c08a936a59f14bfe6fe4d57fa8c92ccf9f6e8badb76fcc8217",
    "Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_44_A_Blues_Resolution_Vocabulary_Lick_Construction_and_Functional_Turnarounds_Fixed_Key_A.pdf": "f06b408d2cdedfc7d68ccb36bef7e18929d55eab60e0ee8dc172bbecf6098677",
}

PDF_GUIDANCE = {
    "A": (3, "Play fretted C# first; match bend, slide, and legato to the exact half-step target. A later blue-third shade is not this page's target."),
    "C": (5, "Wound-string fourth method is a silent shift; whole-step bends apply on G, B, and high e only. Stop if painful."),
    "D": (8, "Keep the eight sounding events in order across straight eighth, shuffle, syncopated sixteenth, and burst-plus-space engines."),
    "E": (9, "Play call, leave one beat of silence, then answer; later shorten the silence without merging phrases."),
    "F": (11, "Copy degree pattern, not fret distances; core lick A P5 extends to fret 19."),
    "G": (13, "Preserve degree order, contour, or rhythmic profile across register change."),
    "H": (14, "Play each pair back to back; tonic A closes, E points toward the V chord in bar 12."),
    "I": (16, "Practice over bars 11 and 12 of a twelve-bar backing track and count both bars aloud."),
    "J": (17, "Leave a small breath between opening and ending; adjust connecting octave or string only when needed while preserving degree function."),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> str:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    return digest(data)


def memory_proxy() -> dict:
    text = subprocess.check_output(["vm_stat"], text=True)
    page_size = int(re.search(r"page size of (\d+) bytes", text).group(1))
    pages = {k: int(v.replace(".", "")) for k, v in re.findall(r"^([^:\n]+):\s+([\d.]+)", text, re.M)}
    active = pages.get("Pages active", 0)
    wired = pages.get("Pages wired down", 0)
    compressed = pages.get("Pages occupied by compressor", 0)
    proxy = (active + wired + compressed) * page_size / 2**30
    ps = subprocess.check_output(["ps", "-axo", "rss="], text=True)
    peak_rss_kib = max(map(int, ps.split()))
    return {"page_size": page_size, "active_pages": active, "wired_pages": wired,
            "occupied_compressor_pages": compressed, "proxy_gib": round(proxy, 3),
            "process_peak_rss_kib": peak_rss_kib}


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip() != str(ROOT):
        raise ValueError("wrong Git root")
    for rel, expected in PINS.items():
        actual = digest((ROOT / rel).read_bytes())
        if actual != expected:
            raise ValueError(f"pin drift: {rel}: {actual}")
    register = (ROOT / "Prompts/parallel-02/Lane-Reservations-Current.md").read_text()
    if "A44/B52/C81 exact 193-key private implementation lease transfer; OPEN_AT_MANAGER_DISPATCH" not in register:
        raise ValueError("P02 open lease not found")
    reservation = json.loads(RESERVATION.read_text())
    keys = reservation["keys"]
    if len(keys) != 46 or len(set(keys)) != 46:
        raise ValueError("reservation key census")
    if digest(("\n".join(sorted(keys)) + "\n").encode()) != reservation["key_set_sha256"]:
        raise ValueError("key set hash")
    index = {x["package_key"]: x for x in map(json.loads, INDEX.read_text().splitlines()) if x["package_key"] in keys}
    prior = {x["package_key"]: x for x in map(json.loads, PRIOR.read_text().splitlines()) if x["package_key"] in keys}
    if set(index) != set(keys) or set(prior) != set(keys):
        raise ValueError("prior/index key mismatch")
    source_path = next(p for p in PINS if p.endswith(".txt"))
    source_lines = (ROOT / source_path).read_text().splitlines()
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_records = []
    batches = []
    for start in range(0, len(keys), 12):
        group = []
        for key in keys[start:start+12]:
            p = prior[key]
            s = p["source_payload"]
            refs = p["source_refs"]
            for ref in refs:
                if digest((ROOT / ref["path"]).read_bytes()) != ref["sha256"]:
                    raise ValueError(f"source hash drift: {key}")
            loc = refs[0]["locator"]
            if not (1 <= loc["line_start"] <= loc["line_end"] <= len(source_lines)):
                raise ValueError(f"TXT locator invalid: {key}")
            excerpt = source_lines[loc["line_start"]-1:loc["line_end"]]
            for line in s["exact_unit_lines"]:
                if line and line not in excerpt:
                    raise ValueError(f"TXT excerpt mismatch: {key}: {line}")
            for block in s["notation_blocks"]:
                for row in block["notation_rows"]:
                    if row["line"] < loc["line_start"] or row["line"] > loc["line_end"]:
                        raise ValueError(f"row locator outside unit: {key}")
                    if row["body"] not in source_lines[row["line"]-1]:
                        raise ValueError(f"notation row mismatch: {key}: {row['line']}")
            imp = p["implementation"]
            module = imp.get("source_module") or "J"
            page, pdf_instruction = PDF_GUIDANCE[module]
            if module == "F" and "core-lick-b" in key:
                page, pdf_instruction = 12, "Descend through the blue note and close on A in every frame; name A-G-E-Eb-D-C-A before each version."
            if page not in refs[1]["locator"]["physical_pages"] and module not in {"D", "E", "F", "H"}:
                raise ValueError(f"PDF page locator mismatch: {key}")
            contacts = []
            for c in imp["ordered_contacts"]:
                line_no = c.get("source_line")
                fret = c.get("fret")
                if line_no and (line_no < loc["line_start"] or line_no > loc["line_end"] or str(fret) not in source_lines[line_no-1]):
                    raise ValueError(f"contact source mismatch: {key}: {line_no}/{fret}")
                contact = {k: c.get(k) for k in ("ordinal", "kind", "block_index", "grid_column", "string_label", "string_low_to_high", "fret", "physical_fret", "finger", "note_spelling", "midi", "source_line", "source_column_1based", "technique_symbols", "technique_origin_contact_ordinal", "bend_interval_semitones", "attack", "pick_attack", "onset_q", "duration_q", "acoustic_gate_q")}
                contact["fret_role"] = "sounding_equivalent_target" if c.get("physical_fret") is not None and c["physical_fret"] != c["fret"] else "physical_fret"
                contacts.append(contact)
            contract = {"schema_version": "fathom-private-exercise-contract-a44.1", "package_key": key,
                        "source_identity": p["source_identity"], "level": 44, "existing_parent_id": p["existing_parent_id"],
                        "source_refs": refs, "prior_record": {"path": str(PRIOR.relative_to(ROOT)), "line": index[key]["line"],
                        "record_canonical_sha256": index[key]["record_canonical_sha256"]},
                        "printed_label": s["printed_label"], "source_kind": s["kind"], "source_module": module,
                        "printed_contacts_in_order": contacts,
                        "source_pdf_instruction": {"physical_page": page, "summary": pdf_instruction},
                        "performer_contract": {}, "timing_authority": {"fixed_bpm": None, "ascii_spacing_is_duration": False,
                        "absolute_onsets": None, "selected_metric_projection": None, "acoustic_gates": None},
                        "unresolved_fields": [], "conflicts": s.get("source_discrepancy", []),
                        "status": {"private_source_contract": "IMPLEMENTED_MANUAL_CHOICE", "native_valid": False,
                        "integrated": False, "accepted": False, "mastery_credit": False}}
            pc = contract["performer_contract"]
            pc["source_task_steps"] = imp.get("task_steps", [])
            pc["role_groups"] = imp.get("technique_groups") or imp.get("phrase_groups") or []
            pc["rests"] = imp.get("ordered_rest_locations", [])
            pc["holds"] = [{"ordinal": c["ordinal"], "qualitative": "sustain printed"} for c in contacts if "~" in (c["technique_symbols"] or "")]
            if module == "A":
                pc["required_methods"] = ["fretted_C_sharp_target", "C_to_C_sharp_bend_release", "C_to_C_sharp_slide", "C_to_C_sharp_hammer_pull"]
                pc["method_groups"] = imp["technique_groups"]
                pc["bend_target_semitones"] = 1
                contract["unresolved_fields"] = ["method_onsets", "method_gates", "continuous_bend_slide_curve", "finger_assignment"]
            elif module == "C":
                pc["required_methods"] = [g["technique"] for g in imp["technique_groups"]]
                pc["method_groups"] = imp["technique_groups"]
                pc["whole_step_bend_allowed"] = s["printed_label"].startswith(("G:", "B:", "High e:"))
                contract["unresolved_fields"] = ["method_onsets", "method_gates", "continuous_bend_slide_curve", "finger_assignment"]
            elif module == "D":
                pc["required_rhythm_templates"] = [r["name"] for r in imp["onset_realizations"]] + ["D_burst_plus_space"]
                pc["relative_rhythm_realizations"] = imp["onset_realizations"]
                pc["burst_plus_space"] = imp["burst_plus_space_contract"]
                pc["syncopated_sixteenth_silent_slots_zero_based"] = [0, 2, 5, 7, 8, 10, 13, 15]
                pc["shuffle_middle_triplet_slots"] = "no new attack; acoustic continuity not printed"
                pc["source_focus"] = imp["source_focus"]
                contract["timing_authority"]["selected_metric_projection"] = "A/B/C relative grids exact; D beat grouping exact, intra-beat placement open"
                contract["unresolved_fields"] = ["D_intra_beat_onsets", "all_acoustic_gates", "tempo_BPM", "finger_assignment"]
                if "blue-third-closure" in key:
                    contract["unresolved_fields"].append("continuous_bend_curve")
            elif module == "E":
                pc["phrase_contract"] = imp["phrase_contract"]
                pc["phrase_contract"]["silence_authority"] = {"PDF_physical_page": 9, "TXT_printed": False}
                contract["timing_authority"]["source_relative_gap_beats"] = 1
                contract["unresolved_fields"] = ["within_phrase_onsets", "phrase_bar_placement", "acoustic_gates", "tempo_BPM", "later_shortened_gap"]
            elif module == "F":
                pc["degree_sequence"] = "b3-4-b5-5-b7-1" if "core-lick-a" in key else "1-b7-5-b5-4-b3-1"
                pc["fixed_fret_route"] = True
                contract["unresolved_fields"] = ["onsets", "acoustic_gates", "tempo_BPM", "finger_assignment"]
            elif module == "G":
                pc["phrase_groups"] = imp["phrase_groups"]
                pc["relationship_choice"] = ["degree_order", "contour", "rhythmic_profile"]
                contract["unresolved_fields"] = ["selected_relationship", "onsets", "between_phrase_gap", "acoustic_gates", "tempo_BPM"]
            elif module == "H":
                pc["ending_groups"] = imp["phrase_groups"]
                pc["required_landing_functions"] = {"tonic": "A closes", "turnaround": "E points to E7/V"}
                contract["unresolved_fields"] = ["onsets", "acoustic_gates", "tempo_BPM", "finger_assignment"]
            elif module == "I":
                pc["phrase_contract"] = imp["phrase_contract"]
                if "simultaneous_shape_groups" in pc["phrase_contract"]:
                    pc["voice_groups"] = pc["phrase_contract"]["simultaneous_shape_groups"]
                contract["timing_authority"]["source_bar_span"] = [11, 12]
                contract["unresolved_fields"] = ["within_bar_onsets", "acoustic_gates", "tempo_BPM", "backing_track", "finger_assignment"]
                if "high-bend" in key:
                    contract["unresolved_fields"].append("continuous_bend_curve")
            else:
                pc["source_choice_definitions"] = imp["source_choice_definitions"]
                pc["all_required_combinations"] = imp["all_required_combinations"]
                pc["between_halves"] = "small breath; quantitative duration unprinted"
                pc["register_or_string_adjustment"] = "allowed only when needed; degree function unchanged"
                pc["required_realized_tones"] = 128
                pc["workload_count_caveat"] = imp["source_workload_caveat"]
                contract["unresolved_fields"] = ["per_combination_rhythm", "breath_duration", "connecting_octave_or_string_choice", "acoustic_gates", "tempo_BPM"]
            group.append(contract)
            all_records.append(contract)
        batch_number = start // 12 + 1
        path = OUT / f"batch-{batch_number:02d}.jsonl"
        payload = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in group).encode()
        path.write_bytes(payload)
        resource = memory_proxy()
        if resource["proxy_gib"] >= 13:
            raise RuntimeError(f"resource guard reached after batch {batch_number}: {resource}")
        batches.append({"batch": batch_number, "path": str(path.relative_to(ROOT)), "sha256": digest(payload),
                        "attempted": len(group), "source_backed_implemented": len(group),
                        "remaining_keys": keys[start+len(group):], "resource": resource, "failures": []})
        write_json(RESULTS / f"batch-{batch_number:02d}-checkpoint.json", batches[-1])
    if [r["package_key"] for r in all_records] != keys:
        raise ValueError("packet order mismatch")
    manifest = {"schema_version": "fathom-private-exercise-a44-manifest.1", "reservation_key_set_sha256": reservation["key_set_sha256"],
                "key_count": len(keys), "batches": batches, "remaining_keys": [],
                "counts": {"attempted": 46, "source_backed_implemented": 46, "manual_choice": 46,
                           "unresolved_field_contracts": sum(bool(r["unresolved_fields"]) for r in all_records), "conflict_records": sum(bool(r["conflicts"]) for r in all_records),
                           "native_valid": 0, "queue_selected": 0, "installed_accepted": 0, "whole_workbook_increment": 0, "WBS_parent_increment": 0},
                "proposed_later_admission_case": "Module D family 2, flat-five resolution, straight eighths: eight fixed printed sounding contacts with an exact relative onset grid; select a bounded tempo and acoustic gates under independent review.",
                "source_pins": PINS}
    write_json(RESULTS / "manifest.json", manifest)
    print(json.dumps({"sealed": 46, "batches": len(batches), "remaining": 0, "proxy_gib": batches[-1]["resource"]["proxy_gib"]}))


if __name__ == "__main__":
    main()
