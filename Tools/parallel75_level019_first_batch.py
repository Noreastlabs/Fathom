#!/usr/bin/env python3
"""P75: original-source-bound, nonadmitted Level19 three-case native reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader
import curriculum_level019_whole_candidate as p09

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-75/controlled-open-level019-first-batch-r01')
TXT, PDF = p09.TXT_REL, p09.PDF_REL
P09 = Path('Build/parallel-09/2.3.1.1.1-level019-whole-r01/candidate-01.json')
P12 = Path('Build/parallel-12/level019-schema1-unallocated-r01/field-proposal.json')
BASE = Path('Content/controls/curriculum-v1')
PINS = {TXT:p09.TXT_SHA256, PDF:p09.PDF_SHA256,
        P09:'c7006360d4de080bafc488cd11098d5b1c464beb88c8a6a89c1f1d02422ea91a',
        P12:'212e85a79e25fda17ab1776b62ecb3043bbf77a1041bb7a3e04a241ca0eb091c',
        BASE/'package.json':'766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255',
        BASE/'identity-registry.json':'5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5',
        BASE/'expected-profile.json':'21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a'}
NATIVE = Path('Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate')
NATIVE_SHA = 'a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714'
ITEMS = tuple(f'fg:item:00975{i}' for i in range(3))
MODULES = tuple(f'fg:module:00975{i}' for i in range(3))
VARIANTS = tuple((f'fg:variant:00975{i*2}',f'fg:variant:00975{i*2+1}') for i in range(3))
WORKBOOK = 'fg:workbook:000019'
STRING = {'E':1,'A':2,'D':3,'G':4,'B':5,'e':6}
OPEN_MIDI = {'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
KEYS = ('A','Bb','B')
ROOT_PCS = {'A-major':9,'Bb-major':10,'B-major':11}
NAMES = ('package.json','identity-registry.json','expected-profile.json',
         'candidate-allocation.json','identity-baseline.json','allocation-baseline.json',
         'lineage-baseline.json','source-provenance.json','summary.json')

class CandidateError(ValueError):
    pass

def need(ok: bool, code: str):
    if not ok:
        raise CandidateError(code)

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads((ROOT/path).read_bytes())

def pin():
    top = Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip())
    need(top.resolve()==ROOT.resolve(),'ROOT_DRIFT')
    for path,digest in PINS.items():
        need(sha((ROOT/path).read_bytes())==digest,'PIN_DRIFT:'+str(path))
    need(sha((ROOT/NATIVE).read_bytes())==NATIVE_SHA,'NATIVE_DRIFT')

def identity_scan():
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):00975[0-2]',
         '-e',r'fg:variant:00975[0-5]','--glob','*.json','--glob','*.hpp',
         '--glob','*.cpp','Content','Source','Build']
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    return {'status':'PASS','scope':['Content','Source','Build'],'method':cmd,
            'wanted':[ *ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)],
            'matches':hits,'canonical_reservation':False,
            'classification':'P75 provisional reference IDs only; P02 must rescan and allocate serially'}

def ref(path,format,text,**where):
    return {'path':str(path),'format':format,'sha256':PINS[path],**where,
            'text':text,'text_sha256':sha(text.encode())}

def source_facts():
    pin()
    whole=p09.build_candidate()
    need(whole==read(P09),'P09_REBUILD_DRIFT')
    rows=whole['records'][:3]
    proposal=read(P12)['records'][:3]
    need([r['source_local_key'] for r in rows]==['L19-rung01','L19-rung02','L19-rung03'],
         'SOURCE_CASE_SCOPE')
    need([r['source_local_key'] for r in proposal]==[r['source_local_key'] for r in rows],
         'P12_CASE_SCOPE')
    for row,prior in zip(rows,proposal):
        actual=[(STRING[n['string']],n['fret'],int(n['finger_digit']),n['degree'],
                 OPEN_MIDI[n['string']]+n['fret'])
                for triad in row['triads'] for n in triad['notes']]
        fields=prior['schema1_fields']['events']
        expected=[(e['string'],e['fret'],e['finger'],
                   next(iter(e['degree_contexts'].values()))['ordinal'],e['midi']) for e in fields]
        need(len(actual)==len(expected)==66 and actual==expected,'P12_CONTACT_PARITY')
        need([(t['roman'],t['quality'],t['chord_name']) for t in row['triads']]==
             [(t['roman'],t['quality'],t['chord_name']) for t in prior['triad_memberships']],
             'P12_HARMONIC_PARITY')
    lines=(ROOT/TXT).read_text().splitlines()
    pages=[(p.extract_text() or '').splitlines() for p in PdfReader(str(ROOT/PDF)).pages]
    need(len(pages)==10,'PDF_PAGE_COUNT')
    for rung,row in enumerate(rows):
        txt=lines[70+28*rung:95+28*rung]
        pdf=pages[2 if rung<2 else 3]
        start=5 if rung in (0,2) else 32
        need(txt[0]==row['printed_txt']['heading'] and pdf[start]==row['printed_pdf']['heading'],
             'SOURCE_CARD_HEADING')
        need(txt[5:14]==pdf[start+6:start+15] and txt[15:24]==pdf[start+16:start+25],
             'PDF_HRM_DEG_FNG_TAB_PARITY')
    guide='\n'.join(lines[:70])
    need('one triad per beat as eighth-note triplets' in guide,'TRIPLET_PULSE_MISSING')
    need('one-beat pause only after each complete cell' in guide,'PAUSE_MISSING')
    need('Triad pulse: D-U-D / U-D-U; do not reset' in pages[2],
         'PDF_PICK_MISSING')
    need('One triad per beat while learning' in pages[3][3],
         'PDF_PULSE_MISSING')
    need('A Bm C#m D E F#m G#dim' in '\n'.join(pages[1]) and
         'Bb Cm Dm Eb F Gm Adim' in '\n'.join(pages[1]) and
         'B C#m D#m E F# G#m A#dim' in '\n'.join(pages[1]),'PDF_HARMONY_MAP')
    return lines,pages,rows,proposal

def derive(*,changed_onsets=None,changed_durations=None,changed_strokes=None,
           force_eligible=False,forced_bpm=None,grouping='source_event_time'):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(grouping in ('source_event_time','even_subdivision'),'GROUPING_INVALID')
    audit=read(OUT/'identity-audit.json')
    need(audit['status']=='PASS' and not audit['matches'] and
         set(audit['wanted'])=={*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)},
         'IDENTITY_AUDIT_DRIFT')
    lines,pages,rows,proposal=source_facts()
    refs=['L19-TXT-GUIDANCE','L19-PDF-GUIDANCE','L19-TXT-RUNG01','L19-TXT-RUNG02',
          'L19-TXT-RUNG03','L19-PDF-CARDS01-02','L19-PDF-CARD03','L19-PDF-ROUTE']
    sources={refs[0]:ref(TXT,'txt','\n'.join(lines[:70]),first_line=1,last_line=70),
             refs[1]:ref(PDF,'pdf','\n'.join(pages[0]),page=1),
             refs[5]:ref(PDF,'pdf','\n'.join(pages[2]),page=3),
             refs[6]:ref(PDF,'pdf','\n'.join(pages[3]),page=4),
             refs[7]:ref(PDF,'pdf','\n'.join(pages[1]),page=2)}
    for rung in range(3):
        sources[refs[2+rung]]=ref(TXT,'txt','\n'.join(lines[70+28*rung:95+28*rung]),
                                  first_line=71+28*rung,last_line=95+28*rung)
    base_package,base_registry,base_profile=(read(BASE/name) for name in
        ('package.json','identity-registry.json','expected-profile.json'))
    entities=[base_registry['entities'][0],
              {'id':WORKBOOK,'kind':'workbook','label':'Legacy Level19',
               'parent':'fg:course:000001'}]
    records=[];provenance={};event_sources={};allocations={};strokes={}
    for case_index,(item,module,vids) in enumerate(zip(ITEMS,MODULES,VARIANTS)):
        count=66*(case_index+1)
        route=KEYS[:case_index+1]
        local=('L019-R01:A:TRIADS','L019-R01-R02:A_BB:TRIADS_ONE_BEAT_PAUSE',
               'L019-R01-R03:A_BB_B:TRIADS_ONE_BEAT_PAUSES')[case_index]
        title=('Level 19 Rung01 A-major 66-contact broken-triad cell',
               'Level 19 A-major to Bb-major 132-contact neighboring triad cells',
               'Level 19 A-major through B-major 198-contact neighboring triad cells')[case_index]
        events=[];sidecar={}
        for rung in range(case_index+1):
            row=rows[rung]
            notes=[n for triad in row['triads'] for n in triad['notes']]
            prior=proposal[rung]['schema1_fields']['events']
            for j,(note,field) in enumerate(zip(notes,prior)):
                i=rung*66+j
                eid=f'{item}:event:{i+1:04d}'
                q=Fraction(rung*23)+Fraction(j,3)
                onset=list(q.as_integer_ratio())
                duration=[1,3]
                if changed_onsets is not None and eid in changed_onsets:onset=changed_onsets[eid]
                if changed_durations is not None and eid in changed_durations:duration=changed_durations[eid]
                triad=row['triads'][j//3]
                key=KEYS[rung]+'-major'
                events.append({'event_id':eid,'kind':'note','string':STRING[note['string']],
                               'fret':note['fret'],'finger':int(note['finger_digit']),
                               'midi':field['midi'],'spelling':field['spelling'],
                               'attack':'picked','onset_q':onset,'duration_q':duration,
                               'tie_from':None,'degree_contexts':{key:{'ordinal':note['degree'],
                                   'alteration':0,'source_label':str(note['degree'])}}})
                event_sources[eid]=refs[2+rung]
                sidecar[eid]={'source_local_event_key':f'{local}:R{rung+1:02d}:{j+1:03d}',
                              'source_txt_ref':refs[2+rung],
                              'source_pdf_ref':refs[5 if rung<2 else 6],
                              'source_txt_line_span':[71+28*rung,95+28*rung],
                              'source_pdf_page':3 if rung<2 else 4,
                              'source_rung':rung+1,'source_triad':j//3+1,
                              'source_triad_slot':j%3+1,
                              'triad_direction':'ascending' if j<33 else 'descending',
                              'source_note_role':note['role'],
                              'harmonic_root_degree':triad['harmonic_root_degree'],
                              'harmonic_function':triad['roman'],
                              'triad_quality':triad['quality'],
                              'chord_name':triad['chord_name'],
                              'string_label':note['string'],'string':STRING[note['string']],
                              'fret':note['fret'],'finger_digit':int(note['finger_digit']),
                              'degree':note['degree'],'spelling':field['spelling'],
                              'midi':field['midi'],
                              'repeated_high_root_at_turn':j in (32,33),
                              'timing_txt_ref':refs[0],'timing_pdf_ref':refs[1],
                              'nominal_slot_q':list(q.as_integer_ratio()),
                              'one_beat_release_after_cell':j==65 and rung<case_index,
                              'frame_move_frets':1 if j==65 and rung<case_index else 0}
        provenance.update(sidecar)
        variants=[]
        for variant,start in zip(vids,('D','U')):
            expected=[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
            if changed_strokes is not None and variant in changed_strokes:expected=changed_strokes[variant]
            strokes[variant]=expected
            variants.append({'id':variant,'label':f'{local.lower()}-{start}-start',
                             'role':'notation_practice','route':
                                 ('standalone_rung01_complete_cell','rung01_to_rung02_neighbor_training',
                                  'rung01_to_rung03_neighbor_training')[case_index],
                             'source_refs':refs,'event_ids':list(sidecar),
                             'pick_start':start,'pick_start_origin':'source_authored',
                             'grouping':{'kind':grouping,
                                         'notes_per_beat':None if grouping=='source_event_time' else 3,
                                         'beat_unit_q':None if grouping=='source_event_time' else [1,1],
                                         'marking_factor':[1,1],
                                         'source_label':'Original Level19 one broken triad per beat as eighth-note triplets; explicit one-beat intercell gaps'},
                             'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]})
        record={'id':item,'module_id':module,'workbook_id':WORKBOOK,
                'content_revision':1,'lineage':{'kind':'new'},'kind':'notation',
                'legacy_level':19,'status':'converted_candidate','runtime_eligible':False,
                'title':title,'source_refs':refs,'authored_text_refs':refs,
                'events':events,'variants':variants,'resource_requirements':[],
                'rubric':None,'control_scope':{'extent':'complete_selected_case',
                   'local_case':local,'source_event_count':count,'basis_refs':refs,
                   'whole_workbook_complete':False,
                   'unresolved':['Rungs beyond selected cases and complete 25-cell route remain outside packet.',
                                 'Runtime admission and whole Level19 remain Pending.']},
                'context':{'local_code':local,
                           'route':'→'.join(route)+' major connected broken-triad cells',
                           'position':'low-E root fret5'+(' to fret'+str(5+case_index) if case_index else ''),
                           'pick_start_variants':['D','U'],
                           'pick_start':'source-authored continuous D/U or U/D without reset at triads, strings, high-root turn or relocation',
                           'tuning_open_midi':[40,45,50,55,59,64],
                           'capo':0,'source_tempo_rules_ref':refs[0]},
                'timing':{'status':'source_defined','unit':'quarter','meter':None,
                          'basis':'Original TXT learning pulse: one sequential broken triad per quarter beat as eighth-note triplets; one quarter-beat released-pressure gap only between completed neighbor cells. No fixed BPM or measured sustain.'},
                'ambiguities':['Performance sextuplet pulse and later tempo increments are outside selected learning pulse; no fixed BPM, performed quality or assessed mastery.',
                               'Capo zero is an untransposed standard-tuning representation, not a capo instruction.'],
                'normalization':[{'kind':'representation_metadata','basis':refs[0],
                                  'text':'Selected complete 66-contact cells with repeated high root, continuous alternate picking and source-defined one-beat intercell gaps.'}]}
        records.append(record)
        entities.extend([{'id':module,'kind':'module','label':title,'parent':WORKBOOK},
                         {'id':item,'kind':'item','label':title,'parent':module},
                         *({'id':v['id'],'kind':'variant','label':v['label'],'parent':item} for v in variants)])
        allocations[item]={'legacy_level':19,
                           'occurrences':{s['source_local_event_key']:eid for eid,s in sidecar.items()},
                           'variants':{v['label']:v['id'] for v in variants}}
    package={k:copy.deepcopy(v) for k,v in base_package.items()
             if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level019-first-three-cases-build-only.1',
                   records=records,sources=sources)
    registry={'identity_version':base_registry['identity_version'],
              'rules':base_registry['rules'],'entities':entities}
    identity_baseline={'identity_version':registry['identity_version'],
                       'rules':registry['rules'],'entities':[entities[0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P75 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1',
                'authority':'P75 provisional nonadmitted; P02 canonical serial scan required',
                'records':allocations}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources',
                          'authority_artifacts','workbook_catalog')}
    profile['degree_roots']={key:{'basis':'Level19 original Rung source card; pitch class only',
                                  'root_pitch_class':pc} for key,pc in ROOT_PCS.items()}
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
             'event_count':396,'variant_count':6,'projected_membership_target':792,
             'item_ids':list(ITEMS),'module_ids':list(MODULES),
             'variant_ids':[v for pair in VARIANTS for v in pair],
             'runtime_eligible':False,'admitted':False,'whole_workbook_complete':False,
             'source_txt_sha256':PINS[TXT],'source_pdf_sha256':PINS[PDF],
             'p09_parity_sha256':PINS[P09],'p12_parity_sha256':PINS[P12],
             'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
             'case_end_q':[[22,1],[45,1],[68,1]],
             'interpretation':'A66, A→Bb132, A→Bb→B198 broken-triad stages; one triad per beat as sequential triplets, one-beat intercell gaps, both continuous pick starts, no fixed BPM/mastery/credit.'}
    return {'package.json':package,'identity-registry.json':registry,
            'expected-profile.json':profile,'candidate-allocation.json':allocation,
            'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,
            'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':refs[:1]+refs[2:5],
                                      'source_pdf_refs':[refs[1],*refs[5:]],
                                      'events':provenance,'variant_strokes':strokes,
                                      'stroke_basis':'Original Level19 continuous D/U or U/D through triads, strings, high-root turn and shifts.'},
            'summary.json':summary}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=('audit','build','verify'))
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args()
    dest=(ROOT/args.out).resolve();allowed=(ROOT/OUT).resolve()
    need(dest==allowed or allowed in dest.parents,'OUTPUT_SCOPE')
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
