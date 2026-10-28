#!/usr/bin/env python3
"""Package the 105 original workbook pairs as a closed, read-only source library."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Build/parallel-06/source-library-bundle-r01"
CATALOG = "Content/controls/curriculum-v1/workbook-coverage.json"
CATALOG_SHA = "d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb"
SCHEMA = "fathom-source-library.1"
PYPDF_PIN = "6.10.0"
ASSET_PREFIX = "assets/"


class Refusal(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refusal(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def safe_relative(value: str, prefix: str | None = None) -> Path:
    path = Path(value)
    require(not path.is_absolute() and path.parts and all(x not in (".", "..") for x in path.parts)
            and path.as_posix() == value and "\\" not in value and "\x00" not in value,
            f"unsafe relative path: {value}")
    if prefix is not None:
        require(value.startswith(prefix), f"path outside {prefix}: {value}")
    return path


def local_source(root: Path, relative: str) -> Path:
    path = safe_relative(relative, "Notes/music/guitar project/")
    full = root
    for part in path.parts:
        full /= part
        require(not full.is_symlink(), f"source symlink: {relative}")
    require(full.is_file() and full.resolve().is_relative_to(root), f"missing source: {relative}")
    return full


def load_catalog(root: Path) -> dict:
    root = root.resolve(strict=True)
    git_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip())
    require(git_root == root, "root is not the sole Git checkout")
    require(PYPDF_VERSION == PYPDF_PIN, f"PDF extractor drift: {PYPDF_VERSION}")
    path = root / CATALOG
    require(path.is_file() and not path.is_symlink(), "missing or symlinked catalog")
    raw = path.read_bytes()
    require(sha(raw) == CATALOG_SHA, "accepted 105-entry catalog drift")
    catalog = json.loads(raw)["workbook_catalog"]
    require(catalog["catalog_version"] == "curriculum-v1-workbook-source-catalog.5"
            and len(catalog["entries"]) == 105, "catalog version/entry count differs")
    return catalog


def validate_catalog_entry(entry: dict, level: int) -> None:
    require(entry["workbook_id"] == f"fg:workbook:{level:06d}",
            f"workbook identity/order differs at level {level}")
    require(entry["catalog_role"] == "read_only_source_preservation"
            and all(entry.get(k) is False for k in ("admitted", "imported", "runtime_admitted",
                                                   "runtime_eligible", "whole_workbook_complete")),
            f"workbook {level} source-only flags differ")
    for kind, count_name, folder in (("txt", "line_count", "TXT version"),
                                     ("pdf", "page_count", "PDF version")):
        source = entry[kind]
        relative = source["path"]
        safe_relative(relative, f"Notes/music/guitar project/{folder}/")
        require(relative.endswith("."+kind) and isinstance(source["bytes"], int)
                and source["bytes"] > 0 and re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
                and isinstance(source[count_name], int) and source[count_name] > 0,
                f"workbook {level} {kind} metadata differs")


def checked_source(root: Path, source: dict, kind: str) -> bytes:
    relative = source["path"]
    raw = local_source(root, relative).read_bytes()
    require(len(raw) == source["bytes"] and sha(raw) == source["sha256"],
            f"changed source: {relative}")
    if kind == "txt":
        require(source.get("encoding") == "utf-8", f"TXT encoding differs: {relative}")
        lines = raw.decode("utf-8").splitlines()
        require(len(lines) == source["line_count"]
                and len(source["lines"]) == len(lines)
                and all(record["line_number"] == n and record["text"] == line
                        for n, (record, line) in enumerate(zip(source["lines"], lines), 1)),
                f"TXT line inventory differs: {relative}")
    else:
        require(len(PdfReader(io.BytesIO(raw)).pages) == source["page_count"]
                and len(source["pages"]) == source["page_count"],
                f"PDF page count differs: {relative}")
    return raw


def prepare(root: Path, catalog: dict) -> tuple[dict, dict[str, bytes]]:
    entries = catalog["entries"]
    require(len(entries) == 105, "catalog entry count differs")
    index_entries = []
    assets: dict[str, bytes] = {}
    inventory = {}
    for level, entry in enumerate(entries, 1):
        validate_catalog_entry(entry, level)
        first_label = next((line["text"] for line in entry["txt"]["lines"] if line["text"].strip()), "")
        require(first_label and "\n" not in first_label and "\x00" not in first_label,
                f"missing source label: level {level}")
        projected = {"workbook_id": entry["workbook_id"], "legacy_level": level,
                     "label": first_label}
        for kind, count_name in (("txt", "line_count"), ("pdf", "page_count")):
            source = entry[kind]
            original = source["path"]
            bundle_path = ASSET_PREFIX + original
            require(bundle_path not in assets, f"duplicate source path: {bundle_path}")
            raw = checked_source(root, source, kind)
            assets[bundle_path] = raw
            projected[kind] = {"path": bundle_path, "bytes": len(raw),
                               "sha256": sha(raw), count_name: source[count_name]}
            inventory[bundle_path] = {"bytes": len(raw), "sha256": sha(raw)}
        index_entries.append(projected)
    require(len(index_entries) == 105 and len(assets) == len(inventory) == 210,
            "source pair coverage differs")
    index = {"schema": SCHEMA, "catalog_version": catalog["catalog_version"],
             "catalog_sha256": CATALOG_SHA, "admitted": False,
             "runtime_admission": False, "whole_workbook_complete": False,
             "entries": index_entries, "files": inventory}
    return index, assets


def verify_bundle(bundle: Path, expected_index_sha: str | None = None) -> dict:
    require(bundle.is_dir() and not bundle.is_symlink(), "missing or symlinked bundle root")
    seen_files = set()
    for current, dirs, files in os.walk(bundle, followlinks=False):
        for name in dirs + files:
            path = Path(current) / name
            require(not path.is_symlink(), f"bundle symlink: {path.relative_to(bundle)}")
        for name in files:
            path = Path(current) / name
            require(path.is_file(), f"nonregular bundle file: {path.relative_to(bundle)}")
            seen_files.add(path.relative_to(bundle).as_posix())
    require("index.json" in seen_files, "missing bundle index")
    index_bytes = (bundle / "index.json").read_bytes()
    if expected_index_sha is not None:
        require(sha(index_bytes) == expected_index_sha, "bundle index hash differs")
    index = json.loads(index_bytes)
    require(index.get("schema") == SCHEMA and index.get("catalog_sha256") == CATALOG_SHA
            and index.get("catalog_version") == "curriculum-v1-workbook-source-catalog.5"
            and all(index.get(k) is False for k in ("admitted", "runtime_admission", "whole_workbook_complete")),
            "bundle schema, catalog or admission flags differ")
    entries, files = index["entries"], index["files"]
    require(len(entries) == 105 and len(files) == 210, "bundle index cardinality differs")
    expected_files = set()
    by_path = {}
    for path, record in files.items():
        safe_relative(path, ASSET_PREFIX + "Notes/music/guitar project/")
        require(path not in by_path, f"duplicate bundle inventory path: {path}")
        by_path[path] = record
        expected_files.add(path)
    require(seen_files == expected_files | {"index.json"},
            f"bundle file set differs: missing={sorted(expected_files-seen_files)} extra={sorted(seen_files-(expected_files|{'index.json'}))}")
    for level, entry in enumerate(entries, 1):
        require(set(entry) == {"workbook_id", "legacy_level", "label", "txt", "pdf"}
                and entry["workbook_id"] == f"fg:workbook:{level:06d}" and entry["legacy_level"] == level
                and isinstance(entry["label"], str) and entry["label"],
                f"bundle workbook identity/order differs: {level}")
        for kind, count_name in (("txt", "line_count"), ("pdf", "page_count")):
            item = entry[kind]
            require(set(item) == {"path", "bytes", "sha256", count_name},
                    f"bundle {kind} index fields differ: {level}")
            path = item["path"]
            safe_relative(path, ASSET_PREFIX + f"Notes/music/guitar project/{'TXT' if kind=='txt' else 'PDF'} version/")
            require(path in by_path and by_path[path] == {k: item[k] for k in ("bytes", "sha256")},
                    f"bundle entry/inventory mismatch: {path}")
    require({entry[kind]["path"] for entry in entries for kind in ("txt", "pdf")} == expected_files,
            "bundle entry/inventory coverage differs")
    for path, item in by_path.items():
        raw = (bundle / path).read_bytes()
        require(len(raw) == item["bytes"] and sha(raw) == item["sha256"],
                f"changed bundle asset: {path}")
    return index


def build_bundle(root: Path, output: Path) -> dict:
    root = root.resolve(strict=True)
    require(output.is_absolute() and output.resolve().is_relative_to(BUILD.resolve())
            and not output.exists(), "choose a new absolute P06 bundle directory")
    catalog = load_catalog(root)
    index, assets = prepare(root, catalog)
    output.mkdir(parents=True)
    for relative, raw in assets.items():
        path = output / safe_relative(relative, ASSET_PREFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    index_raw = encoded(index)
    with (output / "index.json").open("xb") as stream:
        stream.write(index_raw)
    verify_bundle(output, sha(index_raw))
    return {"index_sha256": sha(index_raw), "index_bytes": len(index_raw),
            "asset_bytes": sum(len(raw) for raw in assets.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--handoff", type=Path)
    args = parser.parse_args()
    try:
        result = build_bundle(args.root, args.output)
        if args.handoff is not None:
            require(args.output.resolve() == BUILD / "bundle"
                    and args.handoff.resolve() == BUILD / "handoff.json" and not args.handoff.exists(),
                    "handoff must be the new P06 Build handoff.json")
            args.handoff.write_bytes(encoded({"schema": "fathom-source-library-handoff.1",
                                              "bundle_root": "bundle",
                                              "index": {"path": "index.json", "sha256": result["index_sha256"],
                                                        "bytes": result["index_bytes"]}}))
    except (Refusal, OSError, KeyError, UnicodeError, json.JSONDecodeError) as error:
        parser.exit(2, f"REFUSED: {error}\n")
    print(f"PASS: 105 workbooks, 210 exact source assets, "
          f"{result['asset_bytes']} bytes, index {result['index_sha256']}")


if __name__ == "__main__":
    main()
