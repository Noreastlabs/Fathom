#!/usr/bin/env python3
"""P59 deterministic, source-bound, nonadmitted Level16 A and A→Bb reference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader
import curriculum_level016_whole_candidate as p11

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-59/controlled-open-level016-first-batch-r01')
TXT = Path(p11.TXT[0]); PDF = Path(p11.PDF[0])
P11 = Path('Build/parallel-11/2.3.1.1.1-level016-whole-r01/candidate-final-a.json')
P12 = Path('Build/parallel-12/level016-schema1-unallocated-r01/field-proposal.json')
BASE = Path('Content/controls/curriculum-v1')
PINS = {TXT:p11.TXT[1], PDF:p11.PDF[1], P11:'2fe5f23a73a13b742192588b0d2d6a6336c42ed4e1722403393de79f2bd5289a',
        P12:'c00d3cc643227a0596f7385c58f0e29008daf4450566552bc7433298157f49cf',
        BASE/'package.json':'766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255',
        BASE/'identity-registry.json':'5d265859e1e8a5a530a0e53d88b019a1c920f3bba6cccb4ef0fef2f7640007e5',
        BASE/'expected-profile.json':'21009e3596f325a4b9f73c9532b71cd361703e0f682b40088ff58bff7ba57c8a'}
ITEMS = ('fg:item:001158','fg:item:001159')
MODULES = ('fg:module:001158','fg:module:001159')
VARIANTS = (('fg:variant:007438','fg:variant:007439'),('fg:variant:007440','fg:variant:007441'))
WORKBOOK = 'fg:workbook:000016'
STRING = {'E':1,'A':2,'D':3}
OPEN = {'E':40,'A':45,'D':50}
NAMES = ('package.json','identity-registry.json','expected-profile.json','candidate-allocation.json',
         'identity-baseline.json','allocation-baseline.json','lineage-baseline.json','source-provenance.json','summary.json')

class CandidateError(ValueError): pass
def need(ok, code):
    if not ok: raise CandidateError(code)
def encode(obj): return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',',':'))+'\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads((ROOT/path).read_bytes())
def ref(path, fmt, value, **where):
    return {'path':str(path),'format':fmt,'sha256':PINS[path],**where,
            'text':value,'text_sha256':sha(value.encode())}
def pin():
    need(ROOT.resolve()==Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip()).resolve(), 'ROOT_DRIFT')
    for path,digest in PINS.items(): need(sha((ROOT/path).read_bytes())==digest,'PIN_DRIFT:'+str(path))
def identity_scan():
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):00115[89]',
         '-e',r'fg:variant:0074(?:38|39|40|41)','--glob','*.json','--glob','*.cpp','--glob','*.hpp',
         'Content','Source','Build']
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    wanted=[*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)]
    return {'status':'PASS','scope':['Content','Source','Build'],'method':cmd,
            'wanted':wanted,'matches':hits,'canonical_reservation':False,
            'classification':'P59 provisional only; P02 must re-audit after Level15'}
def source_facts():
    pin()
    whole=p11.build(ROOT)
    need(whole==read(P11),'P11_REBUILD_DRIFT')
    rows=whole['records'][:2]
    need([r['source_local_key'] for r in rows]==['L16-rung01','L16-rung02'],'SOURCE_CASE_SCOPE')
    proposal=read(P12)
    need([r['source_local_key'] for r in proposal['records'][:2]]==['L16-rung01','L16-rung02'],'P12_SCOPE')
    for row, prior in zip(rows,proposal['records'][:2]):
        actual=[(n['string'],n['fret'],n['finger_digit'],n['degree'],n['tone']) for g in row['groups'] for n in g['notes']]
        fields=prior['schema1_fields']['events']
        expected=[(next(k for k,v in STRING.items() if v==e['string']),e['fret'],e['finger'],
                   next(iter(e['degree_contexts'].values()))['ordinal'],e['spelling']) for e in fields]
        need(len(actual)==len(expected)==40 and actual==expected,'P12_CONTACT_PARITY')
    lines=(ROOT/TXT).read_text().splitlines()
    pages=[(p.extract_text() or '').splitlines() for p in PdfReader(str(ROOT/PDF)).pages]
    need(len(pages)==7 and pages[0][19:27]==rows[0]['raw_txt_card'][3:11], 'PDF_WORKED_CARD')
    need(pages[2][7:15]==rows[0]['raw_txt_card'][3:11] and
         pages[2][21:29]==rows[1]['raw_txt_card'][3:11],'PDF_CARD_PARITY')
    rule='\n'.join(lines[:60]); pdf_rule='\n'.join(pages[0])
    for phrase in ('one four-note group per beat','pause one beat after each','Never restart the pick cycle',
                   'Because 40 is even','roughly 75 percent'):
        need(phrase in rule,'TXT_RULE:'+phrase)
    for phrase in ('one four-note group per','pause one beat','downstroke start','upstroke start'):
        need(phrase in pdf_rule,'PDF_RULE:'+phrase)
    return lines,pages,rows
def derive(*,changed_contacts=None,changed_onsets=None,changed_durations=None,
           changed_strokes=None,changed_route=None,forced_bpm=None,force_eligible=False,
           reserved_item=ITEMS[0]):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(reserved_item==ITEMS[0],'FOREIGN_ID')
    audit=read(OUT/'identity-audit.json')
    need(audit['status']=='PASS' and not audit['matches'] and
         set(audit['wanted'])=={*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)},
         'IDENTITY_AUDIT_DRIFT')
    lines,pages,rows=source_facts()
    cells=[[n for g in row['groups'] for n in g['notes']] for row in rows]
    contacts=[cells[0],cells[0]+cells[1]]
    need(changed_contacts is None or changed_contacts==contacts,'CANDIDATE_CONTACT_DRIFT')
    routes=[['A'],['A','Bb']]
    need(changed_route is None or changed_route==routes,'CANDIDATE_ROUTE_DRIFT')
    onsets=[[[i,4] if i%4 else [i//4,1] for i in range(40)],
            [[i,4] if i%4 else [i//4,1] for i in range(40)]+
            [list((Fraction(11)+Fraction(i,4)).as_integer_ratio()) for i in range(40)]]
    onsets=[[list(Fraction(n,d).as_integer_ratio()) for n,d in case] for case in onsets]
    durations=[[[1,4]]*40,[[1,4]]*80]
    need(changed_onsets is None or changed_onsets==onsets,'CANDIDATE_TIMING_DRIFT')
    need(changed_durations is None or changed_durations==durations,'CANDIDATE_DURATION_DRIFT')
    strokes={v:[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(count)]
             for pair,count in zip(VARIANTS,(40,80)) for v,start in zip(pair,('D','U'))}
    need(changed_strokes is None or changed_strokes==strokes,'CANDIDATE_STROKE_DRIFT')
    refs=('L16-TXT-GUIDANCE','L16-PDF-GUIDANCE','L16-TXT-RUNG01','L16-TXT-RUNG02',
          'L16-PDF-CARDS','L16-PDF-ROUTE')
    sources={refs[0]:ref(TXT,'txt','\n'.join(lines[:60]),first_line=1,last_line=60),
             refs[1]:ref(PDF,'pdf','\n'.join(pages[0]),page=1),
             refs[2]:ref(TXT,'txt','\n'.join(rows[0]['raw_txt_card']),first_line=62,last_line=73),
             refs[3]:ref(TXT,'txt','\n'.join(rows[1]['raw_txt_card']),first_line=76,last_line=87),
             refs[4]:ref(PDF,'pdf','\n'.join(pages[2][3:31]),page=3),
             refs[5]:ref(PDF,'pdf','\n'.join(pages[1]),page=2)}
    records=[]; provenance={}; event_sources={}; allocations={}
    entities=[{'id':WORKBOOK,'kind':'workbook','label':'Legacy Level16','parent':'fg:course:000001'}]
    for case_idx,(item,module,vids,notes) in enumerate(zip(ITEMS,MODULES,VARIANTS,contacts)):
        local=('L016-R01:A:FOUR_NOTE','L016-R01-R02:A_BB:FOUR_NOTE_ONE_BEAT_PAUSE')[case_idx]
        title=('Level 16 Rung01 A-major complete 40-note rolling-four cell',
               'Level 16 Rung01 A-major to Rung02 Bb-major rolling-four neighbor pair')[case_idx]
        events=[]; sidecar={}
        for i,n in enumerate(notes):
            rung=0 if i<40 else 1; key=('A-major','Bb-major')[rung]
            event_id=f'{item}:event:{i+1:04d}'; source=refs[2+rung]
            events.append({'event_id':event_id,'kind':'note','string':STRING[n['string']],
                           'fret':n['fret'],'finger':n['finger_digit'],'midi':OPEN[n['string']]+n['fret'],
                           'spelling':n['tone'],'attack':'picked','onset_q':onsets[case_idx][i],
                           'duration_q':durations[case_idx][i],'tie_from':None,
                           'degree_contexts':{key:{'ordinal':n['degree'],'alteration':0,
                                                   'source_label':str(n['degree'])}}})
            event_sources[event_id]=source
            sidecar[event_id]={'source_local_event_key':f'{local}:R{rung+1:02d}:{n["ordinal_in_cell"]:02d}',
                               'source_txt_ref':source,'source_pdf_ref':refs[4],
                               'source_txt_line_span':[62+14*rung,73+14*rung],
                               'source_pdf_page':3,'source_rung':rung+1,
                               'source_group':(i%40)//4+1,'source_group_slot':(i%4)+1,
                               'string_label':n['string'],'string':STRING[n['string']],
                               'fret':n['fret'],'finger_digit':n['finger_digit'],
                               'degree':n['degree'],'spelling':n['tone'],
                               'midi':OPEN[n['string']]+n['fret'],
                               'repeated_octave_root_at_turn':i%40 in (19,20),
                               'timing_txt_ref':refs[0],'timing_pdf_ref':refs[1],
                               'nominal_slot_q':onsets[case_idx][i],
                               'one_beat_release_after_first_cell':case_idx==1 and i==39,
                               'frame_move_frets':1 if case_idx==1 and i==39 else 0}
        provenance.update(sidecar)
        variants=[{'id':v,'label':f'{local.lower()}-{start}-start','role':'notation_practice',
                   'route':'standalone_rung01_complete_cell' if case_idx==0 else 'rung01_to_rung02_neighbor_training',
                   'source_refs':list(refs),'event_ids':list(sidecar),
                   'pick_start':start,'pick_start_origin':'source_authored',
                   'grouping':{'kind':'even_subdivision','notes_per_beat':4,'beat_unit_q':[1,1],
                               'marking_factor':[1,1],
                               'source_label':'Original Level16 sixteenth notes: one four-note group per beat'},
                   'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]}
                  for v,start in zip(vids,('D','U'))]
        record={'id':item,'module_id':module,'workbook_id':WORKBOOK,'content_revision':1,
                'lineage':{'kind':'new'},'kind':'notation','legacy_level':16,
                'status':'converted_candidate','runtime_eligible':False,'title':title,
                'source_refs':list(refs),'authored_text_refs':list(refs),'events':events,
                'variants':variants,'resource_requirements':[],'rubric':None,
                'control_scope':{'extent':'complete_selected_case','local_case':local,
                                 'source_event_count':len(events),'basis_refs':list(refs),
                                 'whole_workbook_complete':False,
                                 'unresolved':['Rungs03-13 and complete 25-cell neck route outside this selected case.',
                                               'Runtime admission and whole Level16 remain Pending.']},
                'context':{'local_code':local,'route':'A-major first complete rolling cell' if case_idx==0 else
                           'A-major to Bb-major first two neighboring cells',
                           'position':'low-E root fret5' if case_idx==0 else 'low-E root fret5 to fret6',
                           'pick_start_variants':['D','U'],
                           'pick_start':'source-authored strict D/U or U/D without reset at groups, strings, turn or shift',
                           'tuning_open_midi':[40,45,50,55,59,64],'capo':0,
                           'source_tempo_rules_ref':refs[0]},
                'timing':{'status':'source_defined','unit':'quarter','meter':None,
                          'basis':'Original TXT/PDF sixteenth notes: one four-note group per quarter beat. Neighbor stage inserts one quarter-beat released-pressure gap after A cell. No fixed BPM or measured sustain.'},
                'ambiguities':['Roughly 75 percent of clean Level15 is relative guidance, not a fixed authored BPM or observed mastery.',
                               'Capo zero is untransposed standard-tuning representation, not a capo instruction.'],
                'normalization':[{'kind':'representation_metadata','basis':refs[0],
                                  'text':'Complete 40-contact A cell or 80-contact A-to-Bb neighboring stage; repeated high root, continuous alternate picking, one-beat pause only between paired cells.'}]}
        records.append(record)
        entities.extend([{'id':module,'kind':'module','label':title,'parent':WORKBOOK},
                         {'id':item,'kind':'item','label':title,'parent':module},
                         *({'id':v['id'],'kind':'variant','label':v['label'],'parent':item} for v in variants)])
        allocations[item]={'legacy_level':16,
                           'occurrences':{s['source_local_event_key']:eid for eid,s in sidecar.items()},
                           'variants':{v['label']:v['id'] for v in variants}}
    base_package,base_registry,base_profile=(read(BASE/name) for name in
                                               ('package.json','identity-registry.json','expected-profile.json'))
    package={k:copy.deepcopy(v) for k,v in base_package.items() if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level016-first-two-cases-build-only.1',
                   records=records,sources=sources)
    registry={'identity_version':base_registry['identity_version'],'rules':base_registry['rules'],
              'entities':[base_registry['entities'][0],*entities]}
    identity_baseline={'identity_version':registry['identity_version'],'rules':registry['rules'],
                       'entities':[registry['entities'][0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P59 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1','authority':'P59 provisional nonadmitted; P02 canonical re-audit required',
                'records':allocations}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources','authority_artifacts','workbook_catalog')}
    profile['degree_roots']={'A-major':{'basis':'Level16 original Rung01 source card; pitch class only','root_pitch_class':9},
                             'Bb-major':{'basis':'Level16 original Rung02 source card; pitch class only','root_pitch_class':10}}
    profile.update(reference_package=package,reference_registry=registry,event_sources=event_sources)
    profile['authority_artifacts']=[copy.deepcopy(a) for a in base_profile['authority_artifacts']
                                     if a['role'] in ('source_manifest','source_acceptance','current_schema_freeze')]
    for role,name,value in (('identity_baseline','identity-baseline.json',identity_baseline),
                            ('allocation_baseline','allocation-baseline.json',allocation_baseline),
                            ('lineage_baseline','lineage-baseline.json',lineage_baseline),
                            ('candidate_identity_allocation','candidate-allocation.json',allocation)):
        profile['authority_artifacts'].append({'path':str(OUT/name),'role':role,'sha256':sha(encode(value))})
    need(set(event_sources)==set(provenance)=={e['event_id'] for r in records for e in r['events']},
         'EVENT_PROVENANCE_COVERAGE')
    summary={'status':'source_interpreted_nonadmitted_reference','item_ids':list(ITEMS),
             'module_ids':list(MODULES),'variant_ids':[v for pair in VARIANTS for v in pair],
             'record_count':2,'event_count':120,'variant_count':4,
             'runtime_eligible':False,'admitted':False,'whole_workbook_complete':False,
             'source_txt_sha256':PINS[TXT],'source_pdf_sha256':PINS[PDF],
             'p11_parity_sha256':PINS[P11],'p12_parity_sha256':PINS[P12],
             'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
             'first_case_end_q':[10,1],'second_case_end_q':[21,1],
             'interpretation':'A 40-contact cell and A-to-Bb 80-contact neighbor stage, sixteenth groups, one-beat inter-cell pause, D/U starts, no fixed BPM/mastery/credit.'}
    return {'package.json':package,'identity-registry.json':registry,'expected-profile.json':profile,
            'candidate-allocation.json':allocation,'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':[refs[0],refs[2],refs[3]],
                                      'source_pdf_refs':[refs[1],refs[4],refs[5]],
                                      'events':provenance,'variant_strokes':strokes,
                                      'stroke_basis':'Original Level16 continuous alternate D/U or U/D through four-note groups, strings, turn and one-fret relocation.'},
            'summary.json':summary}
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=('audit','build','verify'))
    parser.add_argument('--out',type=Path,default=OUT); args=parser.parse_args()
    dest=(ROOT/args.out).resolve(); allowed=(ROOT/OUT).resolve()
    need(dest==allowed or allowed in dest.parents,'OUTPUT_SCOPE')
    if args.command=='audit':
        result=identity_scan(); dest.mkdir(parents=True,exist_ok=True)
        target=dest/'identity-audit.json'; need(not target.exists(),'OUTPUT_EXISTS')
        target.write_bytes(encode(result)); print(json.dumps(result,sort_keys=True)); return
    output=derive()
    if args.command=='build':
        dest.mkdir(parents=True,exist_ok=True)
        need(all(not (dest/name).exists() for name in NAMES),'OUTPUT_EXISTS')
        for name in NAMES: (dest/name).write_bytes(encode(output[name]))
    else:
        for name in NAMES: need((dest/name).read_bytes()==encode(output[name]),'OUTPUT_DRIFT:'+name)
    print(json.dumps(output['summary.json'],sort_keys=True))
if __name__=='__main__': main()
