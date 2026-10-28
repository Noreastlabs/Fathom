#!/usr/bin/env python3
"""Build a hash-bound catalog from saved indexes, never from a filesystem census.

Structural signatures are dispatch HINTS. They neither prove behavior equivalence
nor upgrade private packets to executable, native, installed, or official status.
Run with PYTHONDONTWRITEBYTECODE=1. Outputs are rebuildable private Build files.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import subprocess
import time
from fractions import Fraction


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def compact(value, sort=False):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=sort, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON member: " + key)
            out[key] = value
        return out
    def constant(value):
        raise Refusal("nonfinite JSON number: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def ref_identity(ref):
    return ref["path"], ref["sha256"], ref.get("jsonl_line")


class Cache:
    """Each referenced input is read and hashed once in one build invocation."""
    def __init__(self, root):
        self.root = pathlib.Path(root).resolve()
        self.files = {}
        self.jsons = {}
        self.packets = {}
        self.hash_seconds = 0.0

    def read(self, ref):
        name = ref["path"] if isinstance(ref, dict) else ref
        relative = pathlib.Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts,
                "non-relative input: " + name)
        path = self.root / relative
        require(path.resolve().is_relative_to(self.root), "input escape: " + name)
        require(not any(x.is_symlink() for x in [path, *path.parents]
                        if x.is_relative_to(self.root)), "symlink input: " + name)
        if name not in self.files:
            start = time.perf_counter()
            raw = path.read_bytes()
            self.files[name] = {"raw": raw, "path": name, "bytes": len(raw),
                                "sha256": digest(raw)}
            self.hash_seconds += time.perf_counter() - start
        item = self.files[name]
        if isinstance(ref, dict):
            require("sha256" in ref, "unpinned reference: " + name)
            require(item["sha256"] == ref["sha256"], "file hash mismatch: " + name)
            require("bytes" not in ref or item["bytes"] == ref["bytes"],
                    "file byte-count mismatch: " + name)
        return item["raw"]

    def json(self, ref):
        self.read(ref)
        name = ref["path"] if isinstance(ref, dict) else ref
        if name not in self.jsons:
            self.jsons[name] = strict_json(self.files[name]["raw"])
        return self.jsons[name]

    def reference(self, name):
        item = self.files[name]
        return {k: item[k] for k in ("path", "bytes", "sha256")}

    def packet(self, ref):
        self.read(ref)
        name = ref["path"]
        if name not in self.packets:
            if name.endswith(".json"):
                raw = self.files[name]["raw"]
                row = metadata(self.json(ref), raw)
                row["ref"] = {**self.reference(name), "jsonl_line": None}
                self.packets[name] = [row]
                return self.packets[name]
            rows = []
            seen = set()
            for number, raw in enumerate(self.files[name]["raw"].splitlines(), 1):
                require(raw.strip(), "blank JSONL record: " + name)
                try:
                    obj = strict_json(raw)
                except (Refusal, json.JSONDecodeError) as error:
                    raise Refusal(f"invalid packet {name}:{number}: {error}") from error
                row = metadata(obj, raw)
                require(row["package_key"] not in seen, "duplicate packet key: " + name)
                seen.add(row["package_key"])
                row["ref"] = {**self.reference(name), "jsonl_line": number}
                rows.append(row)
            self.packets[name] = rows
        return self.packets[name]

    def select(self, ref, key):
        rows = self.packet(ref)
        line = ref.get("jsonl_line")
        if line is None:
            selected = [row for row in rows if row["package_key"] == key]
            require(len(selected) == 1, "missing/duplicate key-based payload: " + key)
            return selected[0]
        require(type(line) is int and 1 <= line <= len(rows), "invalid JSONL line: " + key)
        return rows[line - 1]


def shape(value, depth=0):
    """Field/type shape only. No music values, clocks, or behavior inferred."""
    if depth >= 4:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(val, depth + 1) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return {"array_member_shapes": sorted(set(
            compact(shape(val, depth + 1), True).decode() for val in value))}
    return type(value).__name__


def source_references(value):
    """Keep source custody/location pins, without copying source transcriptions."""
    refs = []
    def visit(node):
        if isinstance(node, dict):
            if isinstance(node.get("path"), str):
                fields = ("path", "sha256", "bytes", "physical_page", "physical_pages",
                          "jsonl_line", "line", "lines", "line_range", "start_line", "end_line",
                          "bbox", "region", "pdf_locator", "txt_locator")
                refs.append({key: node[key] for key in fields if key in node})
            for val in node.values():
                if isinstance(val, (dict, list)):
                    visit(val)
        elif isinstance(node, list):
            for val in node:
                visit(val)
    visit(value)
    return list({compact(ref, True): ref for ref in refs}.values())


def metadata(obj, raw):
    require(isinstance(obj, dict), "record must be object")
    key = obj.get("package_key")
    sid = obj.get("source_identity")
    require(isinstance(key, str) and isinstance(sid, str), "missing record identity")
    impl = obj.get("implementation", {})
    contract = obj.get("performer_contract", obj.get("source_contract", {}))
    kind = (impl.get("kind") if isinstance(impl, dict) else None)
    kind = kind or obj.get("contract_kind") or obj.get("implementation_kind")
    if not kind and isinstance(contract, dict):
        kind = contract.get("kind") or contract.get("workflow_kind")
    kind = kind or obj.get("delivery_type") or obj.get("family") or "UNSPECIFIED"
    selected = {field: obj[field] for field in (
        "implementation", "performer_contract", "source_contract", "events",
        "ordered_contacts", "printed_contacts_in_order", "performer_choices",
        "timing_authority", "timing", "source_roles", "refusals") if field in obj}
    signature = {"schema": obj.get("schema_version"), "implementation_kind": kind,
                 "contract_field_shapes": shape(selected)}
    return {"package_key": key, "source_identity": sid, "level": obj.get("level"),
            "existing_parent_id": obj.get("existing_parent_id", obj.get("parent_wbs_id")),
            "schema": obj.get("schema_version"), "implementation_kind": kind,
            "contract_category": obj.get("contract_category"), "status": obj.get("status"),
            "source_refs": source_references(obj.get("source_refs", obj.get("source"))),
            "source_payload_field_shape": shape(obj.get("source_payload", {})),
            "structural_hint_sha256": digest(compact(signature, True)),
            "structural_hint": signature, "raw_sha256": digest(raw),
            "compact_order_sha256": digest(compact(obj)),
            "canonical_sha256": digest(compact(obj, True))}


def metric_q(value):
    if type(value) in (int, float):
        return Fraction(str(value))
    if isinstance(value, list) and len(value) == 2 and all(type(x) is int for x in value) and value[1] > 0:
        return Fraction(value[0], value[1])
    raise Refusal("missing/invalid metric coordinate")


def contact_projection_profile(obj):
    """Check stored projection data, without new music interpretation or native execution."""
    implementation = obj.get("implementation", {})
    contacts = implementation.get("ordered_contacts", [])
    variants = implementation.get("relative_variants", [])
    timing = obj.get("timing_authority", {})
    reasons = []
    def check(condition, reason):
        if not condition:
            reasons.append(reason)
    check(implementation.get("kind") == "ordered_contact_transcription", "different implementation kind")
    check(bool(contacts), "no contacts")
    ordinals = list(range(1, len(contacts) + 1))
    check([c.get("ordinal") for c in contacts] == ordinals, "noncontiguous contact ordinals")
    check(all(type(c.get("midi")) is int and 0 <= c["midi"] <= 127 for c in contacts),
          "frozen MIDI unavailable; no pitch derived in this proposal")
    check(all(type(c.get("string_low_to_high")) is int and 1 <= c["string_low_to_high"] <= 6 and
              type(c.get("fret")) is int and c["fret"] >= 0 and
              type(c.get("finger")) is int and 1 <= c["finger"] <= 4 for c in contacts),
          "incomplete physical contact/finger fields")
    check(all(type(c.get("source_line")) is int and type(c.get("source_column_1based")) is int for c in contacts),
          "missing exact source contact locators")
    check(all(c.get("same_column_contact_count") == 1 and not c.get("technique_symbols") for c in contacts),
          "polyphony or technique symbols need a different projection contract")
    check(not implementation.get("ordered_rest_locations"), "rest locations need separate metric handling")
    check({v.get("start_stroke") for v in variants} == {"D", "U"} and len(variants) == 2,
          "not exactly two saved D/U variants")
    for variant in variants:
        start = variant.get("start_stroke")
        strokes = [start if i % 2 == 0 else ("U" if start == "D" else "D") for i in range(len(contacts))]
        check(variant.get("contact_ordinals") == ordinals and variant.get("strokes") == strokes,
              "saved variant ordinal/stroke parity differs")
    end = None
    try:
        spans = [(metric_q(c["onset_q"]), metric_q(c["duration_q"])) for c in contacts]
        end = metric_q(timing["end_q"])
        check(all(onset >= 0 and duration > 0 for onset, duration in spans), "invalid positive metric span")
        check(all(spans[i][0] + spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1)),
              "selected contact clock is not a continuous packed traversal")
        check(bool(spans) and spans[0][0] == 0 and spans[-1][0] + spans[-1][1] == end,
              "selected clock extent differs from contacts")
        check(all(metric_q(v["end_q"]) == end for v in variants), "variant metric extent differs")
    except (Refusal, KeyError, ValueError, ZeroDivisionError) as error:
        reasons.append("metric data unavailable: " + str(error))
    check(bool(timing.get("selected_projection")), "no explicit selected projection")
    return {"stored_data_projection_eligible": not reasons, "reasons": sorted(set(reasons)),
        "contact_count": len(contacts), "saved_variant_count": len(variants),
        "selected_projection": timing.get("selected_projection"),
        "end_q": [end.numerator, end.denominator] if end is not None else None,
        "timing_kind": timing.get("kind"), "timing_API_fields": sorted(timing),
        "contact_API_fields": sorted(set(key for contact in contacts for key in contact)),
        "variant_API_fields": sorted(set(key for variant in variants for key in variant)),
        "timing_authority_canonical_sha256": digest(compact(timing, True)),
        "relative_variants_canonical_sha256": digest(compact(variants, True)),
        "other_source_obligations_present": bool(timing.get("unselected_options") or timing.get("guidance")),
        "full_source_exercise_completion_claimed": False,
        "acoustic_sounding_span": "Unknown; leave unassigned in a prospective native reference",
        "native_music_validate_run": False}


def join(official, row, key, source_identity=None):
    require(key in official, "unknown official key: " + key)
    require(row["package_key"] == key, "record-key mismatch: " + key)
    expected = official[key]
    require(row["source_identity"] == expected["source_identity"],
            "source-identity mismatch: " + key)
    require(source_identity is None or source_identity == expected["source_identity"],
            "index source-identity mismatch: " + key)
    require(row["level"] is None or row["level"] == expected["level"], "level mismatch: " + key)
    require(row["existing_parent_id"] is None or
            row["existing_parent_id"] == expected["existing_parent_id"], "parent mismatch: " + key)


def count_categories(state):
    return dict(collections.Counter(value["category"] for value in state.values()))


def same_counts(actual, declared, name):
    require({k: v for k, v in actual.items() if v} == {k: v for k, v in declared.items() if v},
            "category/count mismatch: " + name)


ROOT_REFS = {
    "descriptor": {"path": "Planning/Fathom-Exercise-WBS-Annex-v1.json", "bytes": 303569,
                   "sha256": "83c1ab0b54324f032f2b2fac4c7ec0f193bfc489c1eb40308f93da20173ae78e"},
    "family_plan": {"path": "Results/manager-resume-r03/family-plan-r01.json", "bytes": 14720,
                    "sha256": "510ca367e242972b12ad9820dbe5897874ce6a9a7be9ed87c0dee3db62cfe5f2"},
    "A": {"path": "Build/fullscope-private-a-r01/semantic-overlay-index-r13/effective-range-index.jsonl",
          "bytes": 4283428, "sha256": "6786cbcbf1982207ad0d0a815ff96b44426c88c442548f1a8d0a8661bb255945"},
    "B": {"path": "Results/fullscope-private-b-r01/coherent-level053-moduleb-r04/handoff.json",
          "bytes": 90664, "sha256": "fc621ae753ce99d4d7f7279baf9033392b49ab9a7a076e0fd484f2a4d677b513"},
    "C": {"path": "Results/fullscope-private-c-r01/coherent-level083-reduction-repair-r67/effective-range-delta.json",
          "bytes": 25647, "sha256": "7937d60b4f8ac1c56ee4a29fd5df164955e4321a2e6df11583a8565784670bee"},
    "controller": {"path": "Prompts/parallel-02/Lane-Reservations-Current.md", "bytes": 616267,
                   "sha256": "51a71752678d2ed3f44011990a35db36383451554b816086c4b5c3ee76f949cc"},
}


SHARDS = [
    ("a42", "20260929T2052EDT-level042-a42-private-implementation-handoff.md", "4f63419d272c547740e2b6e1dbdfd1ee97f32f2f2490289670b6b63b1c0ca229", "artifact-manifest-r02.json", "51d7f2f32dea4cc284c27dfc09bb995bbeca2e43a09f7c7efffec3dfd368d011", "r01", "1c60e6f3361846f0cc60f30458a490fdc91852ecb1d8c8a82f5ef294f70b46c7"),
    ("a44", "20260929T2109EDT-level044-a44-private-implementation-handoff.md", "995f8b4c7b3baaf5961069850a3e2e806d2e5d6718904b25fc4eeeca48e98293", "evidence-manifest.json", "205e0beb064867a5aefc0ee5943317bad9e1fc576c364dd735ca3d95258c1673", "r02", "e1c54a9a14b5c784677d3ad3853ae7173d0a51dd9ca696da3edb03dd182168d1"),
    ("b52", "20260929T2117EDT-level052-b52-private-implementation-handoff.md", "c1e2d734a0f1446956e07e77d97eef96f60512b613511da1222040d62f7783e6", "artifact-manifest-r02.json", "b2d200cedf20388a0342b27dbc6a7636e19cae677a9a030608a6ad11eb2d4e75", "r02", "4a4252aed5d1d8e615e6d0dfc86aad9b4fee01de9714e397eddaf1ed2f98490a"),
    ("b59", "20260929T2143EDT-level059-b59-private-implementation-handoff.md", "04df255b76ad61e2a12e7f3737be414d8f12dca24435825560ec425729649cbd", "packet-manifest.json", "8a907023d9921b5afe80b0ca9617ac9738cea671cea93a88b5b017ddaa6ba85e", "r03", "773b0e486a389ba2e10ab2610fc1057166b8bf22ac56b5b595d277bccc46e212"),
    ("c78", "20260929T2058EDT-level078-c78-private-implementation-handoff.md", "83c0fd5676a68bf4f0dee1bd8fb72679959d3378b60571e4d06a65079a3d65b7", "artifact-manifest.json", "ef3daae07f0626807a768b3707d878ed3004208dfd2f87b7660d91e01aee8cf5", "r01", "720922e10a0b8bd88e3e0ae305166b90f1039746596e65b7f9f632bd52d208ab"),
    ("c79", "20260929T2054EDT-level079-c79-private-implementation-handoff.md", "58b5cfdcae09e0cfdea1f1992eb96328535766ac95ba730ed08e2653de44e11c", "artifact-manifest-final.json", "cd48c675c5f8468097853afc1f205a529ba6223eec7cd5cbed21f32faba2b0d8", "r01", "6710c208b0b350a4e4172eeba1ca3315f0205328f71c2569e1c163d03f6548b6"),
    ("c81", "20260929T2114EDT-level081-c81-private-implementation-handoff.md", "2abbbfc8f7723abd3a0f20314392748f3b3ec09097c664af2d506e808c677e19", "artifact-manifest-final.json", "47f170acfe8ec93218e8454f0d785241a4d63848ba919396085cd53431a27c59", "r02", "0b7ef2dd90a5628e043fb82a1584881a9cce36255269d4e227b2599cb34646a5"),
    ("c89", "20260929T2136EDT-level089-c89-final-implementation-correction.md", "5f6a2a02b7cc8b2a655ecd1c8f305d4da420a755cb5841db68ee3c9569ba9ca4", "evidence-manifest-r02.json", "7ac7b8e2b1b84203716feb4ea9997d2200ca1ceead43d35592b51f6383195183", "r03", "4562628000ac5784dd7fed7273326d219f0fc3f09d3b1170bb2ce3541c78aeb6"),
]


def official_catalog(cache):
    descriptor = cache.json(ROOT_REFS["descriptor"])
    raw = cache.read(descriptor["base"])
    official = {}
    identities = set()
    operations = {}
    for operation in descriptor["current_status_resolution"]["operations"]:
        key = operation["selection"]["package_key"]
        require(key not in operations, "duplicate official operation: " + key)
        operations[key] = operation
    for number, line in enumerate(raw.splitlines(), 1):
        obj = strict_json(line)
        key = obj["package_key"]
        ex = obj["exercise"]
        sid = ex["source_identity"]
        require(key not in official and sid not in identities, "duplicate official identity: " + key)
        identities.add(sid)
        status = obj["status"]
        app_status = ex["app_status"]
        acceptance = None
        if key in operations:
            operation = operations.pop(key)
            sel = operation["selection"]
            before = operation["assert_before"]
            require(sel["source_identity"] == sid and
                    sel["existing_parent_id"] == obj["existing_parent_id"], "official identity prestate: " + key)
            require(sel["exercise_canonical_json_sha256"] == digest(compact(ex, True)) and
                    sel["candidate_canonical_json_sha256"] == digest(compact(obj, True)), "official hash prestate: " + key)
            actual_before = {"candidate_status": status, "exercise_app_status": app_status,
                             "proposal_status": obj["proposal"]["status"],
                             "proposal_app_status": obj["proposal"]["app_status"]}
            require(before == actual_before, "official status prestate: " + key)
            acceptance = operation["current_overlay"]
            status = acceptance["status"]
            app_status = acceptance["app_status"]
        official[key] = {"package_key": key, "source_identity": sid, "level": ex["level"],
                         "existing_parent_id": obj["existing_parent_id"], "official_status": status,
                         "official_app_status": app_status, "official_base_line": number,
                         "source_unit_kind": ex["kind"], "instruction_path": ex["parent_path"],
                         "printed_label": ex["printed_label"],
                         "source_pins": {k: ex.get(k) for k in ("pdf_sha256", "txt_sha256", "pdf_locator", "txt_locator")},
                         "official_acceptance_binding": acceptance}
    require(not operations, "unknown official operations")
    require(len(official) == 7271, "official denominator")
    same_counts(collections.Counter(row["official_status"] for row in official.values()),
                {"Accepted": 121, "Pending": 7150}, "official statuses")
    require(descriptor["current_view"]["children"]["child_status_counts"] ==
            {"Pending": 7150, "Accepted": 121}, "descriptor status counts")
    return official, descriptor


def load_a(cache, official):
    state = {}
    for raw in cache.read(ROOT_REFS["A"]).splitlines():
        item = strict_json(raw)
        key = item["package_key"]
        require(key not in state, "duplicate A index key: " + key)
        row = cache.select({**item["packet"], "jsonl_line": item["line"]}, key)
        join(official, row, key, item["source_identity"])
        require(row["canonical_sha256"] == item["record_canonical_sha256"], "A record hash: " + key)
        require(item["level"] == official[key]["level"] and
                item["existing_parent_id"] == official[key]["existing_parent_id"], "A index bounds: " + key)
        require(1 <= official[key]["level"] <= 48, "A level scope")
        state[key] = {"row": row, "category": item["category"], "owner": "A",
                      "producer_private_contract_complete": item["private_contract_complete"],
                      "binding": "A sorted-canonical record SHA + packet SHA"}
    require(len(state) == 2566, "A index denominator")
    return state


def chain(cache, first_ref, previous_field):
    nodes = []
    seen = set()
    ref = first_ref
    while ref:
        require(ref["path"] not in seen, "predecessor cycle: " + ref["path"])
        seen.add(ref["path"])
        node = cache.json(ref)
        nodes.append((ref, node))
        ref = node.get(previous_field)
    return list(reversed(nodes))


def b_transition(official, state, change, row, seen, revision):
    key = change["package_key"]
    require(key in state, "unknown B replacement: " + key)
    join(official, row, key, change["source_identity"])
    if key in seen:
        require(revision is True and change.get("replacement_basis") == "previous_effective_record",
                "B repeated key lacks revision/preimage declaration: " + key)
    else:
        require(revision is False, "B new key falsely marked revision: " + key)
    require(state[key]["row"]["compact_order_sha256"] == change["base_record_sha256"],
            "B previous-effective record hash: " + key)
    require(row["compact_order_sha256"] == change["overlay_record_sha256"], "B overlay record hash: " + key)
    require(state[key]["category"] == change["old_category"], "B category prestate: " + key)
    state[key] = {"row": row, "category": change["new_category"], "owner": "B",
                  "binding": "B guarded insertion-order compact record preimage + packet SHA"}
    seen.add(key)


def load_b(cache, official):
    latest = cache.json(ROOT_REFS["B"])
    base_ref = latest["base_index"]
    base = cache.json(base_ref)
    packet_refs = {ref["path"]: ref for ref in base["packets"]}
    state = {}
    for item in base["children"]:
        key = item["package_key"]
        require(key not in state, "duplicate B base key: " + key)
        row = cache.select({**packet_refs[item["packet_path"]], "jsonl_line": item["line"]}, key)
        join(official, row, key, item["source_identity"])
        require(row["raw_sha256"] == item["record_sha256"], "B raw base record hash: " + key)
        require(49 <= official[key]["level"] <= 72 and item["level"] == official[key]["level"], "B level scope")
        state[key] = {"row": row, "category": item["category"], "owner": "B",
                      "binding": "B raw base record SHA + packet SHA"}
    nodes = chain(cache, ROOT_REFS["B"], "prior_overlay_handoff")
    seen, operations = set(), 0
    identity_sha = digest(compact([[x["package_key"], x["source_identity"]] for x in base["children"]]))
    require(identity_sha == base["ordered_identity_sha256"], "B ordered identity hash")
    for ref, node in nodes:
        require(ref_identity({**node["base_index"], "jsonl_line": None}) ==
                ref_identity({**base_ref, "jsonl_line": None}), "B changed base anchor")
        rows = cache.packet(node["overlay"])
        require(len(rows) == len(node["changes"]), "B packet/change denominator")
        batch = set()
        for change in node["changes"]:
            key = change["package_key"]
            require(key not in batch, "duplicate B batch key: " + key)
            batch.add(key)
            line = change["overlay_line"]
            require(type(line) is int and 1 <= line <= len(rows), "B replacement line")
            b_transition(official, state, change, rows[line - 1], seen,
                         node.get("revision_of_existing_overlay", False))
            operations += 1
        same_counts(count_categories(state), node["effective_categories"], ref["path"])
        require(node["ordered_identity_sha256"] == identity_sha, "B changed ordered identities")
    require(len(state) == 2133 and len(seen) == latest["unique_replaced_children"] and
            operations == latest["total_replacement_operations"], "B final fold counts")
    return state, {"nodes": len(nodes), "operations": operations, "unique_replaced": len(seen),
                   "outside_child_ambiguities": base["outside_child_source_ambiguity_count"]}


def c_transition(official, state, item, row):
    key = item["package_key"]
    require(key in state, "unknown C replacement: " + key)
    join(official, row, key, item["source_identity"])
    require(state[key]["category"] == item["previous_category"], "C category prestate: " + key)
    if item.get("previous_effective_payload"):
        require(ref_identity(state[key]["row"]["ref"]) == ref_identity(item["previous_effective_payload"]),
                "C explicit previous payload prestate: " + key)
    state[key] = {"row": row, "category": item["effective_category"], "owner": "C",
                  "binding": "C ordered pinned predecessor/category; explicit payload prestate when supplied"}


def load_c(cache, official):
    latest = cache.json(ROOT_REFS["C"])
    base_ref = latest["base_effective_index"]
    base = cache.json(base_ref)
    state = {}
    for item in base["rows"]:
        key = item["package_key"]
        require(key not in state, "duplicate C base key: " + key)
        row = cache.select(item["effective_payload"], key)
        join(official, row, key, item["source_identity"])
        require(73 <= official[key]["level"] <= 105 and item["level"] == official[key]["level"], "C level scope")
        state[key] = {"row": row, "category": item["category"], "owner": "C",
                      "binding": "C base effective payload pin + exact key/source identity"}
    same_counts(count_categories(state), base["counts"]["categories"], "C base")
    identity_sha = digest(compact([[x["package_key"], x["source_identity"]] for x in base["rows"]]))
    require(identity_sha == base["exact_identity_set_sha256"], "C ordered identity hash")
    nodes = chain(cache, ROOT_REFS["C"], "prior_ordered_delta")
    operations, explicit_prestate = 0, 0
    for ref, node in nodes:
        require(ref_identity(node["base_effective_index"]) == ref_identity(base_ref), "C changed base anchor")
        cache.read(node["ordered_overlay"])
        batch = set()
        for item in node["rows"]:
            key = item["package_key"]
            require(key not in batch, "duplicate C batch key: " + key)
            batch.add(key)
            require(item["effective_payload"]["path"] == node["ordered_overlay"]["path"] and
                    item["effective_payload"]["sha256"] == node["ordered_overlay"]["sha256"], "C wrong overlay binding")
            row = cache.select(item["effective_payload"], key)
            c_transition(official, state, item, row)
            operations += 1
            explicit_prestate += bool(item.get("previous_effective_payload"))
        same_counts(count_categories(state), node["counts"]["categories"], ref["path"])
        require(node["exact_identity_set_sha256"] == identity_sha, "C changed ordered identities")
    require(len(state) == 2411, "C final denominator")
    return state, {"nodes": len(nodes), "operations": operations,
                   "explicit_per_row_payload_prestate_operations": explicit_prestate,
                   "other_operations": "Pinned predecessor plus category prestate; no absent per-row preimage claimed",
                   "outside_child_ambiguities": len(base["outside_child_ambiguities"])}


def transferred_shards(cache, official, state):
    controller = cache.read(ROOT_REFS["controller"]).decode()
    exclusions = {}
    info = []
    for name, manager, manager_sha, manifest, manifest_sha, revision, reservation_sha in SHARDS:
        require(manager in controller and manager_sha in controller, "shard closure absent in controller: " + name)
        manager_ref = {"path": "Results/primary/" + manager, "sha256": manager_sha}
        manager_text = cache.read(manager_ref).decode()
        require(manifest_sha in manager_text, "shard final manifest not adopted: " + name)
        manifest_ref = {"path": f"Results/exercise-impl-shard-{name}-r01/{manifest}", "sha256": manifest_sha}
        index = cache.json(manifest_ref)
        reservation_ref = {"path": f"Prompts/manager-resume-r01/mass-implementation-shards-{revision}/shard-{name}-reservation.json",
                           "sha256": reservation_sha}
        reservation = cache.json(reservation_ref)
        keys = reservation["keys"]
        require(len(keys) == len(set(keys)) == reservation["key_count"], "shard reservation duplicates/count")
        if name == "b59":
            packets = [{"path": item["packet_path"], "sha256": item["packet_sha256"]} for item in index["batches"]]
        else:
            packets = [item for item in index["artifacts"]
                       if item["path"].endswith(".jsonl") and
                       item["path"].startswith(f"Build/exercise-impl-shard-{name}-r01/")]
            # C81 seals both the full packet and its batches. Use the full packet once.
            if name == "c81":
                packets = [item for item in packets if item["role"] == "frozen-private-packet"]
        require(packets, "no authoritative shard packet refs: " + name)
        rows = [row for packet in packets for row in cache.packet(packet)]
        row_keys = [row["package_key"] for row in rows]
        require(len(row_keys) == len(set(row_keys)) and set(row_keys) == set(keys), "shard exact reservation coverage: " + name)
        for row in rows:
            key = row["package_key"]
            join(official, row, key)
            require(key not in exclusions, "duplicate transferred owner: " + key)
            exclusions[key] = name
            previous = state.get(key)
            state[key] = {"row": row, "category": "SEALED_TRANSFERRED_SOURCE_CONTRACT",
                          "owner": "shard-" + name, "broad_lane_excluded": name[0].upper(),
                          "previous_broad_category": previous["category"] if previous else None,
                          "binding": "Controller closure -> manager adoption -> manifest/packet -> exact reservation",
                          "shard_disposition": row["status"]}
        info.append({"shard": name, "keys": len(keys), "manager": cache.reference(manager_ref["path"]),
                     "manifest": cache.reference(manifest_ref["path"]),
                     "reservation": cache.reference(reservation_ref["path"]),
                     "broad_lane_dispatch_exclusion_retained": True})
    require(len(exclusions) == 667, "transferred denominator")
    return exclusions, info


def recipe_bindings(cache, official, state):
    plan = cache.json(ROOT_REFS["family_plan"])
    recipes = {item["family"]: item for item in plan["existing_models"]}
    require(len(recipes) == 6, "known recipe denominator")
    for item in recipes.values():
        cache.read(item["model_ref"])
    refs = [
        {"path": "Results/manager-resume-r02/private-source-bulk-review-r01/final-decisions.json", "bytes": 15960,
         "sha256": "9102b746e437f46af1e37da1786c980863c67d044fbecdb2ad0da5736873cb21"},
        {"path": "Results/manager-resume-r02/private-coherent-bulk-review-r02/final-decisions.json", "bytes": 36687,
         "sha256": "3482b4d4816c837d5d2517993588bf84ef70e3222f63158bbd78b030f92d562f"},
    ]
    names = {"I": "call_answer", "K": "recovery_pair", "F": "chord_tone_transfer",
             "H": "full_reconstruction", "Level53 ModuleB siblings": "triad",
             "Level83 ModuleAB+C": "fixed_top_reduction"}
    bound = {}
    for ref in refs:
        decision = cache.json(ref)
        for item in decision["decisions"]:
            family = names.get(item["family"])
            if family is None and item["family"].startswith("Level83"):
                family = "fixed_top_reduction"
            require(family in recipes, "unknown reviewed recipe family: " + item["family"])
            require(item["private_source_model_QA_decision"] == "Accept", "non-Accept recipe proof")
            artifacts = item.get("exact_artifacts", [item.get("model"), item.get("packet")])
            artifacts = [artifact for artifact in artifacts if artifact]
            model_refs = [artifact for artifact in artifacts if artifact["path"].endswith(".py")]
            packet_refs = [artifact for artifact in artifacts if artifact["path"].endswith(".jsonl")]
            for artifact in artifacts:
                cache.read(artifact)
            for key in item["package_keys"]:
                require(key in official and key in state and key not in bound, "recipe exact key conflict: " + key)
                current_ref = state[key]["row"]["ref"]
                require(any(current_ref["path"] == packet["path"] and current_ref["sha256"] == packet["sha256"]
                            for packet in packet_refs), "reviewed recipe current packet mismatch: " + key)
                bound[key] = {"recipe": family, "review_decision": ref, "model_refs": model_refs,
                              "exact_current_packet_matches_review": True}
    require(len(bound) == 240, "reviewed recipe key denominator")
    for family, item in recipes.items():
        require(sum(x["recipe"] == family for x in bound.values()) == item["rows"], "recipe family exact counts")
    return bound, list(recipes.values())


CATEGORY_MAP = {
    "timed_source_event_contract": "TIMED_SOURCE_CONTRACT",
    "TIMED_SOURCE_EVENT_CONTRACT": "TIMED_SOURCE_CONTRACT",
    "complete_nonplayback_manual_contract": "MANUAL_SOURCE_CONTRACT",
    "complete_manual_nonplayback_contract": "MANUAL_SOURCE_CONTRACT",
    "COMPLETE_MANUAL_NONPLAYBACK_CONTRACT": "MANUAL_SOURCE_CONTRACT",
    "implementation_or_interpretation_pending": "IMPLEMENTATION_OR_INTERPRETATION_PENDING",
    "IMPLEMENTATION_OR_INTERPRETATION_PENDING": "IMPLEMENTATION_OR_INTERPRETATION_PENDING",
    "deliberate_learner_choice_no_fixed_realization": "CHOICE_WITHOUT_FIXED_REALIZATION",
    "performer_choice_missing_fixed_realization": "CHOICE_WITHOUT_FIXED_REALIZATION",
    "LEARNER_CHOICE_WITHOUT_FIXED_REALIZATION": "CHOICE_WITHOUT_FIXED_REALIZATION",
    "demonstrated_source_conflict": "SOURCE_CONFLICT",
    "DEMONSTRATED_SOURCE_CONFLICT": "SOURCE_CONFLICT",
    "SEALED_TRANSFERRED_SOURCE_CONTRACT": "SEALED_TRANSFERRED_SOURCE_CONTRACT",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compact(value, True) + b"\n")
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def build(root, out_dir, result_path, guard_report=None):
    started = time.perf_counter()
    cache = Cache(root)
    official, descriptor = official_catalog(cache)
    a = load_a(cache, official)
    b, b_info = load_b(cache, official)
    c, c_info = load_c(cache, official)
    require(not (set(a) & set(b) or set(a) & set(c) or set(b) & set(c)), "broad owner overlap")
    state = {**a, **b, **c}
    broad_count = len(state)
    exclusions, shard_info = transferred_shards(cache, official, state)
    bound, recipes = recipe_bindings(cache, official, state)
    clusters = {}
    groups = {}
    dispatch_hints = {}
    missing = []
    rows = []
    for key, item in official.items():
        current = state.get(key)
        group = {"level": item["level"], "instruction_path": item["instruction_path"]}
        group_id = digest(compact(group, True))
        groups.setdefault(group_id, {**group, "keys": []})["keys"].append(key)
        entry = {**item, "instruction_group": group_id, "current_payload": None,
                 "known_executable_recipe": bound.get(key), "dispatch_ownership":
                 {"broad_lane_excluded": key in exclusions, "transferred_shard": exclusions.get(key)}}
        if current:
            row = current["row"]
            require(current["category"] in CATEGORY_MAP, "unknown category: " + current["category"])
            cluster_id = row["structural_hint_sha256"]
            cluster = clusters.setdefault(cluster_id, {"HINT_ONLY": True,
                "not_behavioral_equivalence_or_completion": True,
                "shape": row["structural_hint"], "keys": [], "levels": set(), "categories": collections.Counter()})
            cluster["keys"].append(key)
            cluster["levels"].add(item["level"])
            cluster["categories"][current["category"]] += 1
            dispatch_id = digest(compact([group_id, cluster_id]))
            hint = dispatch_hints.setdefault(dispatch_id, {"HINT_ONLY": True,
                "instruction_group": group_id, "structural_hint": cluster_id, "level": item["level"],
                "instruction_path": item["instruction_path"], "keys": [], "broad_dispatch_excluded_keys": []})
            hint["keys"].append(key)
            if key in exclusions:
                hint["broad_dispatch_excluded_keys"].append(key)
            entry["current_payload"] = {"ref": row["ref"], "record_canonical_sha256": row["canonical_sha256"],
                "record_compact_order_sha256": row["compact_order_sha256"], "category": current["category"],
                "normalized_producer_category": CATEGORY_MAP[current["category"]],
                "owner": current["owner"], "binding": current["binding"], "schema": row["schema"],
                "implementation_kind": row["implementation_kind"], "source_refs": row["source_refs"],
                "structural_hint": cluster_id}
        else:
            missing.append(key)
        rows.append(entry)
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "family-ledger.jsonl"
    with ledger_path.open("wb") as stream:
        for row in rows:
            stream.write(compact(row, True) + b"\n")
    ledger_ref = {"path": str(ledger_path), "bytes": ledger_path.stat().st_size,
                  "sha256": digest(ledger_path.read_bytes())}
    for cluster in clusters.values():
        cluster["levels"] = sorted(cluster["levels"])
        cluster["categories"] = dict(cluster["categories"])
        cluster["key_count"] = len(cluster["keys"])
    cluster_ref = write_json(out_dir / "structural-hints.json", clusters)
    group_ref = write_json(out_dir / "instruction-groups.json", groups)
    recipe_dispatch = {recipe["family"]: {"model": recipe["model_ref"],
        "exact_previously_reviewed_keys": [key for key, binding in bound.items() if binding["recipe"] == recipe["family"]],
        "new_execution_not_run": True} for recipe in recipes}
    dispatch_ref = write_json(out_dir / "dispatch-groups.json", {
        "known_six_recipes": recipe_dispatch, "instruction_plus_shape_HINTS": dispatch_hints,
        "ownership_release_required_for_broad_excluded_keys": True,
        "no_new_behavior_equivalence_or_completion": True})
    missing_ref = write_json(out_dir / "missing-coverage.json", {
        "meaning": "No payload in the specified authoritative current indexes/shards; official status retained separately",
        "keys": missing, "per_level": dict(collections.Counter(official[key]["level"] for key in missing)),
        "pending_keys": [key for key in missing if official[key]["official_status"] == "Pending"],
        "accepted_keys": [key for key in missing if official[key]["official_status"] == "Accepted"]})
    b_base = cache.json(cache.json(ROOT_REFS["B"])["base_index"])
    c_base = cache.json(cache.json(ROOT_REFS["C"])["base_effective_index"])
    boundary_ref = write_json(out_dir / "source-and-dispatch-boundaries.json", {
        "outside_official_children": {"B": b_base["source_ambiguities"], "C": c_base["outside_child_ambiguities"]},
        "current_source_conflict_keys": [key for key, item in state.items()
                                         if CATEGORY_MAP[item["category"]] == "SOURCE_CONFLICT"],
        "broad_owner_excluded_keys": exclusions,
        "meaning": "Frozen reported boundaries retained; no source reread, repair, new identity, or ownership release."})
    input_refs = [cache.reference(path) for path in sorted(cache.files)]
    inputs_ref = write_json(out_dir / "inputs.json", {
        "one_read_one_hash_per_file": True, "inputs": input_refs, "B": b_info, "C": c_info,
        "shards": shard_info, "root_pins": ROOT_REFS,
        "source_originals_reread": 0, "model_behavior_executions": 0})
    largest = sorted(clusters.items(), key=lambda item: (-item[1]["key_count"], item[0]))[:10]
    categories = count_categories(state)
    normalized = dict(collections.Counter(CATEGORY_MAP[item["category"]] for item in state.values()))
    guard_ref = None
    if guard_report:
        guard_path = pathlib.Path(guard_report)
        guard_raw = guard_path.read_bytes()
        guard = strict_json(guard_raw)
        require(guard["result"] == "PASS" and guard["failures"] == 0, "focused guard report failed")
        guard_ref = {"path": str(guard_path), "bytes": len(guard_raw), "sha256": digest(guard_raw)}
    result = {
        "schema": "fathom.private-family-inventory.1", "result": "HASH_JOIN_AND_GUARDED_FOLD_PASS",
        "git_HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "official": {"children": 7271, "Accepted": 121, "Pending": 7150, "status_operations": 121},
        "payload_coverage": {"current_proved_file_record_bindings": len(state), "broad_index_rows": broad_count,
            "A": len(a), "B": len(b), "C": len(c), "transferred_shard_rows": len(exclusions),
            "missing": len(missing), "missing_pending": sum(official[key]["official_status"] == "Pending" for key in missing),
            "missing_per_level": dict(collections.Counter(official[key]["level"] for key in missing)),
            "category_counts": categories, "normalized_category_counts": normalized,
            "category_meaning": "Producer/index classifications; explicit spelling map only, file/source-identity binding checked, musical completeness not inferred"},
        "known_executable_recipes": {"count": 6, "exact_previously_reviewed_keys": 240,
            "models": recipes, "new_behavior_execution": 0,
            "other_implementation_kinds_are_not_recipe_or_behavior_counts": True},
        "structural_hint_clusters": {"count": len(clusters), "instruction_groups": len(groups),
            "HINTS_ONLY": True, "instruction_plus_shape_dispatch_hints": len(dispatch_hints),
            "largest_known_reviewed_recipe": {"recipe": "triad", "exact_keys": 167},
            "largest": [{"id": ident, "count": cluster["key_count"],
                "schema": cluster["shape"]["schema"], "implementation_kind": cluster["shape"]["implementation_kind"],
                "levels": cluster["levels"], "categories": cluster["categories"]} for ident, cluster in largest]},
        "guards": {"unknown_duplicate_identity_hash_category_prestate_conflicts": "REFUSE",
            "B": b_info, "C": c_info, "transferred_exact_ownership_exclusions": len(exclusions),
            "focused_mutation_test_report": guard_ref},
        "limits": ["Source original PDFs/TXT were not reread; frozen source pins carried without new musical QA.",
            "Structural clusters are dispatch hints, not behavioral equivalence or executable completion.",
            "Official status is strictly the frozen descriptor projection; no acceptance increments.",
            "17 outside-child source ambiguities retained separately; no invented children or payloads.",
            "Sealed transferred category indicates a sealed source contract only, not a common behavioral category.",
            "Native, listening, integrated, installed, identity, ownership release and source-gap gates remain independent."],
        "artifacts": {"ledger": ledger_ref, "input_cache_manifest": inputs_ref, "structural_hints": cluster_ref,
                      "instruction_groups": group_ref, "dispatch_groups": dispatch_ref,
                      "missing_coverage": missing_ref, "source_and_dispatch_boundaries": boundary_ref},
        "performance": {"seconds": round(time.perf_counter() - started, 6), "unique_input_files": len(cache.files),
                        "input_bytes_read_once": sum(x["bytes"] for x in cache.files.values()),
                        "file_read_hash_seconds": round(cache.hash_seconds, 6)},
        "official_acceptance_increments": 0, "runtime_admission_increments": 0,
    }
    require(b_info["outside_child_ambiguities"] + c_info["outside_child_ambiguities"] == 17,
            "outside-child ambiguity denominator")
    result_ref = write_json(pathlib.Path(result_path), result)
    print(json.dumps({"result": result["result"], "coverage": result["payload_coverage"],
                      "largest_hint": result["structural_hint_clusters"]["largest"][0],
                      "seconds": result["performance"]["seconds"], "result_ref": result_ref}, ensure_ascii=False))
    return result


def derive_ready_cohort(root, out_dir, result_path):
    """Reuse the sealed join; inspect only its exact ready contact packet refs."""
    started = time.perf_counter()
    root = pathlib.Path(root)
    out_dir = pathlib.Path(out_dir)
    result_path = pathlib.Path(result_path)
    result = strict_json(result_path.read_bytes())
    cache = Cache(root)
    ledger_raw = cache.read(result["artifacts"]["ledger"])
    ledger = [strict_json(line) for line in ledger_raw.splitlines()]
    require(len(ledger) == 7271, "cached ledger denominator")
    groups = {}
    selected_packets = {}
    for entry in ledger:
        payload = entry["current_payload"]
        if not payload or payload["normalized_producer_category"] != "TIMED_SOURCE_CONTRACT":
            continue
        group = {"owner": payload["owner"], "schema": payload["schema"],
                 "implementation_kind": payload["implementation_kind"]}
        ident = digest(compact(group, True))
        item = groups.setdefault(ident, {**group, "keys": [], "levels": set(),
            "excluded_from_new_broad_dispatch": []})
        item["keys"].append(entry["package_key"])
        item["levels"].add(entry["level"])
        if entry["official_status"] == "Accepted" or entry["dispatch_ownership"]["broad_lane_excluded"]:
            item["excluded_from_new_broad_dispatch"].append(entry["package_key"])
        if payload["owner"] == "A" and payload["implementation_kind"] == "ordered_contact_transcription":
            selected_packets.setdefault(payload["ref"]["path"], []).append(entry)
    candidates = []
    deferred = []
    # This source identity has an exact case hold in the frozen controller used
    # by the inventory. Exclude it until separately released, even for a new batch.
    protected_sid = "printed:l004:set-1-of-9-exercises-001-012:exercise-006-1234"
    controller = cache.read(ROOT_REFS["controller"]).decode()
    require(protected_sid in controller, "protected case identity absent in controller pin")
    profiles = {}
    for name, entries in selected_packets.items():
        raw = cache.read(entries[0]["current_payload"]["ref"])
        lines = raw.splitlines()
        for entry in entries:
            payload = entry["current_payload"]
            cache.read(payload["ref"])
            line = payload["ref"]["jsonl_line"]
            require(type(line) is int and 1 <= line <= len(lines), "cohort selector line")
            obj = strict_json(lines[line - 1])
            require(obj["package_key"] == entry["package_key"] and obj["source_identity"] == entry["source_identity"],
                    "cohort source/key join")
            require(digest(compact(obj, True)) == payload["record_canonical_sha256"], "cohort canonical record hash")
            profile = contact_projection_profile(obj)
            profiles[entry["package_key"]] = profile
            exclusions = []
            if entry["official_status"] == "Accepted":
                exclusions.append("already Accepted in strict official descriptor projection")
            if entry["dispatch_ownership"]["broad_lane_excluded"]:
                exclusions.append("transferred broad-owner exclusion")
            if entry["source_identity"] == protected_sid:
                exclusions.append("frozen current P02 exact-case hold; separate release required")
            record = {"package_key": entry["package_key"], "source_identity": entry["source_identity"],
                "level": entry["level"], "payload_ref": payload["ref"],
                "record_canonical_sha256": payload["record_canonical_sha256"], "profile": profile}
            if profile["stored_data_projection_eligible"] and not exclusions:
                candidates.append(record)
            else:
                deferred.append({**record, "dispatch_exclusions": exclusions})
    for item in groups.values():
        item["levels"] = sorted(item["levels"])
        item["count"] = len(item["keys"])
    groups_ref = write_json(out_dir / "ready-timed-kind-clusters.json", {
        "classification_basis": "Exact frozen producer TIMED_SOURCE_CONTRACT classifications, grouped by actual schema/kind/owner",
        "not_native_or_behavioral_equivalence": True, "clusters": groups})
    proposed = {
        "schema": "fathom.private-native-projection-cohort-proposal.1", "result": "PROPOSED_NOT_CONSTRUCTED",
        "implementation_kind": "ordered_contact_transcription", "keys": len(candidates),
        "direct_data_eligible_before_dispatch_exclusions": sum(p["stored_data_projection_eligible"] for p in profiles.values()),
        "all_ready_rows_of_this_kind": len(profiles), "per_level": dict(collections.Counter(item["level"] for item in candidates)),
        "selected_projection_counts": dict(collections.Counter(item["profile"]["selected_projection"] for item in candidates)),
        "preserved_saved_D_U_variants": 2 * len(candidates),
        "frozen_contact_records": sum(item["profile"]["contact_count"] for item in candidates),
        "scope": "Selected stored metric contact traversal, both exact saved D/U starts; full source exercise obligations remain outstanding",
        "required_preservation": ["Exact package/source identity, ordered contacts, fret/string/finger/MIDI and original locators",
            "Both saved variant arrays, ordinal/stroke parity across all turns/shifts and saved metric extents",
            "Whole original timing_authority, guidance, unselected_options, task_steps and source payload, accessed by pinned payload ref",
            "Unknown fixed BPM, acoustic sounding span and performance outcome stay unknown unless independently supplied",
            "Private native music::validate reference validity stays separate from renderability, runtime admission, installed acceptance or learner completion"],
        "source_reread_or_interpretation": False, "native_compile_or_validation": False,
        "protected_source_identity": protected_sid, "candidates": candidates, "deferred": deferred,
        "timing_and_variant_API_profiles": profiles,
        "exact_cached_join": result["artifacts"]["ledger"],
        "input_pins": [cache.reference(name) for name in sorted(cache.files)],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    proposal_ref = write_json(out_dir / "native-projection-cohort.json", proposed)
    result["ready_timed_contact_clusters"] = {"ref": groups_ref,
        "total_ready_timed_producer_rows": sum(item["count"] for item in groups.values()),
        "actual_implementation_kind_groups": len(groups), "not_unique_behavior_count": True}
    result["proposed_next_native_projection_cohort"] = {"ref": proposal_ref, "keys": len(candidates),
        "implementation_kind": "ordered_contact_transcription", "per_level": proposed["per_level"],
        "selected_projection_counts": proposed["selected_projection_counts"],
        "saved_D_U_variants": proposed["preserved_saved_D_U_variants"],
        "frozen_contact_records": proposed["frozen_contact_records"],
        "selected_scope_only": True, "native_compile_or_validation": False,
        "P02_case_and_official_Accepted_exclusions_retained": True,
        "cohort_derivation_seconds": proposed["elapsed_seconds"]}
    result["artifacts"]["ready_timed_kind_clusters"] = groups_ref
    result["artifacts"]["native_projection_cohort_proposal"] = proposal_ref
    result_ref = write_json(result_path, result)
    print(json.dumps({"result_ref": result_ref, "cohort": result["proposed_next_native_projection_cohort"],
        "direct_data_eligible": proposed["direct_data_eligible_before_dispatch_exclusions"],
        "deferred_rows": len(deferred), "all_ready_kind_rows": len(profiles)}, ensure_ascii=False))
    return result


def seal_inventory(root, out_dir, result_path):
    """Seal own outputs; verify cached joins without replaying producer/source work."""
    started = time.perf_counter()
    cache = Cache(root)
    out_dir = pathlib.Path(out_dir)
    result_path = pathlib.Path(result_path)
    result = strict_json(result_path.read_bytes())
    for ref in result["artifacts"].values():
        cache.read(ref)
    ledger = [strict_json(line) for line in cache.read(result["artifacts"]["ledger"]).splitlines()]
    by_key = {row["package_key"]: row for row in ledger}
    require(len(ledger) == len(by_key) == len({row["source_identity"] for row in ledger}) == 7271, "sealed ledger identities")
    require(sum(row["official_status"] == "Accepted" for row in ledger) == 121 and
            sum(row["official_status"] == "Pending" for row in ledger) == 7150, "sealed official statuses")
    require(sum(row["current_payload"] is not None for row in ledger) == 7110, "sealed payload count")
    require(sum(row["known_executable_recipe"] is not None for row in ledger) == 240, "sealed reviewed recipe count")
    require(sum(row["dispatch_ownership"]["broad_lane_excluded"] for row in ledger) == 667, "sealed ownership exclusions")
    proposal = cache.json(result["artifacts"]["native_projection_cohort_proposal"])
    candidates = proposal["candidates"]
    require(len(candidates) == len({row["package_key"] for row in candidates}) == 1401, "sealed native cohort count")
    for row in candidates:
        cached = by_key[row["package_key"]]
        require(cached["official_status"] == "Pending" and not cached["dispatch_ownership"]["broad_lane_excluded"], "sealed cohort dispatch bounds")
        require(row["source_identity"] != proposal["protected_source_identity"], "sealed protected case exclusion")
        require(row["record_canonical_sha256"] == cached["current_payload"]["record_canonical_sha256"] and
                row["payload_ref"] == cached["current_payload"]["ref"], "sealed cohort cached record binding")
    guard_path = out_dir / "guard-tests.json"
    guard = cache.json(str(guard_path))
    require(guard["result"] == "PASS" and guard["failures"] == 0 and guard["tests"] == 29, "sealed focused guards")
    checks = ["Tools/exercise-family-compiler/build_family_inventory.py",
              "Tools/exercise-family-compiler/test_family_inventory.py"]
    for path in checks:
        proc = subprocess.run(["git", "diff", "--no-index", "--check", "--", "/dev/null", path],
                              cwd=root, capture_output=True, text=True)
        require(proc.returncode in (0, 1) and not proc.stdout and not proc.stderr, "scoped whitespace check: " + path)
        cache.read(path)
    verification_ref = write_json(out_dir / "verification.json", {
        "result": "PASS", "ledger_rows": 7271, "current_payload_rows": 7110,
        "known_reviewed_recipe_keys": 240, "focused_guard_tests": 29,
        "native_proposal_keys": 1401, "saved_D_U_variants": 2802, "frozen_contacts": 59528,
        "transferred_owner_exclusions": 667, "source_originals_reread": 0,
        "model_behavior_or_native_validation_executions": 0, "official_runtime_increments": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 6), "scoped_whitespace_checks": checks})
    result["artifacts"]["verification"] = verification_ref
    result["guards"]["focused_mutation_test_report"] = cache.reference(str(guard_path))
    result["sealed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result["sealed_by_self_excluding_manifest"] = str(out_dir / "artifact-manifest.json")
    result_ref = write_json(result_path, result)
    status = subprocess.check_output(["git", "status", "--short", "--", *checks, str(result_path), str(out_dir)], cwd=root, text=True)
    git_ref = write_json(out_dir / "git-state.json", {"HEAD": result["git_HEAD"], "scope": checks,
        "status": status, "commit_stage_or_shared_mutation": False})
    artifact_refs = list(result["artifacts"].values()) + [result_ref, git_ref,
        cache.reference(str(guard_path)), *(cache.reference(path) for path in checks)]
    unique_refs = {ref["path"]: ref for ref in artifact_refs}
    manifest_ref = write_json(out_dir / "artifact-manifest.json", {
        "schema": "fathom.private-family-inventory-artifacts.1", "git_HEAD": result["git_HEAD"],
        "artifacts": [unique_refs[path] for path in sorted(unique_refs)], "self_excluded": True,
        "official_runtime_increments": 0})
    print(json.dumps({"result": result_ref, "manifest": manifest_ref,
        "verification": verification_ref, "proposal": result["artifacts"]["native_projection_cohort_proposal"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="Build/manager-resume-r03/family-inventory-r01")
    parser.add_argument("--result", default="Results/manager-resume-r03/family-inventory-r01.json")
    parser.add_argument("--guard-report")
    parser.add_argument("--derive-ready-cohort", action="store_true",
                        help="Reuse saved ledger; propose selected contact projection without reconstructing the guarded fold")
    parser.add_argument("--seal", action="store_true", help="Seal own inventory/proposal without replaying source or behavioral work")
    args = parser.parse_args()
    try:
        if args.seal:
            seal_inventory(args.root, args.out, args.result)
        elif args.derive_ready_cohort:
            derive_ready_cohort(args.root, args.out, args.result)
        else:
            build(args.root, args.out, args.result, args.guard_report)
    except (Refusal, OSError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit("REFUSE: " + str(error))


if __name__ == "__main__":
    main()
