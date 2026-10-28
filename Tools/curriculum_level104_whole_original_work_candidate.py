#!/usr/bin/env python3
"""Pinned, detached whole-Level104 original-work source conversion."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_XV_Level_104_Complete_Original_Work_Production_Compose_Arrange_Revise_Rehearse_Record_Critique_and_Finalize"
TXT = f"Notes/music/guitar project/TXT version/{STEM}.txt"
PDF = f"Notes/music/guitar project/PDF version/{STEM}.pdf"
MAP = "Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json"
PINS = {TXT:(1426,"423796924890455084cf958e2b67ae173028a48bd846fa44d14951e8600259d2"),
        PDF:(48816,"15c67144a0f47883b46822e32cce12c413b6a0db9e1f0d77c7615b3d0454c3d8"),
        MAP:(199753,"bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6")}
CLAIMS = dict(zip("ABCDEFGHIJ",[96,160,144,128,128,112,128,128,352,64]))
COUNTS = dict(zip("ABCDEFGHIJ",[16,16,13,12,15,14,6,14,26,8]))
PAGE_MODULE = {3:"A",4:"A",5:"B",6:"B",7:"C",8:"C",9:"D",10:"D",11:"E",12:"E",
               13:"F",14:"F",15:"G",16:"G",17:"H",18:"H",19:"I",20:"I",21:"I",22:"J"}
END = "Complete the page before advancing."
SPECS = {
  1:("Module\nExercise\nEvents\n","TOTAL\n1440",3,10,["module","exercise","events"]),
  2:("Gate\nQuestion\n",END,2,9,["gate","question"]),
  3:("Field\nWrite before composing\n",END,1,9,["field"]),
  4:("Element\nNon-negotiable?\nWhy?\n",END,1,7,["element"]),
  5:("Stage\nDeliverable\n",END,2,8,["stage","deliverable"]),
  6:("Constraint\nRequirement\n",END,2,8,["constraint","requirement"]),
  7:("Layer\nOwner\nRemove if redundant?\n",END,1,8,["layer"]),
  8:("Version\nRequirement\n",END,2,5,["version","requirement"]),
  9:("Question\nRevision\n",END,2,8,["question","revision"]),
  10:("Version\nKeep\n",END,2,4,["version","keep"]),
  11:("Problem\nRevision\n",END,2,8,["problem","revision"]),
  12:("Pass\nRestriction\n",END,2,7,["pass","restriction"]),
  13:("Risk\n0-4\nFallback\n",END,1,7,["risk"]),
  14:("Pass\nTask\n",END,2,7,["pass","task"]),
  15:("Take\nPurpose\n",END,2,5,["take","purpose"]),
  17:("Priority\nQuestion\n",END,2,8,["priority","question"]),
  18:("Compare\nChoose\n",END,2,6,["compare","choose"]),
  19:("Deliverable\nRequirement\n",END,2,10,["deliverable","requirement"]),
  20:("Dimension\nMust contrast primary in at least four\n",END,2,8,["dimension","contrast_example"]),
  21:("Item\nRequired\n",END,2,8,["item","required"]),
  22:("Category\n0\n1\n2\n","Pass Section XV",4,8,["category","score_0","score_1","score_2"]),
}


class ConversionError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_sources(root: Path = ROOT) -> tuple[list[str],list[str],dict]:
    root = root.resolve(strict=True)
    raw = {}
    for rel,(size,digest) in PINS.items():
        path = root/rel
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ConversionError(f"unsafe source {rel}")
        data = path.read_bytes()
        if len(data)!=size or sha(data)!=digest:
            raise ConversionError(f"pinned source drift {rel}")
        raw[rel] = data
    row = next((r for r in json.loads(raw[MAP])["rows"] if r["level"]==104),None)
    required = {"section":"XV","wbs_owner":"2.3.1.3.1","txt_path":TXT,"pdf_path":PDF,
                "conversion_status":"not_converted","review":"Pending","admitted":False}
    if row is None or any(row.get(k)!=v for k,v in required.items()):
        raise ConversionError("source-map identity/status drift")
    lines = raw[TXT].decode("utf-8").splitlines()
    pages = [p.extract_text() or "" for p in PdfReader(root/PDF).pages]
    if len(pages)!=22 or not pages[0].startswith("Guitar Exercises - Section XV, Level 104"):
        raise ConversionError("PDF page identity drift")
    for p in range(2,23):
        if not pages[p-1].startswith("Production Gate Sequence" if p==2 else "Module "):
            raise ConversionError(f"PDF heading p{p}")
    return lines,pages,row


def table(page: str,p: int) -> list[dict]:
    start,end,width,count,keys = SPECS[p]
    if page.count(start)!=1 or page.count(end)!=1:
        raise ConversionError(f"PDF table boundary p{p}")
    cells = page.split(start,1)[1].split(end,1)[0].strip().splitlines()
    if len(cells)!=width*count:
        raise ConversionError(f"PDF table p{p} shape {len(cells)}")
    return [dict(zip(keys,cells[i:i+width])) for i in range(0,len(cells),width)]


def make(root: Path = ROOT) -> dict:
    lines,pages,row = read_sources(root)
    if "COMPLETE WRITTEN WORKLOAD: 1440 events" not in lines or sum(CLAIMS.values())!=1440:
        raise ConversionError("TXT workload drift")
    cover = table(pages[0],1)
    if [(x["module"],x["events"]) for x in cover] != [(a,str(CLAIMS[a])) for a in "ABCDEFGHIJ"]:
        raise ConversionError("PDF workload drift")
    anchors = {}
    for letter in "ABCDEFGHIJ":
        found = [n for n,s in enumerate(lines,1) if re.fullmatch(rf"{letter}\. .+ - {CLAIMS[letter]} events",s)]
        if len(found)!=1: raise ConversionError(f"TXT module {letter}")
        anchors[letter]=found[0]
    refs = {p:{"page":p,"extracted_text_sha256":sha(pages[p-1].encode())} for p in range(1,23)}
    modules = {a:{"module":a,"printed_event_claim":CLAIMS[a],"tasks":[]} for a in "ABCDEFGHIJ"}
    def add(letter: str,p: int,row_no: int,fields: dict,kind: str) -> None:
        ordinal = len(modules[letter]["tasks"])+1
        modules[letter]["tasks"].append({"local_key":f"level104-{letter.lower()}-{ordinal:02}",
            "kind":kind,"fields":fields,"source":{"txt_module_line":anchors[letter],
               "txt_row_detail":"omitted","pdf":refs[p],"pdf_row":row_no},
            "canonical_task_id":None,"onset_q":None,"duration_q":None,"observed_result":None})
    gates = table(pages[1],2)
    if [x["gate"] for x in gates] != ["Brief","Identity","Draft","Arrangement","Revision","Rehearsal",
                                           "Recording","Critique","Final"]:
        raise ConversionError("production gate order")
    for p in range(2,22):
        if END not in pages[p-1] or "Preserve the three locked identity elements" not in pages[p-1]:
            raise ConversionError(f"identity preservation p{p}")
    for p in (3,4,5,6,7,8,9,10,11,12,13,14,15,17,18,19,20,21,22):
        letter = PAGE_MODULE[p]
        for i,fields in enumerate(table(pages[p-1],p),1):
            if p==3: fields["written_response"] = None
            if p==4:
                fields["non_negotiable"] = None
                fields["why"] = None
            if p==5 and fields["stage"]!=str(i): raise ConversionError("B stage order")
            if p==7:
                fields["owner"] = None
                fields["remove_if_redundant"] = None
            if p==12 and fields["pass"]!=str(i): raise ConversionError("E economy pass order")
            if p==13:
                fields["risk_score_0_to_4"] = None
                fields["fallback"] = None
            if p==14 and fields["pass"]!=str(i): raise ConversionError("F rehearsal pass order")
            if p==15 and fields["take"]!=str(i): raise ConversionError("G take order")
            if p==17 and fields["priority"].split(". ")[0]!=str(i): raise ConversionError("H critique priority")
            if p==19:
                fields["delivered_artifact"] = None
                if fields["deliverable"]=="Length" and fields["requirement"]!="32-64 bars":
                    raise ConversionError("I primary bar range")
            if p==20: fields["actual_contrast"] = None
            if p==21: fields["delivered_artifact"] = None
            add(letter,p,i,fields,f"pdf_table_p{p}")
    # Page 16 is intentionally an empty evidence-log worksheet, not an authored observation row.
    log_header = "Section\nObserved issue\nClass\nAction\n"
    if pages[15].count(log_header)!=1 or pages[15].split(log_header,1)[1].strip()!=END+" Preserve the three locked identity elements unless evidence shows the piece itself has failed.":
        raise ConversionError("G blank recording log")
    add("G",16,1,{"columns":["Section","Observed issue","Class","Action"],
                  "visible_blank_row_slots":5,"visual_inspection_page":16,
                  "entries":[],"actual_recording":None},"blank_recording_evidence_log")
    for letter,n in COUNTS.items():
        if len(modules[letter]["tasks"])!=n: raise ConversionError(f"module {letter} task count")
    audit = modules["J"]["tasks"]
    if [x["fields"]["category"] for x in audit] != ["Identity","Form","Harmony/groove","Arrangement",
       "Revision","Performance","Recording critique","Finalization"]:
        raise ConversionError("J rubric")
    if "14/16 or better" not in pages[21] or "No zero in identity, form, performance, or finalization." not in lines:
        raise ConversionError("J mastery gate")
    if "One contrasting 16-32 bar original" not in "\n".join(lines) or "32-64 bars" not in pages[18]:
        raise ConversionError("capstone length relationship")
    return {"schema":"fathom.detached.level104.whole-source-candidate.v1","level":104,"section":"XV",
      "wbs_owner":"2.3.1.3.1","source_pins":{p:{"bytes":n,"sha256":h} for p,(n,h) in PINS.items()},
      "source_map_row":row,"canonical_ids":None,"review":"Pending","runtime_eligible":False,
      "imported":False,"admitted":False,"printed_workload_claim":1440,"atomic_event_interpretation":None,
      "production_gate_sequence_pdf_p2":gates,"modules":modules,
      "pdf_page_sources":[{"page":p,"extracted_text_sha256":refs[p]["extracted_text_sha256"],"text":pages[p-1]} for p in range(1,23)],
      "identity_lock":{"required_chosen_elements":3,"chosen_elements":None,"preserve_unless_piece_itself_failed":True},
      "primary_work":{"bar_min":32,"bar_max":64,"actual_bars":None,"final_recording":None,
                      "one_page_map":None,"revision_log":None},
      "companion_work":{"bar_min":16,"bar_max":32,"actual_bars":None,"minimum_major_contrasting_dimensions":4,
                        "selected_dimensions":None,"final_recording":None,"map":None},
      "portfolio":{"printed_item_count":8,"delivered_items":None},
      "mastery_gate":{"rubric_0_to_2":[x["fields"] for x in audit],"threshold":"14/16 or better",
          "required_nonzero":["Identity","Form","Performance","Finalization"],"observed_scores":None},
      "unresolved":["1440 printed events lack complete timed attack records","blank creative brief and identity decisions",
          "blank arrangement responsibilities, risk ratings, fallbacks and recording log",
          "no authored motif/chord/arrangement/performance or audio evidence","no companion dimension choices or finalized portfolio",
          "no observed rubric scores or canonical admission","PDF p20 lacks the companion 16-32 bar length stated in TXT"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    allowed = (ROOT/"Build/parallel-05/2.3.1.3.1-level104-whole-r01").resolve()
    if not output.is_relative_to(allowed): ap.error("output must remain under P05 Level104 Build")
    value = make()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
