#!/usr/bin/env python3
"""P86 source-bound Level21 first three paused-learning cases; nonadmitted."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader
import parallel10_level021_minor_candidate as p10

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-86/controlled-open-level021-first-batch-r01')
BASE = Path('Content/controls/curriculum-v1')
P10 = Path('Build/parallel-10/2.3.1.1.1-level021-whole-minor-r01/candidate-02.json')
P12 = Path('Build/parallel-12/level021-schema1-unallocated-r01/field-proposal.json')
TXT, PDF = p10.TXT_REL, p10.PDF_REL
NATIVE = Path('Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate')
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
PINS = {
    TXT: p10.TXT_SHA, PDF: p10.PDF_SHA,
    P10: '980300d90260fe7c3df030426eaed27ca42a51baf18eeb4f31d14a83fd46bf5d',
    P12: 'c0d4530029e00be809fc1b6aefda7d14e9208b8cfc3ad39186a84d3c2034eec8',
    BASE/'package.json': '766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255',
    BASE/'identity-registry.json': '5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5',
    BASE/'expected-profile.json': '21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a',
}
ITEMS = tuple(f'fg:item:00986{i}' for i in range(3))
MODULES = tuple(f'fg:module:00986{i}' for i in range(3))
VARIANTS = tuple((f'fg:variant:00986{i*2}', f'fg:variant:00986{i*2+1}') for i in range(3))
WORKBOOK = 'fg:workbook:000021'
KEYS = ('A', 'Bb', 'B')
ROOT_PCS = (9, 10, 11)
NAMES = ('package.json', 'identity-registry.json', 'expected-profile.json',
         'candidate-allocation.json', 'identity-baseline.json', 'allocation-baseline.json',
         'lineage-baseline.json', 'source-provenance.json', 'summary.json')

class CandidateError(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise CandidateError(code)

def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))+'\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads((ROOT/path).read_bytes())

def pin():
    top = Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip())
    need(top.resolve() == ROOT.resolve(), 'ROOT_DRIFT')
    for path,digest in PINS.items():
        need(sha((ROOT/path).read_bytes()) == digest, 'PIN_DRIFT:'+str(path))
    need(sha((ROOT/NATIVE).read_bytes()) == NATIVE_SHA, 'NATIVE_DRIFT')

def identity_scan():
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):00986[0-2]',
         '-e',r'fg:variant:00986[0-5]','--glob','*.json','--glob','*.hpp',
         '--glob','*.cpp','Content','Source','Build']
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    return {'status':'PASS','method':cmd,'scope':['Content','Source','Build'],
            'wanted':[ *ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)],
            'matches':hits,'canonical_reservation':False,
            'classification':'P86 private provisional labels; P02 serially allocates canonical IDs'}

def ref(path,fmt,value,**where):
    return {'path':str(path),'format':fmt,'sha256':PINS[path],**where,
            'text':value,'text_sha256':sha(value.encode())}

def source_facts():
    pin()
    whole=p10.build_candidate(ROOT)
    need(whole==read(P10),'P10_REBUILD_DRIFT')
    rows=whole['rungs'][:3]
    proposal=read(P12)['records'][:3]
    need([(r['rung'],r['key'],r['low_e_root_fret']) for r in rows] ==
         [(1,'A',5),(2,'Bb',6),(3,'B',7)],'SOURCE_RUNG_SCOPE')
    need([r['source_local_key'] for r in proposal] ==
         ['L21-rung01','L21-rung02','L21-rung03'],'P12_SCOPE')
    lines=(ROOT/TXT).read_text().splitlines()
    pages=[(p.extract_text() or '').splitlines() for p in PdfReader(str(ROOT/PDF)).pages]
    need(len(pages)==6,'PDF_PAGE_COUNT')
    guide='\n'.join(lines[:43])
    for phrase in ('A major:','A natural minor:','3 -> b3, 6 -> b6, 7 -> b7',
                   'Play even eighth notes and pause one beat after each 16-note cell.',
                   'Do not restart the pick cycle at the scale turn or at the one-fret shift.'):
        need(phrase in guide,'GUIDANCE:'+phrase)
    need('A B C  D E F  G  A' in guide,'A_MINOR_C_NATURAL')
    pdf='\n'.join(pages[:3][0])+ '\n' + '\n'.join(pages[1])
    need('A natural minor' in pdf and 'one beat' in pdf,'PDF_GUIDANCE')
    for rung,(row,prior) in enumerate(zip(rows,proposal),1):
        start=row['txt_header_line']
        need(start==45+(rung-1)*14,'TXT_CARD_START')
        need(lines[start-1].startswith(f'RUNG {rung:02d} OF 13'),'TXT_CARD_HEADING')
        need(row['txt_rows']['Deg']==lines[start+2] and
             row['txt_rows']['Fng']==lines[start+3],'TXT_DEG_FINGER')
        for offset,string in enumerate(('e','B','G','D','A','E'),5):
            need(row['txt_rows'][string]==lines[start+offset-1],'TXT_TAB_ROW')
        fields=prior['schema1_fields']['events']
        need(len(fields)==len(row['notes'])==16,'CONTACT_COUNT')
        for n,e in zip(row['notes'],fields):
            d=e['degree_contexts'][f'{row["key"]}-natural-minor']
            need((e['string'],e['fret'],e['finger'],e['midi'],e['spelling'],d['source_label'],d['alteration'])==
                 (p10.STRINGS.index(n['string'])+1,n['fret'],n['finger'],n['midi'],n['source_tone'],
                  n['degree'],-1 if n['degree'].startswith('b') else 0),'P12_CONTACT_PARITY')
        need(row['notes'][7]['midi']==row['notes'][8]['midi'] and
             row['notes'][7]['fret']==row['notes'][8]['fret'],'REPEATED_HIGH_ROOT')
    return lines,pages,rows,proposal

def derive(*, changed_contacts=None,changed_onsets=None,changed_durations=None,
           changed_strokes=None,forced_bpm=None,force_eligible=False,
           reserved_item=ITEMS[0],grouping='source_event_time'):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(reserved_item==ITEMS[0],'FOREIGN_ID')
    need(grouping=='source_event_time','SOURCE_EVENT_TIME_REQUIRED')
    audit=read(OUT/'identity-audit.json')
    need(audit['status']=='PASS' and not audit['matches'] and
         set(audit['wanted'])=={*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)},
         'IDENTITY_AUDIT_DRIFT')
    lines,pages,rows,proposal=source_facts()
    need(changed_contacts is None or changed_contacts==[r['notes'] for r in rows],
         'CONTACT_DRIFT')
    refs=['L21-TXT-GUIDANCE','L21-PDF-GUIDANCE','L21-TXT-RUNG01',
          'L21-TXT-RUNG02','L21-TXT-RUNG03','L21-PDF-CARDS01-03','L21-PDF-ROUTE']
    sources={refs[0]:ref(TXT,'txt','\n'.join(lines[:43]),first_line=1,last_line=43),
             refs[1]:ref(PDF,'pdf','\n'.join(pages[0]),page=1),
             refs[5]:ref(PDF,'pdf','\n'.join(pages[2]),page=3),
             refs[6]:ref(PDF,'pdf','\n'.join(pages[1]),page=2)}
    for rung,row in enumerate(rows):
        start=row['txt_header_line']
        sources[refs[2+rung]]=ref(TXT,'txt','\n'.join(lines[start-1:start+11]),
                                  first_line=start,last_line=start+11)
    base_package,base_registry,base_profile=(read(BASE/n) for n in
        ('package.json','identity-registry.json','expected-profile.json'))
    entities=[base_registry['entities'][0],
              {'id':WORKBOOK,'kind':'workbook','label':'Legacy Level21','parent':'fg:course:000001'}]
    records=[];provenance={};event_sources={};allocations={};strokes={}
    for cidx,(item,module,vids) in enumerate(zip(ITEMS,MODULES,VARIANTS)):
        count=16*(cidx+1)
        local=('L021-R01:A:MINOR','L021-R01-R02:A_BB:MINOR_PAUSED',
               'L021-R01-R03:A_BB_B:MINOR_PAUSED')[cidx]
        title=('Level 21 A natural minor 16-contact cell',
               'Level 21 A to Bb natural minor 32-contact paused cells',
               'Level 21 A through B natural minor 48-contact paused cells')[cidx]
        events=[];sidecar={}
        for rung in range(cidx+1):
            row=rows[rung];fields=proposal[rung]['schema1_fields']['events']
            for j,(note,field) in enumerate(zip(row['notes'],fields)):
                eid=f'{item}:event:{rung*16+j+1:04d}'
                q=Fraction(rung*9)+Fraction(j,2)
                onset=list(q.as_integer_ratio());duration=[1,2]
                if changed_onsets is not None and eid in changed_onsets:onset=changed_onsets[eid]
                if changed_durations is not None and eid in changed_durations:duration=changed_durations[eid]
                event=copy.deepcopy(field)
                event.update(event_id=eid,onset_q=onset,duration_q=duration)
                events.append(event)
                event_sources[eid]=refs[2+rung]
                sidecar[eid]={
                    'source_local_event_key':f'{local}:R{rung+1:02d}:{j+1:02d}',
                    'source_txt_ref':refs[2+rung],'source_pdf_ref':refs[5],
                    'source_txt_lines':[row['txt_header_line'],row['txt_header_line']+11],
                    'source_pdf_page':3,'source_rung':rung+1,
                    'source_contact':j+1,'source_degree':note['degree'],
                    'source_pitch_spelling':note['source_tone'],
                    'source_string_label':note['string'],'source_string':event['string'],
                    'source_fret':note['fret'],'source_finger':note['finger'],
                    'source_midi':note['midi'],'repeated_high_root_at_turn':j in (7,8),
                    'timing_txt_ref':refs[0],'timing_pdf_ref':refs[1],
                    'nominal_slot_q':list(q.as_integer_ratio()),
                    'one_beat_release_after_cell':j==15 and rung<cidx,
                    'frame_move_frets':1 if j==15 and rung<cidx else 0}
        variants=[]
        for vid,start in zip(vids,('D','U')):
            expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
            if changed_strokes is not None and vid in changed_strokes:
                expected=changed_strokes[vid]
            strokes[vid]=expected
            variants.append({'id':vid,'label':f'{local.lower()}-{start}-start',
                             'role':'notation_practice','route':'first_neighboring_minor_rungs_paused_learning',
                             'source_refs':refs,'event_ids':list(sidecar),
                             'pick_start':start,'pick_start_origin':'source_authored',
                             'grouping':{'kind':'source_event_time','notes_per_beat':None,
                                         'beat_unit_q':None,'marking_factor':[1,1],
                                         'source_label':'Original Level21 even eighth notes and one-beat pressure-release gap between complete selected cells'},
                             'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]})
        record={'id':item,'module_id':module,'workbook_id':WORKBOOK,
                'content_revision':1,'lineage':{'kind':'new'},'kind':'notation',
                'legacy_level':21,'status':'converted_candidate','runtime_eligible':False,
                'title':title,'source_refs':refs,'authored_text_refs':refs,
                'events':events,'variants':variants,'resource_requirements':[],
                'rubric':None,'control_scope':{'extent':'complete_selected_case',
                    'local_case':local,'source_event_count':count,'basis_refs':refs,
                    'whole_workbook_complete':False,
                    'unresolved':['Remaining rungs and complete 25-cell route outside packet.',
                                  'Runtime admission and whole Level21 Pending.']},
                'context':{'local_code':local,'route':'→'.join(KEYS[:cidx+1])+' natural minor paused-learning cells',
                           'position':'low-E root fret5'+(' through fret'+str(5+cidx) if cidx else ''),
                           'pick_start_variants':['D','U'],
                           'pick_start':'source-authored continuous D/U or U/D without restart at high-root turn or shift',
                           'tuning_open_midi':[40,45,50,55,59,64],
                           'capo':0,'source_tempo_rules_ref':refs[0]},
                'timing':{'status':'source_defined','unit':'quarter','meter':None,
                          'basis':'Original Level21 even eighth contacts q1/2; one quarter-beat released-pressure gap only between completed selected 16-note cells; no fixed BPM.'},
                'ambiguities':['Later connected route, clean-round-trip adaptation and mastery outside selected learning mode.',
                               'Capo zero represents untransposed standard tuning, not an authored capo instruction.'],
                'normalization':[{'kind':'representation_metadata','basis':refs[0],
                                  'text':'Selected complete 16-contact cells; repeated octave root and continuous alternate picking retained.'},
                                 {'kind':'representation_metadata','basis':refs[0],
                                  'text':'Learn guidance: compare A major A B C# D E F# G# A with A natural minor A B C D E F G A before neighboring rungs; identify lowered 3rd, 6th, 7th.'}]}
        records.append(record)
        entities.extend([{'id':module,'kind':'module','label':title,'parent':WORKBOOK},
                         {'id':item,'kind':'item','label':title,'parent':module},
                         *({'id':v['id'],'kind':'variant','label':v['label'],'parent':item} for v in variants)])
        allocations[item]={'legacy_level':21,
                           'occurrences':{s['source_local_event_key']:eid for eid,s in sidecar.items()},
                           'variants':{v['label']:v['id'] for v in variants}}
        provenance.update(sidecar)
    package={k:copy.deepcopy(v) for k,v in base_package.items()
             if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level021-first-three-cases-build-only.1',
                   records=records,sources=sources)
    registry={'identity_version':base_registry['identity_version'],
              'rules':base_registry['rules'],'entities':entities}
    identity_baseline={'identity_version':registry['identity_version'],
                       'rules':registry['rules'],'entities':[entities[0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P86 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1','authority':'P86 provisional nonadmitted; P02 canonical scan required',
                'records':allocations}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources',
                          'authority_artifacts','workbook_catalog')}
    profile['degree_roots']={f'{key}-natural-minor':{
        'basis':f'Original Level21 {key} natural-minor Rung source card; pitch class only',
        'root_pitch_class':pc} for key,pc in zip(KEYS,ROOT_PCS)}
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
    need(set(event_sources)==set(provenance)=={e['event_id'] for r in records for e in r['events']},
         'EVENT_PROVENANCE_COVERAGE')
    summary={'status':'source_interpreted_nonadmitted_reference','record_count':3,
             'event_count':96,'variant_count':6,'projected_membership_target':192,
             'item_ids':list(ITEMS),'module_ids':list(MODULES),
             'variant_ids':[v for pair in VARIANTS for v in pair],
             'runtime_eligible':False,'admitted':False,'whole_workbook_complete':False,
             'source_txt_sha256':PINS[TXT],'source_pdf_sha256':PINS[PDF],
             'p10_parity_sha256':PINS[P10],'p12_parity_sha256':PINS[P12],
             'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
             'case_end_q':[[8,1],[17,1],[26,1]],
             'interpretation':'A16, A→Bb32, A→Bb→B48 natural-minor paused-learning stages, even eighth q1/2, one-beat internal gaps, both continuous pick starts, no fixed BPM/mastery/credit.'}
    return {'package.json':package,'identity-registry.json':registry,
            'expected-profile.json':profile,'candidate-allocation.json':allocation,
            'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,
            'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':refs[:1]+refs[2:5],
                                      'source_pdf_refs':[refs[1],refs[5],refs[6]],
                                      'events':provenance,'variant_strokes':strokes,
                                      'stroke_basis':'Original Level21 continuous D/U or U/D through repeated high roots and one-fret shifts.'},
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
