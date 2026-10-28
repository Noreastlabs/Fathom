"""Pure, strict resolution of reviewed child operations against an immutable base.

This module grants no acceptance authority and writes no evidence or descriptor.
The caller must bind every new operation to a distinct review and manager decision.
"""
from __future__ import annotations

import collections
import hashlib
import json


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def canonical_sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def resolve(base_bytes, operations):
    """Return exact row/count projection; refuse unknown or mismatched operations."""
    pending = {}
    for operation in operations:
        key = operation["selection"]["package_key"]
        require(isinstance(key, str) and key, "empty operation key")
        require(key not in pending, "duplicate operation: " + key)
        pending[key] = operation

    rows, identities = {}, set()
    status_counts, app_counts = collections.Counter(), collections.Counter()
    parents = {}
    for number, line in enumerate(base_bytes.splitlines(), 1):
        candidate = strict_json(line)
        key, exercise = candidate["package_key"], candidate["exercise"]
        identity, parent = exercise["source_identity"], candidate["existing_parent_id"]
        require(key not in rows and identity not in identities, "duplicate base identity")
        identities.add(identity)
        status, app = candidate["status"], exercise["app_status"]
        overlay = None
        if key in pending:
            operation = pending.pop(key)
            selection = operation["selection"]
            require(selection["source_identity"] == identity and
                    selection["existing_parent_id"] == parent, "operation identity mismatch: " + key)
            require(selection["exercise_canonical_json_sha256"] == canonical_sha(exercise) and
                    selection["candidate_canonical_json_sha256"] == canonical_sha(candidate),
                    "operation base hash mismatch: " + key)
            require(selection["canonical_hash_encoding"] ==
                    "UTF-8 JSON sort_keys=true separators=(comma,colon) ensure_ascii=false",
                    "operation canonical encoding mismatch: " + key)
            before = {"candidate_status": status, "exercise_app_status": app,
                      "proposal_status": candidate["proposal"]["status"],
                      "proposal_app_status": candidate["proposal"]["app_status"]}
            require(operation["assert_before"] == before, "operation prestate mismatch: " + key)
            require("current_overlay" in operation and "proposed_overlay" not in operation,
                    "proposed operation cannot grant acceptance: " + key)
            overlay = operation["current_overlay"]
            require(overlay["status"] == "Accepted" and overlay["app_status"] == "installed",
                    "unsupported reviewed transition: " + key)
            require(bool(overlay.get("acceptance_evidence")), "missing acceptance evidence: " + key)
            if "base_line" in overlay:
                require(type(overlay["base_line"]) is int and overlay["base_line"] == number,
                        "operation base line mismatch: " + key)
            if "source_key" in overlay:
                require(overlay["source_key"] == key, "operation source key mismatch: " + key)
            status, app = overlay["status"], overlay["app_status"]
        rows[key] = {"base_line": number, "source_identity": identity, "parent": parent,
                     "status": status, "app_status": app, "overlay": overlay}
        status_counts[status] += 1
        app_counts[app] += 1
        parents.setdefault(parent, collections.Counter())[status] += 1
    require(not pending, "unknown operation keys: " + ",".join(sorted(pending)))
    return {"rows": rows, "total": len(rows), "status_counts": dict(status_counts),
            "app_counts": dict(app_counts),
            "parent_counts": {parent: {"total": sum(counts.values()), **counts}
                              for parent, counts in parents.items()}}
