#!/usr/bin/env python3
"""P95: pinned-original Level23 first A-minor rolling cell, nonadmitted native reference."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("Build/parallel-95/controlled-open-level023-first-rolling-cell-r01")
BASE = Path("Content/controls/curriculum-v1")
STEM = "Scale_Exercises_Section_III_Level_23_Natural_Minor_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder"
TXT = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
P08 = Path("Build/parallel-08/2.3.1.1.1-level023-whole-r01/candidate-01.json")
P08_RESULT = Path("Results/parallel-08/exercises/conversion/20260923T150205Z-2.3.1.1.1-level023-whole-candidate-r01-results.md")
P12_RESULT = Path("Results/parallel-12/conversion/20260923T180914Z-2.3-level023-whole-source-preservation-schema1-r01-results.md")
RELEASE = Path("Prompts/parallel-95/controlled-open-level023-first-rolling-cell-r01/manager-source-slot-release-addendum-01.md")
NATIVE = Path("Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate")
PINS = {
 TXT:"c8c01c4a4ad95e1aed5323d485b359a1bd4d057f46fd2b3ffe8277324b0032f7",
 PDF:"5601a14c406f3b33e455e96d4539ade22160ed0ac95aa782b36a2ef9d960dd43",
 P08:"4ac1bacef35c57994038c5957c891c9bc491c38566d62c506dc955ef96c273dc",
 P08_RESULT:"d49801965fb3d9233920723cb86f59ca1c025f15474c8400157a2f83e3559880",
 P12_RESULT:"d7e469c01a58762a19dcd0f1c2942f3c776fef4ffdbf413ee8bd391988eb79b3",
 RELEASE:"070931f9ef65f0ab2996532e5e5dbc7a437bd6fdf371f868c53bcc70d8501903",
 BASE/"package.json":"766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255",
 BASE/"identity-registry.json":"5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5",
 BASE/"expected-profile.json":"21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a",
 NATIVE:"a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714"
}
ITEM = "fg:item:009950"
MODULE = "fg:module:009950"
VARIANTS = ("fg:variant:009950","fg:variant:009951")
WORKBOOK = "fg:workbook:000023"
NAMES = ("package.json","identity-registry.json","expected-profile.json",
         "candidate-allocation.json","identity-baseline.json","allocation-baseline.json",
         "lineage-baseline.json","source-provenance.json","summary.json")
OPEN = {"E":(1,40),"A":(2,45),"D":(3,50),"G":(4,55),"B":(5,59),"e":(6,64)}
TONES = ("A","B","C","D","E","F","G","A")
DEGREE = ("1","2","b3","4","5","b6","b7","8")
OFFSETS = (0,2,3,5,7,8,10,12)
PLACEMENT = (("E",5,1),("E",7,3),("E",8,4),("A",5,1),("A",7,3),
             ("A",8,4),("D",5,1),("D",7,3))
GROUPS = ((1,2,3),(2,3,4),(3,4,5),(4,5,6),(5,6,7),(6,7,8),
          (8,7,6),(7,6,5),(6,5,4),(5,4,3),(4,3,2),(3,2,1))
CROSSINGS = ("EEE","EEA","EAA","AAA","AAD","ADD","DDA","DAA","AAA","AAE","AEE","EEE")

class CandidateError(ValueError): pass
def need(ok, code):
    if not ok: raise CandidateError(code)
def encode(v): return (json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n").encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def read(path): return json.loads((ROOT/path).read_bytes())
def pin():
    top=Path(subprocess.check_output(["git","-C",str(ROOT),"rev-parse","--show-toplevel"],text=True).strip())
    need(top.resolve()==ROOT.resolve(),"ROOT_DRIFT")
    for path,digest in PINS.items():
        need(sha((ROOT/path).read_bytes())==digest,"PIN_DRIFT:"+str(path))
def audit_id():
    cmd=["rg","-l","--no-messages","-e",r"fg:(?:item|module):009950",
         "-e",r"fg:variant:00995[01]","--glob","*.json","--glob","*.cpp",
         "--glob","*.hpp","Content","Source","Build"]
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),"IDENTITY_SCAN_FAILED")
    hits=sorted(s for s in run.stdout.splitlines() if not s.startswith(str(OUT)+"/"))
    need(not hits,"PROVISIONAL_ID_COLLISION")
    return {"status":"PASS","scope":["Content","Source","Build"],"method":cmd,
            "wanted":[ITEM,MODULE,*VARIANTS],"matches":hits,"canonical_reservation":False}
def cells(row,label):
    parts=row.split("|")
    need(len(parts)==14 and parts[0]==label and parts[-1]=="","ROW_SHAPE:"+label)
    out=[]
    for block in parts[1:-1]:
        need(len(block)==9,"GROUP_WIDTH:"+label)
        slots=[]
        for n in (0,3,6):
            token=block[n:n+3]; value=token.rstrip("-")
            allowed=value.isdigit() or (label=="Deg" and value in ("b3","b6","b7"))
            need((not value and token=="---") or
                 (allowed and value+"-"*(3-len(value))==token),"SLOT:"+label)
            slots.append(value or None)
        out.append(slots)
    return out
def source_facts():
    pin()
    raw=(ROOT/TXT).read_bytes()
    lines=raw.decode().splitlines()
    pages=[(page.extract_text() or "").splitlines() for page in PdfReader(str(ROOT/PDF)).pages]
    need(len(lines)==275 and not raw.endswith(b"\n") and len(pages)==7,"SOURCE_BOUNDARY")
    for phrase in ("Each new triplet starts one scale degree farther",
                   "Do not pause or reset at a triplet boundary",
                   "12 triplets and 36 notes","one three-note group per beat",
                   "pause one beat after each 36-note cell","Begin 12-18 BPM below"):
        need(phrase in "\n".join(lines[:61]),"TXT_RULE:"+phrase)
    for phrase in ("Worked example - A natural minor at low-E fret 5",
                   "The octave root is repeated at the turn",
                   "Master the A-minor 36-note cell","pause one beat after each cell"):
        need(phrase in "\n".join(pages[0]),"PDF_RULE:"+phrase)
    need("Eighth-note triplets: one three-note group per beat" in "\n".join(pages[2]),
         "PDF_TRIPLET_RULE")
    block=lines[61:73]
    card=pages[2][3:17]
    worked=pages[0][22:30]
    need(block[0]=="RUNG 01 OF 13 - A NATURAL MINOR - ROOT ON LOW E FRET 5 - FRAME 5-8"
         and block[1]=="Scale tones: A B C D E F G A"
         and "36-note cell" in block[2]
         and card[:4]==["01  A NATURAL MINOR","ROOT E5  |  FRAME 5-8",
                         "36-NOTE / 12-TRIPLET CELL","Scale tones: A B C D E F G A"]
         and block[3:11]==card[4:12]==worked,"FIRST_CARD_PDF_PARITY")
    deg=cells(block[3],"Deg");fng=cells(block[4],"Fng")
    tabs={s:cells(row,s+"  ") for s,row in zip(("e","B","G","D","A","E"),block[5:11])}
    notes=[]
    for g,group in enumerate(GROUPS):
        for slot,pos in enumerate(group):
            wanted=PLACEMENT[pos-1];string,fret,finger=wanted
            need(deg[g][slot]==DEGREE[pos-1] and fng[g][slot]==str(finger),
                 "DEGREE_FINGER")
            printed=[(s,int(tabs[s][g][slot])) for s in tabs if tabs[s][g][slot] is not None]
            need(printed==[(string,fret)],"TAB_CONTACT")
            n={"contact":g*3+slot+1,"group":g+1,"slot":slot+1,"position":pos,
               "degree":DEGREE[pos-1],"finger":finger,"string":string,"fret":fret,
               "midi":OPEN[string][1]+fret,"spelling":TONES[pos-1],
               "phase":"up" if g<6 else "down"}
            need(n["midi"]==45+OFFSETS[pos-1],"PITCH")
            notes.append(n)
        need("".join(notes[-3+i]["string"] for i in range(3))==CROSSINGS[g],"CROSSING")
    need(len(notes)==36 and notes[17]["position"]==notes[18]["position"]==8
         and notes[17]["string"]==notes[18]["string"]=="D"
         and notes[17]["fret"]==notes[18]["fret"]==7
         and notes[0]["fret"]==notes[-1]["fret"]==5,"CELL_COMPLETENESS")
    prior=read(P08)["records"][0]
    need(prior["source_local_key"]=="L23-rung01" and len(prior["groups"])==12,
         "P08_SCOPE")
    for note,earlier in zip(notes,[n for group in prior["groups"] for n in group["notes"]]):
        need((note["string"],note["fret"],str(note["finger"]),note["degree"])==
             (earlier["string"],earlier["fret"],earlier["finger_digit"],earlier["degree_label"]),
             "P08_PRINTED_PARITY")
    return lines,pages,notes
def passage(path,fmt,value,**where):
    return {"path":str(path),"format":fmt,"sha256":PINS[path],**where,
            "text":value,"text_sha256":sha(value.encode())}
def derive(*,force_eligible=False,forced_bpm=None,changed_contacts=None,
           changed_onsets=None,changed_durations=None,changed_strokes=None,
           reserved_item=ITEM,grouping="source_event_time"):
    need(not force_eligible,"FORCED_ELIGIBILITY")
    need(forced_bpm is None,"FIXED_BPM_UNAUTHORIZED")
    need(reserved_item==ITEM,"FOREIGN_ID")
    need(grouping=="source_event_time","SOURCE_EVENT_TIME_REQUIRED")
    audit=read(OUT/"identity-audit.json")
    need(audit["status"]=="PASS" and audit["wanted"]==[ITEM,MODULE,*VARIANTS]
         and not audit["matches"],"IDENTITY_AUDIT_DRIFT")
    lines,pages,notes=source_facts()
    need(changed_contacts is None or changed_contacts==notes,"CONTACT_DRIFT")
    onsets=[list(Fraction(i,3).as_integer_ratio()) for i in range(36)]
    durations=[[1,3] for _ in range(36)]
    need(changed_onsets is None or changed_onsets==onsets,"TIMING_DRIFT")
    need(changed_durations is None or changed_durations==durations,"DURATION_DRIFT")
    strokes={vid:[start if i%2==0 else ("U" if start=="D" else "D") for i in range(36)]
             for vid,start in zip(VARIANTS,("D","U"))}
    need(changed_strokes is None or changed_strokes==strokes,"STROKE_DRIFT")
    refs=("L23-TXT-RULE-1-60","L23-PDF-GUIDANCE-P1","L23-TXT-RUNG01-62-73",
          "L23-PDF-CARD01-P3")
    sources={
      refs[0]:passage(TXT,"txt","\n".join(lines[:60]),first_line=1,last_line=60),
      refs[1]:passage(PDF,"pdf","\n".join(pages[0]),page=1),
      refs[2]:passage(TXT,"txt","\n".join(lines[61:73]),first_line=62,last_line=73),
      refs[3]:passage(PDF,"pdf","\n".join(pages[2]),page=3)}
    events=[];side={};event_sources={}
    for i,n in enumerate(notes):
        eid=f"{ITEM}:event:{i+1:04d}";q=onsets[i]
        context={"source_label":n["degree"],
                 "ordinal":n["position"],
                 "alteration":-1 if n["degree"].startswith("b") else 0}
        event={"event_id":eid,"kind":"note","string":OPEN[n["string"]][0],
               "fret":n["fret"],"finger":n["finger"],"midi":n["midi"],
               "spelling":n["spelling"],"attack":"picked","onset_q":q,
               "duration_q":durations[i],"tie_from":None,
               "degree_contexts":{"A-natural-minor":context}}
        events.append(event);event_sources[eid]=refs[2]
        tabline=67+("e","B","G","D","A","E").index(n["string"])
        side[eid]={"source_local_event_key":f"L23-R01:A:ROLL:{i+1:02d}",
                   "source_txt_ref":refs[2],"source_pdf_ref":refs[3],
                   "source_txt_card_lines":[62,73],"source_txt_degree_line":65,
                   "source_txt_finger_line":66,"source_txt_tab_line":tabline,
                   "source_pdf_page":3,"source_pdf_card_lines":[4,17],
                   "source_pdf_worked_example_lines":[17,30],
                   "source_contact":i+1,"source_group":n["group"],
                   "source_group_slot":n["slot"],"source_scale_position":n["position"],
                   "source_degree":n["degree"],"source_string_label":n["string"],
                   "source_string":event["string"],"source_fret":n["fret"],
                   "source_finger":n["finger"],"source_midi":n["midi"],
                   "source_pitch_spelling":n["spelling"],"source_phase":n["phase"],
                   "repeated_high_root_at_turn":i in (17,18),
                   "timing_txt_ref":refs[0],"timing_txt_line":55,
                   "timing_pdf_ref":refs[1],"nominal_slot_q":q,"duration_q":[1,3],
                   "pick_strokes":{vid:strokes[vid][i] for vid in VARIANTS}}
    variants=[{"id":vid,"label":f"l23-a-first-rolling-{start}-start",
               "role":"notation_practice","route":"isolated_first_a_minor_cell",
               "source_refs":list(refs),"event_ids":list(side),
               "pick_start":start,"pick_start_origin":"source_authored",
               "grouping":{"kind":"source_event_time","notes_per_beat":None,
                           "beat_unit_q":None,"marking_factor":[1,1],
                           "source_label":"eighth-note triplets: one three-note group per beat"},
               "accent_policy":"source_unspecified","tail_pause":None,"unresolved":[]}
              for vid,start in zip(VARIANTS,("D","U"))]
    title="Level 23 Rung01 A-natural-minor isolated 36-contact rolling-triplet cell"
    record={"id":ITEM,"module_id":MODULE,"workbook_id":WORKBOOK,
            "content_revision":1,"lineage":{"kind":"new"},"kind":"notation",
            "legacy_level":23,"status":"converted_candidate","runtime_eligible":False,
            "title":title,"source_refs":list(refs),"authored_text_refs":list(refs),
            "events":events,"variants":variants,"resource_requirements":[],"rubric":None,
            "control_scope":{"extent":"complete_selected_case",
                             "local_case":"L023-R01:A:ROLLING_TRIPLET",
                             "source_event_count":36,"basis_refs":list(refs),
                             "whole_workbook_complete":False,
                             "unresolved":["Other rungs and full route outside packet.",
                                           "Canonical identity and runtime admission pending."]},
            "context":{"local_code":"L023-R01:A:ROLLING_TRIPLET",
                       "route":"isolated A-natural-minor first rolling cell",
                       "position":"low-E root fret5, frame5-8, E/A/D strings",
                       "pick_start_variants":["D","U"],
                       "pick_start":"continuous alternate D/U or U/D through triplets, crossings and octave turn",
                       "tuning_open_midi":[40,45,50,55,59,64],"capo":0,
                       "source_tempo_rules_ref":refs[0]},
            "timing":{"status":"source_defined","unit":"quarter","meter":None,
                      "basis":"Twelve consecutive one-beat groups of three equal eighth-note triplet contacts; q1/3 each, isolated cell q0..12; no intercell pause or fixed BPM."},
            "ambiguities":["Source-relative clean-Level22 tempo is not fixed BPM or observed performance.",
                           "One-beat pressure-release relocation pause applies between neighboring cells, not this isolated cell.",
                           "Capo zero means untransposed standard tuning, not an authored capo instruction."],
            "normalization":[{"kind":"representation_metadata","basis":refs[0],
                              "text":"Source degree 8 is the octave root at contacts 18/19, preserved as ordinal 8."}]}
    base_package,base_registry,base_profile=(read(BASE/name) for name in
       ("package.json","identity-registry.json","expected-profile.json"))
    package={k:copy.deepcopy(v) for k,v in base_package.items()
             if k not in ("records","sources","workbook_catalog")}
    package.update(content_version="curriculum-v1-level023-a-first-rolling-build-only.1",
                   records=[record],sources=sources)
    entities=[base_registry["entities"][0],
              {"id":WORKBOOK,"kind":"workbook","label":"Legacy Level23","parent":"fg:course:000001"},
              {"id":MODULE,"kind":"module","label":title,"parent":WORKBOOK},
              {"id":ITEM,"kind":"item","label":title,"parent":MODULE},
              *({"id":v["id"],"kind":"variant","label":v["label"],"parent":ITEM} for v in variants)]
    registry={"identity_version":base_registry["identity_version"],
              "rules":base_registry["rules"],"entities":entities}
    identity_baseline={"identity_version":registry["identity_version"],
                       "rules":registry["rules"],"entities":[entities[0]]}
    allocation_baseline={"version":"control-allocation.1","authority":"P95 provisional only","records":{}}
    lineage_baseline={"version":"lineage-baseline.1","records":{}}
    allocation={"version":"control-allocation.1",
                "authority":"P95 private provisional nonadmitted; P02 canonical scan required",
                "records":{ITEM:{"legacy_level":23,
                                 "occurrences":{v["source_local_event_key"]:k for k,v in side.items()},
                                 "variants":{v["label"]:v["id"] for v in variants}}}}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ("reference_package","reference_registry","event_sources",
                          "authority_artifacts","workbook_catalog")}
    profile["degree_roots"]={"A-natural-minor":{"basis":"Original Level23 Rung01 A-natural-minor card; pitch class only",
                                               "root_pitch_class":9}}
    profile.update(reference_package=package,reference_registry=registry,
                   event_sources=event_sources)
    profile["authority_artifacts"]=[copy.deepcopy(a) for a in base_profile["authority_artifacts"]
                                    if a["role"] in ("source_manifest","source_acceptance",
                                                     "current_schema_freeze")]
    for role,name,value in (("identity_baseline","identity-baseline.json",identity_baseline),
                            ("allocation_baseline","allocation-baseline.json",allocation_baseline),
                            ("lineage_baseline","lineage-baseline.json",lineage_baseline),
                            ("candidate_identity_allocation","candidate-allocation.json",allocation)):
        profile["authority_artifacts"].append({"path":str(OUT/name),"role":role,
                                                "sha256":sha(encode(value))})
    need(set(event_sources)==set(side)=={e["event_id"] for e in events},"PROVENANCE_COVERAGE")
    summary={"status":"source_interpreted_nonadmitted_reference","record_count":1,
             "event_count":36,"variant_count":2,"projected_membership_target":72,
             "item_id":ITEM,"module_id":MODULE,"variant_ids":list(VARIANTS),
             "identifiers":"provisional_noncanonical","runtime_eligible":False,
             "admitted":False,"whole_workbook_complete":False,
             "source_txt_sha256":PINS[TXT],"source_pdf_sha256":PINS[PDF],
             "p08_comparator_sha256":PINS[P08],"p12_result_sha256":PINS[P12_RESULT],
             "identity_audit_sha256":sha((ROOT/OUT/"identity-audit.json").read_bytes()),
             "case_end_q":[12,1],"last_onset_q":[35,3],
             "interpretation":"One isolated A-minor q1/3 rolling cell; no internal or trailing relocation pause, fixed BPM, mastery or credit."}
    return {"package.json":package,"identity-registry.json":registry,
            "expected-profile.json":profile,"candidate-allocation.json":allocation,
            "identity-baseline.json":identity_baseline,
            "allocation-baseline.json":allocation_baseline,
            "lineage-baseline.json":lineage_baseline,
            "source-provenance.json":{"source_txt_refs":[refs[0],refs[2]],
                                      "source_pdf_refs":[refs[1],refs[3]],
                                      "events":side,"variant_strokes":strokes,
                                      "stroke_basis":"Original TXT/PDF continuous D/U or U/D through twelve triplets and repeated octave root; isolated cell no relocation."},
            "summary.json":summary}
def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=("audit","build","verify"))
    args=parser.parse_args();dest=ROOT/OUT
    if args.command=="audit":
        pin();result=audit_id();dest.mkdir(parents=True,exist_ok=True)
        path=dest/"identity-audit.json";need(not path.exists(),"OUTPUT_EXISTS")
        path.write_bytes(encode(result));print(json.dumps(result,sort_keys=True));return
    output=derive()
    if args.command=="build":
        need(all(not (dest/name).exists() for name in NAMES),"OUTPUT_EXISTS")
        for name in NAMES:(dest/name).write_bytes(encode(output[name]))
    else:
        for name in NAMES:need((dest/name).read_bytes()==encode(output[name]),"OUTPUT_DRIFT:"+name)
    print(json.dumps(output["summary.json"],sort_keys=True))
if __name__=="__main__":main()
