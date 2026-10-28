"""Publish exact reviewed manual-child operations under a named manager decision.

This local command is for an authorized controller, after distinct review. It
archives the reviewed bytes before changing the descriptor and never rewrites
the immutable base. Required inputs are explicit hash guards, not discovery.
"""
from pathlib import Path
import argparse
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from zoneinfo import ZoneInfo

from reviewed_child_overlay import canonical_sha, require, resolve, strict_json


def retain_reviewed_inputs(root, frozen_bytes, archive, freeze_ref, verify, ref,
                           custody_manifest=None, reuse_indexes=()):
    """Retain exact bytes once; old invocation keeps its historical layout."""
    archived = []
    reuse = {}
    if custody_manifest is not None:
        require(not custody_manifest.exists(), "new custody manifest required")
        spec = importlib.util.spec_from_file_location("fathom_evidence", root / "Tools/fathom_evidence.py")
        evidence = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evidence)
        evidence.safe_relative_path(root, custody_manifest, "custody manifest", must_exist=False)
        require((root / "Results") in custody_manifest.parents, "custody manifest must be below Results")
        for index_ref, index in reuse_indexes:
            for item in index["refs"]:
                original, retained = item["original"], item["archive"]
                require(original["bytes"] == retained["bytes"] and
                        original["sha256"] == retained["sha256"], "prior custody identity mismatch")
                reuse.setdefault((original["bytes"], original["sha256"]), retained)
    else:
        require(not reuse_indexes, "reuse requires content-addressed custody mode")
    by_identity = {}
    reused_prior = stored_new = 0
    for pin, raw in frozen_bytes:
        identity = (pin["bytes"], pin["sha256"])
        if custody_manifest is None:
            target = archive / "reviewed-bytes" / pin["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            retained = ref(target)
        elif identity in by_identity:
            retained = by_identity[identity]
        elif identity in reuse:
            retained = reuse[identity]
            evidence.safe_relative_path(root, Path(retained["path"]), "prior custody", must_exist=True)
            require(verify(retained) == raw, "prior custody bytes differ from reviewed input")
            by_identity[identity] = retained
            reused_prior += 1
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                evidence.cmd_store(argparse.Namespace(
                    root=root, source=Path(pin["path"]), manifest=custody_manifest,
                    role="exact independently reviewed exercise implementation input",
                    reason="Retain reviewed bytes before shared owners are released and before child publication; reuse a single SHA-addressed object."))
            target = root / "Evidence/objects" / pin["sha256"]
            retained = ref(target)
            require(verify(retained) == raw, "stored custody bytes differ from reviewed input")
            by_identity[identity] = retained
            stored_new += 1
        archived.append({"original": pin, "archive": retained})
    index = {"freeze": freeze_ref, "refs": archived}
    if custody_manifest is not None:
        index["custody"] = {
            "mode": "immutable_prior_archive_or_sha256_object",
            "prior_indexes": [item[0] for item in reuse_indexes],
            "store_manifest": ref(custody_manifest) if custody_manifest.exists() else None,
            "logical_input_bytes": sum(pin["bytes"] for pin, _ in frozen_bytes),
            "unique_input_bytes": sum(size for size, _ in by_identity),
            "unique_prior_archive_objects_reused": reused_prior,
            "unique_objects_stored_or_reused": stored_new,
            "refs": len(archived)}
    archive_index = archive / "reviewed-bytes.json"
    archive_index.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return archive_index, archived


def main():
    parser = argparse.ArgumentParser()
    for name in ("review", "review-sha", "decision", "freeze", "freeze-sha",
                 "proposal", "proposal-sha", "descriptor-sha", "result", "archive"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--custody-manifest")
    parser.add_argument("--reuse-archive-index", action="append", default=[])
    parser.add_argument("--reuse-archive-index-sha", action="append", default=[])
    args = parser.parse_args()
    root = Path.cwd().resolve()

    def path(relative):
        p = root / relative
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                "unsafe relative path")
        require(p.resolve().is_relative_to(root), "path escapes repository")
        return p

    def digest(raw):
        return hashlib.sha256(raw).hexdigest()

    def ref(p):
        raw = p.read_bytes()
        return {"path": p.relative_to(root).as_posix(), "bytes": len(raw), "sha256": digest(raw)}

    def verify(pin):
        raw = path(pin["path"]).read_bytes()
        require(len(raw) == pin["bytes"] and digest(raw) == pin["sha256"],
                "input pin mismatch: " + pin["path"])
        return raw

    def guarded(relative, expected):
        pin = ref(path(relative))
        require(pin["sha256"] == expected, "input version mismatch: " + relative)
        return pin, strict_json(verify(pin))

    review_ref, review = guarded(args.review, args.review_sha)
    freeze_ref, freeze = guarded(args.freeze, args.freeze_sha)
    require(review["decision"] == args.decision and
            args.decision == f"ACCEPT_{args.rows}_SCOPED_INSTALLED_MANUAL_IMPLEMENTATIONS",
            "distinct scoped acceptance required")
    require(review["reviewed_freeze"]["sha256"] == freeze_ref["sha256"], "review/freeze mismatch")
    for key, value in review.items():
        if key.startswith("remaining_material"):
            require(value == [], "material defect remains")
    proposal_ref = ref(path(args.proposal))
    require(proposal_ref["sha256"] == args.proposal_sha, "proposal pin mismatch")
    recommendation = review["strict_adoption_recommendation"]
    reviewed_proposal = recommendation.get("operations", recommendation.get("operation_input"))
    require(reviewed_proposal == proposal_ref, "proposal not distinctly reviewed")
    proposals = [strict_json(line) for line in verify(proposal_ref).splitlines()]
    require(len(proposals) == args.rows > 0, "proposal denominator mismatch")
    descriptor_path = path("Planning/Fathom-Exercise-WBS-Annex-v1.json")
    before_bytes = descriptor_path.read_bytes()
    require(digest(before_bytes) == args.descriptor_sha, "descriptor preimage mismatch")
    descriptor = strict_json(before_bytes)
    base = verify(descriptor["base"])
    before = resolve(base, descriptor["current_status_resolution"]["operations"])
    require(before["total"] == descriptor["current_view"]["children"]["total_child_identities"],
            "official denominator mismatch")
    require(before["status_counts"] == descriptor["current_view"]["children"]["child_status_counts"],
            "current descriptor counts mismatch")
    archive = path(args.archive)
    result_path = path(args.result)
    require(not archive.exists() and not result_path.exists(), "new archive/result required")
    require(len(args.reuse_archive_index) == len(args.reuse_archive_index_sha), "prior archive version guards required")
    custody_manifest = path(args.custody_manifest) if args.custody_manifest else None
    require(custody_manifest is not None or not args.reuse_archive_index, "reuse requires custody manifest")
    reuse_indexes = [guarded(p, sha) for p, sha in
                     zip(args.reuse_archive_index, args.reuse_archive_index_sha)]
    # Read and verify every frozen input before the first publication write.
    frozen_bytes = [(pin, verify(pin)) for pin in freeze["refs"]]
    archive.mkdir(parents=True)
    archive_index, archived = retain_reviewed_inputs(
        root, frozen_bytes, archive, freeze_ref, verify, ref, custody_manifest, reuse_indexes)
    prior = archive / "descriptor.preimage.json"
    prior.write_bytes(before_bytes)
    now = datetime.now(timezone.utc)
    version = {"distinct_review": review_ref, "freeze": freeze_ref,
               "reviewed_byte_archive": ref(archive_index)}
    version_sha = canonical_sha(version)
    # Validate the proposed transitions before publishing the manager decision.
    adopted = []
    for proposal in proposals:
        operation = copy.deepcopy(proposal)
        overlay = operation.pop("proposed_overlay")
        overlay.pop("official_acceptance", None)
        overlay["accepted_cutoff"] = now.isoformat()
        overlay["content_version"] += "@sha256:" + version_sha
        overlay["reviewed_version_canonical_sha256"] = version_sha
        overlay["acceptance_evidence"] = {"scope": "prepublication validation only"}
        operation["current_overlay"] = overlay
        adopted.append(operation)
    combined = descriptor["current_status_resolution"]["operations"] + adopted
    after = resolve(base, combined)
    changed = {key for key in after["rows"] if after["rows"][key]["status"] != before["rows"][key]["status"]}
    require(changed == {op["selection"]["package_key"] for op in adopted} and len(changed) == args.rows,
            "unexpected changed children")
    require(all(before["rows"][key]["status"] == "Pending" for key in changed), "nonpending prestate")
    source_counts = dict(descriptor["current_view"]["source_status_counts"])
    for kind in set(before["app_counts"]) | set(after["app_counts"]):
        source_counts[kind] = source_counts.get(kind, 0) + after["app_counts"].get(kind, 0) - before["app_counts"].get(kind, 0)
    require(sum(source_counts.values()) == descriptor["current_view"]["source_units"], "source denominator changed")
    controller = strict_json(path("Results/manager-resume-r03/controller-state.json").read_bytes())
    authority = copy.deepcopy(controller["authorization_correction"])
    if controller.get("direct_user_reauthorization"):
        verify(controller["direct_user_reauthorization"])
        authority["direct_user_reauthorization"] = controller["direct_user_reauthorization"]
    require(authority["old_pause_superseded"] is True, "current execution authority missing")
    decision = {"schema": "fathom.manager-reviewed-child-adoption.1", "as_of_utc": now.isoformat(),
                "as_of_America_New_York": now.astimezone(ZoneInfo("America/New_York")).isoformat(),
                "decision_owner": "/root current manager/P02", "decision": "ADOPT_EXACT_REVIEWED_MANUAL_CHILDREN",
                "authority": authority, "prior_descriptor": ref(prior), "immutable_base": descriptor["base"],
                "reviewed_proposal": proposal_ref, "reviewed_version": version,
                "reviewed_version_canonical_sha256": version_sha,
                "operation_selection_canonical_sha256": canonical_sha([
                    {"selection": op["selection"], "assert_before": op["assert_before"]} for op in proposals]),
                "before": before["status_counts"], "after": after["status_counts"], "children": after["total"],
                "source_units_after": source_counts, "criteria": review.get("child_criteria", review.get("named_decisions")),
                "scope": "Individual reviewed source-key manual implementation only; construction flags remain historical. No numeric identity allocation, Practice/Session/Attempt/credit/mastery/workbook/parent/MVP increment.",
                "limits": review.get("limits", review.get("fixture_limits")),
                "custody_exception": review.get("custody_exception")}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n")
    result_ref = ref(result_path)
    for operation in adopted:
        operation["current_overlay"]["acceptance_evidence"] = result_ref
    operations_path = archive / "child-operations.ADOPTED.jsonl"
    operations_path.write_text("".join(json.dumps(op, ensure_ascii=False, sort_keys=True,
                                                 separators=(",", ":")) + "\n" for op in adopted))
    view = descriptor["current_view"]
    descriptor["current_status_resolution"]["operations"] = combined
    view["children"]["child_status_counts"] = after["status_counts"]
    view["children"]["parent_child_counts"] = after["parent_counts"]
    view["source_status_counts"] = source_counts
    previous = view.get("installed_manual_guidance", {})
    count = previous.get("accepted_children", 0) + args.rows
    view["installed_manual_guidance"] = {"accepted_children": count,
        "scope": "Existing source-key manual implementation children; excludes unrelated Catalog/Practice counts",
        "latest_authority": result_ref, "version_canonical_sha256": version_sha}
    view["cutoff"] = now.isoformat() + f"; official{after['status_counts']}; source{source_counts}; separate Catalog and whole/parent metrics unchanged."
    descriptor.setdefault("historical_delta_authorities", []).append(descriptor["current_delta_authority"])
    descriptor["current_delta_authority"] = result_ref
    descriptor["reviewed_overlay_authorities"].append(review_ref)
    descriptor["updated_utc"] = now.isoformat()
    descriptor["current_decision_owner"] = decision["decision_owner"]
    descriptor["current_distinct_mapping_reviewer"] = review["reviewer"]
    final_projection = resolve(base, combined)
    require(final_projection["status_counts"] == after["status_counts"], "publication projection changed")
    require(descriptor_path.read_bytes() == before_bytes and verify(descriptor["base"]) == base,
            "publication inputs changed")
    temp = descriptor_path.with_name(descriptor_path.name + ".new")
    require(not temp.exists(), "publication scratch path occupied")
    temp.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, descriptor_path)
    require(resolve(base, strict_json(descriptor_path.read_bytes())["current_status_resolution"]["operations"])["status_counts"] == after["status_counts"], "published resolution differs")
    print(json.dumps({"decision": result_ref, "descriptor": ref(descriptor_path), "operations": ref(operations_path),
                      "archived_refs": len(archived), "status_counts": after["status_counts"],
                      "parent_counts": after["parent_counts"], "source_units": source_counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
