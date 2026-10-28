#!/usr/bin/env python3
"""P90 Level22 A->Bb first neighboring-rung source/native reference; nonadmitted."""
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
import parallel_12_level022_whole_ladder as p12source

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-90/controlled-open-level022-first-neighbor-r01')
BASE = Path('Content/controls/curriculum-v1')
TXT, PDF = p12source.TXT, p12source.PDF
P12 = Path('Build/parallel-12/level022-schema1-unallocated-r01/field-proposal.json')
P12_RESULT = Path('Results/parallel-12/conversion/20260923T150132Z-level022-whole-ladder-r01-results.md')
RELEASE = Path('Prompts/parallel-90/controlled-open-level022-first-neighbor-r01/manager-source-slot-release-addendum-01.md')
NATIVE = Path('Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate')
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PINS = {
    TXT: '0031bdd05834d1f1f381240a48a5fa193da561f7bdf51df580771f593c82b1dc',
    PDF: 'f07518814be26b8290c6b9a688251eb77fd2b2aedb8efc03a0469167d8be7bde',
    P12: '5b8197bd4957cc3550151f9c11d453a4729ab232384ed88acaadd512ed9b94d7',
    P12_RESULT: '9712ac7cfcafc27b60b95db8360dc46c45fd38e7891a892e8033b3ac43c84023',
    RELEASE: '6f732ffdc6d5d4f2bb261ea0b7a45c7f60bf7547088a145ffb189f79e641ad51',
    BASE/'package.json': '766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255',
    BASE/'identity-registry.json': '5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5',
    BASE/'expected-profile.json': '21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a',
}
ITEM = 'fg:item:009900'
MODULE = 'fg:module:009900'
VARIANTS = ('fg:variant:009900', 'fg:variant:009901')
WORKBOOK = 'fg:workbook:000022'
NAMES = ('package.json','identity-registry.json','expected-profile.json',
         'candidate-allocation.json','identity-baseline.json','allocation-baseline.json',
         'lineage-baseline.json','source-provenance.json','summary.json')
OPEN = {'E':(1,40),'A':(2,45),'D':(3,50),'G':(4,55),'B':(5,59),'e':(6,64)}
DEGREES = {'1':1,'2':2,'b3':3,'4':4,'5':5,'b6':6,'b7':7}

class CandidateError(ValueError):
    pass

def need(ok, code):
    if not ok: raise CandidateError(code)

def encode(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads((ROOT/path).read_bytes())

def pin():
    top=Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip())
    need(top.resolve()==ROOT.resolve(),'ROOT_DRIFT')
    for path,digest in PINS.items():
        need(sha((ROOT/path).read_bytes())==digest,'PIN_DRIFT:'+str(path))
    need(sha((ROOT/NATIVE).read_bytes())==NATIVE_SHA,'NATIVE_DRIFT')

def identity_scan():
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):009900',
         '-e',r'fg:variant:00990[01]','--glob','*.json','--glob','*.hpp',
         '--glob','*.cpp','Content','Source','Build']
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    return {'status':'PASS','scope':['Content','Source','Build'],'method':cmd,
            'wanted':[ITEM,MODULE,*VARIANTS],'matches':hits,'canonical_reservation':False,
            'classification':'P90 private provisional labels only; P02 serial canonical allocation required'}

def source_ref(path, fmt, value, **where):
    return {'path':str(path),'format':fmt,'sha256':PINS[path],**where,
            'text':value,'text_sha256':sha(value.encode())}

