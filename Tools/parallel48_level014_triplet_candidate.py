#!/usr/bin/env python3
"""Build P48's source-closed, nonadmitted Level14 rolling-triplet reference."""
from __future__ import annotations
import argparse, copy, hashlib, json, re, subprocess
from fractions import Fraction
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-48/controlled-open-level014-triplet-batch-r01')
STEM = 'Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder'
TXT = Path(f'Notes/music/guitar project/TXT version/{STEM}.txt')
PDF = Path(f'Notes/music/guitar project/PDF version/{STEM}.pdf')
P09 = Path('Build/parallel-09/2.3.1.1.1-level014-whole-r01/candidate-01.json')
BASE = Path('Content/controls/curriculum-v1')
TXT_SHA = '301edb98b64daa90a015a3560b8c2219cfab13984d6a8c320765af48f444912b'
PDF_SHA = 'c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19'
P09_SHA = '76f17ced310675c370d19afb8f07bcedac2ab8527410e27e507820a8c543b3b1'
ITEMS = ('fg:item:001155','fg:item:001156')
MODULES = ('fg:module:001155','fg:module:001156')
VARIANTS = (('fg:variant:007432','fg:variant:007433'),('fg:variant:007434','fg:variant:007435'))
WORKBOOK = 'fg:workbook:000014'
NAMES = ('package.json','identity-registry.json','expected-profile.json','candidate-allocation.json',
         'identity-baseline.json','allocation-baseline.json','lineage-baseline.json','source-provenance.json','summary.json')
