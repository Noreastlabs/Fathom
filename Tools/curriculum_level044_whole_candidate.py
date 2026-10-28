#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level44 source candidate."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('Build/parallel-11/2.3.1.1.1-level044-whole-r01')
TXT=('Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_44_A_Blues_Resolution_Vocabulary_Lick_Construction_and_Functional_Turnarounds_Fixed_Key_A.txt','fcbc0712e7e874c08a936a59f14bfe6fe4d57fa8c92ccf9f6e8badb76fcc8217',23879)
PDF=('Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_44_A_Blues_Resolution_Vocabulary_Lick_Construction_and_Functional_Turnarounds_Fixed_Key_A.pdf','f06b408d2cdedfc7d68ccb36bef7e18929d55eab60e0ee8dc172bbecf6098677',51574)
MAP=('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json','bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6',199753)
P43_TXT=('Notes/music/guitar project/TXT version/Scale_Exercises_Section_V_Level_43_A_Blues_Scale_Map_and_Blue_Note_Control_Fixed_Key_A_Final.txt','2757cc44d1b231e6e2203b12ba8da82a7d6784db7a11ca94719efc7f34d3804f',24994)
P43_PDF=('Notes/music/guitar project/PDF version/Scale_Exercises_Section_V_Level_43_A_Blues_Scale_Map_and_Blue_Note_Control_Fixed_Key_A_Final.pdf','6641317bad903771dba4a2e50779dd66ed0d34626ca63f356d3d59b955668f2a',43204)
PC={'A':9,'C':0,'D':2,'Eb':3,'E':4,'G':7,'C#':1,'F#':6,'F':5,'B':11,'G#':8}
DEG={'A':'1','C':'b3','D':'4','Eb':'b5','E':'5','G':'b7','C#':'3*','F#':'6*','F':'b6*','B':'2*/E7-5','G#':'7*/E7-3'}
OPEN={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
STRINGS=('e','B','G','D','A','E')
COUNTS={'A':54,'B':36,'C':48,'D':160,'E':57,'F':65,'G':51,'H':70,'I':41,'J':64}
PDF_PAGES={'A':[3],'B':[4],'C':[5],'D':[6,7,8],'E':[9,10],'F':[11,12],'G':[13],'H':[14,15],'I':[16],'J':[17]}

class SourceError(ValueError):pass

def need(value:bool,message:str)->None:
    if not value:raise SourceError(message)

def pin(root:Path,spec:tuple[str,str,int])->bytes:
    path,digest,size=spec;target=root/path
    try:resolved=target.resolve(strict=True)
    except OSError as exc:raise SourceError(f'missing pinned source {path}') from exc
    need(not target.is_symlink() and resolved.is_relative_to(root) and resolved.is_file(),f'unsafe source {path}')
    raw=target.read_bytes();need(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,f'pin drift {path}')
    return raw

def ref(a:int,b:int|None=None)->str:return f'L44-TXT-L{a}' if b is None else f'L44-TXT-L{a}-{b}'

def note_degree_check(notes:list[str],degrees:list[str],context:str)->None:
    need(len(notes)==len(degrees),f'{context} note/degree length')
    for n,d in zip(notes,degrees):
        need(n in DEG,f'{context} unsupported note {n}')
        # E7 suffixes are authored functional labels, not new A-blues degree members.
        need(d==DEG[n] or (n=='B' and d in ('2*/E7-5','E7-5')) or (n=='G#' and d in ('7*/E7-3','E7-3')),f'{context} degree {n}/{d}')

def tab_lines(rows:list[str],context:str)->None:
    need(len(rows)==6 and [r[0] for r in rows]==list(STRINGS) and all(r[1]=='|' and r.endswith('|') for r in rows),f'{context} six TAB strings')

def tab_fret_multiset(rows:list[str])->list[int]:
    return sorted((OPEN[row[0]]+int(fret))%12 for row in rows for fret in re.findall(r'\d+',row.split('|',1)[1].split('|',1)[0]))

def check_plain_tab_degrees(rows:list[str],degrees:list[str],context:str)->None:
    core={degree:PC[note] for note,degree in DEG.items() if note in ('A','C','D','Eb','E','G')}
    need(sorted(core[d] for d in degrees)==tab_fret_multiset(rows),f'{context} TAB/degree pitch multiset')

def source_sections(lines:list[str])->dict[str,dict[str,Any]]:
    hits=[(i,re.match(r'^MODULE ([A-J]) - ',s).group(1)) for i,s in enumerate(lines) if re.match(r'^MODULE ([A-J]) - ',s)]
    need([k for _,k in hits]==list('ABCDEFGHIJ'),'module order/coverage')
    sections={}
    for j,(start,key) in enumerate(hits):
        end=hits[j+1][0]-2 if j<9 else 620  # J ends before progression separator, zero-based exclusive
        if key=='J':end=621
        need(start>0 and lines[start-1].startswith('=') and lines[start+1].startswith('='),f'module {key} separators')
        sections[key]={'heading':lines[start],'start_line':start+1,'end_line':end,'txt_ref':ref(start+1,end),'raw_lines':lines[start:end],'pdf_pages':PDF_PAGES[key]}
    need(lines[622]=='PRACTICE PROGRESSION' and lines[651]=='MASTERY GATE BEFORE LEVEL 45','post-module guidance boundary')
    return sections

def parse_a(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    result=[];base=30 # zero-based first site header
    expected=[('Low E','E',8,9),('A','A',15,16),('D','D',10,11),('G','G',5,6),('B','B',13,14),('High e','e',8,9)]
    for j,(label,string,source,target) in enumerate(expected):
        i=base+6*j;block=lines[i:i+6]
        need(block[0]==f'{label}: C fret {source} -> C# fret {target}',f'A site {j+1} header')
        need((OPEN[string]+source)%12==PC['C'] and (OPEN[string]+target)%12==PC['C#'] and target-source==1,f'A site {j+1} pitch')
        patterns=[f'TGT {string}|--{target}~~~~--|',f'BND {string}|--{source}b({target})r{source}--|',f'SLD {string}|--{source}/{target}--|',f'LEG {string}|--{source}h{target}p{source}--|','Degrees: b3 -> 3* -> b3']
        need(block[1:]==patterns,f'A site {j+1} alternatives')
        page='\n'.join(pdf[2]);need(all(f'{tag} {string}|--{source if tag!="TGT" else target}' in page for tag in ('TGT','BND','SLD','LEG')),f'A site {j+1} PDF alternatives')
        result.append({'site':j+1,'string':string,'source_note':'C','source_fret':source,'target_note':'C#','target_fret':target,'alternatives':{'fretted_target':block[1],'bend_release':block[2],'slide':block[3],'hammer_pull':block[4]},'degree_path':block[5],'txt_ref':ref(i+1,i+6),'pdf_page':3})
    return result

def parse_b(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    result=[];expected=[('Low E','E',10),('A','A',5),('D','D',12),('G','G',7),('B','B',15),('High e','e',10)]
    for j,(label,string,start) in enumerate(expected):
        i=70+3*j;row=lines[i]
        need(row==f'{label}: {string}|{start}--{start+1}--{start+2}--|{start+2}--{start+1}--{start}--|' and lines[i+1]=='Degrees: 4-b5-5 | 5-b5-4' and lines[i+2].startswith('Passes: picked triplet; one-pick slide chain; accent b5; then equalize all notes.'),f'B site {j+1}')
        need([(OPEN[string]+f)%12 for f in (start,start+1,start+2)]==[PC[n] for n in ('D','Eb','E')],f'B site {j+1} pitch')
        need(any(f'{string}|{start}' in x or f'{string}|{start} ' in x for x in pdf[3]),f'B site {j+1} PDF row')
        result.append({'site':j+1,'string':string,'frets':[start,start+1,start+2,start+2,start+1,start],'notes':['D','Eb','E','E','Eb','D'],'degree_paths':['4-b5-5','5-b5-4'],'passes':['picked triplet','one-pick slide chain','accent b5','equalize all notes'],'raw_txt':lines[i:i+3],'txt_ref':ref(i+1,i+3),'pdf_page':4})
    return result

def parse_c(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    result=[];expected=[('Low E','E',15,17,'SFT'),('A','A',10,12,'SFT'),('D','D',5,7,'SFT'),('G','G',12,14,'BND'),('B','B',8,10,'BND'),('High e','e',15,17,'BND')]
    for j,(label,string,source,target,last) in enumerate(expected):
        i=92+6*j;block=lines[i:i+6]
        need(block[0]==f'{label}: G fret {source} -> A fret {target}' and block[-1]=='Degrees: b7 -> 1',f'C site {j+1} header')
        need((OPEN[string]+source)%12==PC['G'] and (OPEN[string]+target)%12==PC['A'] and target-source==2,f'C site {j+1} pitch')
        need(block[1].startswith(f'PCK {string}|--{source}--{target}--|') and block[2]==f'SLD {string}|--{source}/{target}--|' and block[3]==f'LEG {string}|--{source}h{target}--|' and block[4].startswith(f'{last} {string}|'),f'C site {j+1} alternatives')
        if last=='BND':need(block[4]==f'BND {string}|--{source}b({target})--|',f'C site {j+1} bend')
        need(any(f'PCK {string}|--{source}' in x for x in pdf[4]),f'C site {j+1} PDF')
        result.append({'site':j+1,'string':string,'source_note':'G','source_fret':source,'target_note':'A','target_fret':target,'alternatives':{'picked':block[1],'slide':block[2],'legato':block[3],last.lower():block[4]},'degree_path':'b7 -> 1','txt_ref':ref(i+1,i+6),'pdf_page':5})
    return result

def parse_d(lines:list[str],pdf:list[list[str]])->dict[str,Any]:
    rhythms=lines[132:145]
    need(len(rhythms)==13 and rhythms[0]=='Apply all four rhythm templates to every eight-tone family.' and [x for x in rhythms if re.match(r'^[A-D]\. ',x)]==[lines[133],lines[136],lines[139],lines[142]],'D rhythm templates')
    starts=[146,157,168,179,190]
    families=[]
    for j,i in enumerate(starts,1):
        block=lines[i:i+10]
        need(block[0].startswith(f'FAMILY {j} - ') and block[7].startswith('Notes:') and block[8].startswith('Degrees:') and block[9].startswith('Focus:'),f'D family {j}')
        tab_lines(block[1:7],f'D family {j}')
        notes=block[7].split(':',1)[1].split();need(len(notes)==1,f'D family {j} note row shape')
        note_list=notes[0].split('-');degree_list=block[8].split(':',1)[1].strip().split('-')
        need(len(note_list)==len(degree_list)==8,f'D family {j} eight tones')
        note_degree_check(note_list,degree_list,f'D family {j}')
        page=5 if j<3 else 6 if j<5 else 7
        need(any(f'FAMILY {j}' in x or f'Family {j}' in x for x in pdf[page]),f'D family {j} PDF')
        families.append({'family':j,'title':block[0],'tab_rows':block[1:7],'notes':note_list,'degrees':degree_list,'focus':block[9],'rhythm_template_refs':['A','B','C','D'],'written_tones_per_template':8,'printed_workload_tones':32,'txt_ref':ref(i+1,i+10),'pdf_page':page+1})
    return {'rhythm_templates_raw':rhythms,'families':families,'printed_workload_tones':160,'txt_ref':ref(133,200),'pdf_pages':[6,7,8]}

def phrase_blocks(lines:list[str],pattern:str,first:int,last:int)->list[tuple[int,list[str]]]:
    starts=[i for i in range(first,last) if re.fullmatch(pattern,lines[i])]
    return [(i,lines[i:i+9]) for i in starts]

def parse_e(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    starts=phrase_blocks(lines,r'P[1-5] (CALL|ANSWER) - .+',204,299)
    need(len(starts)==10,'E ten phrases')
    pairs=[]
    for p in range(1,6):
        members=[]
        for kind in ('CALL','ANSWER'):
            matches=[(i,b) for i,b in starts if b[0].startswith(f'P{p} {kind} - ')]
            need(len(matches)==1,f'E P{p} {kind}')
            i,block=matches[0];tab_lines(block[1:7],f'E P{p} {kind}')
            need(block[7].startswith('Degrees: ') and block[8].startswith('Focus:'),f'E P{p} summary')
            degrees=block[7].split(': ',1)[1].split('-')
            need(len(degrees) in (4,5,6,7) and all(d in ('1','b3','4','b5','5','b7') for d in degrees),f'E P{p} degrees')
            check_plain_tab_degrees(block[1:7],degrees,f'E P{p} {kind}')
            if kind=='ANSWER':need(degrees[-1]=='1',f'E P{p} answer root')
            page=8 if p<=2 else 9
            need(any(f'P{p}' in x for x in pdf[page]),f'E P{p} PDF')
            members.append({'kind':kind,'title':block[0],'tab_rows':block[1:7],'degrees':degrees,'focus':block[8],'written_tones':len(degrees),'txt_ref':ref(i+1,i+9),'pdf_page':page+1})
        pairs.append({'position':p,'call':members[0],'answer':members[1],'written_tones':sum(x['written_tones'] for x in members)})
    need(sum(x['written_tones'] for x in pairs)==57,'E workload')
    return pairs

def parse_f(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    specs=[('A',302,6),('B',348,7)]
    result=[]
    for name,start,note_count in specs:
        head=lines[start];need(head.startswith(f'CORE LICK {name}: '),f'F lick {name}')
        degrees=head.split(': ',1)[1].split('-');need(len(degrees)==note_count,f'F lick {name} degree length')
        blocks=[];region_end=348 if name=='A' else 393
        matches=[i for i in range(start+1,region_end) if re.match(r'^P[1-5] - ',lines[i])]
        need(len(matches)==5,f'F lick {name} positions')
        for p,i in enumerate(matches,1):
            block=lines[i:i+8];need(block[0].startswith(f'P{p} - ') and block[7].startswith('Notes: '),f'F {name} P{p}')
            tab_lines(block[1:7],f'F {name} P{p}')
            notes=block[7].split(': ',1)[1].split('-')
            note_degree_check(notes,degrees,f'F {name} P{p}')
            need(sorted(PC[n] for n in notes)==tab_fret_multiset(block[1:7]),f'F {name} P{p} TAB pitch multiset')
            page=10 if name=='A' else 11
            need(any(f'P{p}' in x for x in pdf[page]),f'F {name} P{p} PDF')
            blocks.append({'position':p,'title':block[0],'tab_rows':block[1:7],'notes':notes,'degrees':degrees,'written_tones':note_count,'txt_ref':ref(i+1,i+8),'pdf_page':page+1})
        result.append({'core_lick':name,'degree_formula':degrees,'positions':blocks,'written_tones':5*note_count})
    need(sum(x['written_tones'] for x in result)==65,'F workload')
    return result

def parse_g(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    labels=['LOW CALL','HIGH ANSWER','HIGH CALL','LOW ANSWER','MID CALL - COMPLETE OCTAVE','UPPER ANSWER - SAME DEGREES','HIGH CALL - ASCENDING','LOW CONTRAST ANSWER']
    starts=[i for i in range(397,465) if lines[i] in labels]
    need(len(starts)==8 and [lines[i] for i in starts]==labels,'G four conversations/order')
    halves=[]
    for i in starts:
        block=lines[i:i+8];tab_lines(block[1:7],f'G {block[0]}')
        need(block[7].startswith('Degrees: '),'G degrees')
        degrees=block[7].split(': ',1)[1].split('-')
        need(len(degrees) in (6,7) and all(d in ('1','b3','4','b5','5','b7') for d in degrees),'G degree set')
        check_plain_tab_degrees(block[1:7],degrees,f'G {block[0]}')
        halves.append({'title':block[0],'tab_rows':block[1:7],'degrees':degrees,'written_tones':len(degrees),'txt_ref':ref(i+1,i+8),'pdf_page':13})
    need(sum(h['written_tones'] for h in halves)==51 and len(pdf[12])==67,'G workload/PDF page')
    return [{'conversation':k+1,'call':halves[2*k],'answer':halves[2*k+1],'written_tones':halves[2*k]['written_tones']+halves[2*k+1]['written_tones']} for k in range(4)]

def parse_h(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    starts=[i for i in range(470,555) if re.fullmatch(r'P[1-5] (TONIC|TURNAROUND) ENDING',lines[i])]
    need(len(starts)==10,'H ending count')
    result=[]
    for p in range(1,6):
        pair=[]
        for kind in ('TONIC','TURNAROUND'):
            i=next((x for x in starts if lines[x]==f'P{p} {kind} ENDING'),None)
            need(i is not None,f'H P{p} {kind}')
            block=lines[i:i+8];tab_lines(block[1:7],f'H P{p} {kind}')
            need(block[7].startswith('Degrees: '),f'H P{p} degrees')
            degrees=block[7].split(': ',1)[1].split('-')
            need(len(degrees)==7 and degrees[-1]==('1' if kind=='TONIC' else '5'),f'H P{p} ending function')
            check_plain_tab_degrees(block[1:7],degrees,f'H P{p} {kind}')
            page=13 if p<=3 else 14
            pair.append({'kind':kind,'tab_rows':block[1:7],'degrees':degrees,'written_tones':7,'txt_ref':ref(i+1,i+8),'pdf_page':page+1})
        need(pair[0]['degrees'][:-1]==pair[1]['degrees'][:-1],f'H P{p} common opening')
        result.append({'position':p,'tonic_ending':pair[0],'turnaround_ending':pair[1],'written_tones':14})
    need(len(pdf[13])==67 and len(pdf[14])==57,'H PDF pages')
    return result

def parse_i(lines:list[str],pdf:list[list[str]])->list[dict[str,Any]]:
    starts=[i for i in range(558,602) if re.match(r'^[1-4]\. [A-Z]',lines[i])]
    need(len(starts)==4,'I four models')
    result=[]
    for k,i in enumerate(starts,1):
        block=lines[i:i+10];need(block[0].startswith(f'{k}. ') and block[7].startswith('Notes:') and block[8].startswith('Degrees:') and block[9].startswith('Focus:'),f'I model {k}')
        tab_lines(block[1:7],f'I model {k}')
        if k==3:
            need('four descending three-note shapes' in block[8] and 'E7' in block[8] and 'chromatic inner voices' in block[7], 'I chordal shape semantics')
            need(len(re.findall(r'\d+',block[1]+block[2]+block[3]+block[4]+block[5]+block[6]))==16,'I simultaneous shape tone count')
            need(re.findall(r'\d+',block[2])==['5']*5,'I common upper E')
            kind='simultaneous_voice_leading_shapes';tones=16
        else:
            notes=block[7].split(':',1)[1].strip().split('-');need(len(notes)==(9 if k==1 else 8),f'I model {k} note count')
            need(all(n in PC for n in notes),f'I model {k} unsupported note')
            if k==1:
                need(notes==['A','G','F#','F','E','D','G#','B','E'] and block[8]=='Degrees: 1-b7-6*-b6*-5 | E7:b7-3-5-1','I E7 arpeggio function')
            elif k==2:
                need(notes==['A','C','C#','E','G','F#','F','E'] and block[8]=='Degrees: 1-b3-3*-5-b7-6*-b6*-5','I chromatic V approach')
            else:
                need(notes==['G','A','G','E','D','C','C#','B'] and block[8]=='Degrees: b7-1-b7-5-4-b3-3*-2*/E7-5','I B landing function')
            kind='single_note_line';tones=len(notes)
        need(any(block[0] in x for x in pdf[15]),f'I model {k} PDF')
        result.append({'model':k,'title':block[0],'kind':kind,'tab_rows':block[1:7],'notes_raw':block[7],'degrees_raw':block[8],'focus':block[9],'printed_workload_tones':tones,'txt_ref':ref(i+1,i+10),'pdf_page':16})
    need(sum(x['printed_workload_tones'] for x in result)==41,'I workload')
    return result

def parse_j(lines:list[str],pdf:list[list[str]])->dict[str,Any]:
    need(lines[605]=='OPENINGS' and lines[610]=='ENDINGS','J opening/ending headings')
    openings=[];endings=[]
    for k,i in enumerate(range(606,610)):
        parts=[x.strip() for x in lines[i].split(' | ',2)]
        need(len(parts)==3 and parts[0].startswith(f'{chr(65+k)}: '),f'J opening {k+1}')
        deg=parts[0].split(': ',1)[1].split('-');notes=parts[1].split('-')
        need(len(deg)==len(notes)==4 and parts[2].startswith(('G|','e|','B|')),f'J opening {k+1} four-note')
        note_degree_check(notes,deg,f'J opening {k+1}')
        openings.append({'label':chr(65+k),'degrees':deg,'notes':notes,'tab_raw':parts[2],'txt_ref':ref(i+1)})
    for k,i in enumerate(range(611,615),1):
        parts=[x.strip() for x in lines[i].split(' | ',2)]
        need(parts[0].startswith(f'{k}: '),'J ending label')
        deg=parts[0].split(': ',1)[1].split('-');notes=parts[1].split('-')
        need(len(deg)==len(notes)==4,'J ending four-note')
        note_degree_check(notes,deg,f'J ending {k}')
        endings.append({'label':str(k),'degrees':deg,'notes':notes,'tab_raw':parts[2],'txt_ref':ref(i+1)})
    models=lines[616:620]
    need(len(models)==4 and [m.split(':',1)[0] for m in models]==['A + 1','B + 3','C + 2','D + 4'],'J four model choices')
    combinations=[{'opening':o['label'],'ending':e['label'],'component_degree_occurrences':8} for o in openings for e in endings]
    need(len(combinations)==16 and 16*8==128 and pdf[16][2]=='4 OPENINGS x 4 ENDINGS = 16 PHRASES','J combinations')
    return {'openings':openings,'endings':endings,'model_combinations_raw':models,'all_combinations':combinations,'printed_workload_tones':64,'implied_full_combination_degree_occurrences':128,'count_status':'unresolved_source_counting_convention','txt_ref':ref(606,620),'pdf_page':17}

def build_candidate(root:Path=ROOT)->dict[str,Any]:
    root=root.resolve(strict=True)
    raw={name:pin(root,spec) for name,spec in [('txt',TXT),('pdf',PDF),('source_map',MAP),('predecessor_txt',P43_TXT),('predecessor_pdf',P43_PDF)]}
    try:
        lines=raw['txt'].decode('utf-8').splitlines();pages=[(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']),strict=True).pages]
        source_map=json.loads(raw['source_map'])
    except Exception as exc:raise SourceError('source decode failure') from exc
    need(len(lines)==660 and len(pages)==19,'TXT/PDF coverage drift')
    need(lines[:2]==['SCALE EXERCISES - SECTION V, LEVEL 44','A BLUES RESOLUTION VOCABULARY, LICK CONSTRUCTION, AND FUNCTIONAL TURNAROUNDS - FIXED KEY A'],'TXT title drift')
    need(all(p[4]==f'Page {n} of 19' for n,p in enumerate(pages,1)),'PDF page identity drift')
    need(lines[10:12]==['A blues scale: A C D Eb E G','Degrees:       1 b3 4 b5 5 b7'],'core pitch pool')
    need([len(p) for p in pages]==[58,70,43,37,43,33,33,36,47,51,57,57,67,67,57,47,49,54,32],'PDF extraction coverage')
    rows=source_map.get('rows');need(isinstance(rows,list),'source-map rows')
    mapped={r['level']:r for r in rows if r.get('level') in (43,44)}
    need(set(mapped)=={43,44},'source-map predecessor/current')
    for level,txt,pdf in ((43,P43_TXT,P43_PDF),(44,TXT,PDF)):
        row=mapped[level]
        need(row['pair_status']=='exact_stem_pair' and row['wbs_owner']=='2.3.1.1.1' and row['review']=='Pending' and not row['admitted'] and not row['imported'] and not row['runtime_eligible'],'source-map status')
        need(row['txt_path']==txt[0] and row['txt_sha256']==txt[1] and row['txt_bytes']==txt[2] and row['pdf_path']==pdf[0] and row['pdf_sha256']==pdf[1] and row['pdf_bytes']==pdf[2],'source-map identity')
    sections=source_sections(lines)
    modules={'A':parse_a(lines,pages),'B':parse_b(lines,pages),'C':parse_c(lines,pages),'D':parse_d(lines,pages),'E':parse_e(lines,pages),'F':parse_f(lines,pages),'G':parse_g(lines,pages),'H':parse_h(lines,pages),'I':parse_i(lines,pages),'J':parse_j(lines,pages)}
    computed={'A':len(modules['A'])*9,'B':len(modules['B'])*6,'C':len(modules['C'])*8,'D':modules['D']['printed_workload_tones'],'E':sum(x['written_tones'] for x in modules['E']),'F':sum(x['written_tones'] for x in modules['F']),'G':sum(x['written_tones'] for x in modules['G']),'H':sum(x['written_tones'] for x in modules['H']),'I':sum(x['printed_workload_tones'] for x in modules['I']),'J':modules['J']['printed_workload_tones']}
    need(computed==COUNTS and sum(computed.values())==646,'PDF printed workload reconciliation')
    page1=pages[0]
    need(page1[2]=='FIXED KEY: A  |  10 MODULES  |  646 TONES' and page1[50:52]==['TOTAL','646'],'PDF total')
    need([int(page1[i]) for i in range(31,50,2)]==list(COUNTS.values()),'PDF module workload table')
    need('six blue-third sites in tune' in lines[652] and 'all 16 recombination' in lines[654] and 'two separate days' in lines[655],'TXT mastery gate')
    need('Sixteen recombinations' in pages[18] and 'Two separate clean days' in pages[18],'PDF completion audit')
    differences=[{'kind':'PDF_only_post_workbook_variations','pdf_ref':'L44-PDF-p18-L37-51','pdf_text':pages[17][36:51],'txt_equivalent':None},{'kind':'PDF_only_completion_audit_checklist','pdf_ref':'L44-PDF-p19-L9-21','pdf_text':pages[18][8:21],'txt_equivalent':None},{'kind':'PDF_visual_completion_audit_border_overlap','pdf_ref':'L44-PDF-p19','inspection':'rendered page shows lower checklist row intersecting panel border; source-layout observation only'},{'kind':'J_workload_count_ambiguous','pdf_ref':'L44-PDF-p1-L49-52','pdf_printed_tones':64,'txt_ref':ref(607,620),'full_combinations':16,'degrees_per_combination':8,'implied_full_degree_occurrences':128,'status':'pending_curriculum_review'}]
    source={name:{'path':spec[0],'bytes':spec[2],'sha256':spec[1],'role':name} for name,spec in [('txt',TXT),('pdf',PDF),('source_map',MAP),('predecessor_txt',P43_TXT),('predecessor_pdf',P43_PDF)]}
    return {'schema':'fathom.level044.detached-source-candidate.1','wbs':'2.3.1.1.1','status':'non_admitted','admitted':False,'canonical_id':None,'exercise_id':None,'onset_q':None,'duration_q':None,'fixed_bpm':None,'pick_attack_count':None,'executable_events':None,'source':source,'source_map_rows':{'predecessor_level43':mapped[43],'level44':mapped[44]},'key':'A blues','core_notes':['A','C','D','Eb','E','G'],'core_degrees':['1','b3','4','b5','5','b7'],'marked_support_notes':{'C#':'3*','F#':'6*','F':'b6*','B':'2*/E7-5','G#':'7*/E7-3'},'module_sections':sections,'modules':modules,'pdf_printed_workload_by_module':computed,'pdf_printed_total_tones':646,'source_differences':differences,'source_guidance':{'txt_full_lines':lines,'pdf_full_extracted_pages':pages,'txt_practice_and_mastery_lines_622_660':lines[621:],'pdf_practice_and_mastery_pages_18_19':pages[17:]}}

def encode(value:dict[str,Any])->bytes:return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')

def output_path(root:Path,value:str)->Path:
    root=root.resolve(strict=True);r=Path(value)
    need(not r.is_absolute() and '..' not in r.parts and r.parts[:len(BUILD.parts)]==BUILD.parts and r.suffix=='.json','output outside reserved Build directory')
    p=root
    for part in r.parts:p=p/part;need(not p.is_symlink(),'symlink output path')
    need(not p.exists(),'refusing overwrite')
    return p

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True);args=ap.parse_args()
    target=output_path(ROOT,args.output);value=build_candidate(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encode(value))
    print(f'{target.relative_to(ROOT)} bytes={target.stat().st_size} sha256={hashlib.sha256(target.read_bytes()).hexdigest()}')
    return 0

if __name__=='__main__':raise SystemExit(main())