def source_facts():
    pin()
    lines=(ROOT/TXT).read_text().splitlines()
    pages=[(p.extract_text() or '').splitlines() for p in PdfReader(str(ROOT/PDF)).pages]
    need(len(lines)==264 and len(pages)==7,'SOURCE_LENGTH')
    for number,phrase in ((16,'1 2 b3 4 5 b6 b7'),(20,'R, R+2, R+3'),
                          (23,'R-1, R, R+2'),(24,'R, R+1, R+3'),
                          (30,'3 - 3 - 2 - 3 - 3 - 1'),
                          (37,'30 notes'),(38,'strict D-U'),(39,'strict U-D'),
                          (40,'Do not restart'),(43,'A(5) > Bb(6)'),
                          (48,'2-3 neighboring rungs, play even eighth notes, and pause one beat')):
        need(phrase in lines[number-1],f'TXT_GUIDANCE_{number}')
    need('Use 2-3 neighboring' in '\n'.join(pages[0]) and
         'pause one' in '\n'.join(pages[0]) and
         'A natural minor' in '\n'.join(pages[1]) and
         'Bb natural minor' in '\n'.join(pages[1]),'PDF_GUIDANCE')
    proposal=read(P12)['records'][:2]
    rungs=[]
    for index,(key,root,start,pdfline) in enumerate((('A',5,55,6),('Bb',6,69,20))):
        block=lines[start-1:start+11]
        pdfblock=pages[2][pdfline-1:pdfline+13]
        need(len(block)==12 and len(pdfblock)==14 and
             block[0].startswith(f'RUNG {index+1:02d} OF 13 - {key.upper()} NATURAL MINOR') and
             pdfblock[0]==f'{index+1:02d}  {key.upper()} MINOR' and
             pdfblock[4:12]==block[3:11],f'TXT_PDF_CARD_{index+1}')
        tones=block[1].removeprefix('Scale tones across two octaves: ').replace(' | ',' ').split()
        degrees=re.findall(r'b[367]|[1-7]',block[3][4:])
        fingers=[int(x) for x in re.findall(r'[1-4]',block[4][4:])]
        need(len(tones)==15 and len(degrees)==len(fingers)==30 and
             tones[0]==tones[-1]==key and degrees[14:16]==['1','1'] and
             fingers[14:16]==[1,1],f'PRINTED_SEQUENCES_{index+1}')
        ascending=[(s,root+offset,f) for s,offs,fs in
                   (('E',(0,2,3),(1,3,4)),('A',(0,2,3),(1,3,4)),
                    ('D',(0,2),(1,3)),('G',(-1,0,2),(1,2,4)),
                    ('B',(0,1,3),(1,2,4)),('e',(0,),(1,)))
                   for offset,f in zip(offs,fs)]
        layout=ascending+list(reversed(ascending))
        need(len(layout)==30 and layout[14]==layout[15]==('e',root,1),f'TURN_{index+1}')
        for row,string in zip(block[5:11],('e','B','G','D','A','E')):
            need(row.startswith(string+'  |') and
                 [int(x) for x in re.findall(r'\d+',row[4:])]==
                 [fret for s,fret,_ in layout if s==string],f'TAB_{index+1}_{string}')
        fields=proposal[index]['schema1_fields']['events']
        need(len(fields)==30 and proposal[index]['key']==key and
             proposal[index]['root_fret']==root,f'P12_SCOPE_{index+1}')
        for ordinal,((string,fret,finger),degree,printed_finger,field) in enumerate(
            zip(layout,degrees,fingers,fields),1):
            expected_spelling=tones[ordinal-1 if ordinal<=15 else 30-ordinal]
            need((finger,field['string'],field['fret'],field['finger'],field['midi'],
                  field['spelling'],field['degree_contexts'][f'{key}-natural-minor']['source_label'])==
                 (printed_finger,OPEN[string][0],fret,finger,OPEN[string][1]+fret,
                  expected_spelling,degree),f'P12_NOTE_PARITY_{index+1}_{ordinal}')
        rungs.append({'key':key,'root':root,'start':start,'pdfline':pdfline,
                      'layout':layout,'degrees':degrees,'fingers':fingers,
                      'tones':tones,'fields':fields})
    return lines,pages,rungs

