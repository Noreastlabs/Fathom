#!/usr/bin/env python3
"""Build the B52 private exercise contracts from pinned source and prior B records."""
from __future__ import annotations

import hashlib
import json
import re
import resource
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = "exercise-impl-shard-b52-r01"
RESERVATION = ROOT / "Prompts/manager-resume-r01/mass-implementation-shards-r02/shard-b52-reservation.json"
INDEX = ROOT / "Results/fullscope-private-b-r01/checkpoint-r03/range-index.json"
OVERLAYS = [
    ROOT / "Build/fullscope-private-b-r01/finite-level052-triad-scans-r01/implementation-overlay.jsonl",
    ROOT / "Build/fullscope-private-b-r01/finite-level052-cycles-switches-r01/implementation-overlay.jsonl",
]
TXT = ROOT / "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_VI_Level_52_Major_and_Minor_Triads_Root_Position_First_Inversion_Second_Inversion_Top_Three_Strings.txt"
PDF = ROOT / "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_VI_Level_52_Major_and_Minor_Triads_Root_Position_First_Inversion_Second_Inversion_Top_Three_Strings.pdf"
OUT = ROOT / "Build" / PRIVATE
RESULTS = ROOT / "Results" / PRIVATE
PINS = {
    RESERVATION: "4a4252aed5d1d8e615e6d0dfc86aad9b4fee01de9714e397eddaf1ed2f98490a",
    INDEX: "3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8",
    TXT: "6e8a5b93bf8b5b66c045ed943e6b873fe52c849da2d741f59857c6a736ea0bd3",
    PDF: "0cdfff4afe53df5c881e05c61908f4576c0a5d828e7440bb9ec88ebaa6fba503",
    ROOT / "Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl": "dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c",
    ROOT / "Planning/Fathom-Exercise-WBS-Annex-v1.json": "a76f5ca0b6bae1bf793cd9867b67f27dfa35e95f8a0596bc0eb1fe756ea67ce1",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def memory_snapshot() -> dict:
    import subprocess

    raw = subprocess.check_output(["vm_stat"], text=True)
    page = int(re.search(r"page size of (\d+) bytes", raw).group(1))
    counts = {k: int(v.replace(".", "")) for k, v in re.findall(r"Pages ([^:]+):\s+([0-9.]+)", raw)}
    names = ("active", "wired down", "occupied by compressor")
    proxy = sum(counts.get(n, 0) for n in names) * page
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"page_bytes": page, "active_wired_occupied_compressor_bytes": proxy,
            "proxy_gib": round(proxy / 2**30, 3), "process_peak_rss_bytes": peak,
            "projected_proxy_gib": round((proxy + 512 * 2**20) / 2**30, 3)}


def get_prior() -> dict:
    index = json.loads(INDEX.read_text())
    rows = {}
    for entry in index["children"]:
        if entry["level"] == 52:
            path = ROOT / entry["packet_path"]
            line = path.read_bytes().splitlines()[entry["line"] - 1]
            if hashlib.sha256(line).hexdigest() != entry["record_sha256"]:
                raise ValueError(f"prior index record hash drift: {entry['package_key']}")
            rows[entry["package_key"]] = (json.loads(line), str(path.relative_to(ROOT)), entry["record_sha256"])
    for path in OVERLAYS:
        for i, line in enumerate(path.read_bytes().splitlines(), 1):
            obj = json.loads(line)
            key = obj["package_key"]
            if key in rows:
                rows[key] = (obj, str(path.relative_to(ROOT)), hashlib.sha256(line).hexdigest())
    return rows


def shapes(lines: list[str]) -> dict:
    result = {}
    current_root = None
    for i, line in enumerate(lines):
        m = re.fullmatch(r"([A-G])(m)? - (Root position|First inversion|Second inversion)", line)
        if not m or i + 5 >= len(lines):
            continue
        root, minor, inversion = m.groups()
        if not lines[i + 1].startswith("G-B-e frets:"):
            continue
        frets = tuple(map(int, lines[i + 1].split(":", 1)[1].strip().split("-")))
        notes = lines[i + 2].split(":", 1)[1].split()
        degrees = lines[i + 3].split(":", 1)[1].split()
        fingers = lines[i + 4].split(":", 1)[1].split()
        if not (len(notes) == len(degrees) == len(fingers) == 3):
            raise ValueError(f"shape cardinality line {i+1}")
        quality = "minor" if minor else "major"
        result[(root, quality, frets)] = {
            "root": root, "quality": quality, "inversion": inversion.lower().replace(" position", ""),
            "frets": frets, "notes": notes, "degrees": degrees, "fingers": fingers,
            "txt_lines": [i + 1, i + 6],
        }
        current_root = root
    if len(result) != 42 or current_root != "B":
        raise ValueError(f"shape atlas incomplete: {len(result)}")
    return result


