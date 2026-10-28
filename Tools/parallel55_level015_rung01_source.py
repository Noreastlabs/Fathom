#!/usr/bin/env python3
"""P55 source-closed, nonadmitted Level15 complete Rung01 triplet reference."""
from __future__ import annotations
import argparse, copy, hashlib, json, re, subprocess
from fractions import Fraction
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('Build/parallel-55/controlled-open-level015-rung01-source-r01')
STEM='Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder'
TXT=Path(f'Notes/music/guitar project/TXT version/{STEM}.txt')
PDF=Path(f'Notes/music/guitar project/PDF version/{STEM}.pdf')
P08=Path('Build/parallel-08/2.3.1.1.1-level015-whole-r01/candidate-01.json')
P12=Path('Build/parallel-12/level015-schema1-unallocated-r01/field-proposal.json')
P53=Path('Results/parallel-53/level015-lineage-decision-r01/20260924T072200Z-2.3.1.1.1-level015-lineage-decision-r01-results.md')
P54=Path('Results/parallel-54/level015-lineage-review-r01/20260924T073325Z-2.3.1.1.1-level015-lineage-review-r01-results.md')
BASE=Path('Content/controls/curriculum-v1')
TXT_SHA='896937c0d5040c8e7590364433e141bbe7f6da419e063a8ed2590666d5a2c514'
PDF_SHA='9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e'
P08_SHA='bff1da256722d18dff4c564032a74947fa56cbd3af460b3733537380dc9d804b'
P12_SHA='a006058a80ff6d4627cbeb26c0b8ed35731d29b08233aed18838fbcaff15f88f'
P53_SHA='d5a4174c9a3985c7b22940d477d0c440276eeed9fb5e3679a515fadcb983e213'
P54_SHA='317d6a84c86a637e027121bc6da271b73a7f2981bd844421d8369e4555ba2ab0'
BASE_SHA='766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255'
ITEM='fg:item:001157'; MODULE='fg:module:001157'; VARIANTS=('fg:variant:007436','fg:variant:007437')
WORKBOOK='fg:workbook:000015'; OLD_ITEM='fg:item:000004'
LOCAL='L15-rung01-complete-triplets'
OPEN_MIDI={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
STRING={'E':1,'A':2,'D':3,'G':4,'B':5,'e':6}
TONES=('A','B','C#','D','E','F#','G#','A','B','C#','D','E','F#','G#','A')
PC={'A':9,'B':11,'C#':1,'D':2,'E':4,'F#':6,'G#':8}
NAMES=('package.json','identity-registry.json','expected-profile.json','candidate-allocation.json',
       'identity-baseline.json','allocation-baseline.json','lineage-baseline.json','source-provenance.json','summary.json')
class CandidateError(ValueError): pass
def need(ok,code):
    if not ok: raise CandidateError(code)
def encode(obj): return (json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads((ROOT/path).read_bytes())
def passage(path,digest,fmt,value,**where):
    return {'path':str(path),'sha256':digest,'format':fmt,**where,'text':value,'text_sha256':sha(value.encode())}
def identity_scan():
    cmd=['rg','-l','--no-messages','-e',r'fg:(?:item|module):001157',
         '-e',r'fg:variant:00743[67]','--glob','*.json','--glob','*.cpp','--glob','*.hpp',
         'Content','Source','Build']
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    need(r.returncode in (0,1),'IDENTITY_SCAN_FAILED')
    hits=sorted(x for x in r.stdout.splitlines() if not x.startswith(str(OUT)+'/'))
    need(not hits,'PROVISIONAL_ID_COLLISION')
    return {'status':'PASS','scope':['Content','Source','Build'],'method':cmd,
            'wanted':[ITEM,MODULE,*VARIANTS],'matches':hits,'canonical_reservation':False,
            'classification':'Prospective new-case numeric IDs clear today; workbook000015 and old item000004 intentionally preexist. P02 must rescan after Level14.'}
def _cells(row,label):
    parts=row.split('|'); need(len(parts)==15 and parts[0]==label and parts[-1]=='','ROW_SHAPE:'+label)
    out=[]
    for block in parts[1:-1]:
        need(len(block)==9,'GROUP_WIDTH:'+label)
        chunks=[]
        for i in (0,3,6):
            token=block[i:i+3]; value=token.rstrip('-')
            need((not value and token=='---') or (value.isdigit() and value+'-'*(3-len(value))==token),'SLOT:'+label)
            chunks.append(value or None)
        out.append(chunks)
    return out
def _parse_half(block,half):
    need(len(block)==9 and block[0]==f'{half.upper()} - 13 TRIPLETS / 39 NOTES','HALF_HEADER')
    degrees=_cells(block[1],'Deg'); fingers=_cells(block[2],'Fng')
    tab={s:_cells(row,f'{s}  ') for s,row in zip(('e','B','G','D','A','E'),block[3:])}
    notes=[]
    for g in range(13):
        expected=tuple(range(g+1,g+4)) if half=='ascending' else tuple(range(15-g,12-g,-1))
        for slot,degree in enumerate(expected):
            need(degrees[g][slot]==str(degree),'DEGREE_SEQUENCE')
            finger=int(fingers[g][slot]); need(1<=finger<=4,'FINGER_RANGE')
            hits=[(s,int(tab[s][g][slot])) for s in tab if tab[s][g][slot] is not None]
            need(len(hits)==1,'TAB_CONTACT_COUNT')
            string,fret=hits[0]; midi=OPEN_MIDI[string]+fret; spelling=TONES[degree-1]
            need(midi%12==PC[spelling],'PITCH_SPELLING')
            notes.append({'ordinal':len(notes)+1+(0 if half=='ascending' else 39),
                          'group':g+1+(0 if half=='ascending' else 13),'slot':slot+1,
                          'phase':'up' if half=='ascending' else 'down',
                          'degree':degree,'finger':finger,'string':string,'fret':fret,
                          'midi':midi,'spelling':spelling})
    need(len(notes)==39,'HALF_COUNT')
    return notes
def source_facts():
    for path,digest,code in ((TXT,TXT_SHA,'TXT_PIN_DRIFT'),(PDF,PDF_SHA,'PDF_PIN_DRIFT'),
                             (P08,P08_SHA,'P08_PIN_DRIFT'),(P12,P12_SHA,'P12_PIN_DRIFT'),
                             (P53,P53_SHA,'P53_PIN_DRIFT'),(P54,P54_SHA,'P54_PIN_DRIFT'),
                             (BASE/'package.json',BASE_SHA,'CURRENT659_PIN_DRIFT')):
        need(sha((ROOT/path).read_bytes())==digest,code)
    lines=(ROOT/TXT).read_text().splitlines()
    pdf=PdfReader(str(ROOT/PDF)); need(len(pdf.pages)==10,'PDF_PAGE_COUNT')
    pages=[(page.extract_text(extraction_mode='layout') or '').splitlines() for page in pdf.pages]
    practice='\n'.join(lines[58:67]); rule='\n'.join(lines[40:53]); page1='\n'.join(pages[0]); page3='\n'.join(pages[2])
    for phrase in ('Use eighth-note triplets: one three-note group per beat','pause one beat after each 78-note cell',
                   'Repeat with both pick starts','15-20 BPM below your clean Level 14 tempo'):
        need(phrase in practice,'TXT_PRACTICE_RULE:'+phrase)
    for phrase in ('26 triplets and 78 notes','played twice at the turn','Never restart the pick cycle'):
        need(phrase in rule,'TXT_CELL_RULE:'+phrase)
    need('26 triplets. One unbroken pick cycle.' in page1 and 'Complete all 78 notes' in page1,
         'PDF_GUIDANCE_DRIFT')
    need('78 NOTES / 26 TRIPLETS' in page3 and 'Eighth-note triplets: one three-note group per beat.' in page3,
         'PDF_CARD_RULE_DRIFT')
    card=lines[69:91]; need(len(card)==22 and card[0].startswith('RUNG 01 OF 13 - A MAJOR') and
                             card[1]=='Scale tones across two octaves: '+' '.join(TONES) and
                             card[2].startswith('78-note cell:') and card[-1].startswith('Finish on the low root'),
                             'TXT_CARD_BOUNDARY')
    notes=_parse_half(card[3:12],'ascending')+_parse_half(card[12:21],'descending')
    need(len(notes)==78 and notes[38]['degree']==notes[39]['degree']==15 and
         (notes[38]['string'],notes[38]['fret'],notes[38]['midi'],notes[38]['finger'])==
         (notes[39]['string'],notes[39]['fret'],notes[39]['midi'],notes[39]['finger'])==('e',5,69,2),
         'HIGH_ROOT_TURN')
    need([(n['string'],n['fret'],n['midi']) for n in (notes[0],notes[-1])]==[('E',5,45),('E',5,45)],'LOW_ROOT')
    need({n['fret'] for n in notes if n['string']=='B'}=={5,7},'B_STRING_OFFSET')
    printed=[x.strip() for x in pages[2] if x.strip().startswith(('Deg|','Fng|','e  |','B  |','G  |','D  |','A  |','E  |'))]
    need(printed[:16]==card[4:12]+card[13:21],'TXT_PDF_CARD_ROWS')
    # Secondary parity only: the original rows parsed above supply musical facts.
    p08=read(P08)['records'][0]; p12=read(P12)['records'][0]
    prior=[n for g in p08['groups'] for n in g['notes']]; proposed=p12['schema1_fields']['events']
    need(len(prior)==len(proposed)==78,'BACKGROUND_COUNT')
    for n,a,b in zip(notes,prior,proposed):
        need((n['string'],n['fret'],n['finger'],n['degree'])==
             (a['string'],a['fret'],int(a['finger_digit']),a['degree']),'P08_CONTACT_PARITY')
        need((STRING[n['string']],n['fret'],n['midi'],n['finger'],n['degree'],n['spelling'])==
             (b['string'],b['fret'],b['midi'],b['finger'],b['degree_contexts']['A-major']['ordinal'],b['spelling']),
             'P12_CONTACT_PARITY')
    current=read(BASE/'package.json')
    old=[r for r in current['records'] if r['id']==OLD_ITEM]
    need(len(current['records'])==659 and len(old)==1 and old[0]['content_revision']==3 and
         old[0]['control_scope']['extent']=='selected_illustration' and len(old[0]['events'])==3 and
         [v['id'] for v in old[0]['variants']]==[f'fg:variant:{i:06d}' for i in range(33,37)],
         'OLD_SELECTED_IDENTITY_DRIFT')
    for i,(o,n) in enumerate(zip(old[0]['events'],notes[:3])):
        need((o['string'],o['fret'],o['midi'],o['finger'],next(iter(o['degree_contexts'].values()))['ordinal'])==
             (STRING[n['string']],n['fret'],n['midi'],n['finger'],n['degree']),
             'OLD_FIRST_TRIPLET_OVERLAP:'+str(i))
    oldref=current['sources']['L15-TXT59-81']
    need((oldref['first_line'],oldref['last_line'],oldref['sha256'])==(59,81,TXT_SHA) and
         oldref['text']=='\n'.join(lines[58:81]),'OLD_SOURCE_REF_DRIFT')
    return lines,pages,notes,current
def derive(*,changed_contacts=None,changed_onsets=None,changed_durations=None,
           changed_strokes=None,forced_bpm=None,force_eligible=False,
           reserved_item=ITEM,old_item_rebound=False):
    need(not force_eligible,'FORCED_ELIGIBILITY')
    need(forced_bpm is None,'FIXED_BPM_UNAUTHORIZED')
    need(reserved_item==ITEM and not old_item_rebound,'OLD_ID_REBIND_FORBIDDEN')
    audit_path=ROOT/OUT/'identity-audit.json'; need(audit_path.exists(),'IDENTITY_AUDIT_MISSING')
    audit=json.loads(audit_path.read_bytes())
    need(audit['status']=='PASS' and not audit['matches'] and set(audit['wanted'])=={ITEM,MODULE,*VARIANTS},
         'IDENTITY_AUDIT_DRIFT')
    lines,pages,notes,current=source_facts()
    need(changed_contacts is None or changed_contacts==notes,'CANDIDATE_CONTACT_DRIFT')
    onsets=[list(Fraction(i,3).as_integer_ratio()) for i in range(78)]
    durations=[[1,3]]*78
    need(changed_onsets is None or changed_onsets==onsets,'CANDIDATE_TIMING_DRIFT')
    need(changed_durations is None or changed_durations==durations,'CANDIDATE_DURATION_DRIFT')
    strokes={vid:[start if i%2==0 else ('U' if start=='D' else 'D') for i in range(78)]
             for vid,start in zip(VARIANTS,('D','U'))}
    need(changed_strokes is None or changed_strokes==strokes,'CANDIDATE_STROKE_DRIFT')
    refs=('L15-TXT1-60-67','L15-TXT1-70-91','L15-PDF-GUIDANCE-P1','L15-PDF-CARD-P3')
    sources={
      refs[0]:passage(TXT,TXT_SHA,'txt','\n'.join(lines[59:67]),first_line=60,last_line=67),
      refs[1]:passage(TXT,TXT_SHA,'txt','\n'.join(lines[69:91]),first_line=70,last_line=91),
      refs[2]:passage(PDF,PDF_SHA,'pdf','\n'.join(pages[0]),page=1),
      refs[3]:passage(PDF,PDF_SHA,'pdf','\n'.join(pages[2]),page=3)}
    event_list=[]; event_sources={}; sidecar={}
    old=[r for r in current['records'] if r['id']==OLD_ITEM][0]
    for i,n in enumerate(notes):
        eid=f'{ITEM}:event:{i+1:04d}'
        event_list.append({'event_id':eid,'kind':'note','string':STRING[n['string']],
                           'fret':n['fret'],'finger':n['finger'],'midi':n['midi'],
                           'spelling':n['spelling'],'attack':'picked',
                           'onset_q':onsets[i],'duration_q':durations[i],'tie_from':None,
                           'degree_contexts':{'A-major':{'ordinal':n['degree'],'alteration':0,
                                                          'source_label':str(n['degree'])}}})
        event_sources[eid]=refs[1]
        sidecar[eid]={'source_local_event_key':f'{LOCAL}:{i+1:02d}',
                      'source_txt_ref':refs[1],'source_pdf_ref':refs[3],
                      'source_txt_line_span':[70,91],'source_pdf_page':3,
                      'source_triplet_group':n['group'],'source_group_slot':n['slot'],
                      'string_label':n['string'],'string':STRING[n['string']],
                      'fret':n['fret'],'finger_digit':n['finger'],'degree':n['degree'],
                      'spelling':n['spelling'],'midi':n['midi'],'phase':n['phase'],
                      'high_root_turn_repeat':i in (38,39),
                      'timing_txt_ref':refs[0],'timing_pdf_ref':refs[2],
                      'nominal_slot_q':onsets[i],
                      'physical_contact_overlap_with_old_selected_illustration':i<3}
    need(set(event_sources)==set(sidecar)=={e['event_id'] for e in event_list},
         'EVENT_PROVENANCE_COVERAGE')
    variants=[]
    for vid,start in zip(VARIANTS,('D','U')):
        variants.append({'id':vid,'label':f'{LOCAL}-{start}-start',
                         'role':'notation_practice','route':'standalone_rung01_complete_cell',
                         'source_refs':list(refs),'event_ids':list(sidecar),
                         'pick_start':start,'pick_start_origin':'source_authored',
                         'grouping':{'kind':'even_subdivision','notes_per_beat':3,
                                     'beat_unit_q':[1,1],'marking_factor':[1,1],
                                     'source_label':'Original Level15 eighth-note triplets: one three-note group per beat'},
                         'accent_policy':'source_unspecified','tail_pause':None,'unresolved':[]})
    title='Level 15 Rung01 A-major complete 78-note two-octave rolling-triplet cell'
    record={'id':ITEM,'module_id':MODULE,'workbook_id':WORKBOOK,'content_revision':1,
            'lineage':{'kind':'new'},'kind':'notation','legacy_level':15,
            'status':'converted_candidate','runtime_eligible':False,'title':title,
            'source_refs':list(refs),'authored_text_refs':list(refs),
            'events':event_list,'variants':variants,'resource_requirements':[],
            'rubric':None,
            'control_scope':{'extent':'complete_selected_case','local_case':LOCAL,
                             'source_event_count':78,'basis_refs':list(refs),
                             'whole_workbook_complete':False,
                             'unresolved':['Rungs02-13 and complete 25-cell neck route outside this selected case.',
                                           'Runtime admission and whole Level15 remain Pending.']},
            'context':{'local_code':LOCAL,'route':'A-major Rung01 complete single cell',
                       'position':'low-E root fret5; six-string two-octave frame4-7',
                       'pick_start_variants':['D','U'],
                       'pick_start':'source-authored continuous D/U or U/D through triplets, strings, octave and turn',
                       'tuning_open_midi':[40,45,50,55,59,64],'capo':0,
                       'source_tempo_rules_ref':refs[0]},
            'timing':{'status':'source_defined','unit':'quarter','meter':None,
                      'basis':'Original Level15 eighth-note triplets: one three-note group per beat. Complete 78-note cell spans 26 quarter beats; no within-cell or single-cell tail pause, fixed BPM or measured sustain.'},
            'ambiguities':['Existing item000004 revision3 is a separate three-event selected illustration of the same first physical triplet; no ID, variant, attempt or progress equivalence.',
                           'Existing old TXT ref L15-TXT59-81 and this full-card ref L15-TXT1-70-91 share original lines70-81; this is reviewed source overlap, not an item revision.',
                           'Relative 15-20 BPM below clean Level14 is guidance, not a fixed BPM or observed mastery.',
                           'Capo zero is an untransposed standard-tuning representation, not a capo instruction.'],
            'normalization':[{'kind':'representation_metadata','basis':refs[1],
                              'text':'Full 78-note A-major Rung01 is distinct from old three-event item000004; first physical triplet overlaps but identity/history/credit do not. New source-local case bridges to P08 L15-rung01.'}]}
    entities=[{'id':WORKBOOK,'kind':'workbook','label':'Legacy Level15','parent':'fg:course:000001'},
              {'id':MODULE,'kind':'module','label':title,'parent':WORKBOOK},
              {'id':ITEM,'kind':'item','label':title,'parent':MODULE},
              *({'id':v['id'],'kind':'variant','label':v['label'],'parent':ITEM} for v in variants)]
    base_package,base_registry,base_profile=(read(BASE/name) for name in
                                               ('package.json','identity-registry.json','expected-profile.json'))
    package={k:copy.deepcopy(v) for k,v in base_package.items() if k not in ('records','sources','workbook_catalog')}
    package.update(content_version='curriculum-v1-level015-rung01-complete-triplet-build-only.1',
                   records=[record],sources=sources)
    registry={'identity_version':base_registry['identity_version'],'rules':base_registry['rules'],
              'entities':[base_registry['entities'][0],*entities]}
    identity_baseline={'identity_version':registry['identity_version'],'rules':registry['rules'],
                       'entities':[registry['entities'][0]]}
    allocation_baseline={'version':'control-allocation.1','authority':'P55 provisional only','records':{}}
    lineage_baseline={'version':'lineage-baseline.1','records':{}}
    allocation={'version':'control-allocation.1',
                'authority':'P55 provisional distinct new case; P02 canonical re-audit required',
                'records':{ITEM:{'legacy_level':15,
                                 'occurrences':{p['source_local_event_key']:eid for eid,p in sidecar.items()},
                                 'variants':{v['label']:v['id'] for v in variants}}}}
    profile={k:copy.deepcopy(v) for k,v in base_profile.items()
             if k not in ('reference_package','reference_registry','event_sources','authority_artifacts','workbook_catalog')}
    profile['degree_roots']={'A-major':{'basis':'Level15 original Rung01 A major source card; pitch class only','root_pitch_class':9}}
    profile.update(reference_package=package,reference_registry=registry,event_sources=event_sources)
    profile['authority_artifacts']=[copy.deepcopy(a) for a in base_profile['authority_artifacts']
                                     if a['role'] in ('source_manifest','source_acceptance','current_schema_freeze')]
    for role,name,value in (('identity_baseline','identity-baseline.json',identity_baseline),
                            ('allocation_baseline','allocation-baseline.json',allocation_baseline),
                            ('lineage_baseline','lineage-baseline.json',lineage_baseline),
                            ('candidate_identity_allocation','candidate-allocation.json',allocation)):
        profile['authority_artifacts'].append({'path':str(OUT/name),'role':role,'sha256':sha(encode(value))})
    old_ids=[e['event_id'] for e in old['events']]; new_ids=[e['event_id'] for e in event_list]
    need(not set(old_ids)&set(new_ids) and set(v['id'] for v in old['variants']).isdisjoint(VARIANTS),
         'OLD_ID_REUSE')
    summary={'status':'source_interpreted_nonadmitted_reference','item_id':ITEM,
             'module_id':MODULE,'variant_ids':list(VARIANTS),'record_count':1,
             'event_count':78,'variant_count':2,'runtime_eligible':False,'admitted':False,
             'whole_workbook_complete':False,'source_txt_sha256':TXT_SHA,'source_pdf_sha256':PDF_SHA,
             'p08_parity_sha256':P08_SHA,'p12_parity_sha256':P12_SHA,
             'p53_lineage_sha256':P53_SHA,'p54_lineage_review_sha256':P54_SHA,
             'current659_sha256':BASE_SHA,'identity_audit_sha256':sha(audit_path.read_bytes()),
             'end_q':[26,1],'old_item':OLD_ITEM,'old_item_preserved':True,
             'interpretation':'One complete A-major 78-note Rung01 triplet cell, both D/U starts; separate from old first-three-note illustration, no fixed BPM/mastery/credit.'}
    overlap={'old_item':OLD_ITEM,'old_module':'fg:module:000004','old_content_revision':3,
             'old_variant_ids':[v['id'] for v in old['variants']],
             'old_event_ids':old_ids,'new_event_ids_first_three':new_ids[:3],
             'old_txt_ref':'L15-TXT59-81','new_txt_card_ref':refs[1],
             'shared_original_txt_sha256':TXT_SHA,'shared_line_span':[70,81],
             'same_physical_first_triplet':True,'same_case_or_history_identity':False,
             'p53_p54_reviewed_separate_item':True}
    return {'package.json':package,'identity-registry.json':registry,'expected-profile.json':profile,
            'candidate-allocation.json':allocation,'identity-baseline.json':identity_baseline,
            'allocation-baseline.json':allocation_baseline,'lineage-baseline.json':lineage_baseline,
            'source-provenance.json':{'source_txt_refs':[refs[0],refs[1]],
                                      'source_pdf_refs':[refs[2],refs[3]],
                                      'events':sidecar,'variant_strokes':strokes,
                                      'stroke_basis':'Original Level15 continuous alternate D/U or U/D through all 26 triplets, string crossings and high-root turn.',
                                      'existing_illustration_overlap':overlap},
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
