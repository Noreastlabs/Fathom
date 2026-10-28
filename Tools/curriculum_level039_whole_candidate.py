#!/usr/bin/env python3
"""Build pinned, detached Section V Level 39 F# minor source evidence."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('Build/parallel-11/2.3.1.1.1-level039-whole-r01')
TXT = ('Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_39_F_Sharp_Minor_Pentatonic_Re_Centering_Workbook.txt','24dfc7b858a2211ff28c47861967e5c10831002c95ea345363ae8270e17ccccd',25219)
PDF = ('Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_39_F_Sharp_Minor_Pentatonic_Re_Centering_Workbook.pdf','4f263085b49918b80702669c1a11949ecf3bb04708bf38019c2f3daa6c05b63b',33495)
PRINTED=('e','B','G','D','A','E')
OPEN={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
ROLES={'A':('1','b3',9),'B':('2','4',11),'C#':('3','5',1),'E':('5','b7',4),'F#':('6','1',6)}
F_ROOTS=[('E',14),('A',9),('D',4),('D',16),('G',11),('B',7),('e',14)]


class SourceError(ValueError):
    pass


def require(ok:bool,why:str)->None:
    if not ok: raise SourceError(why)


def read_pinned(root:Path,spec:tuple[str,str,int])->bytes:
    path,digest,size=spec; target=root/path
    try: resolved=target.resolve(strict=True)
    except OSError as exc: raise SourceError(f'missing pinned input: {path}') from exc
    require(not target.is_symlink() and resolved.is_relative_to(root) and resolved.is_file(),f'unsafe input: {path}')
    raw=target.read_bytes()
    require(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,f'pinned input drift: {path}')
    return raw


def grid(row:str,label:str,bars:list[int])->list[str]:
    require(row.startswith(label+'|') and row.endswith('|'),f'{label} row boundary')
    parts=row.split('|')[1:-1]
    require([len(p) for p in parts]==[4*n for n in bars],f'{label} bar widths')
    return [part[i:i+4].strip('-') for part in parts for i in range(0,len(part),4)]


def check_rows(rows:list[str],bars:list[int],accent:bool=False)->dict[str,Any]:
    labels=['Nte','AMj','F#m']+(['A >','F#>'] if accent else [])+['Fng']+[f'  {s}' for s in PRINTED]
    require(len(rows)==len(labels),'printed row count')
    cols={label:grid(row,label,bars) for label,row in zip(labels,rows)}
    notes=cols['Nte']; require(all(n in ROLES for n in notes),'note outside shared pitch pool')
    require(cols['AMj']==[ROLES[n][0] for n in notes],'A-major degree conflict')
    require(cols['F#m']==[ROLES[n][1] for n in notes],'F#-minor degree conflict')
    require(all(f in ('1','2','3','4') for f in cols['Fng']),'finger row conflict')
    events=[]
    for j,note in enumerate(notes):
        active=[(s,cols[f'  {s}'][j]) for s in PRINTED if cols[f'  {s}'][j]]
        require(len(active)==1,f'TAB column {j+1} active string count')
        string,fret=active[0]
        require(fret.isdigit() and (OPEN[string]+int(fret))%12==ROLES[note][2],f'TAB pitch column {j+1}')
        events.append({'ordinal':j+1,'string':string,'fret':int(fret),'note':note,'A_major_degree':cols['AMj'][j],'F_sharp_minor_degree':cols['F#m'][j],'finger':int(cols['Fng'][j])})
    result={'events':events,'bars':bars,'raw_rows':rows}
    if accent:
        a=[j+1 for j,x in enumerate(cols['A >']) if x=='>']
        f=[j+1 for j,x in enumerate(cols['F#>']) if x=='>']
        require(all(x in ('','>') for x in cols['A >']+cols['F#>']),'accent glyph conflict')
        require(a==[2,7,12] and f==[1,6,11], 'accent location conflict')
        require(all(notes[j-1]=='A' for j in a) and all(notes[j-1]=='F#' for j in f),'accent pitch conflict')
        result['A_accent_ordinals']=a;result['F_sharp_accent_ordinals']=f
    return result


def pdf_block(page:list[str],heading:str,stop:str|None=None)->tuple[list[str],int,int]:
    matches=[i for i,x in enumerate(page) if x.strip()==heading]
    require(len(matches)==1,f'PDF heading {heading}')
    start=matches[0]
    end=next((i for i in range(start+1,len(page)) if stop and page[i].strip()==stop),len(page))
    return page[start:end],start+1,end


def pdf_has(block:list[str],rows:list[str],why:str)->None:
    previous=-1
    for row in rows:
        matches=[i for i,value in enumerate(block) if value==row]
        require(len(matches)==1 and matches[0]>previous,f'{why} PDF row disagreement/order: {row[:12]}')
        previous=matches[0]


def source_ref(start:int,end:int)->str: return f'L39-TXT-L{start}-{end}'


def parse_sources(lines:list[str],pages:list[list[str]])->dict[str,Any]:
    require(len(lines)==520 and [len(p) for p in pages]==[55,104,71,31,44,44,44,37,74,30,82,39],'source line/page coverage drift')
    require(lines[:2]==['SCALE EXERCISES - SECTION V, LEVEL 39','F# MINOR PENTATONIC RELATIVE-MINOR RE-CENTERING - SAME FIVE NOTES, NEW TONIC'],'TXT title drift')
    require(all(page[-1]==f'Page {n} of 12' for n,page in enumerate(pages,1)),'PDF page identity drift')
    require(lines[7:9]==['A major pentatonic:  A B C# E F#   = 1 2 3 5 6','F# minor pentatonic: F# A B C# E   = 1 b3 4 5 b7'],'pitch pool drift')
    for k,(name,(major,minor,_)) in enumerate(ROLES.items()):
        require(lines[10+k].split()==[name,'A','major',major,'|','F#','minor',minor],'TXT role map')
        require(pages[1][8+5*k:13+5*k][0:1]==[name] and pages[1][9+5*k]==major and pages[1][11+5*k]==minor,'PDF role map')
    require(lines[17]=='P1-P5 remain the established Level 34 ascending-neck labels. Do not renumber the boxes. The tonal center changes; the fret map and position identities do not.','position-label rule')
    require(lines[20]=='Low E 14 | A 9 | D 4 and 16 | G 11 | B 7 | high e 14','TXT F# root atlas')
    for string,fret in F_ROOTS: require((OPEN[string]+fret)%12==ROLES['F#'][2],'root atlas pitch')
    require(pages[1][63:84]==['String','A roots from Level 34','F# roots for Level 39','Low E','5, 17','14','A','12','9','D','7','4, 16','G','14','11','B','10','7','High e','5, 17','14'],'PDF root atlas')
    differences=[]
    # A: five invariant eight-note phrases under two drone contexts.
    a=[]
    for n in range(1,6):
        start=29+12*(n-1); header=lines[start]
        require(header==f'P{n} DRONE-COMPARISON PHRASE',f'Module A position {n}')
        rows=lines[start+1:start+11];parsed=check_rows(rows,[8])
        require([e['note'] for e in parsed['events']]==['B','C#','E','F#','A','F#','E','C#'],f'Module A contour {n}')
        block,_,_=pdf_block(pages[2],f'P{n} - unchanged pitch phrase',f'P{n+1} - unchanged pitch phrase' if n<5 else None)
        pdf_has(block,rows[0:3]+rows[4:],f'Module A P{n}')
        require(rows[3] not in block,f'Module A P{n} PDF Fng unexpectedly present')
        differences.append({'module':'A','item':f'P{n}','kind':'TXT_Fng_row_not_printed_in_PDF','txt_ref':source_ref(start+5,start+5),'pdf_page':3})
        a.append({'position':n,**parsed,'drone_contexts':['A','F#'],'written_tones_per_context':8,'sounding_tones':16,'txt_ref':source_ref(start+1,start+11),'pdf_page':3})
    require(lines[88]=='Module count: 5 phrases x 8 notes x 2 drones = 80 sounding tones.' and pages[2][2]=='5 PHRASES x 8 NOTES x 2 DRONES = 80 TONES','Module A count')
    # B: unchanged vertical cells with dual-degree labels.
    b=[]
    for n in range(1,6):
        start=95+12*(n-1); header=lines[start]
        require(header.startswith(f'P{n} - ') and 'FRETS' in header,f'Module B position {n}')
        rows=lines[start+1:start+11];parsed=check_rows(rows,[12,12]);notes=[e['note'] for e in parsed['events']]
        require(notes[11]==notes[12],'Module B repeated high endpoint')
        page_no=4 if n<3 else 5
        page=pages[page_no-1]
        heading=next((x for x in page if x.startswith(f'P{n} - ')),None)
        require(heading is not None,f'Module B PDF heading {n}')
        next_heading=next((x for x in page if x.startswith(f'P{n+1} - ')),None) if n<5 else None
        block,_,_=pdf_block(page,heading,next_heading)
        pdf_has(block,rows,f'Module B P{n}')
        b.append({'position':n,'header':header,**parsed,'sounding_tones':24,'txt_ref':source_ref(start+1,start+11),'pdf_page':page_no})
    require(lines[154]=='Module count: 5 cells x 24 notes = 120 sounding tones.','Module B count')
    # C: five 12-note cells and a full 22-note P5 root cell.
    c=[]
    for n in range(1,7):
        start=161+12*(n-1) if n<=5 else 221
        header=lines[start];expected=f'P{n} ONE-OCTAVE F# MINOR PENTATONIC CELL' if n<=5 else 'P5 FULL TWO-OCTAVE TONIC-FRAME CELL'
        require(header==expected,f'Module C cell {n}')
        bars=[6,6] if n<=5 else [11,11]
        rows=lines[start+1:start+11];parsed=check_rows(rows,bars);notes=[e['note'] for e in parsed['events']]
        require(notes[0]==notes[-1]=='F#' and notes[bars[0]-1]==notes[bars[0]]=='F#',f'Module C root turn {n}')
        require(notes[:6]==['F#','A','B','C#','E','F#'],f'Module C ascent {n}')
        page_no=6 if n<=3 else 7;page=pages[page_no-1]
        heading=f'P{n} - one-octave F# minor pentatonic cell' if n<=5 else 'P5 - full two-octave tonic-frame cell'
        next_heading=f'P{n+1} - one-octave F# minor pentatonic cell' if n<5 else 'P5 - full two-octave tonic-frame cell' if n==5 else None
        if next_heading not in page:next_heading=None
        block,_,_=pdf_block(page,heading,next_heading)
        pdf_has(block,rows,f'Module C cell {n}')
        c.append({'cell':n,'position':min(n,5),'kind':'one_octave' if n<=5 else 'two_octave','header':header,**parsed,'sounding_tones':sum(bars),'txt_ref':source_ref(start+1,start+11),'pdf_page':page_no})
    require(lines[232]=='Module count: 5 x 12-note cells + 22-note P5 cell = 82 sounding tones.','Module C count')
    # D: one line, four unchanged-note passes, two marked accent locations.
    drows=lines[237:249]
    d=check_rows(drows,[12],accent=True)
    pdf_has(pages[7],drows,'Module D')
    require(lines[249].startswith('Pass 1: A drone; accent A. Pass 2: F# drone; accent F#.') and lines[250]=='Module count: 4 passes x 12 notes = 48 sounding tones.','Module D pass/count')
    d.update({'pass_contexts':['A drone; accent A','F# drone; accent F#','A drone; accents removed','F# drone; accents removed'],'sounding_tones':48,'txt_ref':source_ref(238,251),'pdf_page':8})
    # E: five paired six-note cadences with identical four-note seed.
    e=[]
    for n in range(1,6):
        start=257+23*(n-1)
        pairs=[]
        for j,kind in enumerate(('A-MAJOR','F#-MINOR')):
            head=lines[start+11*j]
            require(head==f'P{n} {kind} CADENCE',f'Module E P{n} {kind}')
            rows=lines[start+11*j+1:start+11*j+11]
            parsed=check_rows(rows,[6]);notes=[x['note'] for x in parsed['events']]
            require(notes[:4]==['B','C#','E','C#'] and notes[-2:]==(['B','A'] if j==0 else ['A','F#']),f'Module E ending P{n} {kind}')
            block,_,_=pdf_block(pages[8],f'P{n} - common seed, alternate destination',f'P{n+1} - common seed, alternate destination' if n<5 else None)
            caption='A CADENCE' if j==0 else 'F# CADENCE'
            index=block.index(caption);end=next((z for z in range(index+1,len(block)) if block[z] in ('A CADENCE','F# CADENCE') or re.match(r'P\d - common seed',block[z])),len(block))
            pdf_part=block[index:end]
            pdf_has(pdf_part,[rows[0],rows[2]]+[r for r in rows[4:] if re.search(r'\d',r)],f'Module E P{n} {kind}')
            require(rows[1] not in pdf_part and rows[3] not in pdf_part,f'Module E P{n} PDF extra degree/finger')
            blank=[r[:3].strip() for r in rows[4:] if not re.search(r'\d',r)]
            differences.append({'module':'E','item':f'P{n} {kind}','kind':'TXT_AMj_Fng_and_blank_TAB_rows_not_printed_in_PDF','blank_tab_strings':blank,'txt_ref':source_ref(start+11*j+2,start+11*j+11),'pdf_page':9})
            pairs.append({'center':'A' if j==0 else 'F#',**parsed,'sounding_tones':6,'txt_ref':source_ref(start+11*j+1,start+11*j+11),'pdf_page':9})
        require([x['note'] for x in pairs[0]['events'][:4]]==[x['note'] for x in pairs[1]['events'][:4]],f'Module E common seed {n}')
        e.append({'position':n,'cadences':pairs,'sounding_tones':12})
    require(lines[371]=='Module count: 5 positions x 2 cadences x 6 notes = 60 sounding tones.','Module E count')
    # F: eight bars with printed center/position plan in PDF.
    frows=lines[377:387];f=check_rows(frows,[4]*8)
    require(frows==pages[9][7:17],'Module F TXT/PDF row disagreement')
    require(pages[9][5].startswith('Ctr|') and pages[9][6].startswith('Pos|'),'Module F PDF context/position rows')
    ctr_cells=grid(pages[9][5],'Ctr',[4]*8);pos_cells=grid(pages[9][6],'Pos',[4]*8)
    require(all(ctr_cells[i]==pos_cells[i]=='' for i in range(32) if i%4),'Module F context/position filler')
    ctr=ctr_cells[::4];pos=pos_cells[::4]
    require(ctr==['A','A','F#','F#','A','A','F#','F#'] and pos==['P1','P1','P2','P2','P3','P3','P5','P5'],'Module F center/position plan')
    f.update({'center_by_bar':ctr,'position_by_bar':pos,'sounding_tones':32,'txt_ref':source_ref(378,387),'pdf_page':10})
    differences.append({'module':'F','kind':'PDF_Ctr_and_Pos_rows_not_printed_in_TXT','pdf_ref':'L39-PDF-p10-L6-7','txt_ref':source_ref(377,378)})
    require(lines[388]=='Module count: 8 bars x 4 tones = 32 sounding tones.','Module F count')
    # G: eight ear cards and a printed answer key, without auditory inference.
    g=[]
    for n,letter in enumerate('ABCDEFGH'):
        start=395+12*n
        require(lines[start]==f'CARD {letter} - CENTER? __________',f'Module G card {letter}')
        rows=lines[start+1:start+11];parsed=check_rows(rows,[5]);page=pages[10]
        block,_,_=pdf_block(page,f'Card {letter} - center? __________',f'Card {chr(ord(letter)+1)} - center? __________' if letter!='H' else None)
        pdf_has(block,[rows[0]]+rows[4:],f'Module G card {letter}')
        require(all(r not in block for r in rows[1:4]),f'Module G card {letter} extra PDF annotations')
        differences.append({'module':'G','item':letter,'kind':'TXT_AMj_F_sharp_minor_Fng_rows_not_printed_in_PDF','txt_ref':source_ref(start+3,start+5),'pdf_page':11})
        g.append({'card':letter,**parsed,'sounding_tones':5,'txt_ref':source_ref(start+1,start+11),'pdf_page':11})
    answer=['A-centered','F#-centered']*4
    expected='ANSWER KEY: '+' | '.join(f'{letter} {center}' for letter,center in zip('ABCDEFGH',answer))
    require(lines[490]==expected,'TXT ear answer key')
    require(pages[10][78]=='   '.join(f'{letter}: {center}' for letter,center in zip('ABCDEFGH',answer)),'PDF ear answer key')
    for card,center in zip(g,answer):card['printed_answer']=center
    require(lines[491]=='Module count: 8 cards x 5 notes = 40 sounding tones.','Module G count')
    counts={'A':sum(x['sounding_tones'] for x in a),'B':sum(x['sounding_tones'] for x in b),'C':sum(x['sounding_tones'] for x in c),'D':d['sounding_tones'],'E':sum(x['sounding_tones'] for x in e),'F':f['sounding_tones'],'G':sum(x['sounding_tones'] for x in g)}
    require(counts=={'A':80,'B':120,'C':82,'D':48,'E':60,'F':32,'G':40} and sum(counts.values())==462,'whole-workout counts')
    require(lines[512]=='MASTERY GATE BEFORE LEVEL 40' and 'score at least 7 of 8 on the ear test twice' in lines[513] and lines[516]=='462 written sounding tones.','mastery/total guidance')
    require(pages[7][17].startswith('Do not lengthen the accented note.'),'PDF accent guidance')
    require(pages[8][3].startswith('A-major cadence:') and 'partner to call the destination' in pages[8][3],'PDF cadence guidance')
    require(pages[9][17].startswith('Use quarter notes first. Later use swung eighth-note pickups'),'PDF pivot guidance')
    require(pages[10][3].startswith('Cover the answer key. Play each card twice: first exactly as written, then repeat its final note and hold it for two beats.'),'PDF ear test guidance')
    require('462 written sounding tones:' in pages[0][51],'PDF written total guidance')
    guidance_variants=[
        {'module':'D','kind':'PDF_attack_weight_clarification','txt_ref':source_ref(250,250),'txt_text':lines[249],'pdf_ref':'L39-PDF-p8-L18','pdf_text':pages[7][17]},
        {'module':'E','kind':'PDF_partner_call_task','txt_ref':source_ref(256,256),'txt_text':lines[255],'pdf_ref':'L39-PDF-p9-L4','pdf_text':pages[8][3]},
        {'module':'F','kind':'PDF_quarter_and_swing_practice_guidance','txt_ref':source_ref(388,388),'txt_text':lines[387],'pdf_ref':'L39-PDF-p10-L18','pdf_text':pages[9][17]},
        {'module':'G','kind':'PDF_second_pass_final_note_two_beat_hold','txt_ref':source_ref(394,394),'txt_text':lines[393],'pdf_ref':'L39-PDF-p11-L4-5','pdf_text':pages[10][3:5]},
    ]
    return {'modules':{'A_drone_comparison':a,'B_dual_degree_boxes':b,'C_root_to_root_cells':c,'D_accent_relocation':d,'E_paired_cadences':e,'F_tonic_pivot':f,'G_ear_cards':g},'counts':{**counts,'total_written_sounding_tones':462},'source_presentation_differences':differences,'source_guidance_variants':guidance_variants,'printed_ear_answer_key':lines[490],'mastery_gate_raw':lines[512:514],'source_guidance':{'txt_full_lines':lines,'pdf_full_extracted_pages':pages}}


def build_candidate(root:Path=ROOT)->dict[str,Any]:
    root=root.resolve(strict=True);txt=read_pinned(root,TXT);pdf=read_pinned(root,PDF)
    try:
        lines=txt.decode('utf-8').splitlines()
        pages=[(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(pdf),strict=True).pages]
    except Exception as exc:raise SourceError('source decode failure') from exc
    parsed=parse_sources(lines,pages)
    return {'schema':'fathom.level039.detached-source-candidate.1','wbs':'2.3.1.1.1','status':'non_admitted','admitted':False,'canonical_id':None,'exercise_id':None,'onset_q':None,'duration_q':None,'fixed_bpm':None,'executable_audio_events':None,'source':{'txt':{'path':TXT[0],'bytes':TXT[2],'sha256':TXT[1],'role':'original authored TXT'},'pdf':{'path':PDF[0],'bytes':PDF[2],'sha256':PDF[1],'role':'original paginated PDF'}},'shared_pitch_pool':['A','B','C#','E','F#'],'pitch_roles':{n:{'A_major_degree':v[0],'F_sharp_minor_degree':v[1]} for n,v in ROLES.items()},'F_sharp_root_atlas':[{'string':s,'fret':f} for s,f in F_ROOTS],**parsed}


def encode(value:dict[str,Any])->bytes:
    return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')


def output_path(root:Path,value:str)->Path:
    root=root.resolve(strict=True);relative=Path(value)
    require(not relative.is_absolute() and '..' not in relative.parts and relative.parts[:len(BUILD.parts)]==BUILD.parts and relative.suffix=='.json','output outside reserved Build directory')
    current=root
    for part in relative.parts:
        current=current/part;require(not current.is_symlink(),'symlink output path')
    require(not current.exists(),'refusing overwrite')
    return current


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();path=output_path(ROOT,args.output);candidate=build_candidate(ROOT)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encode(candidate))
    print(f'{path.relative_to(ROOT)} bytes={path.stat().st_size} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}')
    return 0


if __name__=='__main__':raise SystemExit(main())