def contact(shape: dict, string: int) -> dict:
    i = 3 - string
    return {"string": string, "fret": shape["frets"][i], "printed_note": shape["notes"][i],
            "degree": shape["degrees"][i], "finger": shape["fingers"][i]}


def decorate_event(event: dict, shape: dict) -> dict:
    kind = event["kind"]
    decorated = {"order": event["order"], "kind": kind, "onset_q": None, "duration_q": None}
    if kind == "string_contact":
        decorated.update(contact(shape, event["string"]))
    elif kind == "blocked_triad":
        decorated["members"] = [contact(shape, s) for s in (3, 2, 1)]
    elif kind == "muted_strum":
        decorated["kind"] = "pressure_release_mute"
        decorated["sounded_members"] = []
        decorated["held_shape_contacts"] = [contact(shape, s) for s in (3, 2, 1)]
        decorated["performer_action"] = "maintain finger contact, remove pressure, mute backbeat"
    else:
        raise ValueError(kind)
    return decorated


def verify_prior_contact(old: dict, new: dict, key: str) -> None:
    if old["kind"] == "string_contact":
        if (old["string"], old["fret"]) != (new["string"], new["fret"]):
            raise ValueError(f"prior contact mismatch {key}")
    elif old["kind"] in ("blocked_triad", "muted_strum"):
        members = old["members"]
        if [(m["string"], m["fret"]) for m in members] != [(s, c["fret"]) for s, c in zip((3, 2, 1), new.get("members", new.get("held_shape_contacts", [])))]:
            raise ValueError(f"prior blocked contact mismatch {key}")