def derive(*,force_eligible=False,forced_bpm=None,grouping='source_event_time',
           changed_onsets=None,changed_durations=None,changed_strokes=None,
           changed_contacts=None,reserved_item=ITEM):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(grouping=='source_event_time','SOURCE_EVENT_TIME_REQUIRED')
    need(reserved_item==ITEM,'FOREIGN_ID')
    audit=read(OUT/'identity-audit.json')
    need(audit['status']=='PASS' and not audit['matches'] and
         audit['wanted']==[ITEM,MODULE,*VARIANTS],'IDENTITY_AUDIT_DRIFT')
    lines,pages,rungs=source_facts()
    need(changed_contacts is None or changed_contacts==[r['layout'] for r in rungs],
         'CONTACT_DRIFT')
    refs=['L22-TXT-GUIDANCE','L22-PDF-GUIDANCE','L22-PDF-ROUTE',
          'L22-TXT-RUNG01','L22-TXT-RUNG02','L22-PDF-CARDS01-02']
    sources={refs[0]:source_ref(TXT,'txt','\n'.join(lines[:52]),first_line=1,last_line=52),
             refs[1]:source_ref(PDF,'pdf','\n'.join(pages[0]),page=1),
             refs[2]:source_ref(PDF,'pdf','\n'.join(pages[1]),page=2),
             refs[5]:source_ref(PDF,'pdf','\n'.join(pages[2]),page=3)}
    for index,rung in enumerate(rungs):
        start=rung['start']
        sources[refs[3+index]]=source_ref(TXT,'txt','\n'.join(lines[start-1:start+11]),
                                          first_line=start,last_line=start+11)
    base_package,base_registry,base_profile=(read(BASE/n) for n in
        ('package.json','identity-registry.json','expected-profile.json'))
    events=[];sidecar={};event_sources={}
    for cell,rung in enumerate(rungs):
        for j,((string,fret,finger),degree,field) in enumerate(
            zip(rung['layout'],rung['degrees'],rung['fields'])):
            eid=f'{ITEM}:event:{cell*30+j+1:04d}'
            q=Fraction(cell*16)+Fraction(j,2)
            onset=list(q.as_integer_ratio())
            duration=[1,2]
            if changed_onsets and eid in changed_onsets:onset=changed_onsets[eid]
            if changed_durations and eid in changed_durations:duration=changed_durations[eid]
            event=copy.deepcopy(field)
            event.update(event_id=eid,onset_q=onset,duration_q=duration)
            # Native minor-degree ordinal is the printed 1..7 degree; preserve
            # the distinct 1..15 scale position in the provenance sidecar.
            event['degree_contexts'][f'{rung["key"]}-natural-minor']['ordinal']=DEGREES[degree]
            events.append(event)
            card_ref=refs[3+cell]
            event_sources[eid]=card_ref
            local=(j+1 if j<15 else 30-j)
            tabline=rung['start']+5+('e','B','G','D','A','E').index(string)
            sidecar[eid]={
                'source_local_event_key':f'L22-A-Bb:R{cell+1:02d}:{j+1:02d}',
                'source_txt_ref':card_ref,'source_pdf_ref':refs[5],
                'source_txt_card_lines':[rung['start'],rung['start']+11],
                'source_txt_degree_line':rung['start']+3,
                'source_txt_finger_line':rung['start']+4,
                'source_txt_tab_line':tabline,'source_pdf_page':3,
                'source_pdf_card_lines':[rung['pdfline'],rung['pdfline']+13],
                'source_cell':cell+1,'source_contact':j+1,'source_scale_position':local,
                'source_degree':degree,'source_pitch_spelling':event['spelling'],
                'source_string_label':string,'source_string':event['string'],
                'source_fret':fret,'source_finger':finger,'source_midi':event['midi'],
                'repeated_high_root_at_turn':j in (14,15),
                'timing_txt_ref':refs[0],'timing_txt_line':48,'timing_pdf_ref':refs[1],
                'nominal_slot_q':list(q.as_integer_ratio()),'duration_q':[1,2],
                'one_beat_release_after_cell':j==29 and cell==0,
                'frame_move_frets':1 if j==29 and cell==0 else 0}
    variants=[];strokes={}
    for vid,start in zip(VARIANTS,('D','U')):
        expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(60)]
        if changed_strokes and vid in changed_strokes:expected=changed_strokes[vid]
        strokes[vid]=expected
        variants.append({'id':vid,'label':f'l22-a-bb-neighbor-{start}-start',
                         'role':'notation_practice','route':'first_neighboring_minor_rungs_paused_learning',
                         'source_refs':refs,'event_ids':[e['event_id'] for e in events],
                         'pick_start':start,'pick_start_origin':'source_authored',
                         'grouping':{'kind':'source_event_time','notes_per_beat':None,
                                     'beat_unit_q':None,'marking_factor':[1,1],
                                     'source_label':'even eighth contacts and one-beat released-pressure pause after A cell'},
                         'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]})
    for index,event in enumerate(events):
        sidecar[event['event_id']]['pick_strokes']={vid:strokes[vid][index] for vid in VARIANTS}
        sidecar[event['event_id']]['pick_txt_lines']=[38,39,40]
        sidecar[event['event_id']]['pick_pdf_page']=1
    title='Level 22 A to Bb natural-minor two-octave 60-contact neighboring cells'
    record={'id':ITEM,'module_id':MODULE,'workbook_id':WORKBOOK,
            'content_revision':1,'lineage':{'kind':'new'},'kind':'notation',
            'legacy_level':22,'status':'converted_candidate','runtime_eligible':False,
            'title':title,'source_refs':refs,'authored_text_refs':refs,
            'events':events,'variants':variants,'resource_requirements':[],'rubric':None,
            'control_scope':{'extent':'complete_selected_case','local_case':'L022-R01-R02:A_BB:MINOR_PAUSED',
                             'source_event_count':60,'basis_refs':refs,'whole_workbook_complete':False,
                             'unresolved':['Other rungs and full route outside packet.',
                                           'Canonical identity and runtime admission pending.']},
            'context':{'local_code':'L022-R01-R02:A_BB:MINOR_PAUSED',
                       'route':'A(5)→Bb(6) natural-minor neighboring rungs',
                       'position':'low-E root fret5 through fret6; moving frame R-1 through R+3',
                       'pick_start_variants':['D','U'],
                       'pick_start':'source-authored continuous D/U or U/D through turn, crossings and one-fret shift',
                       'tuning_open_midi':[40,45,50,55,59,64],'capo':0,
                       'source_tempo_rules_ref':refs[0]},
            'timing':{'status':'source_defined','unit':'quarter','meter':None,
                      'basis':'Neighboring-rung mode: even eighth q1/2; A q0..14.5; one-beat released-pressure [15,16); Bb q16..30.5; end q31; no fixed BPM.'},
            'ambiguities':['First A cell timing belongs to this neighboring stage, not isolated first-mastery protocol.',
                           'Full connected route, adaptive tempo and mastery remain outside selected mode.',
                           'Capo zero denotes untransposed standard tuning, not an authored capo instruction.'],
            'normalization':[{'kind':'representation_metadata','basis':refs[0],
                              'text':'Two complete 30-contact cells; repeated high root at each turn and continuous alternate picking.'}]}
    package={k:copy.deepcopy(v) for k,v in base_package.items()
             if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level022-a-bb-neighbor-build-only.1',
                   records=[record],sources=sources)
    entities=[base_registry['entities'][0],
              {'id':WORKBOOK,'kind':'workbook','label':'Legacy Level22','parent':'fg:course:000001'},
              {'id':MODULE,'kind':'module','label':title,'parent':WORKBOOK},
              {'id':ITEM,'kind':'item','label':title,'parent':MODULE},
              *({'id':v['id'],'kind':'variant','label':v['label'],'parent':ITEM} for v in variants)]
    registry={'identity_version':base_registry['identity_version'],
              'rules':base_registry['rules'],'entities':entities}
    identity_baseline={'identity_version':registry['identity_version'],
                       'rules':registry['rules'],'entities':[entities[0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P90 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1',
                'authority':'P90 private provisional nonadmitted; P02 canonical scan required',
                'records':{ITEM:{'legacy_level':22,
                                 'occurrences':{s['source_local_event_key']:eid for eid,s in sidecar.items()},
                                 'variants':{v['label']:v['id'] for v in variants}}}}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources',
                          'authority_artifacts','workbook_catalog')}
    profile['degree_roots']={f'{key}-natural-minor':{
        'basis':f'Original Level22 {key} natural-minor rung card; pitch class only',
        'root_pitch_class':pc} for key,pc in (('A',9),('Bb',10))}
    profile.update(reference_package=package,reference_registry=registry,
                   event_sources=event_sources)
    profile['authority_artifacts']=[copy.deepcopy(a) for a in base_profile['authority_artifacts']
                                    if a['role'] in ('source_manifest','source_acceptance','current_schema_freeze')]
    for role,name,value in (('identity_baseline','identity-baseline.json',identity_baseline),
                            ('allocation_baseline','allocation-baseline.json',allocation_baseline),
                            ('lineage_baseline','lineage-baseline.json',lineage_baseline),
                            ('candidate_identity_allocation','candidate-allocation.json',allocation)):
        profile['authority_artifacts'].append({'path':str(OUT/name),'role':role,
                                               'sha256':sha(encode(value))})
    need(set(event_sources)==set(sidecar)=={e['event_id'] for e in events},
         'EVENT_PROVENANCE_COVERAGE')
    summary={'status':'source_interpreted_nonadmitted_reference','record_count':1,
             'event_count':60,'variant_count':2,'projected_membership_target':120,
             'item_id':ITEM,'module_id':MODULE,'variant_ids':list(VARIANTS),
             'identifiers':'provisional_noncanonical','runtime_eligible':False,
             'admitted':False,'whole_workbook_complete':False,
             'source_txt_sha256':PINS[TXT],'source_pdf_sha256':PINS[PDF],
             'p12_comparator_sha256':PINS[P12],
             'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
             'case_end_q':[31,1],'first_bb_onset_q':[16,1],
             'rest':{'start_q':[15,1],'end_q':[16,1],'kind':'released_pressure; one-fret frame move'},
             'interpretation':'One A→Bb neighboring-rung mode only, even-eighth q1/2, one-beat internal gap, both continuous pick starts; no fixed BPM/mastery/credit.'}
    return {'package.json':package,'identity-registry.json':registry,
            'expected-profile.json':profile,'candidate-allocation.json':allocation,
            'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,
            'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':[refs[0],refs[3],refs[4]],
                                      'source_pdf_refs':[refs[1],refs[2],refs[5]],
                                      'events':sidecar,'variant_strokes':strokes,
                                      'rest':summary['rest'],
                                      'stroke_basis':'Original Level22 continuous D/U or U/D through both repeated high-root turns and one-fret shift.'},
            'summary.json':summary}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('audit','build','verify'))
    args=parser.parse_args();dest=ROOT/OUT
    if args.command=='audit':
        result=identity_scan();dest.mkdir(parents=True,exist_ok=True)
        target=dest/'identity-audit.json';need(not target.exists(),'OUTPUT_EXISTS')
        target.write_bytes(encode(result));print(json.dumps(result,sort_keys=True));return
    output=derive()
    if args.command=='build':
        dest.mkdir(parents=True,exist_ok=True)
        need(all(not (dest/name).exists() for name in NAMES),'OUTPUT_EXISTS')
        for name in NAMES:(dest/name).write_bytes(encode(output[name]))
    else:
        for name in NAMES:need((dest/name).read_bytes()==encode(output[name]),'OUTPUT_DRIFT:'+name)
    print(json.dumps(output['summary.json'],sort_keys=True))

if __name__=='__main__':main()
