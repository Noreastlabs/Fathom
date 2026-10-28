#!/usr/bin/env python3
"""Export two proven Level68 recipes; retain contracts, never choose for a user.

Definitions keep original contract field order because the frozen validators
hash insertion-order JSON. The shared closure deduplicates source/version pins
and operational contexts; retained contracts are complete immutable witnesses.
FrozenFamilies.allowed_choices/selection delegate to the existing pinned models.
No source extraction, native build, scheduler, runtime admission or credit path.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

SCHEMA = "fathom.compiled-level068-definition.1"
CLOSURE_SCHEMA = "fathom.compiled-level068-closure.1"
RECIPES = {
    "call_answer": {
        "rows": 5,
        "model": "Tools/fullscope-private-b-r01/finite-level068-mode-mirrors-manual-r02/call_answer_model.py",
        "model_sha": "578d3471299a3568676c0b0a39cab8de825442633849256004c91540b2055946",
        "packet": "Build/fullscope-private-b-r01/finite-level068-mode-mirrors-manual-r02/implementation-overlay.jsonl",
        "packet_sha": "7aecccb9e583246108ef0a773162539441ad96c61b82b4baea31cf76fb46db1f",
        "handoff": "Results/fullscope-private-b-r01/finite-level068-mode-mirrors-manual-r02/handoff.json",
        "handoff_sha": "47c8cda6777ce56b58a89dc0c8ea4118ea57d0fc82559952302aa8e012f666ac",
    },
    "recovery_pair": {
        "rows": 12,
        "model": "Tools/fullscope-private-b-r01/finite-level068-recovery-pairs-manual-r03/recovery_pair_model.py",
        "model_sha": "c3192a6b2f67d0a06a9f4e6f6aa9e5d862b440e2f7e8a746152fb7b73e4cdf39",
        "packet": "Build/fullscope-private-b-r01/finite-level068-recovery-pairs-manual-r03/implementation-overlay.jsonl",
        "packet_sha": "fc35f02fb662002b90dcd7725dfed03b429b690737e6e5a5be2e68dd904da8cf",
        "handoff": "Results/fullscope-private-b-r01/finite-level068-recovery-pairs-manual-r03/handoff.json",
        "handoff_sha": "62485314592b503d0c9029123bfaf36badf4e17fbba5f5a9bb02fec43be8e48f",
    },
}
SOURCE_PINS = {
    "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VIII_Level_68_E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_Harmonic_Minor_Improvisation_Synthesis.txt": "e270fa9365dfd6e061ce4fd7807df1ba0d82fc52b867dc1b29ec180cb7923f2b",
    "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VIII_Level_68_E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_Harmonic_Minor_Improvisation_Synthesis.pdf": "4db7d55cd64c1b038dfce68dfc3eda60fc82077fcf21532d96ad79457031a378",
    "Build/fullscope-private-b-r01/level068-r02/source-context.json": "32f09850b9bf85fcda7871c8885fa4f66a8668e82e4f65d7138fbfa7e76b6942",
}
REVIEW = "Results/manager-resume-r02/private-source-bulk-review-r01/final-decisions.json"
REVIEW_SHA = "9102b746e437f46af1e37da1786c980863c67d044fbecdb2ad0da5736873cb21"


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def encoded(value, *, sort=False):
    return json.dumps(value, ensure_ascii=False, sort_keys=sort,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(value, *, sort=False):
    return hashlib.sha256(encoded(value, sort=sort)).hexdigest()


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out

    def nonfinite(_):
        raise Refusal("NONFINITE_JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def read_pinned(root, path, expected):
    file = root / path
    require(not any(p.is_symlink() for p in (file, *file.parents)), "INPUT_SYMLINK")
    raw = file.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "FROZEN_INPUT_DRIFT:" + path)
    return raw, {"path": path, "bytes": len(raw), "sha256": expected}


def model_module(root, spec, recipe):
    read_pinned(root, spec["model"], spec["model_sha"])
    loader = importlib.util.spec_from_file_location("frozen_level068_" + recipe, root / spec["model"])
    model = importlib.util.module_from_spec(loader)
    before = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        loader.loader.exec_module(model)
    finally:
        sys.dont_write_bytecode = before
    return model


class FrozenFamilies:
    """Trusted family registry and a thin API over the frozen choice validators."""

    def __init__(self, root):
        self.root = Path(root)
        self.models, self.rows, self.inputs, self.contexts = {}, [], [], {}
        self.source_pins = [read_pinned(self.root, p, h)[1] for p, h in SOURCE_PINS.items()]
        self.review = read_pinned(self.root, REVIEW, REVIEW_SHA)[1]
        for recipe, spec in RECIPES.items():
            model = self.models[recipe] = model_module(self.root, spec, recipe)
            for kind in ("model", "packet", "handoff"):
                _, ref = read_pinned(self.root, spec[kind], spec[kind + "_sha"])
                self.inputs.append(ref)
            packet = model.load_packet(self.root / spec["packet"], spec["packet_sha"])
            handoff = strict_json((self.root / spec["handoff"]).read_bytes())
            require(handoff["overlay"]["path"] == spec["packet"] and
                    handoff["overlay"]["sha256"] == spec["packet_sha"] and
                    len(handoff["changes"]) == spec["rows"], "HANDOFF_PACKET_CLOSURE")
            keys = (["exercise-completeness-r01/level068/modulei/p015-card0" + str(i) + "/p" + str(i)
                     for i in range(1, 6)] if recipe == "call_answer" else
                    [model.identity(i)[0] for i in range(1, 13)])
            require([r["package_key"] for r in packet] == keys, "EXACT_RECIPE_KEYS")
            for line, (original, change) in enumerate(zip(packet, handoff["changes"]), 1):
                c = original["implementation"]["manual_execution_contract"]
                model.validate_contract(c)
                require(c["package_key"] == original["package_key"] and c["source_identity"] == original["source_identity"] and
                        change["package_key"] == c["package_key"] and change["overlay_line"] == line and
                        change["overlay_record_sha256"] == digest(original), "EXACT_ROW_SOURCE_RECORD")
                events_field = "ordered_contacts" if recipe == "call_answer" else "source_pitch_events"
                require(encoded(c[events_field]) == encoded(original["implementation"]["events"]), "RETAINED_SOURCE_EVENTS")
                for ref in original["source_refs"]:
                    require(ref["path"] in SOURCE_PINS and ref["sha256"] == SOURCE_PINS[ref["path"]] and
                            ref["bytes"] == next(p["bytes"] for p in self.source_pins if p["path"] == ref["path"]), "SOURCE_REFERENCE_CLOSURE")
                source_context = {"recipe": recipe, "context_tasks": original["implementation"]["context_tasks"]}
                if recipe == "call_answer":
                    source_context["source_rules"] = c["source_rules"]
                else:
                    source_context.update({k: c[k] for k in ("source_rule", "source_safety", "source_target_naming_rule")})
                context_ref = digest(source_context, sort=True)
                self.contexts[context_ref] = copy.deepcopy(source_context)
                self.rows.append({"schema": SCHEMA, "source_key": c["package_key"], "source_identity": c["source_identity"],
                                  "recipe": recipe, "contract": copy.deepcopy(c), "contract_sha256": model.digest(c),
                                  "record_sha256": digest(original), "packet_line": line,
                                  "context_ref": context_ref, "choice_domain_ref": recipe,
                                  "source_locators": [{"source_path": ref["path"], "locator": ref.get("locator")} for ref in original["source_refs"]]})
        self.by_key = {r["source_key"]: r for r in self.rows}
        require(len(self.rows) == len(self.by_key) == 17, "EXACT_SEVENTEEN")

    def validate_row(self, row):
        require(type(row) is dict and type(row.get("source_key")) is str and
                row["source_key"] in self.by_key, "EXACT_FAMILY_SCOPE")
        require(encoded(row) == encoded(self.by_key[row["source_key"]]), "EXACT_FROZEN_DEFINITION")
        self.models[row["recipe"]].validate_contract(row["contract"])

    def allowed_choices(self, source_key, origin=None):
        require(type(source_key) is str and source_key in self.by_key, "EXACT_FAMILY_SCOPE")
        row = self.by_key[source_key]
        result = {"package_key": source_key, "contract_sha256": row["contract_sha256"],
                  "start_strokes": ["D", "U"], "default_choice": None}
        if row["recipe"] == "recovery_pair":
            model = self.models["recovery_pair"]
            result["source_contacts"] = copy.deepcopy(row["contract"]["source_contact_menu"])
            result["rest_of_bar_plan"] = {"type": "string", "nonblank": True, "max_characters": 500, "generated_notes": False}
            if origin is not None:
                model.contact_midi(origin)
                require(origin in result["source_contacts"], "ORIGIN_PITCH_MENU")
                result["nearest_target_contacts"] = model.nearest_targets(origin, row["contract"]["source_pitch_events"][1]["printed_note"])
        else:
            require(origin is None, "CALL_ANSWER_HAS_PRINTED_CONTACTS")
        return result

    def selection(self, row, request):
        self.validate_row(row)
        return self.models[row["recipe"]].selection(row["contract"], request)

    def closure(self):
        domains = {
            "call_answer": {"request_fields": {"package_key": "exact source_key", "contract_sha256": "insertion-order contract_sha256",
                                                "start_stroke": ["D", "U"]}, "default_choice": None,
                            "printed_contacts_fixed": True, "alternating_picks_are_implementation_choice": True,
                            "validation_api": "FrozenFamilies.selection(row,request) delegates to pinned call_answer.selection(contract,request)",
                            "workflow_api": "call_answer.workflow_state(contract,request,responses); done_responses() supplies exact report schema",
                            "steps": 6, "required_final_reports": self.models["call_answer"].REPORTS},
            "recovery_pair": {"request_fields": {"package_key": "exact source_key", "contract_sha256": "insertion-order contract_sha256",
                                                  "source_contact": {"string": "integer1..6", "fret": "integer0..24"},
                                                  "target_contact": {"string": "integer1..6", "fret": "integer0..24"},
                                                  "start_stroke": ["D", "U"], "rest_of_bar_plan": "explicit nonblank string, length1..500 after strip"},
                              "default_choice": None, "printed_contacts_fixed": False,
                              "origin_domain": "contract.source_contact_menu; exact first printed pitch in standard tuning within0..24",
                              "target_domain": "allowed_choices(source_key,origin).nearest_target_contacts; second printed pitch with minimum absolute MIDI distance",
                              "nearest_is_provisional_implementation_policy": True, "physical_security_certified": False,
                              "validation_api": "FrozenFamilies.selection(row,request) delegates to pinned recovery_pair.selection(contract,request)",
                              "workflow_api": "recovery_pair.workflow_state(contract,request,responses); done_responses(contract,request) supplies exact report schema",
                              "steps": 5, "required_final_reports": self.models["recovery_pair"].REPORTS},
        }
        return {"schema": CLOSURE_SCHEMA, "rows": 17, "recipe_counts": {"call_answer": 5, "recovery_pair": 12},
                "contexts": copy.deepcopy(self.contexts), "choice_domains": domains,
                "source_pins": self.source_pins, "cached_inputs": self.inputs, "retained_private_review": self.review,
                "contract_hash_encoding": "UTF-8 ensure_ascii=false compact JSON; insertion order preserved, not sort_keys",
                "definition_row_encoding": "same insertion-order encoding; contract object retains original frozen order",
                "context_hash_encoding": "sorted-key compact JSON; content-addressed shared operational context",
                "source_clock": None, "fixed_bpm": None, "source_acoustic_gates": None,
                "manual_reports_are_observations": False, "runtime_admitted": False, "official_accepted": False,
                "native_contract_gaps": [
                    "Frozen workflows are stateless report evaluators; native instance/generation/revision ownership, navigation/retry/history and explicit release fences remain shared-engine integration work.",
                    "No source clock, hearing, physical security, exact rest-of-bar realization, runtime admission, Attempt/credit or whole-book mastery is supplied.",
                    "Call variation has two source beats of silence but no beat-to-quarter mapping, duration or scheduler; final A is the existing16th contact, never an extra attack.",
                    "Recovery nearest means the retained provisional bounded minimum-MIDI-distance interpretation; textual rest-of-bar plan does not generate notes/attacks.",
                ]}


def compile_family(root, output):
    begin = time.perf_counter()
    root, output = Path(root).absolute(), Path(output).absolute()
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    require(top.returncode == 0 and root.resolve() == root and Path(top.stdout.strip()) == root, "ROOT_SCOPE")
    require(output.resolve() == output and not output.exists() and
            output == root / "Build/manager-resume-r03/level068-generation-r01", "OUTPUT_SCOPE")
    family = FrozenFamilies(root)
    closure = family.closure()
    definitions = b"".join(encoded(row) + b"\n" for row in family.rows)
    roundtrip = [strict_json(line) for line in definitions.splitlines()]
    for row in roundtrip:
        family.validate_row(row)
    require(encoded(roundtrip) == encoded(family.rows), "ROUNDTRIP_CONTRACT_ORDER")
    payloads = {"definitions.jsonl": definitions, "family-closure.json": encoded(closure, sort=True) + b"\n"}
    output.mkdir(parents=True)
    refs = []
    for name, raw in payloads.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
        refs.append({"path": str((output / name).relative_to(root)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    receipt = {"schema": "fathom.family-generation.1", "rows": 17, "recipe_counts": {"call_answer": 5, "recovery_pair": 12},
               "shared_contexts": len(family.contexts), "source_files_rehashed_once": len(family.source_pins),
               "seconds": round(time.perf_counter() - begin, 6), "payloads": refs,
               "source_pins": family.source_pins, "cached_inputs": family.inputs, "retained_private_review": family.review,
               "per_row_models_or_prompts": 0, "new_source_research": False, "native_build": False,
               "runtime_admitted": False, "official_accepted": False, "contract_gaps": closure["native_contract_gaps"]}
    with (output / "generation-receipt.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2); stream.write("\n")
    return receipt


def write_native_table(root, output):
    """Add a trusted table beside existing exports without rewriting any bytes."""
    begin = time.perf_counter()
    root, output = Path(root).absolute(), Path(output).absolute()
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    require(top.returncode == 0 and root.resolve() == root and Path(top.stdout.strip()) == root, "ROOT_SCOPE")
    require(output.resolve() == output and output == root / "Build/manager-resume-r03/level068-generation-r01" and output.is_dir(), "NATIVE_TABLE_SCOPE")
    family = FrozenFamilies(root)
    raw, definitions_ref = read_pinned(root, str((output / "definitions.jsonl").relative_to(root)),
                                       "0dee1bf5ebebf361eafc9ad7b79e56ca6e7d3c4ad58a4fd6c53ab986d2d4efdf")
    closure_raw, closure_ref = read_pinned(root, str((output / "family-closure.json").relative_to(root)),
                                           "e1ec9a40e149cb58c60af53b9f5bf63e0e23ecb9a6359046bdf93a2798dfb511")
    rows = [strict_json(line) for line in raw.splitlines()]
    require(encoded(rows) == encoded(family.rows) and encoded(strict_json(closure_raw), sort=True) ==
            encoded(family.closure(), sort=True), "FROZEN_NATIVE_TABLE_INPUT")
    header = ["#pragma once", "#include <array>", "namespace fathom::tasks::recipe_generated {",
              "struct RawDefinition { const char* key; const char* definition; const char* reports; const char* reportBindings; const char* sourceClosureSha256; };",
              "inline const std::array<RawDefinition,17> rows = {{"]
    quote = lambda s: json.dumps(s, ensure_ascii=False)
    oracle = []
    for row in rows:
        model = family.models[row["recipe"]]
        if row["recipe"] == "call_answer":
            reports, bindings = model.done_responses(), []
        else:
            reports = model.done_responses(row["contract"], {"rest_of_bar_plan": ""})
            bindings = [{"step": 4, "report_field": "rest_of_bar_plan", "request_field": "rest_of_bar_plan"}]
        values = [row["source_key"], encoded(row).decode(), encoded(reports).decode(),
                  encoded(bindings).decode(), closure_ref["sha256"]]
        header.append("{" + ",".join(map(quote, values)) + "},")
        requests = []
        if row["recipe"] == "call_answer":
            requests = [{"package_key": row["source_key"], "contract_sha256": row["contract_sha256"], "start_stroke": start}
                        for start in ("D", "U")]
        else:
            for origin in row["contract"]["source_contact_menu"]:
                for target in model.nearest_targets(origin, row["contract"]["source_pitch_events"][1]["printed_note"]):
                    for start in ("D", "U"):
                        requests.append({"package_key": row["source_key"], "contract_sha256": row["contract_sha256"],
                                         "source_contact": origin, "target_contact": target, "start_stroke": start,
                                         "rest_of_bar_plan": "Explicit fixture-only manual remainder plan; not a default user choice."})
        for index, request in enumerate(requests):
            example = {"source_key": row["source_key"], "request": request,
                       "selection": model.selection(row["contract"], request), "fixture_only": True}
            if index == 0:
                responses = model.done_responses() if row["recipe"] == "call_answer" else model.done_responses(row["contract"], request)
                example["responses"] = responses
                example["next_steps"] = [model.workflow_state(row["contract"], request, responses[:n])["next_step"]
                                         for n in range(len(responses))]
            oracle.append(example)
    header.extend(["}};", "}"])
    data = ("\n".join(header) + "\n").encode()
    path = output / "GeneratedLevel068Family.hpp"
    with path.open("xb") as stream:
        stream.write(data)
    oracle_raw = b"".join(encoded(row) + b"\n" for row in oracle)
    oracle_path = output / "native-choice-oracle.jsonl"
    with oracle_path.open("xb") as stream:
        stream.write(oracle_raw)
    receipt = {"schema": "fathom.level068-native-table-generation.1", "rows": 17,
               "recipes": ["call_answer", "recovery_pair"], "seconds": round(time.perf_counter() - begin, 6),
               "definitions": definitions_ref, "source_closure": closure_ref,
               "header": {"path": str(path.relative_to(root)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
               "choice_oracle": {"path": str(oracle_path.relative_to(root)), "bytes": len(oracle_raw),
                                 "sha256": hashlib.sha256(oracle_raw).hexdigest(), "choice_cases": len(oracle)},
               "oracle_limit": "All finite source origin/nearest target/D-U combinations; one test-only remainder string per choice, not all free-text plans. Per-row report/next-step parity on one choice each.",
               "reports": "Exact frozen done_responses; only selected recovery remainder-plan report is bound at execution.",
               "source_clock": None, "default_choice": None, "runtime_admitted": False, "official_accepted": False}
    with (output / "native-generation-receipt.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2); stream.write("\n")
    return receipt


def write_native_context(root, output):
    """Add exact cached shared context; preserve all original exports/table."""
    begin = time.perf_counter()
    root, output = Path(root).absolute(), Path(output).absolute()
    require(root.resolve() == root and output.resolve() == output and
            output == root / "Build/manager-resume-r03/level068-generation-r01" and output.is_dir(), "NATIVE_CONTEXT_SCOPE")
    family = FrozenFamilies(root)
    raw, closure_ref = read_pinned(root, str((output / "family-closure.json").relative_to(root)),
                                  "e1ec9a40e149cb58c60af53b9f5bf63e0e23ecb9a6359046bdf93a2798dfb511")
    closure = strict_json(raw)
    require(encoded(closure, sort=True) == encoded(family.closure(), sort=True), "FROZEN_CONTEXT_INPUT")
    contexts = closure["contexts"]
    require(len(contexts) == 2 and all(digest(v, sort=True) == k for k, v in contexts.items()), "CONTEXT_HASH")
    data = ("#pragma once\nnamespace fathom::tasks::recipe_generated {\n" +
            "inline constexpr const char* contextClosureSha256 = " + json.dumps(closure_ref["sha256"]) + ";\n" +
            "inline constexpr const char* contexts = " + json.dumps(encoded(contexts, sort=True).decode(), ensure_ascii=False) + ";\n}\n").encode()
    path = output / "GeneratedLevel068Context.hpp"
    with path.open("xb") as stream: stream.write(data)
    receipt = {"schema": "fathom.level068-native-context-generation.1", "source_closure": closure_ref,
               "context_refs": sorted(contexts), "contexts": len(contexts),
               "header": {"path": str(path.relative_to(root)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
               "seconds": round(time.perf_counter() - begin, 6), "new_source_research": False,
               "original_native_header_unchanged": True, "runtime_admitted": False, "official_accepted": False}
    with (output / "native-context-receipt.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2); stream.write("\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--native-table", action="store_true", help="Add native report table to unchanged existing r01 exports")
    mode.add_argument("--native-context", action="store_true", help="Add shared source context to unchanged native r01 table")
    args = parser.parse_args()
    run = write_native_context if args.native_context else write_native_table if args.native_table else compile_family
    print(json.dumps(run(args.root, args.output), ensure_ascii=False))
