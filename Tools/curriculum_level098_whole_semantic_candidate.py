#!/usr/bin/env python3
"""Build a detached whole-Level98 repertoire-adaptation semantic candidate."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from typing import Any

STEM="Guitar_Exercises_Section_XIV_Level_98_Repertoire_Adaptation_Transposition_Ensemble_Roles_Acoustic_Electric_Conversion_Simplification_and_Alternate_Performance_Versions"
TXT_REL=Path(f"Notes/music/guitar project/TXT version/{STEM}.txt")
PDF_REL=Path(f"Notes/music/guitar project/PDF version/{STEM}.pdf")
CATALOG_REL=Path("Content/controls/curriculum-v1/workbook-coverage.json")
PREDECESSOR_REL=Path("Build/parallel-06/2.3-level098-music-r01/candidate-a.json")
TXT_SHA="1b0fdba1e4988adb02d54b2acc8c4141646db8940b7e4f27deff439d6957b2a0"
PDF_SHA="055bb7557770c83e1b2aebb3114c832f81774bf52034cce9c9270589c6057e56"
CATALOG_SHA="d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb"
PREDECESSOR_SHA="cbf29aad374b31a4fb3d8ef24bc2011c9eb38b05efe5cfb1c9df78debc00f480"
PYPDF_VERSION="6.10.0";WORKBOOK_ID="fg:workbook:000098"
MODULE_COUNTS=dict(zip("ABCDEFGHIJ",(128,128,144,128,128,112,144,216,336,64)))
BUILD_REL=Path("Build/parallel-09/2.3.1.3.1-level098-whole-semantic-r01")
EVIDENCE_REL=Path("Results/parallel-09/exercises/conversion/20260923T171812Z-2.3.1.3.1-level098-whole-semantic-r01-evidence")
OUTPUT_NAME="level098-whole-semantic-candidate.json"

class CandidateError(ValueError):pass

def refuse_if(condition:bool,code:str)->None:
    if condition:raise CandidateError(code)

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def pinned(root:Path,rel:Path,digest:str,length:int|None=None)->bytes:
    refuse_if(rel.is_absolute() or ".." in rel.parts,"UNSAFE_INPUT_PATH")
    path=(root/rel).resolve(strict=True)
    refuse_if(not path.is_relative_to(root) or not path.is_file(),"INPUT_OUTSIDE_ROOT")
    data=path.read_bytes()
    refuse_if(sha(data)!=digest or (length is not None and len(data)!=length),f"PINNED_INPUT_DRIFT {rel}")
    return data

def table(lines:list[str],header:list[str],count:int)->dict[str,Any]:
    starts=[i for i in range(len(lines)-len(header)+1) if lines[i:i+len(header)]==header]
    refuse_if(len(starts)!=1,f"TABLE_HEADER_DRIFT {header}")
    start=starts[0];first=start+len(header);end=first+count*len(header)
    refuse_if(end>len(lines) or any(not x for x in lines[first:end]),f"TABLE_BODY_DRIFT {header}")
    return {"header":header,"rows":[dict(zip(header,lines[i:i+len(header)])) for i in range(first,end,len(header))],"intro":lines[:start],"tail":lines[end:]}

def parse_txt(value:str)->dict[str,Any]:
    lines=value.splitlines()
    refuse_if(len(lines)!=46 or lines[9]!="COMPLETE WRITTEN WORKLOAD: 1528 events","TXT_HEADER_DRIFT")
    modules=[]
    for index,letter in enumerate("ABCDEFGHIJ",start=12):
        match=re.fullmatch(rf"{letter}\. (.+) - (\d+) events",lines[index])
        refuse_if(match is None or int(match.group(2))!=MODULE_COUNTS[letter],f"TXT_MODULE_DRIFT {letter}")
        modules.append({"module":letter,"title":match.group(1),"written_event_count":int(match.group(2)),"txt_line":index+1})
    refuse_if(sum(x["written_event_count"] for x in modules)!=1528,"TXT_COUNT_DRIFT")
    skills=[{"txt_line":i+1,"text":lines[i].removeprefix("- ")} for i in range(24,33)]
    refuse_if(any(not lines[i].startswith("- ") for i in range(24,33)),"TXT_SKILL_DRIFT")
    return {"line_count":46,"lines":[{"line":i+1,"text":x} for i,x in enumerate(lines)],"core_idea":[{"txt_line":7,"text":lines[6]},{"txt_line":8,"text":lines[7]}],"modules":modules,"skills":skills,"capstone":[{"txt_line":i+1,"text":lines[i]} for i in range(35,39)],"mastery":[{"txt_line":i+1,"text":lines[i]} for i in (41,42)],"next":{"txt_line":46,"text":lines[45]}}

def semantic_page(n:int,lines:list[str])->dict[str,Any]:
    if n==1:
        t=table(lines,["Module","Exercise","Events"],10)
        refuse_if([x["Module"] for x in t["rows"]]!=list("ABCDEFGHIJ") or [int(x["Events"]) for x in t["rows"]]!=[MODULE_COUNTS[k] for k in "ABCDEFGHIJ"],"PDF_MODULE_COUNT_DRIFT")
        refuse_if(t["tail"][:2]!=["TOTAL","1528"],"PDF_TOTAL_DRIFT")
        return {"kind":"overview","table":t,"printed_total":1528}
    specs={2:("identity_layers",["Layer","Usually preserve","May change"],7,[]),3:("functional_transposition",["Original","Function","Transpose task"],6,["A"]),4:("transposition_ladder",["Pass","Requirement"],7,["A"]),5:("melody_riff_transposition",["Source pattern","Preserve","Repair if register fails"],6,["B"]),6:("register_repair",["Problem","Repair"],6,["B"]),7:("ensemble_roles",["Situation","Guitar role"],7,["C"]),8:("two_guitar_split",["Pass","Guitar 1","Guitar 2"],6,["C"]),9:("acoustic_to_electric",["Acoustic behavior","Electric adaptation"],6,["D"]),10:("electric_to_acoustic",["Electric behavior","Acoustic adaptation"],6,["D"]),11:("simplifications",["Original complexity","Simplified version"],7,["E"]),12:("reduction_versions",["Version","Content"],5,["E"]),13:("instrumentation_substitution",["Missing element","Guitar may add"],6,["F"]),14:("register_substitution",["Source role","Alternate register treatment"],6,["F"]),15:("alternate_version_design",["Version","Constraint"],8,["G"]),19:("forty_eight_bar_capstone",["Bars","Section","Harmony","Baseline role"],6,["I"]),20:("adaptation_audit",["Category","0","1","2"],8,["J"])}
    if 16<=n<=18:
        t=table(lines,["Pass","Deliverable"],6)
        refuse_if([r["Pass"] for r in t["rows"]]!=list("123456"),"STUDY_PASS_DRIFT")
        refuse_if("16-bar" not in t["intro"][1],"STUDY_BAR_COUNT_DRIFT")
        return {"kind":"sixteen_bar_study","module_scope":["H"],"study_number":n-15,"title":t["intro"][0],"source_piece":t["intro"][1],"adaptation_assignment":t["intro"][2],"passes":t["rows"],"tail":t["tail"],"performed_result":None}
    refuse_if(n not in specs,f"UNKNOWN_PAGE {n}")
    kind,header,count,scope=specs[n]
    t=table(lines,header,count)
    if n==4:refuse_if([r["Pass"] for r in t["rows"]]!=list("1234567"),"A_PASS_DRIFT")
    if n==8:refuse_if([r["Pass"] for r in t["rows"]]!=list("123456"),"C_PASS_DRIFT")
    if n==12:refuse_if([r["Version"] for r in t["rows"]]!=["100%","75%","50%","25%","Emergency"],"REDUCTION_VERSION_DRIFT")
    if n==19:
        refuse_if([r["Bars"] for r in t["rows"]]!=["1-8","9-16","17-24","25-32","33-40","41-48"],"CAPSTONE_FORM_DRIFT")
        return {"kind":kind,"module_scope":scope,"section_rows":t["rows"],"instruction":t["tail"],"required_versions":["solo/acoustic","electric trio","full-band support"],"complete_arrangement_notes":None,"performed_versions":None,"heading":t["intro"]}
    if n==20:
        refuse_if(not t["tail"] or not t["tail"][0].startswith("Pass Level 98: 14/16"),"MASTERY_DRIFT")
        return {"kind":kind,"module_scope":scope,"rubric":t["rows"],"pass_condition":t["tail"][0],"next":t["tail"][1:],"performed_score":None,"heading":t["intro"]}
    return {"kind":kind,"module_scope":scope,"table":t,"performed_result":None}

def validate_catalog(value:dict[str,Any])->dict[str,Any]:
    entries=[e for e in value.get("workbook_catalog",{}).get("entries",[]) if e.get("workbook_id")==WORKBOOK_ID]
    refuse_if(len(entries)!=1,"CATALOG_ENTRY_DRIFT")
    e=entries[0]
    wanted={"review":"Pending","conversion_status":"not_converted","runtime_eligible":False,"runtime_admitted":False,"imported":False,"admitted":False,"whole_workbook_complete":False,"representative_item_id":None}
    refuse_if(any(e.get(k)!=v for k,v in wanted.items()),"CATALOG_STATUS_DRIFT")
    refuse_if(e.get("playable_projection",{}).get("status")!="explicitly_empty_unresolved","CATALOG_PROJECTION_DRIFT")
    for k,path,digest,length in (("txt",TXT_REL,TXT_SHA,1482),("pdf",PDF_REL,PDF_SHA,46898)):
        x=e[k]
        refuse_if((x.get("path"),x.get("sha256"),x.get("bytes"))!=(str(path),digest,length),f"CATALOG_{k.upper()}_DRIFT")
    refuse_if(e["pdf"].get("page_count")!=20 or len(e["pdf"].get("pages",[]))!=20,"CATALOG_PAGE_DRIFT")
    return e

def build(root:Path)->dict[str,Any]:
    import pypdf
    refuse_if(pypdf.__version__!=PYPDF_VERSION,"PYPDF_VERSION_DRIFT")
    catalog=validate_catalog(json.loads(pinned(root,CATALOG_REL,CATALOG_SHA)))
    txt=parse_txt(pinned(root,TXT_REL,TXT_SHA,1482).decode("utf-8"))
    pinned(root,PDF_REL,PDF_SHA,46898)
    predecessor=json.loads(pinned(root,PREDECESSOR_REL,PREDECESSOR_SHA))
    refuse_if(predecessor.get("level")!=98 or predecessor.get("selected_cell_count")!=6 or predecessor.get("whole_workbook_complete") is not False,"PREDECESSOR_STATUS_DRIFT")
    reader=pypdf.PdfReader(root/PDF_REL)
    refuse_if(len(reader.pages)!=20,"PDF_PAGE_COUNT_DRIFT")
    pages=[]
    for n,page in enumerate(reader.pages,1):
        extracted=page.extract_text() or ""
        cached=catalog["pdf"]["pages"][n-1]
        refuse_if(cached.get("page_number")!=n or cached.get("extracted_text_sha256")!=sha(extracted.encode()),f"PDF_TEXT_DRIFT {n}")
        pages.append({"page":n,"extracted_text":extracted,"extracted_text_sha256":sha(extracted.encode()),"semantic":semantic_page(n,extracted.splitlines())})
    first=pages[2]["semantic"]["table"]["rows"]
    narrow=predecessor["module_a"]["cells"]
    refuse_if(any((r["Original"],r["Function"],r["Transpose task"])!=(c["printed_original"],c["printed_function"],c["printed_transpose_task"]) for r,c in zip(first,narrow)),"PREDECESSOR_CELL_MISMATCH")
    spans={"A":[3,4],"B":[5,6],"C":[7,8],"D":[9,10],"E":[11,12],"F":[13,14],"G":[15],"H":[16,17,18],"I":[19],"J":[20]}
    modules=[]
    for m in txt["modules"]:
        slots=[{"slot":i+1,"pitch":None,"string":None,"fret":None,"onset":None,"duration":None,"performed_result":None} for i in range(m["written_event_count"])]
        modules.append({**m,"pdf_pages":spans[m["module"]],"written_event_slots":slots,"slot_allocation":"module_count_only_unresolved_per_row_bar_and_version"})
    return {"schema_status":"detached_whole_source_semantic_candidate_not_curriculum_record","candidate_status":"pending_source_reconciliation","workbook_id":WORKBOOK_ID,"legacy_level":98,"wbs_owner":"2.3.1.3.1","curriculum_review":"Pending","runtime_eligible":False,"imported":False,"admitted":False,"whole_workbook_complete":False,"stable_ids_assigned_by_this_candidate":False,"written_event_total":1528,"source_pair":{"txt":{"path":str(TXT_REL),"bytes":1482,"sha256":TXT_SHA},"pdf":{"path":str(PDF_REL),"bytes":46898,"sha256":PDF_SHA,"page_count":20,"extractor":"pypdf","extractor_version":PYPDF_VERSION}},"frozen_catalog":{"path":str(CATALOG_REL),"sha256":CATALOG_SHA,"status":"read_only_pending","representative_item_id":None},"predecessor":{"path":str(PREDECESSOR_REL),"sha256":PREDECESSOR_SHA,"scope":"six PDF page-3 Module A functional-transposition triples","rows_match":True},"modules":modules,"txt":txt,"pdf_pages":pages,"source_reconciliation":{"module_totals_match_txt_and_pdf":True,"module_A_triples_match_P06_narrow_candidate":True,"no_destination_chords_or_student_solutions_computed":True,"capstone_three_versions_are_assignments_not_performed":True,"module_counts_not_allocated_to_rows_bars_passes_or_versions":True,"no_representative_id":True},"visual_review":[{"pages":[1],"observation":"rendered subtitle has visible bullet separators; pypdf extracted U+007F at those positions","disposition":"preserve extracted text and original PDF, do not treat U+007F as a task symbol"},{"pages":[3,7,12,16,19,20],"observation":"rendered task tables, capstone map and audit are legible at 1200px review scale"}]}

def git_root(cwd:Path)->Path:
    p=subprocess.run(["git","rev-parse","--show-toplevel"],cwd=cwd,capture_output=True,text=True,check=True)
    return Path(p.stdout.strip()).resolve(strict=True)

def output_path(root:Path,output:Path)->Path:
    refuse_if(not output.is_absolute() or output.name!=OUTPUT_NAME,"OUTPUT_PATH_DRIFT")
    parent=output.parent.resolve(strict=True)
    refuse_if(parent not in (root/BUILD_REL,root/EVIDENCE_REL),"OUTPUT_OUTSIDE_LANE")
    target=parent/OUTPUT_NAME
    refuse_if(target.exists() or target.is_symlink(),"OUTPUT_EXISTS")
    return target

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,required=True);ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        refuse_if(root!=git_root(root),"ROOT_NOT_GIT_TOP")
        target=output_path(root,args.output)
        candidate=build(root)
        with target.open("x",encoding="utf-8",newline="\n") as f:
            json.dump(candidate,f,ensure_ascii=False,sort_keys=True,separators=(",",":"));f.write("\n")
        print(json.dumps({"status":"PASS","output":str(target),"written_event_total":1528,"pdf_pages":20},sort_keys=True));return 0
    except (CandidateError,OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError,ImportError) as e:
        print(f"REFUSED: {e}",file=sys.stderr);return 2

if __name__=="__main__":raise SystemExit(main())
