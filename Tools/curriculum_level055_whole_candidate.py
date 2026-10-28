#!/usr/bin/env python3
"""Pinned detached whole-Level-55 major-key harmony candidate."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
STEM = "Guitar_Exercises_Section_VI_Level_55_Diatonic_Major_Key_Harmony_Roman_Numeral_Progressions_and_Transposition"
TXT_REL = Path("Notes/music/guitar project/TXT version") / (STEM + ".txt")
PDF_REL = Path("Notes/music/guitar project/PDF version") / (STEM + ".pdf")
TXT_BYTES, TXT_SHA = 23049, "e21a5b75f68f16d39339b411d156bbf913cde5a2df1f2b1526432605737bd3d2"
PDF_BYTES, PDF_SHA = 62387, "7b0b08ff149323b1715c9e154bd2a9606bd8c409777bc2b657e29b668d91b3d3"
BUILD_REL = Path("Build/parallel-09/2.3.1.2.1-level055-whole-r01")
KEYS = ("F", "C", "G", "D", "A", "E")
FAMILY_KEYS = ("C", "G", "D", "A", "E", "F")
ROMAN = ("I", "ii", "iii", "IV", "V", "vi", "vii°")
QUALITY = ("major", "minor", "minor", "major", "major", "minor", "diminished")
FUNC = ("T", "P", "D")
FUNCTION = ("tonic", "predominant", "tonic color", "predominant", "dominant", "tonic / relative minor", "dominant / leading tone")
SHORT_FUNCTION = {"I":"T","ii":"P","iii":"T","IV":"P","V":"D","vi":"T","vii°":"D"}
PC = {"C":0,"C#":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"Bb":10,"B":11}
OPEN = {"E":40,"A":45,"D":50,"G":55,"B":59,"e":64}
SCALE = {"C":["C","D","E","F","G","A","B"],
         "G":["G","A","B","C","D","E","F#"],
         "D":["D","E","F#","G","A","B","C#"],
         "A":["A","B","C#","D","E","F#","G#"],
         "E":["E","F#","G#","A","B","C#","D#"],
         "F":["F","G","A","Bb","C","D","E"]}
MODULE_LINE = {"A":29,"B":36,"C":142,"D":183,"E":224,"F":265,"G":306,
               "H":347,"I":388,"J":446,"K":476}
ATTACKS = {"A":0,"B":168,"C":96,"D":96,"E":96,"F":96,"G":96,"H":96,
           "I":96,"J":0,"K":96}
PDF_PAGES = {"A":[2],"B":[3,4,5,6,7,8],"C":[9],"D":[10],"E":[11],
             "F":[12],"G":[13],"H":[14],"I":[15,16],"J":[17],"K":[18]}
PROGRESSION_ROMAN = {"C":["I","IV","V","I"],"D":["I","V","vi","IV"],
    "E":["I","vi","IV","V"],"F":["ii","V","I","I"],
    "G":["vi","IV","I","V"],"H":["I","ii","IV","V"]}


class CandidateError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pin(data: bytes, size: int, digest: str, label: str) -> None:
    if len(data)!=size or sha(data)!=digest:
        raise CandidateError(f"PINNED_INPUT_DRIFT {label}: {len(data)} {sha(data)}")


def _list(line: str, prefix: str, count: int) -> list[str]:
    if not line.startswith(prefix):
        raise CandidateError(f"ROW_PREFIX {prefix}")
    parts = [x.strip() for x in line[len(prefix):].split(" | ")]
    if len(parts)!=count or any(not x for x in parts):
        raise CandidateError(f"ROW_COUNT {prefix}")
    return parts


def _chord_from_roman(key: str, roman: str) -> str:
    if key not in SCALE or roman not in ROMAN:
        raise CandidateError(f"ROMAN_UNKNOWN {key}/{roman}")
    index=ROMAN.index(roman)
    return SCALE[key][index]+("m" if QUALITY[index]=="minor" else "dim" if QUALITY[index]=="diminished" else "")


def _triad_spelling(key: str, degree: int) -> list[str]:
    notes=SCALE[key]
    return [notes[(degree-1+j)%7] for j in (0,2,4)]


def _check_triad(chord: str, spelling: list[str], quality: str, context: str) -> None:
    root=chord.removesuffix("dim").removesuffix("m")
    if len(spelling)!=3 or root!=spelling[0] or any(x not in PC for x in spelling):
        raise CandidateError(f"TRIAD_SPELLING {context}")
    intervals=[(PC[x]-PC[root])%12 for x in spelling]
    expected={"major":[0,4,7],"minor":[0,3,7],"diminished":[0,3,6]}[quality]
    if intervals!=expected:
        raise CandidateError(f"TRIAD_QUALITY {context}: {intervals}")


def _fret_triad(raw: str, string_set: list[str], spelling: list[str], inversion: str, context: str) -> list[int]:
    parts=raw.split("-")
    if len(parts)!=3 or any(not p.isdigit() for p in parts):
        raise CandidateError(f"TRIAD_FRET_SHAPE {context}")
    frets=list(map(int,parts))
    sounding=[]
    for string,fret in zip(string_set,frets,strict=True):
        pc=(OPEN[string]+fret)%12
        if pc not in [PC[x] for x in spelling]:
            raise CandidateError(f"TRIAD_FRET_PITCH {context} {string}{fret}")
        sounding.append(pc)
    if sorted(sounding)!=sorted(PC[x] for x in spelling):
        raise CandidateError(f"TRIAD_FRET_CARDINALITY {context}")
    bass_degree={"root":0,"1st":1,"2nd":2}.get(inversion)
    if bass_degree is None or sounding[0]!=PC[spelling[bass_degree]]:
        raise CandidateError(f"TRIAD_INVERSION {context}")
    return frets


def _parse_txt(data: bytes) -> dict:
    lines=data.decode("utf-8").splitlines()
    def L(n: int) -> str: return lines[n-1]
    if len(lines)!=545 or L(1)!="GUITAR EXERCISES - SECTION VI, LEVEL 55" or \
            L(25)!="COMPLETE SOUNDED WORKOUT: 936 attacks.":
        raise CandidateError("TXT_BOUNDARY")
    for key,line in MODULE_LINE.items():
        if not L(line).startswith(f"MODULE {key} - "):
            raise CandidateError(f"MODULE_BOUNDARY {key}")
    if L(8)!="W-W-H-W-W-W-H" or \
            L(11)!="I major | ii minor | iii minor | IV major | V major | vi minor | vii° diminished" or \
            [L(n) for n in (14,15,16)] != ["Tonic: I, iii, vi","Predominant: ii, IV","Dominant: V, vii°"]:
        raise CandidateError("HARMONY_FOUNDATION")
    if L(31)!="Practice keys in circle order: F -> C -> G -> D -> A -> E." or \
            L(32)!="Order of sharps: F C G D A E B. Order of flats: B E A D G C F.":
        raise CandidateError("CIRCLE_SIGNATURE")
    a={"circle_order":list(KEYS),"key_scales":SCALE,"silent_prompts":[],
       "silent_prompt_count":42,"instructions":lines[30:33],"txt_line":29,"pdf_page":2}
    for key in KEYS:
        for degree in range(1,8):
            a["silent_prompts"].append({"key":key,"degree":degree,"scale_note":SCALE[key][degree-1],
                "roman":ROMAN[degree-1],"chord":_chord_from_roman(key,ROMAN[degree-1]),
                "quality":QUALITY[degree-1],"function":FUNCTION[degree-1],
                "sounded_attacks":0,"onset_q":None,"duration_q":None})
    # Six fully printed seven-degree triad families.
    b=[]
    for key,start in zip(FAMILY_KEYS,(38,55,72,89,106,123),strict=True):
        header=L(start)
        if not header.startswith(key+" MAJOR - ") or L(start+1)!="Degree | Note | Roman | Chord | Quality | Spelling | Function":
            raise CandidateError(f"B_KEY_HEADER {key}")
        degrees=[]
        for degree in range(1,8):
            row=L(start+1+degree)
            parts=[p.strip() for p in row.split("|")]
            if len(parts)!=7 or parts[0]!=str(degree):
                raise CandidateError(f"B_DEGREE_ROW {key}-{degree}")
            note,roman,chord,quality,spelling,function=parts[1:]
            if (note,roman,chord,quality,spelling.split("-"),function)!=(SCALE[key][degree-1],ROMAN[degree-1],
                _chord_from_roman(key,ROMAN[degree-1]),QUALITY[degree-1],_triad_spelling(key,degree),FUNCTION[degree-1]):
                raise CandidateError(f"B_HARMONY {key}-{degree}")
            _check_triad(chord,spelling.split("-"),quality,f"B-{key}-{degree}")
            degrees.append({"degree":degree,"note":note,"roman":roman,"chord":chord,
                "quality":quality,"spelling":spelling.split("-"),"function":function,
                "txt_line":start+1+degree})
        set_raw=L(start+9).removeprefix("Triad set: ")
        string_set=set_raw.split("-")
        if len(string_set)!=3 or any(s not in OPEN for s in string_set):
            raise CandidateError(f"B_STRING_SET {key}")
        roman=_list(L(start+10),"Roman: ",7)
        chords=_list(L(start+11),"Chord: ",7)
        inversions=_list(L(start+12),"Inv:   ",7)
        frets_raw=_list(L(start+13),"Fret:  ",7)
        rhythm=_list(L(start+14),"Rhythm voicings: ",7)
        if roman!=list(ROMAN) or chords!=[x["chord"] for x in degrees]:
            raise CandidateError(f"B_LADDER_LABELS {key}")
        for degree,item in enumerate(degrees,1):
            item["inversion"]=inversions[degree-1]
            item["string_set"]=string_set
            item["frets"]=_fret_triad(frets_raw[degree-1],string_set,item["spelling"],inversions[degree-1],f"B-{key}-{degree}")
            item["rhythm_voicing_alternatives"]=rhythm[degree-1].split(" / ")
            item["blocked_plus_arpeggio_attacks"]=4
            item["onset_q"]=item["duration_q"]=None
        if L(start+15)!="Exercise: one blocked triad plus low-middle-high arpeggio for every degree = 28 attacks.":
            raise CandidateError(f"B_ATTACKS {key}")
        b.append({"key":key,"header":header,"degrees":degrees,"string_set":string_set,
                  "attack_count":28,"txt_line":start,"pdf_page":3+FAMILY_KEYS.index(key)})
    # Six fixed Roman/function progression families in six keys.
    progressions={}
    starts={"C":145,"D":186,"E":227,"F":268,"G":309,"H":350}
    for family,start in starts.items():
        cells=[]
        for j,key in enumerate(KEYS):
            n=start+j*6
            m=re.fullmatch(r"([A-G]) major: (.+)",L(n))
            if not m or m.group(1)!=key:
                raise CandidateError(f"PROGRESSION_KEY {family} L{n}")
            chords=m.group(2).split(" - ")
            roman=L(n+1).removeprefix("Roman: ").split(" - ")
            funcs=L(n+2).removeprefix("Function: ").split(" - ")
            voicings=_list(L(n+3),"Voicings: ",4)
            if roman!=PROGRESSION_ROMAN[family] or chords!=[_chord_from_roman(key,r) for r in roman] or \
                    funcs!=[SHORT_FUNCTION[r] for r in roman] or \
                    L(n+4)!="Exercise: one bar per chord, four quarter-note attacks per bar = 16 attacks.":
                raise CandidateError(f"PROGRESSION_HARMONY {family}-{key}")
            bars=[{"bar":q+1,"chord":chords[q],"roman":roman[q],"function":funcs[q],
                    "rhythm_voicing_alternatives":voicings[q].split(" / "),"sounded_attacks":4,
                    "onset_q":None,"duration_q":None} for q in range(4)]
            cells.append({"key":key,"family":family,"bars":bars,"attack_count":16,
                          "txt_line":n,"pdf_page":ord(family)-ord("C")+9})
        progressions[family]=cells
    # Six nearest-inversion four-chord cells; printed voices must equal fret columns.
    i=[]
    family_by_key={x["key"]:x for x in b}
    for key,start in zip(("C","G","D","A","E","F"),(390,399,408,417,426,435),strict=True):
        m=re.fullmatch(r"([A-G]) major on ([EADGBe]-[EADGBe]-[EADGBe])",L(start))
        if not m or m.group(1)!=key:
            raise CandidateError(f"I_HEADER {key}")
        string_set=m.group(2).split("-")
        chords=_list(L(start+1),"Chord: ",4)
        inversions=_list(L(start+2),"Inv:   ",4)
        fret_raw=_list(L(start+3),"Fret:  ",4)
        voices=[]
        for j,name in enumerate(("Low","Mid","Top"),4):
            raw=L(start+j)
            match=re.fullmatch(rf"{name} voice: (\d+-\d+-\d+-\d+)",raw)
            if not match:
                raise CandidateError(f"I_VOICE_SHAPE {key}-{name}")
            voices.append(list(map(int,match.group(1).split("-"))))
        if string_set!=family_by_key[key]["string_set"] or \
                chords!=[_chord_from_roman(key,r) for r in ("I","IV","V","I")]:
            raise CandidateError(f"I_CHORD_ROUTE {key}")
        bars=[]
        for j,chord in enumerate(chords):
            degree=ROMAN.index(("I","IV","V","I")[j])+1
            spelling=_triad_spelling(key,degree)
            frets=_fret_triad(fret_raw[j],string_set,spelling,inversions[j],f"I-{key}-{j+1}")
            if frets!=[v[j] for v in voices]:
                raise CandidateError(f"I_VOICE_FRET {key}-{j+1}")
            bars.append({"bar":j+1,"chord":chord,"roman":("I","IV","V","I")[j],
                         "inversion":inversions[j],"string_set":string_set,"frets":frets,
                         "blocked_plus_arpeggio_attacks":4,"onset_q":None,"duration_q":None})
        if L(start+7)!="Exercise: one blocked attack plus low-middle-high arpeggio per chord = 16 attacks.":
            raise CandidateError(f"I_ATTACKS {key}")
        i.append({"key":key,"bars":bars,"voice_frets":{"low":voices[0],"middle":voices[1],"top":voices[2]},
                  "attack_count":16,"txt_line":start,"pdf_page":15 if len(i)<3 else 16})
    # Twelve analysis keys and twelve transposition answer keys, kept written-only.
    j={"analysis":[],"transposition":[],"written_prompt_count":24,"attack_count":0}
    for number in range(1,13):
        raw=L(448+number)
        m=re.fullmatch(rf"{number}\. (.+) \| answer: key ([A-G]); (.+); (.+)",raw)
        if not m:
            raise CandidateError(f"J_ANALYZE_SHAPE {number}")
        progression,key,roman_raw,func_raw=m.groups()
        chords=progression.split("-")
        numerals=roman_raw.split("-")
        functions=func_raw.split("-")
        if key not in KEYS or len(chords)!=4 or len(numerals)!=4 or len(functions)!=4 or \
                chords!=[_chord_from_roman(key,r) for r in numerals] or \
                functions!=[SHORT_FUNCTION[r] for r in numerals]:
            raise CandidateError(f"J_ANALYZE_ANSWER {number}")
        j["analysis"].append({"number":number,"progression":chords,"answer_key":key,
            "answer_roman":numerals,"answer_function":functions,"printed_text":raw,
            "txt_line":448+number,"pdf_page":17})
    for number in range(1,13):
        raw=L(461+number)
        m=re.fullmatch(rf"{number}\. Move (.+) from ([A-G]) to ([A-G]) \| answer: (.+)",raw)
        if not m:
            raise CandidateError(f"J_TRANSPOSE_SHAPE {number}")
        roman_raw,from_key,to_key,answer=m.groups()
        roman=roman_raw.split("-")
        chords=answer.split("-")
        if from_key not in KEYS or to_key not in KEYS or len(roman)!=4 or \
                chords!=[_chord_from_roman(to_key,r) for r in roman]:
            raise CandidateError(f"J_TRANSPOSE_ANSWER {number}")
        j["transposition"].append({"number":number,"roman":roman,"from_key":from_key,
            "to_key":to_key,"answer_chords":chords,"printed_text":raw,"txt_line":461+number,"pdf_page":17})
    # Twenty-four bars, plus two separately instructed passes without speculative extra count.
    k=[]
    for jkey,key in enumerate(KEYS):
        n=478+jkey*5
        if L(n)!=f"Bars {jkey*4+1}-{jkey*4+4}: {key} major":
            raise CandidateError(f"K_RANGE {key}")
        chords=_list(L(n+1),"Chord: ",4)
        roman=_list(L(n+2),"Roman: ",4)
        funcs=_list(L(n+3),"Function: ",4)
        voicings=_list(L(n+4),"Voicings: ",4)
        if roman!=["I","IV","V","I"] or chords!=[_chord_from_roman(key,r) for r in roman] or \
                funcs!=[SHORT_FUNCTION[r] for r in roman] or \
                chords!=[x["chord"] for x in progressions["C"][KEYS.index(key)]["bars"]]:
            raise CandidateError(f"K_HARMONY {key}")
        k.append({"key":key,"bars":[{"bar":jkey*4+q+1,"chord":chords[q],"roman":roman[q],
            "function":funcs[q],"rhythm_voicing_alternatives":voicings[q].split(" / "),
            "sounded_attacks":4,"onset_q":None,"duration_q":None} for q in range(4)],
            "attack_count":16,"txt_line":n,"pdf_page":18})
    if L(508)!="Pass 1: four quarter-note rhythm attacks per bar = 96 attacks." or \
            not L(509).startswith("Pass 2: ") or not L(510).startswith("Pass 3: "):
        raise CandidateError("K_PASSES")
    modules={"A":a,"B":b,**progressions,"I":i,"J":j,"K":k}
    actual={"A":0,"B":sum(x["attack_count"] for x in b),
        **{m:sum(x["attack_count"] for x in progressions[m]) for m in "CDEFGH"},
        "I":sum(x["attack_count"] for x in i),"J":0,"K":sum(x["attack_count"] for x in k)}
    if actual!=ATTACKS or sum(actual.values())!=936 or len(a["silent_prompts"])!=42 or \
            len(j["analysis"])+len(j["transposition"])!=24:
        raise CandidateError(f"WORKLOAD_MISMATCH {actual}")
    return {"modules":modules,"instructions":{"purpose":L(5),"major_scale_formula":L(8),
        "quality_sequence":L(11),"function_families":lines[13:16],"workload":lines[17:25],
        "circle_order":lines[30:33],"progression_family_titles":{m:L(MODULE_LINE[m]+2) for m in "CDEFGH"},
        "capstone_passes":lines[507:510],"practice":lines[514:524],"error_diagnosis":lines[525:533],
        "mastery":lines[534:542],"next_level":lines[543:545]},"lines":lines}


def _pdf(data: bytes, parsed: dict) -> dict:
    pages=[p.extract_text() or "" for p in PdfReader(BytesIO(data)).pages]
    if len(pages)!=20 or any(f"Page {n} of 20" not in page for n,page in enumerate(pages,1)):
        raise CandidateError("PDF_BOUNDARY")
    modules=parsed["modules"]
    checked={m:0 for m in "ABCDEFGHIJK"}
    def grids(page: str, labels: tuple[str,...]) -> list[list[list[str]]]:
        pattern="".join(re.escape(label)+r"\|([^\n]+)\n" for label in labels)
        return [[[v.strip() for v in raw.split("|") if v.strip()] for raw in match]
                for match in re.findall(pattern,page)]
    if "Six-key circle route used in this level: F -> C -> G -> D -> A -> E" not in pages[1] or \
            "6 keys x 7 degrees = 42 prompts." not in pages[1]:
        raise CandidateError("PDF_A_CIRCLE_COUNT")
    checked["A"]=42
    for family in modules["B"]:
        page=pages[family["pdf_page"]-1]
        ladder=grids(page,(" Rom"," Chd"," Inv"," Frt"))
        if len(ladder)!=1 or ladder[0] != [
            [x["roman"] for x in family["degrees"]],
            [x["chord"] for x in family["degrees"]],
            [x["inversion"] for x in family["degrees"]],
            ["-".join(map(str,x["frets"])) for x in family["degrees"]]]:
            raise CandidateError(f"PDF_B_LADDER {family['key']}")
        for item in family["degrees"]:
            sequence="\n".join((str(item["degree"]),item["note"],item["roman"],item["chord"],
                item["quality"],"-".join(item["spelling"]),item["function"]))
            if sequence not in page:
                raise CandidateError(f"PDF_B_DEGREE {family['key']}-{item['degree']}")
            checked["B"]+=1
        if not re.search(r"Printed\s+triad\s+set:\s+"+re.escape('-'.join(family['string_set']))+r"\.",page):
            raise CandidateError(f"PDF_B_STRING_SET {family['key']}")
        for item in family["degrees"]:
            fret="-".join(map(str,item["frets"]))
            if fret not in page or item["inversion"] not in page:
                raise CandidateError(f"PDF_B_LADDER {family['key']}-{item['degree']}")
        rhythm=" | ".join(" / ".join(x["rhythm_voicing_alternatives"]) for x in family["degrees"])
        if rhythm not in page:
            raise CandidateError(f"PDF_B_RHYTHM {family['key']}")
    for m in "CDEFGH":
        page=pages[PDF_PAGES[m][0]-1]
        pdf_grids=grids(page,(" Rom"," Chd","Func"))
        if len(pdf_grids)!=6:
            raise CandidateError(f"PDF_{m}_GRID_COUNT")
        for cell,grid in zip(modules[m],pdf_grids,strict=True):
            if f'{cell["key"]} major - 16 attacks' not in page:
                raise CandidateError(f"PDF_{m}_CELL {cell['key']}")
            if grid != [[x["roman"] for x in cell["bars"]],
                        [x["chord"] for x in cell["bars"]],
                        [x["function"] for x in cell["bars"]]]:
                raise CandidateError(f"PDF_{m}_GRID {cell['key']}")
            voicings="Voicings: "+" | ".join(" / ".join(x["rhythm_voicing_alternatives"]) for x in cell["bars"])
            if voicings not in page:
                raise CandidateError(f"PDF_{m}_VOICING {cell['key']}")
            checked[m]+=1
    for cell in modules["I"]:
        page=pages[cell["pdf_page"]-1]
        cell_index=("C","G","D","A","E","F").index(cell["key"])%3
        pdf_grids=grids(page,(" Chd"," Inv"," Frt"))
        if len(pdf_grids)!=3 or pdf_grids[cell_index] != [
            [x["chord"] for x in cell["bars"]],
            [x["inversion"] for x in cell["bars"]],
            ["-".join(map(str,x["frets"])) for x in cell["bars"]]]:
            raise CandidateError(f"PDF_I_GRID {cell['key']}")
        label=f'{cell["key"]} major - {"-".join(cell["bars"][0]["string_set"])} set - 16 attacks'
        voices="Voice frets: low "+"-".join(map(str,cell["voice_frets"]["low"]))+" | middle "+ \
            "-".join(map(str,cell["voice_frets"]["middle"]))+" | high "+"-".join(map(str,cell["voice_frets"]["top"]))
        if label not in page or voices not in page:
            raise CandidateError(f"PDF_I_CELL {cell['key']}")
        for bar in cell["bars"]:
            if "-".join(map(str,bar["frets"])) not in page:
                raise CandidateError(f"PDF_I_FRET {cell['key']}-{bar['bar']}")
        checked["I"]+=1
    page=pages[16]
    for item in modules["J"]["analysis"]:
        prompt="-".join(item["progression"])
        answer=f'{item["answer_key"]}: {"-".join(item["answer_roman"])}; {"-".join(item["answer_function"])}'
        if prompt not in page or answer not in page:
            raise CandidateError(f"PDF_J_ANALYSIS {item['number']}")
        checked["J"]+=1
    for item in modules["J"]["transposition"]:
        prompt=f'Move {"-".join(item["roman"])} from {item["from_key"]} to {item["to_key"]}'
        answer="-".join(item["answer_chords"])
        if prompt not in page or answer not in page:
            raise CandidateError(f"PDF_J_TRANSPOSE {item['number']}")
        checked["J"]+=1
    page=pages[17]
    capstone_grids=grids(page,(" Rom"," Chd","Func"))
    if len(capstone_grids)!=6:
        raise CandidateError("PDF_K_GRID_COUNT")
    for cell,grid in zip(modules["K"],capstone_grids,strict=True):
        first=cell["bars"][0]["bar"]
        if grid != [[x["roman"] for x in cell["bars"]],
                    [x["chord"] for x in cell["bars"]],
                    [x["function"] for x in cell["bars"]]] or \
                f'Bars {first}-{first+3}: {cell["key"]} major' not in page or \
                "Voicings: "+" | ".join(" / ".join(x["rhythm_voicing_alternatives"]) for x in cell["bars"]) not in page:
            raise CandidateError(f"PDF_K_CELL {cell['key']}")
        checked["K"]+=1
    if checked!={"A":42,"B":42,"C":6,"D":6,"E":6,"F":6,"G":6,"H":6,"I":6,"J":24,"K":6}:
        raise CandidateError(f"PDF_ITEM_COUNT {checked}")
    return {"pages":20,"module_pages":PDF_PAGES,"checked_items":checked,
        "discrepancies":[],"extracted_page_text":pages}


def build_candidate(txt_data: bytes | None=None,pdf_data: bytes | None=None) -> dict:
    for rel in (TXT_REL,PDF_REL):
        path=ROOT/rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise CandidateError(f"SOURCE_PATH_INVALID {rel}")
    txt=txt_data if txt_data is not None else (ROOT/TXT_REL).read_bytes()
    pdf=pdf_data if pdf_data is not None else (ROOT/PDF_REL).read_bytes()
    _pin(txt,TXT_BYTES,TXT_SHA,"L55-TXT")
    _pin(pdf,PDF_BYTES,PDF_SHA,"L55-PDF")
    parsed=_parse_txt(txt)
    pdf_check=_pdf(pdf,parsed)
    return {"schema":"fathom-level055-whole-detached-candidate-v1","wbs_id":"2.3.1.2.1","level":55,
        "source":{"txt_path":TXT_REL.as_posix(),"txt_bytes":TXT_BYTES,"txt_sha256":TXT_SHA,
                  "pdf_path":PDF_REL.as_posix(),"pdf_bytes":PDF_BYTES,"pdf_sha256":PDF_SHA,"pdf_pages":20},
        "modules":parsed["modules"],"module_sounded_attacks":ATTACKS,
        "complete_sounded_workout_attacks":936,"silent_spelling_formation_prompts":42,
        "written_analysis_transposition_prompts":24,"instructions":parsed["instructions"],
        "txt_document_text":txt.decode("utf-8"),"pdf_reconciliation":pdf_check,
        "canonical_item_id":None,"canonical_variant_id":None,"fixed_bpm":None,
        "note_per_click":None,"onset_q":None,"duration_q":None,"runtime_eligible":False,
        "runtime_admitted":False,"imported":False,"admitted":False,"curriculum_signoff":False,
        "performed_result":None}


def write_candidate(path: Path) -> dict:
    build=ROOT/BUILD_REL
    if (not build.resolve().is_relative_to(ROOT.resolve()) or build.is_symlink() or path.is_symlink()
            or path.parent.is_symlink() or path.parent.resolve()!=build.resolve() or path.suffix!=".json"):
        raise CandidateError("OUTPUT_OUTSIDE_LANE_BUILD")
    if path.exists():
        raise CandidateError("OUTPUT_EXISTS")
    candidate=build_candidate()
    build.mkdir(parents=True,exist_ok=True)
    encoded=(json.dumps(candidate,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode()
    with path.open("xb") as handle: handle.write(encoded)
    return {"path":str(path),"bytes":len(encoded),"sha256":sha(encoded),
            "modules":11,"sounded_attacks":936,"silent_prompts":42,"written_prompts":24}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    print(json.dumps(write_candidate(args.output),sort_keys=True))


if __name__=="__main__": main()