def generate(key: str, prior: tuple, atlas: dict, lines: list[str], pdf_pages: list[str]) -> dict:
    obj, prior_path, prior_sha = prior
    refs = obj["source_refs"][:2]
    tl = refs[0]["locator"]
    pl = refs[1]["locator"]
    page_no = pl["physical_pages"][0]
    page = pdf_pages[page_no - 1]
    if "Level 52" not in page:
        raise ValueError(f"bad PDF page {key}")
    if tl:
        start, end = tl["line_start"], tl["line_end"]
        excerpt = "\n".join(lines[start - 1:end])
        if excerpt != obj["source_payload"]["txt_excerpt"]:
            raise ValueError(f"TXT excerpt mismatch {key}")
    else:
        excerpt = None
    source = {"txt": {"path": str(TXT.relative_to(ROOT)), "sha256": PINS[TXT], "line_start": tl["line_start"] if tl else None,
                      "line_end": tl["line_end"] if tl else None, "excerpt": excerpt},
              "pdf": {"path": str(PDF.relative_to(ROOT)), "sha256": PINS[PDF], "physical_page": page_no,
                      "page_label": pl.get("within_page_label"), "page_header": page.splitlines()[1]}}
    common = {"schema_version": "fathom-private-l052-exercise-contract.1", "package_key": key,
              "source_identity": obj["source_identity"], "level": 52, "source": source,
              "prior_record": {"path": prior_path, "sha256": prior_sha},
              "timing": {"authority": "unavailable", "fixed_bpm": None, "onsets_q": None, "durations_q": None,
                         "attack_curve": None, "rule": "No fixed clock or metric placement is printed for this task."},
              "unsupplied": ["fixed_bpm", "absolute_onset", "duration", "attack_curve", "absolute_pitch_octave", "mastery_credit", "rights"],
              "runtime_admitted": False, "canonical_id": None, "status": "private_source_backed_manual_contract"}
    prior_events = obj["implementation"].get("events", [])
    if "major-and-minor-triads" in key and "module-" not in key:
        m = re.search(r"-(major|minor)-([a-g])m?-(root-position|first-inversion|second-inversion)$", key)
        if not m:
            raise ValueError(key)
        quality, root, _ = m.groups()
        frets = tuple(map(int, lines[tl["line_start"]].split(":", 1)[1].strip().split("-")))
        shape = atlas[(root.upper(), quality, frets)]
        if len(prior_events) != 10:
            raise ValueError(key)
        events = [decorate_event(e, shape) for e in prior_events]
        for old, new in zip(prior_events, events):
            verify_prior_contact(old, new, key)
        common.update({"family": "shape_workout", "shape": shape, "events": events,
                       "printed_order": "four blocked triads, then G-B-e-e-B-G",
                       "performer_choices": ["pace", "spacing and sustain of all ten attacks", "silent formation before first attack"],
                       "unresolved_or_conflict": []})
    elif "module-d" in key:
        first = excerpt.splitlines()[0]
        token = first.split(":", 1)[0]
        root, quality = token[0], "minor" if token.endswith("m") else "major"
        parsed = re.findall(r"([R12])\(([0-9]+-[0-9]+-[0-9]+)\)", first)
        if len(parsed) != 6 or len(prior_events) != 6:
            raise ValueError(key)
        events = []
        for old, (inv, fret_text) in zip(prior_events, parsed):
            shape = atlas[(root, quality, tuple(map(int, fret_text.split("-"))))]
            event = decorate_event(old, shape)
            verify_prior_contact(old, event, key)
            if [x["fret"] for x in event["members"]] != list(shape["frets"]):
                raise ValueError(key)
            event["inversion"] = {"R": "root", "1": "first", "2": "second"}[inv]
            events.append(event)
        common.update({"family": "inversion_cycle", "events": events, "printed_order": first,
                       "performer_choices": ["pace", "spacing and sustain between blocked attacks"],
                       "performance_instruction": "Name each inversion before playing; release pressure before moving, without a sounding slide.",
                       "unresolved_or_conflict": []})
    elif "module-e" in key:
        first = excerpt.splitlines()[0]
        m = re.match(r"([A-G]) \(([^)]+)\) <-> ([A-G]m) \(([^)]+)\):", first)
        if not m or len(prior_events) != 8:
            raise ValueError(key)
        root, major_frets, minor_name, minor_frets = m.groups()
        shapes = [atlas[(root, "major", tuple(map(int, major_frets.replace(" ", "").split(","))))],
                  atlas[(root, "minor", tuple(map(int, minor_frets.replace(" ", "").split(","))))]]
        events = []
        for i, old in enumerate(prior_events):
            event = decorate_event(old, shapes[i % 2])
            verify_prior_contact(old, event, key)
            event["quality"] = "major" if i % 2 == 0 else "minor"
            events.append(event)
        changing = [s for s in (3, 2, 1) if contact(shapes[0], s)["fret"] != contact(shapes[1], s)["fret"]]
        if len(changing) != 1:
            raise ValueError(f"quality switch moves {len(changing)} strings: {key}")
        if shapes[0].get("variant_source"):
            common["unsupplied"].append("C major second-inversion high-voicing fingers")
        common.update({"family": "quality_switch", "events": events,
                       "quality_string": changing[0], "printed_order": "major-minor repeated to eight re-attacks",
                       "performance_instruction": "Move only the quality-defining third. Keep common root and fifth ringing when possible in slow pass; clean re-attacks count.",
                       "performer_choices": ["pace", "slow-pass sustain", "spacing of eight counted re-attacks"],
                       "unresolved_or_conflict": []})
    elif "module-f" in key:
        if "voice-test" in key:
            label = "TOP-VOICE TEST" if "top-voice" in key else "BASS-VOICE TEST"
            statement = next((s for s in page.splitlines() if s.startswith(label)), None)
            if not statement:
                raise ValueError(key)
            common.update({"family": "voice_emphasis_test", "events": [], "pdf_instruction": statement,
                           "pattern_references": ["F2", "F3", "F4", "F5"] if label.startswith("TOP") else None,
                           "accent_string": 1 if label.startswith("TOP") else 3,
                           "performer_choices": ["which pattern(s) to repeat" if label.startswith("BASS") else "pace and expressive accent",
                                                 "pace and accent strength", "further chord/quality/inversion selection"],
                           "unresolved_or_conflict": ([{"field": "bass_test_repeat_scope", "reason": "PDF says 'Repeat while accenting only G' without restating F2-F5; surrounding top-voice instruction supplies context but does not fix scope."}] if label.startswith("BASS") else [])})
            common["status"] = "private_source_backed_choice_contract"
        else:
            m = re.search(r"-f([2-6])-", key)
            if not m or len(prior_events) != 8:
                raise ValueError(key)
            cell = int(m.group(1))
            reps = {2: ("A", "minor", (5, 5, 5)), 3: ("E", "major", (4, 5, 4)),
                    4: ("G", "major", (4, 3, 3)), 5: ("D", "minor", (7, 6, 5)),
                    6: ("F", "major", (5, 6, 5))}
            shape = atlas[reps[cell]]
            events = [decorate_event(e, shape) for e in prior_events]
            for old, new in zip(prior_events, events):
                verify_prior_contact(old, new, key)
            common.update({"family": "pattern_cell", "cell": f"F{cell}", "representative_shape": shape,
                           "events": events, "printed_order": excerpt.splitlines()[1],
                           "performer_choices": ["pace", "spacing and hold/release length", "one major and one minor triad in each inversion for extension"],
                           "unresolved_or_conflict": []})
            if cell == 6:
                common["unresolved_or_conflict"].append({"field": "printed_attack_count_vs_mute", "reason": "PDF/TXT label eight attacks although the cell alternates four sounded CHORDs and four pressure-release mute actions; do not credit mute as pitched chord attack."})
    else:
        raise ValueError(key)
    for i, event in enumerate(common["events"], 1):
        if event["order"] != i:
            raise ValueError(f"order corruption {key}")
    if common["family"] in ("shape_workout", "inversion_cycle", "quality_switch"):
        members = common["events"][0]["members"]
        frets = "-".join(str(c["fret"]) for c in members)
        if frets not in page:
            raise ValueError(f"PDF printed contact absent on physical page {page_no}: {key}")
    return common


