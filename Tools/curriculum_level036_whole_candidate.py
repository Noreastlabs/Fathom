#!/usr/bin/env python3
"""Build pinned, detached Level 36 expressive-articulation source evidence."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('Build/parallel-11/2.3.1.1.1-level036-whole-r01')
TXT = ('Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_36_Major_Pentatonic_Expressive_Articulation_Legato_Slides_Bends_Releases_and_Vibrato_Fixed_Key_A.txt', '4aee029db1f594b01963374e1269dba273fd82ae8e24d0e24df551cb442ef828', 23355)
PDF = ('Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_36_Major_Pentatonic_Expressive_Articulation_Legato_Slides_Bends_Releases_and_Vibrato_Fixed_Key_A.pdf', 'ecdb6d4b249ac09116647f9b278413727bab6cf4b2557e094d9ee34741c11a43', 41361)
STRINGS = ('E', 'A', 'D', 'G', 'B', 'e')
PRINTED = ('e', 'B', 'G', 'D', 'A', 'E')
OPEN = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}
PC = {'A': 9, 'B': 11, 'C#': 1, 'E': 4, 'F#': 6}
DEG = {'A': 1, 'B': 2, 'C#': 3, 'E': 5, 'F#': 6}


class SourceError(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceError(reason)


def read_pinned(root: Path, spec: tuple[str, str, int]) -> bytes:
    path, digest, size = spec
    target = root / path
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        raise SourceError(f'missing pinned input: {path}') from exc
    require(not target.is_symlink() and resolved.is_relative_to(root) and resolved.is_file(), f'unsafe pinned input: {path}')
    raw = target.read_bytes()
    require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, f'pinned input drift: {path}')
    return raw


def pitch(string: str, fret: int) -> int:
    return (OPEN[string] + fret) % 12


def check_note(string: str, fret: int, note: str) -> None:
    require(note in PC and pitch(string, fret) == PC[note], f'pitch mismatch {string}{fret} {note}')


def cells(line: str, label: str) -> list[str]:
    require(line.startswith(label + '|') and line.endswith('|'), f'{label} row boundary')
    result = [x.strip() for x in line.split('|')[1:-1]]
    require(len(result) == 12, f'{label} 12-column loss')
    return result


def parse_pair(token: str, op: str, names: bool = False) -> tuple[str, str]:
    pat = r'([A-G]#?)' if names else r'(\d+)'
    m = re.fullmatch(pat + op + pat, token)
    require(m is not None, f'pair {token!r}')
    return m.group(1), m.group(2)


def parse_position(lines: list[str], pages: list[list[str]], n: int) -> dict[str, Any]:
    start = 40 + 20 * (n - 1)  # zero based header
    block = lines[start:start + 19]
    require(len(block) == 19 and block[0].startswith(f'POSITION {n} - ') and block[7] == '24-TONE LEGATO CELL', f'position {n} boundary')
    require(lines[start + 19] == '', f'position {n} terminal blank')
    page = pages[n + 1]
    require(page[0] == f'Level 36 - Module A: Position {n} Legato Cell', f'position {n} PDF page')
    maps = []
    for k, string in enumerate(STRINGS):
        row = block[k + 1]
        m = re.fullmatch(r'\s*(Low E|High e|[ADGB])\s+frets (\d+)-(\d+)\s+notes ([A-G]#?)-([A-G]#?)\s+degrees ([12356])-([12356])\s+fingers ([1-4])-([1-4])', row)
        require(m is not None, f'position {n} string map {k}')
        label, lo, hi, nlo, nhi, dlo, dhi, flo, fhi = m.groups()
        require(label == ('Low E' if string == 'E' else 'High e' if string == 'e' else string), f'position {n} string order')
        lo, hi = int(lo), int(hi)
        require(hi > lo and [DEG[nlo], DEG[nhi]] == [int(dlo), int(dhi)], f'position {n} degree map')
        check_note(string, lo, nlo); check_note(string, hi, nhi)
        pdf_row = page[9 + 5*k:14 + 5*k]
        require(pdf_row == [label, f'{lo}-{hi}', f'{nlo}-{nhi}', f'{dlo}-{dhi}', f'{flo}-{fhi}'], f'position {n} PDF map')
        maps.append({'string': string, 'frets': [lo, hi], 'notes': [nlo, nhi], 'degrees': [int(dlo), int(dhi)], 'fingers': [int(flo), int(fhi)], 'txt_ref': f'L36-TXT-L{start+k+2}', 'pdf_ref': f'L36-PDF-p{n+2}-L{10+5*k}-{14+5*k}'})
    rows = block[8:18]
    require(rows == page[46:56], f'position {n} TXT/PDF cell disagreement')
    nte, deg, fng, art = [cells(rows[i], ('Nte','Deg','Fng','Art')[i]) for i in range(4)]
    tabs = {s: cells(rows[4+j], f'{s}  ') for j,s in enumerate(PRINTED)}
    groups = []
    for j in range(12):
        op = 'h' if j < 6 else 'p'
        active = [(s,tabs[s][j]) for s in PRINTED if tabs[s][j] != '---------']
        require(len(active) == 1 and art[j] == op, f'position {n} group {j+1} active/art')
        string, tab = active[0]
        require(string == STRINGS[j] if j < 6 else string == STRINGS[11-j], f'position {n} group string order')
        note_pair = parse_pair(nte[j], op, True)
        degree_pair = parse_pair(deg[j], op)
        finger_pair = parse_pair(fng[j], op)
        fret_pair = parse_pair(tab, op)
        spec = maps[STRINGS.index(string)]
        lohi = [0,1] if op == 'h' else [1,0]
        require(list(note_pair) == [spec['notes'][i] for i in lohi] and list(map(int,degree_pair)) == [spec['degrees'][i] for i in lohi] and list(map(int,finger_pair)) == [spec['fingers'][i] for i in lohi] and list(map(int,fret_pair)) == [spec['frets'][i] for i in lohi], f'position {n} group {j+1} map conflict')
        groups.append({'string': string, 'notes': list(note_pair), 'degrees': list(map(int,degree_pair)), 'fingers': list(map(int,finger_pair)), 'frets': list(map(int,fret_pair)), 'articulation': op, 'pick_attacks': 1, 'sounding_tones': 2})
    return {'position': n, 'string_maps': maps, 'groups': groups, 'sounding_tones': 24, 'pick_attacks': 12, 'txt_ref': f'L36-TXT-L{start+1}-{start+19}', 'pdf_ref': f'L36-PDF-p{n+2}', 'raw_txt': block, 'raw_pdf_cell': page[46:56]}


def parse_seams(lines: list[str], pages: list[list[str]]) -> list[dict[str, Any]]:
    result = []
    for seam in range(1,5):
        start = 147 + 9*(seam-1)
        block = lines[start:start+8]
        require(block[0] == f'SEAM P{seam} <-> P{seam+1}' and block[7].startswith('One phrase = 5 sounding tones / 1 pick attack.'), f'seam {seam} boundary')
        page_no = 8 if seam < 3 else 9
        base = 11 if seam % 2 else 47
        page = pages[page_no-1]
        require(page[base-6].startswith(f'Seam P{seam} <-> P{seam+1}'), f'seam {seam} PDF heading')
        phrases = []
        for k,string in enumerate(STRINGS):
            row = block[k+1]
            m = re.fullmatch(r'\s*(Low E|High e|[ADGB])\s+([EADGBe]\|\d+h\d+/\d+\\\d+p\d+\|)\s+Deg ([12356](?:-[12356]){4})\s+Notes ([A-G]#?(?:-[A-G]#?){4})\s+Work finger ([1-4])', row)
            require(m is not None, f'seam {seam} phrase {k+1}')
            label, phrase, degrees, notes, finger = m.groups()
            require(label == ('Low E' if string=='E' else 'High e' if string=='e' else string) and phrase[0] == string, f'seam {seam} string order')
            frets = list(map(int, re.fullmatch(r'[EADGBe]\|(\d+)h(\d+)/(\d+)\\(\d+)p(\d+)\|', phrase).groups()))
            require(frets[0] < frets[1] < frets[2] and frets[1] == frets[3] and frets[0] == frets[4], f'seam {seam} phrase contour')
            note_list, deg_list = notes.split('-'), list(map(int,degrees.split('-')))
            for fret,note,degree in zip(frets,note_list,deg_list):
                check_note(string,fret,note)
                require(DEG[note] == degree, f'seam {seam} degree')
            pdf_row = page[base+5*k:base+5*k+5]
            require(pdf_row == [label, phrase, degrees, notes, finger], f'seam {seam} PDF row {k+1}')
            phrases.append({'string':string,'tab':phrase,'frets':frets,'notes':note_list,'degrees':deg_list,'work_finger':int(finger),'articulations':['pick','hammer_on','slide_up','slide_down','pull_off'],'sounding_tones':5,'pick_attacks':1,'txt_ref':f'L36-TXT-L{start+k+2}','pdf_ref':f'L36-PDF-p{page_no}-L{base+5*k+1}-{base+5*k+5}'})
        result.append({'seam':seam,'phrases':phrases,'sounding_tones':30,'pick_attacks':6,'txt_ref':f'L36-TXT-L{start+1}-{start+8}','pdf_ref':f'L36-PDF-p{page_no}'})
    return result


def bend_row(row: str, mode: str) -> tuple[str,int,int,str,int,str,int,str]:
    m = re.fullmatch(r'\s*(G|B|High e)\s+([GBe]\|[^|]+\|)\s+([A-G]#?)\(([12356])\) -> ([A-G]#?)\(([12356])\)',row)
    require(m is not None, f'{mode} row shape')
    label, tab, source_note, source_deg, target_note, target_deg = m.groups()
    string = 'e' if label == 'High e' else label
    require(tab[0] == string, f'{mode} string mismatch')
    if mode == 'bend':
        pattern = r'[GBe]\|--(\d+)----(\d+)b\((\d+)\)----(\d+)b\((\d+)\)r(\d+)----(\d+)~~~~--\|'
    else:
        pattern = r'[GBe]\|--(\d+)----(\d+)pb\((\d+)\)r(\d+)----(\d+)b\((\d+)\)~~~~--\|'
    p = re.fullmatch(pattern,tab)
    require(p is not None, f'{mode} TAB articulation')
    vals = list(map(int,p.groups()))
    if mode == 'bend':
        target, source, t2, s3, t3, r3, t4 = vals
        require(target == t2 == t3 == t4 and source == s3 == r3, f'{mode} tab target/release')
    else:
        target, source, t2, r2, s3, t3 = vals
        require(target == t2 == t3 and source == r2 == s3, f'{mode} tab target/release')
    require(target == source+2 and DEG[source_note] == int(source_deg) and DEG[target_note] == int(target_deg), f'{mode} whole-step/degree')
    check_note(string,source,source_note); check_note(string,target,target_note)
    return string,source,target,source_note,int(source_deg),target_note,int(target_deg),tab


def parse_bends(lines: list[str], pages: list[list[str]], mode: str) -> list[dict[str,Any]]:
    first,count,pdf_page,pdf_indices = (190,9,11,[5,7,9,13,15,17,21,23,25]) if mode=='bend' else (206,6,12,[6,8,10,12,14,16])
    result=[]
    for j in range(count):
        row=lines[first+j]
        string,source,target,source_note,source_degree,target_note,target_degree,tab=bend_row(row,mode)
        pdf=pages[pdf_page-1]
        require(pdf[pdf_indices[j]] == tab and pdf[pdf_indices[j]+1] == f'{source_note}({source_degree}) -> {target_note}({target_degree})', f'{mode} PDF site {j+1}')
        result.append({'site':j+1,'string':string,'source_fret':source,'target_fret':target,'source_note':source_note,'target_note':target_note,'source_degree':source_degree,'target_degree':target_degree,'tab':tab,'pick_attacks':4 if mode=='bend' else 3,'articulation_sequence':['fretted_target','bend_to_target','bend_release','fretted_target_vibrato'] if mode=='bend' else ['fretted_target','silent_prebend_attack_release','fresh_bend_target_vibrato'],'txt_ref':f'L36-TXT-L{first+j+1}','pdf_ref':f'L36-PDF-p{pdf_page}-L{pdf_indices[j]+1}-{pdf_indices[j]+2}'})
    return result


def parse_roots(lines: list[str], pages: list[list[str]]) -> list[dict[str,Any]]:
    require(lines[213]=='A-ROOT VIBRATO MAP', 'root map heading')
    roots=[]
    for j,row in enumerate(lines[214:222]):
        m=re.fullmatch(r'\s*(Low E|High e|[ADGB])\s+fret\s+(\d+)\s+A degree 1  hold four beats with narrow wrist vibrato',row)
        require(m is not None, f'root hold {j+1}')
        label,fret=m.groups(); string='E' if label=='Low E' else 'e' if label=='High e' else label
        check_note(string,int(fret),'A')
        roots.append({'string':string,'fret':int(fret),'note':'A','degree':1,'pick_attacks':1,'raw_guidance':row,'txt_ref':f'L36-TXT-L{215+j}'})
    table=pages[11][22:34]
    require(table == ['Low E','5, 17','A','12','D','7','G','14','B','10','High e','5, 17'], 'PDF root map')
    expected=[('E',5),('D',7),('B',10),('A',12),('G',14),('E',17),('e',5),('e',17)]
    require([(x['string'],x['fret']) for x in roots]==expected, 'root hold order')
    return roots


def parse_cadences(lines: list[str], pages: list[list[str]]) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    result=[]; discrepancy=[]; pdf=pages[12]
    bases=[4,13,22,31,40]
    for n in range(1,6):
        first=228+10*(n-1)
        block=lines[first:first+9]
        m=re.fullmatch(rf'{n}\. POSITION {n} CADENCE - (.+) - frets (\d+)-(\d+) - ([34]) PICK ATTACKS',block[0])
        require(m is not None and lines[first+9]=='',f'cadence {n} boundary')
        _,lo,hi,attacks=m.groups(); lo=int(lo);hi=int(hi);attacks=int(attacks)
        base=bases[n-1]
        require(pdf[base].startswith(f'Position {n} cadence - ') and pdf[base+1]==f'frets {lo}-{hi} | {attacks} pick attacks',f'cadence {n} PDF header')
        tabs=block[1:7]
        require(tabs==pdf[base+2:base+8],f'cadence {n} PDF TAB mismatch')
        require([t[0] for t in tabs]==list(PRINTED),f'cadence {n} string order')
        require(block[7].startswith('Degrees: ') and block[7]==pdf[base+8] and block[8].startswith('Notes: '),f'cadence {n} summary')
        phrase_tokens=[]
        for row in tabs:
            tokens=re.findall(r'(?<![0-9A-Za-z(])\d+(?:h\d+|p\d+|/\d+|\\\d+|b\(\d+\)|r\d+|~+)*',row)
            phrase_tokens.extend(tokens)
            for token in tokens:
                for src,tgt in re.findall(r'(\d+)b\((\d+)\)',token):
                    require(int(tgt)==int(src)+2,f'cadence {n} bend whole step')
        require(len(phrase_tokens)==attacks,f'cadence {n} attack count')
        note_groups=[x.strip().split('-') for x in block[8].split(':',1)[1].split('|')]
        degree_groups=[x.strip() for x in block[7].split(':',1)[1].split('|')]
        require(len(note_groups)==len(degree_groups)==attacks,f'cadence {n} phrase group count')
        for ng,dg in zip(note_groups,degree_groups):
            degrees=list(map(int,re.findall(r'[12356]',dg)))
            require([DEG.get(x) for x in ng]==degrees,f'cadence {n} notes/degrees')
        require(note_groups[-1][-1]=='A',f'cadence {n} tonic ending')
        pdf_notes=pdf[base+9] if n==5 else None
        if n==5:
            require(pdf_notes==block[8].replace('Notes:   ','Notes: '), 'cadence 5 PDF notes')
        else:
            require(not any(x.startswith('Notes:') for x in pdf[base:base+9]),f'cadence {n} unexpected PDF notes')
            discrepancy.append({'position':n,'kind':'pdf_cadence_notes_summary_omitted','status':'pending_curriculum_review','txt_ref':f'L36-TXT-L{first+9}','txt_notes':block[8],'pdf_ref':f'L36-PDF-p13-L{base+1}-{base+9}','pdf_notes':None})
        result.append({'position':n,'frame_frets':[lo,hi],'pick_attacks':attacks,'tab_rows':tabs,'degrees_raw':block[7],'txt_notes_raw':block[8],'pdf_notes_raw':pdf_notes,'attack_tokens':phrase_tokens,'txt_ref':f'L36-TXT-L{first+1}-{first+9}','pdf_ref':f'L36-PDF-p13-L{base+1}-{base+(10 if n==5 else 9)}'})
    require([x['pick_attacks'] for x in result]==[4,4,4,3,4], 'cadence attack distribution')
    return result,discrepancy


def build_candidate(root: Path=ROOT) -> dict[str,Any]:
    root=root.resolve(strict=True)
    raw_txt=read_pinned(root,TXT); raw_pdf=read_pinned(root,PDF)
    try:
        lines=raw_txt.decode('utf-8').splitlines()
        pages=[(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw_pdf),strict=True).pages]
    except Exception as exc:
        raise SourceError('TXT/PDF decode failure') from exc
    require(len(lines)==324 and [len(p) for p in pages]==[67,113,65,65,65,65,65,78,78,92,28,51,51,62], 'source line/page coverage drift')
    require(lines[:3]==['SCALE EXERCISES - SECTION IV, LEVEL 36','A MAJOR PENTATONIC EXPRESSIVE ARTICULATION - LEGATO, SLIDES, BENDS, RELEASES, AND VIBRATO','FIXED KEY A - FIVE POSITIONS - FRETS 4-17'], 'TXT title drift')
    require(lines[17:19]==['Notes: A B C# E F#','Degrees: 1 2 3 5 6'], 'pentatonic formula')
    require(all(p[4 if i==1 else 3]==f'Page {i} of 14' for i,p in enumerate(pages,1)), 'PDF page identity')
    require(lines[20:23]==['ARTICULATION NOTATION','h = hammer-on; p = pull-off; / = ascending slide; \\ = descending slide; b(T) = bend to target fret T;','r = release; pb(T) = pre-bend silently to target pitch before the attack; ~ = vibrato.'], 'articulation notation drift')
    require(lines[24]=='COUNTS' and lines[30].startswith('Complete core workout: 165 pick attacks'), 'counts heading drift')
    module_a=[parse_position(lines,pages,n) for n in range(1,6)]
    module_b=parse_seams(lines,pages)
    module_c=parse_bends(lines,pages,'bend')
    atlas=pages[9][28:82]
    require(len(atlas)==54, 'PDF bend atlas coverage')
    for j,site in enumerate(module_c):
        expected=['High e' if site['string']=='e' else site['string'],str(site['source_fret']),str(site['target_fret']),site['source_note'],site['target_note'],f"{site['source_degree']}->{site['target_degree']}"]
        require(atlas[6*j:6*j+6]==expected, f'PDF bend atlas site {j+1}')
    module_d_prebend=parse_bends(lines,pages,'prebend')
    module_d_roots=parse_roots(lines,pages)
    module_e,discrepancies=parse_cadences(lines,pages)
    attacks=sum(x['pick_attacks'] for x in module_a+module_b+module_c+module_d_prebend+module_d_roots+module_e)
    require(attacks==165 and sum(x['sounding_tones'] for x in module_a+module_b)==240, 'aggregate count')
    require(len(module_c)+len(module_d_prebend)==15 and len(module_d_roots)==8 and len(module_e)==5, 'cell family count')
    source={'txt':{'path':TXT[0],'bytes':TXT[2],'sha256':TXT[1],'role':'original authored TXT'},'pdf':{'path':PDF[0],'bytes':PDF[2],'sha256':PDF[1],'role':'original paginated PDF'}}
    return {'schema':'fathom.level036.detached-source-candidate.1','wbs':'2.3.1.1.1','status':'non_admitted','admitted':False,'canonical_id':None,'exercise_id':None,'onset_q':None,'duration_q':None,'fixed_bpm':None,'source':source,'key':'A major pentatonic','notes':['A','B','C#','E','F#'],'degrees':[1,2,3,5,6],'modules':{'A_legato_positions':module_a,'B_seam_chains':module_b,'C_whole_step_bends':module_c,'D_prebend_cells':module_d_prebend,'D_A_root_vibrato_holds':module_d_roots,'E_cadences':module_e},'counts':{'A_sounding_tones':120,'A_pick_attacks':60,'B_sounding_tones':120,'B_pick_attacks':24,'C_pick_attacks':36,'D_prebend_pick_attacks':18,'D_vibrato_pick_attacks':8,'E_pick_attacks':19,'total_pick_attacks':attacks,'explicit_legato_slide_tones':240,'bend_prebend_cells':15,'A_root_vibrato_holds':8,'cadences':5},'source_discrepancies':discrepancies,'source_guidance':{'txt_lines_1_40':lines[:40],'txt_module_A_rules':[lines[58+20*k] for k in range(5)],'txt_lines_140_147':lines[139:147],'txt_lines_183_190':lines[182:190],'txt_lines_200_206':lines[199:206],'txt_lines_223_228':lines[222:228],'txt_lines_279_324':lines[278:],'pdf_pages_full_extracted':pages}}


def encode(candidate:dict[str,Any])->bytes:
    return (json.dumps(candidate,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')


def output_path(root:Path,value:str)->Path:
    root=root.resolve(strict=True)
    relative=Path(value)
    require(not relative.is_absolute() and '..' not in relative.parts and relative.parts[:len(BUILD.parts)]==BUILD.parts and relative.suffix=='.json','output outside reserved Build directory')
    path=root/relative
    current=root
    for part in relative.parts:
        current=current/part
        require(not current.is_symlink(),'symlink output path')
    require(not path.exists(),'refusing overwrite')
    return path


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='new JSON path below reserved Build directory')
    args=parser.parse_args()
    output=output_path(ROOT,args.output)
    candidate=build_candidate(ROOT)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(encode(candidate))
    print(f'{output.relative_to(ROOT)} bytes={output.stat().st_size} sha256={hashlib.sha256(output.read_bytes()).hexdigest()}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