OPEN_MIDI = {'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
STRING = {'E':1,'A':2,'D':3,'G':4,'B':5,'e':6}
TONES = (('A','B','C#','D','E','F#','G#','A'),('Bb','C','D','Eb','F','G','A','Bb'))
DEGREES = tuple(tuple(range(k,k+3)) for k in range(1,7)) + tuple(tuple(range(k,k-3,-1)) for k in range(8,2,-1))
FINGERS = (2,4,1,2,4,1,3,4)
class CandidateError(ValueError): pass
def need(ok, code):
    if not ok: raise CandidateError(code)
def encode(obj): return (json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads((ROOT/path).read_bytes())
def passage(path,digest,fmt,value,**where):
    return {'path':str(path),'sha256':digest,'format':fmt,**where,'text':value,'text_sha256':sha(value.encode())}
def identity_scan():
    wanted=[*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)]
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):00115[56]',
         '-e',r'fg:variant:00743[2-5]','--glob','*.json','--glob','*.cpp','--glob','*.hpp',
         'Content','Source','Build']
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    need(run.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in run.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    return {'status':'PASS','scope':['Content','Source','Build'],'method':cmd,'wanted':wanted,
            'matches':hits,'canonical_reservation':False,
            'classification':'No live Content/Source/Build identity hit; P02 must re-audit after Level13.'}
def _cells(row,label):
    parts=row.split('|')
    need(len(parts)==14 and parts[0]==label and parts[-1]=='','ROW_SHAPE:'+label)
    out=[]
    for block in parts[1:-1]:
        need(len(block)==9,'GROUP_WIDTH:'+label)
        slots=[]
        for i in (0,3,6):
            token=block[i:i+3]; value=token.rstrip('-')
            need((not value and token=='---') or (value.isdigit() and value+'-'*(3-len(value))==token),'SLOT:'+label)
            slots.append(value or None)
        out.append(slots)
    return out
def _parse_card(block,root,key,first_line):
    need(len(block)==12 and block[0]==f'RUNG {root-4:02d} OF 13 - {key.upper()} MAJOR - ROOT ON LOW E FRET {root} - FRAME {root-1}-{root+2}',
         'TXT_CARD_HEADER')
    need(block[1]=='Scale tones: '+' '.join(TONES[root-5]) and block[2].startswith('36-note cell:'),'TXT_CARD_TONES')
    d=_cells(block[3],'Deg'); f=_cells(block[4],'Fng')
    tab={s:_cells(row,f'{s}  ') for s,row in zip(('e','B','G','D','A','E'),block[5:11])}
    expected_place={1:('E',root),2:('E',root+2),3:('A',root-1),4:('A',root),
                    5:('A',root+2),6:('D',root-1),7:('D',root+1),8:('D',root+2)}
    notes=[]
    for g,group in enumerate(DEGREES):
        for slot,degree in enumerate(group):
            need(d[g][slot]==str(degree) and f[g][slot]==str(FINGERS[degree-1]),'DEGREE_FINGER')
            printed=[(s,int(tab[s][g][slot])) for s in tab if tab[s][g][slot] is not None]
            need(len(printed)==1 and printed[0]==expected_place[degree],'TAB_CONTACT')
            string,fret=printed[0]; spelling=TONES[root-5][degree-1]
            notes.append({'index':g*3+slot+1,'group':g+1,'slot':slot+1,'degree':degree,
                          'finger':FINGERS[degree-1],'string':string,'fret':fret,
                          'midi':OPEN_MIDI[string]+fret,'source_tone':spelling,
                          'phase':'up' if g<6 else 'down','repeated_high_root_at_turn':g*3+slot+1 in (18,19)})
    need(len(notes)==36 and notes[17]['midi']==notes[18]['midi'] and
         notes[0]['string']==notes[-1]['string']=='E' and notes[0]['fret']==notes[-1]['fret']==root,
         'CELL_COMPLETENESS')
    return notes
def source_facts():
    need(sha((ROOT/TXT).read_bytes())==TXT_SHA,'TXT_PIN_DRIFT')
    need(sha((ROOT/PDF).read_bytes())==PDF_SHA,'PDF_PIN_DRIFT')
    need(sha((ROOT/P09).read_bytes())==P09_SHA,'P09_PIN_DRIFT')
    lines=(ROOT/TXT).read_text().splitlines()
    pages=[(p.extract_text() or '').splitlines() for p in PdfReader(str(ROOT/PDF)).pages]
    need(len(pages)==7,'PDF_PAGE_COUNT')
    rule='\n'.join(lines[28:53]); pdf_rule='\n'.join(pages[0]); route='\n'.join(pages[1])
    for phrase in ('one three-note group per beat','pause one beat after each 36-note cell','Repeat with both pick starts',
                   'Because 36 is even, the next key begins','Do not restart the pick cycle'):
        need(phrase in rule,'TXT_TRIPLET_RULE:'+phrase)
    for phrase in ('Hear 12 equal triplets','pause one beat after','downstroke','upstroke'):
        need(phrase in pdf_rule,'PDF_TRIPLET_RULE:'+phrase)
    need('one three-note group per beat' in route and 'never' in route and '36 notes' in route,'PDF_ROUTE_RULE')
    selected=[]
    for idx,(root,key) in enumerate(((5,'A'),(6,'Bb'))):
        start=55+14*idx; block=lines[start:start+12]
        notes=_parse_card(block,root,key,start+1)
        pb=pages[2][3+14*idx:17+14*idx]
        need(pb[:4]==[f'{idx+1:02d}  {key.upper()} MAJOR',f'ROOT E{root}  |  FRAME {root-1}-{root+2}',
                      f'Scale tones: {" ".join(TONES[idx][:-1])} | octave {key}','36-NOTE / 12-TRIPLET CELL'],
             'PDF_CARD_HEADER')
        need(pb[4:12]==block[3:11] and 'D-start and U-start' in pb[13],'TXT_PDF_CONTACT_PARITY')
        selected.append(notes)
    # P09 is secondary contact parity only; original card parsing above supplies facts.
    p09=read(P09)
    need(p09['source']['txt_sha256']==TXT_SHA and p09['source']['pdf_sha256']==PDF_SHA,'P09_SOURCE_DRIFT')
    for idx,notes in enumerate(selected):
        prior=[n for g in p09['records'][idx]['groups'] for n in g['notes']]
        need(len(prior)==36,'P09_NOTE_COUNT')
        for a,b in zip(notes,prior):
            need((a['degree'],a['finger'],a['string'],a['fret'])==
                 (b['degree'],int(b['finger_digit']),b['string'],b['fret']),'P09_CONTACT_PARITY')
    return lines,pages,selected
def derive(*,changed_contacts=None,changed_onsets=None,changed_durations=None,
           changed_strokes=None,changed_route=None,forced_bpm=None,force_eligible=False,
           reserved_item=ITEMS[0]):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(reserved_item==ITEMS[0],'FOREIGN_ID')
    audit_path=ROOT/OUT/'identity-audit.json'
    need(audit_path.exists(),'IDENTITY_AUDIT_MISSING')
    audit=json.loads(audit_path.read_bytes())
    need(audit['status']=='PASS' and not audit['matches'] and
         set(audit['wanted'])==set([*ITEMS,*MODULES,*(v for pair in VARIANTS for v in pair)]),
         'IDENTITY_AUDIT_DRIFT')
    lines,pages,selected=source_facts()
    contacts=[selected[0],selected[0]+selected[1]]
    need(changed_contacts is None or changed_contacts==contacts,'CANDIDATE_CONTACT_DRIFT')
    routes=[['A'],['A','Bb']]
    need(changed_route is None or changed_route==routes,'CANDIDATE_ROUTE_DRIFT')
    onsets=[[list(Fraction(i,3).as_integer_ratio()) for i in range(36)],
            [list(Fraction(i,3).as_integer_ratio()) for i in range(36)]+
            [list((Fraction(13)+Fraction(i,3)).as_integer_ratio()) for i in range(36)]]
    durations=[[[1,3]]*36,[[1,3]]*72]
    need(changed_onsets is None or changed_onsets==onsets,'CANDIDATE_TIMING_DRIFT')
    need(changed_durations is None or changed_durations==durations,'CANDIDATE_DURATION_DRIFT')
    strokes={vid:[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(n)]
             for pair,n in zip(VARIANTS,(36,72)) for vid,start in zip(pair,('D','U'))}
    need(changed_strokes is None or changed_strokes==strokes,'CANDIDATE_STROKE_DRIFT')
    refs=('L14-TXT-RULE-29-53','L14-PDF-GUIDANCE-P1','L14-TXT-RUNG01-56-67',
          'L14-TXT-RUNG02-70-81','L14-PDF-CARDS-P3','L14-PDF-ROUTE-P2')
    sources={
      refs[0]:passage(TXT,TXT_SHA,'txt','\n'.join(lines[28:53]),first_line=29,last_line=53),
      refs[1]:passage(PDF,PDF_SHA,'pdf','\n'.join(pages[0]),page=1),
      refs[2]:passage(TXT,TXT_SHA,'txt','\n'.join(lines[55:67]),first_line=56,last_line=67),
      refs[3]:passage(TXT,TXT_SHA,'txt','\n'.join(lines[69:81]),first_line=70,last_line=81),
      refs[4]:passage(PDF,PDF_SHA,'pdf','\n'.join(pages[2]),page=3),
      refs[5]:passage(PDF,PDF_SHA,'pdf','\n'.join(pages[1]),page=2)}
    records=[]; entities=[{'id':WORKBOOK,'kind':'workbook','label':'Legacy Level14','parent':'fg:course:000001'}]
    event_sources={}; provenance={}; allocations={}
    for case_idx,(item,module,vids,case_notes) in enumerate(zip(ITEMS,MODULES,VARIANTS,contacts)):
        local=('L014-R01:A:TRIPLET','L014-R01-R02:A_BB:TRIPLET_ONE_BEAT_PAUSE')[case_idx]
        title=('Level 14 Rung01 A-major complete 36-note rolling-triplet cell',
               'Level 14 Rung01 A-major to Rung02 Bb-major two-cell rolling-triplet ladder')[case_idx]
        event_list=[]; sidecar={}
        for i,note in enumerate(case_notes):
            eid=f'{item}:event:{i+1:04d}'; rung_idx=0 if i<36 else 1
            source_ref=refs[2+rung_idx]; key=('A-major','Bb-major')[rung_idx]
            event_list.append({'event_id':eid,'kind':'note','string':STRING[note['string']],
                               'fret':note['fret'],'finger':note['finger'],'midi':note['midi'],
                               'spelling':note['source_tone'],'attack':'picked',
                               'onset_q':onsets[case_idx][i],'duration_q':durations[case_idx][i],
                               'tie_from':None,
                               'degree_contexts':{key:{'ordinal':note['degree'],'alteration':0,
                                                       'source_label':str(note['degree'])}}})
            event_sources[eid]=source_ref
            sidecar[eid]={'source_local_event_key':f'{local}:R{rung_idx+1:02d}:{note["index"]:02d}',
                          'source_txt_ref':source_ref,'source_pdf_ref':refs[4],
                          'source_txt_line':56+rung_idx*14,'source_pdf_page':3,
                          'source_rung':rung_idx+1,'source_triplet_group':note['group'],
                          'source_group_slot':note['slot'],'string_label':note['string'],
                          'string':STRING[note['string']],'fret':note['fret'],
                          'finger_digit':note['finger'],'degree':note['degree'],
                          'spelling':note['source_tone'],'midi':note['midi'],
                          'phase':note['phase'],'repeated_high_root_at_turn':note['repeated_high_root_at_turn'],
                          'timing_txt_ref':refs[0],'timing_pdf_ref':refs[1],
                          'nominal_slot_q':onsets[case_idx][i],
                          'one_beat_pause_after_first_cell':case_idx==1 and i==35,
                          'whole_frame_move_fret':1 if case_idx==1 and i==35 else 0}
        provenance.update(sidecar)
        variants=[{'id':vid,'label':f'{local.lower()}-{start}-start',
                   'role':'notation_practice',
                   'route':'standalone_rung01' if case_idx==0 else 'rung01_to_rung02_neighbor_training',
                   'source_refs':list(refs),'event_ids':list(sidecar),
                   'pick_start':start,'pick_start_origin':'source_authored',
                   'grouping':{'kind':'source_event_time','notes_per_beat':None,
                               'beat_unit_q':None,'marking_factor':[1,1],
                               'source_label':'TXT/PDF eighth-note triplets: one three-note group per beat; paired neighbor stage pauses one beat after 36-note cell'},
                   'accent_policy':'even','tail_pause':None,'unresolved':[]}
                  for vid,start in zip(vids,('D','U'))]
        record={'id':item,'module_id':module,'workbook_id':WORKBOOK,
                'content_revision':1,'lineage':{'kind':'new'},'kind':'notation',
                'legacy_level':14,'status':'converted_candidate','runtime_eligible':False,
                'title':title,'source_refs':list(refs),'authored_text_refs':list(refs),
                'events':event_list,'variants':variants,'resource_requirements':[],
                'rubric':None,
                'control_scope':{'extent':'complete_selected_case','local_case':local,
                                 'source_event_count':len(event_list),'basis_refs':list(refs),
                                 'whole_workbook_complete':False,
                                 'unresolved':['Rungs03-13 and full neck-ladder route outside this case.',
                                               'Runtime admission and whole Level14 remain Pending.']},
                'context':{'local_code':local,
                           'route':'A-major first complete rolling cell' if case_idx==0 else 'A-major to Bb-major first two neighboring cells',
                           'position':'low-E root fret5' if case_idx==0 else 'low-E root fret5 to fret6',
                           'pick_start_variants':['D','U'],
                           'pick_start':'source-authored strict D/U or U/D without reset at groups, strings, turn or relocation',
                           'tuning_open_midi':[40,45,50,55,59,64], 'capo':0,
                           'source_tempo_rules_ref':refs[0]},
                'timing':{'status':'source_defined','unit':'quarter','meter':None,
                          'basis':'Original TXT/PDF eighth-note triplets: one three-note group per quarter beat. Two-neighbor case adds one quarter beat after 36-note A cell before Bb. No fixed BPM or measured sustain.'},
                'ambiguities':['Relative to clean Level13 tempo does not establish fixed BPM, observed clean performance, mastery or credit.',
                               'Capo zero is untransposed standard-tuning representation, not a capo instruction.'],
                'normalization':[{'kind':'representation_metadata','basis':refs[0],
                                  'text':'Complete 36-note A triplet cell or A-to-Bb two-cell triplet neighbor stage; repeated high root, continuous alternate picking, one-beat pause only between paired cells.'}]}
        records.append(record)
        entities.extend([{'id':module,'kind':'module','label':title,'parent':WORKBOOK},
                         {'id':item,'kind':'item','label':title,'parent':module},
                         *({'id':v['id'],'kind':'variant','label':v['label'],'parent':item} for v in variants)])
        allocations[item]={'legacy_level':14,
                           'occurrences':{p['source_local_event_key']:eid for eid,p in sidecar.items()},
                           'variants':{v['label']:v['id'] for v in variants}}
    base_package,base_registry,base_profile=(read(BASE/name) for name in
                                               ('package.json','identity-registry.json','expected-profile.json'))
    package={k:copy.deepcopy(v) for k,v in base_package.items() if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1',
                   records=records,sources=sources)
    registry={'identity_version':base_registry['identity_version'],'rules':base_registry['rules'],
              'entities':[base_registry['entities'][0],*entities]}
    identity_baseline={'identity_version':registry['identity_version'],'rules':registry['rules'],
                       'entities':[registry['entities'][0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P48 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1',
                'authority':'P48 provisional nonadmitted allocation; P02 canonical re-audit required',
                'records':allocations}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources','authority_artifacts','workbook_catalog')}
    profile['degree_roots']={'A-major':{'basis':'Level14 original Rung01 A major source card; pitch class only','root_pitch_class':9},
                             'Bb-major':{'basis':'Level14 original Rung02 Bb major source card; pitch class only','root_pitch_class':10}}
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
             'variant_ids':[v for pair in VARIANTS for v in pair],
             'record_count':2,'event_count':108,'variant_count':4,
             'runtime_eligible':False,'admitted':False,'whole_workbook_complete':False,
             'source_txt_sha256':TXT_SHA,'source_pdf_sha256':PDF_SHA,'p09_parity_sha256':P09_SHA,
             'identity_audit_sha256':sha((ROOT/OUT/'identity-audit.json').read_bytes()),
             'first_case_end_q':[12,1],'second_case_end_q':[25,1],
             'interpretation':'Complete 36-note A triplet cell; A-to-Bb two-neighbor triplet stage with one-beat pause; no fixed BPM or mastery. Independent P50 review required.'}
    return {'package.json':package,'identity-registry.json':registry,'expected-profile.json':profile,
            'candidate-allocation.json':allocation,'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':[refs[0],refs[2],refs[3]],
                                      'source_pdf_refs':[refs[1],refs[4],refs[5]],
                                      'events':provenance,'variant_strokes':strokes,
                                      'stroke_basis':'Original TXT/PDF continuous strict alternate D/U or U/D through triplet groups, turn and relocation; 36 even attacks preserve next-cell orientation.'},
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
