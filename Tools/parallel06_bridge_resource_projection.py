#!/usr/bin/env python3
"""Project sealed source cards into an offline, non-admitted asset contract.

This is a packaging input for a future native reader, not an app integration.
"""

import argparse
import hashlib
import json
from pathlib import Path

PLAN = "Results/primary/20260906T184530Z-2.4.1.1.1-r01-evidence/plan.json"
CONTENT = "Results/primary/20260912T220613Z-2.4.1.2.1-r01-evidence/output02/content.json"
PRESENTATION = "Results/primary/20260912T220613Z-2.4.1.2.1-r01-evidence/output02/manifest.json"
CORRECTION = "Results/primary/20260912T220613Z-2.4.1.2.1-r01-evidence/correction-plan.json"
LESSON_MANIFEST = "Content/runtime/representative-v1-manifest.json"
PINNED = {
    PLAN: "cb3c3f7a47343ac0255dbdb8bf53411af6dd7b929c101b04d00ed62d6e3f637a",
    CONTENT: "8e14d1df140dfd329ba6fe6d993489b1407b0a39d50f1920fc1a8db8abc57d56",
    PRESENTATION: "fa0a0a59fe07307eb55214ec102d31781053ac553fc6134de45dd27d824e2c91",
    CORRECTION: "7a5853e86813e5b74ad163b1d54365f1b30f72a7044b1dc3f04d82645127c5b4",
    LESSON_MANIFEST: "f57b3c6e1adddd3699bb27c8c0c35f356fbbcb2808f409f87bcca531afa75a8e",
}


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def local_file(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and path.parts and all(x not in (".", "..") for x in path.parts),
            f"unsafe local source path: {relative}")
    full = root / path
    require(not full.is_symlink() and full.is_file() and full.resolve().is_relative_to(root),
            f"missing or unsafe local source: {relative}")
    return full


def load_pinned(root):
    raw = {}
    for name, expected in PINNED.items():
        data = local_file(root, name).read_bytes()
        require(digest(data) == expected, f"changed sealed input: {name}")
        raw[name] = data
    return {name: json.loads(data) for name, data in raw.items()}


def validate_cards(plan, content):
    cards = content.get("cards")
    require(isinstance(cards, list), "missing source cards")
    expected_gaps = {x["id"]: x for x in plan["gaps"]}
    expected_resources = {x["id"]: x for x in plan["resources"]}
    require(set(expected_gaps) == {f"G{x:02d}" for x in range(1, 6)}, "accepted gap set differs")
    require(len(expected_resources) == 16 and all(x["availability"] == "required_unsupplied" for x in expected_resources.values()),
            "accepted required-unsupplied set differs")
    ids = [x.get("id") for x in cards]
    require(len(ids) == len(set(ids)), "duplicate source card ID")
    require(set(ids) == set(expected_gaps) | set(expected_resources),
            f"source card omission or addition: missing={sorted((set(expected_gaps)|set(expected_resources))-set(ids))} extra={sorted(set(ids)-(set(expected_gaps)|set(expected_resources)))}")
    for card in cards:
        identifier = card["id"]
        approved = expected_gaps.get(identifier) or expected_resources.get(identifier)
        field = "approved_gap" if identifier in expected_gaps else "approved_requirement"
        kind = "bridge" if identifier in expected_gaps else "resource"
        require(card.get("kind") == kind and card.get(field) == approved,
                f"{identifier}: changed or incomplete accepted requirement")
        require(card.get("source_refs") == approved["source_refs"], f"{identifier}: source refs differ")
        require(card.get("canonical_task_id") is None and card.get("runtime_admitted") is False
                and card.get("new_wording_curriculum_accepted") is False and card.get("hard_lock") is False,
                f"{identifier}: unsupported task mapping or admission")
        require(card.get("difficulty", {}).get("value") == "unknown" and isinstance(card.get("search_terms"), list)
                and isinstance(card.get("domains"), list) and isinstance(card.get("prerequisite_links"), list),
                f"{identifier}: missing local discovery fields")
        if kind == "resource":
            require(card.get("availability") == "required_unsupplied" and approved["supplied_asset"] is None
                    and approved["rights_evidence"] is None and approved["runtime_network"] is False
                    and approved["in_app_recorder"] is False and approved["in_app_import"] is False,
                    f"{identifier}: resource availability or capability differs")
            require(isinstance(approved["required_outputs"], list) and approved["required_outputs"],
                    f"{identifier}: required outputs omitted")
        else:
            require((card.get("content") is None if identifier in {"G01", "G02", "G03"}
                     else isinstance(card.get("content"), dict))
                    and card.get("see_hear_play_use") == approved["see_hear_play_use"],
                    f"{identifier}: unsupported bridge content")
    require(content.get("bundled_assets") == [] and content.get("actual_learner_evidence") == []
            and content.get("runtime_admitted") is False, "source preview claims supplied assets or admission")
    return cards