def main() -> None:
    for path, expected in PINS.items():
        if sha(path) != expected:
            raise ValueError(f"pin drift: {path}")
    reg = (ROOT / "Prompts/parallel-02/Lane-Reservations-Current.md").read_text()
    if "B52 Level52 transfers 84 keys" not in reg.splitlines()[2] or "OPEN_AT_MANAGER_DISPATCH" not in reg.splitlines()[0]:
        raise ValueError("P02 B52 lease not open")
    reservation = json.loads(RESERVATION.read_text())
    keys = reservation["keys"]
    if len(keys) != len(set(keys)) or len(keys) != 84:
        raise ValueError("reservation key cardinality")
    lines = TXT.read_text().splitlines()
    atlas = shapes(lines)
    # Module E3 prints a higher C-major second inversion than the C workout card.
    # It is the same pitch classes, but the PDF does not supply fingers for this voicing.
    atlas[("C", "major", (12, 13, 12))] = {
        **atlas[("C", "major", (0, 1, 0))], "frets": (12, 13, 12),
        "fingers": [None, None, None], "variant_source": "PDF physical page 13; TXT line 390",
    }
    from pdfplumber import open as pdf_open
    with pdf_open(PDF) as doc:
        pages = [p.extract_text() or "" for p in doc.pages]
    if len(pages) != 20:
        raise ValueError("PDF page count")
    prior = get_prior()
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    outputs = []
    for batch_no, segment in enumerate((keys[:42], keys[42:77], keys[77:]), 1):
        mem = memory_snapshot()
        if mem["projected_proxy_gib"] >= 13:
            dump(RESULTS / f"batch-{batch_no:02d}-resource-stop.json", {"remaining_keys": keys[sum(map(len, outputs)):], "memory": mem})
            raise RuntimeError("resource guard")
        recs = [generate(key, prior[key], atlas, lines, pages) for key in segment]
        path = OUT / f"contracts-batch-{batch_no:02d}.jsonl"
        path.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in recs))
        outputs.append(segment)
        done = sum(map(len, outputs))
        dump(RESULTS / f"checkpoint-batch-{batch_no:02d}.json", {"batch": batch_no,
             "attempted": done, "source_backed_dispositioned": done,
             "remaining_count": 84 - done, "remaining_keys": keys[done:],
             "packet": {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)},
             "memory": memory_snapshot(), "failures": []})
    print(json.dumps({"attempted": 84, "dispositioned": 84, "remaining": 0,
                      "packets": [str((OUT / f'contracts-batch-{i:02d}.jsonl').relative_to(ROOT)) for i in (1, 2, 3)]}))


if __name__ == "__main__":
    main()