def validate_passages(root, content, read_source=None):
    read_source = read_source or (lambda rel: local_file(root, rel).read_bytes())
    passages = content["source_passages"]
    used = set().union(*(set(c["source_refs"]) | set(c.get("public_source_refs", []))
                         | set(c.get("supplemental_source_refs", [])) for c in content["cards"]))
    require(used <= set(passages), f"missing source passages: {sorted(used-set(passages))}")
    bindings = content["input_bindings"]
    for ref, passage in passages.items():
        rel = passage["path"]
        raw = read_source(rel)
        require(digest(raw) == passage["sha256"] == bindings.get(rel), f"source drift: {ref} {rel}")
        require(digest(passage["text"].encode()) == passage["text_sha256"], f"passage text drift: {ref}")
        if passage["format"] == "txt":
            lines = raw.decode().splitlines()
            start, end = passage["first_line"], passage["last_line"]
            require(1 <= start <= end <= len(lines) and "\n".join(lines[start-1:end]) == passage["text"],
                    f"source line mismatch: {ref}")
        else:
            require(passage["format"] == "pdf" and passage["page"] >= 1, f"unsupported passage: {ref}")
    return passages


def project(root, output):
    root = root.resolve(strict=True)
    require((root / ".git").exists(), "root must be Fathom Git checkout")
    require(output.is_absolute() and not output.exists(), "choose a new absolute output directory")
    docs = load_pinned(root)
    plan, content = docs[PLAN], docs[CONTENT]
    presentation, lesson = docs[PRESENTATION], docs[LESSON_MANIFEST]
    require(presentation["files"]["content.json"] == PINNED[CONTENT]
            and presentation["plan_sha256"] == PINNED[CORRECTION], "corrected output02 binding differs")
    require(lesson["version"] == "lesson-bundle.1"
            and lesson["entries"]["profile"] == "Content/controls/representative-v1/expected-profile.json",
            "current lesson bundle schema differs")
    plan_entry = next((x for x in lesson["files"] if x["path"].endswith("2.4.1.1.1-r01-evidence/plan.json")), None)
    require(plan_entry is not None and plan_entry["sha256"] == PINNED[PLAN],
            "lesson bundle accepted resource-plan binding differs")
    profile_path = lesson["entries"]["profile"]
    profile_bytes = local_file(root, profile_path).read_bytes()
    profile_entry = next((x for x in lesson["files"] if x["path"] == profile_path), None)
    require(profile_entry is not None and profile_entry["sha256"] == digest(profile_bytes)
            and profile_entry["bytes"] == len(profile_bytes), "lesson profile drift")
    resource_binding = json.loads(profile_bytes)["resource_plan"]
    require(resource_binding["sha256"] == PINNED[PLAN]
            and set(resource_binding["entry_ids"]) == {x["id"] for x in plan["resources"]}
            and resource_binding["availability"] == "required_unsupplied",
            "lesson profile resource-plan binding differs")
    cards = validate_cards(plan, content)
    passages = validate_passages(root, content)
    projected = []
    for card in cards:
        is_resource = card["kind"] == "resource"
        approved = card["approved_requirement"] if is_resource else card["approved_gap"]
        refs = list(dict.fromkeys(card["source_refs"] + card.get("public_source_refs", [])
                                  + card.get("supplemental_source_refs", [])))
        projected.append({
            "id": card["id"], "kind": card["kind"], "title": card["title"],
            "legacy_level": card["legacy_level"], "source_order": card["source_order"],
            "applies_to_levels": card["applies_to_levels"], "summary": card["public_summary"],
            "search_terms": card["search_terms"], "tags": card["domains"],
            "prerequisite_links": card["prerequisite_links"], "context_links": card["context_links"],
            "source_refs": card["source_refs"], "public_source_refs": card["public_source_refs"],
            "source_links": [{"ref": ref, "asset_path": "source-passages.json",
                              "passage_id": ref, "path": passages[ref]["path"],
                              "source_sha256": passages[ref]["sha256"],
                              "passage_sha256": passages[ref]["text_sha256"],
                              "locator": ({"lines": [passages[ref]["first_line"], passages[ref]["last_line"]]}
                                          if passages[ref]["format"] == "txt" else {"page": passages[ref]["page"]})}
                             for ref in refs],
            "required_outputs": approved["required_outputs"] if is_resource else [],
            "selection_constraints": approved["selection_constraints"] if is_resource else [],
            "availability": "required_unsupplied" if is_resource else "source_context_only",
            "supplied_asset": None, "runtime_admitted": False, "canonical_task_id": None,
            "approved_requirement": approved,
            "preview_content": card.get("content") if not is_resource else None,
            "new_wording_curriculum_accepted": False,
        })
    assets = {"cards.json": encoded({"version": "bridge-resource-cards.1", "cards": projected}),
              "source-passages.json": encoded({"version": "bridge-source-passages.1", "passages": passages,
                                                "search_indexed": False})}
    manifest = {"version": "bridge-resource-bundle.1", "offline": True, "runtime_admitted": False,
                "supplied_assets": [], "bridge_ids": [c["id"] for c in projected if c["kind"] == "bridge"],
                "resource_ids": [c["id"] for c in projected if c["kind"] == "resource"],
                "source_bindings": PINNED, "files": [{"path": n, "bytes": len(b), "sha256": digest(b)}
                                               for n, b in assets.items()],
                "lesson_bundle_schema": "lesson-bundle.1",
                "future_reader_required": True}
    assets["manifest.json"] = encoded(manifest)
    output.mkdir(parents=True)
    for name, data in assets.items():
        (output / name).write_bytes(data)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = project(args.root, args.output)
    except (Refusal, KeyError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"REFUSED: {error}\n")
    print(f"PASS: {len(result['bridge_ids'])} bridges, {len(result['resource_ids'])} required-unsupplied resources, {len(result['files'])} local assets")


if __name__ == "__main__":
    main()
