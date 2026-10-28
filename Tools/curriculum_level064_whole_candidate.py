#!/usr/bin/env python3
"""Build a detached, lossless whole-Level-64 structured source candidate."""
from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
STEM='Guitar_Exercises_Section_VII_Level_64_Long_Form_Arpeggio_Solo_Construction_Secondary_Dominants_Key_Changes_and_System_Aware_Phrase_Orchestration'
TXT_REL=Path('Notes/music/guitar project/TXT version')/(STEM+'.txt')
PDF_REL=Path('Notes/music/guitar project/PDF version')/(STEM+'.pdf')
INDEX_REL=Path('Build/parallel-01/2.3-level064-whole-coverage-index-r01/candidate-r01.json')
MAP_REL=Path('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv')
BUILD_REL=Path('Build/parallel-09/2.3.1.2.1-level064-whole-r01')
PINS={'txt':(32273,'f00e6ef35a1971a91aab67103c69338c4b4a041ca37a100ec857b8537f3f6f24'),
      'pdf':(49479,'70c3179403ca12179f99f072911a76c56c88279e40534030184415e8f6d8a145'),
      'index':(33271,'9e9256c41c65656298c97d0e45f88e7430a4256e955f562e5739cef3bbd12c23')}
EXPECTED={'A':40,'B':40,'C':40,'D':64,'E':64,'F':64,'G':128,'H':64,'I':64,'J':72}
FIELDS=('Date','Study / key change','System','BPM','Clean?','Weak harmony / phrase / system','Next target')

class CandidateError(ValueError):pass

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def pin(data:bytes,key:str)->None:
    size,sha=PINS[key]
    if len(data)!=size or digest(data)!=sha:raise CandidateError(f'PINNED_{key.upper()}_DRIFT')

def valid_path(rel:Path)->Path:
    if rel.is_absolute() or '..' in rel.parts:raise CandidateError('INPUT_PATH_INVALID')
    p=ROOT/rel
    if p.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()):raise CandidateError('INPUT_PATH_INVALID')
    return p

def collect_positions(obj:object,path:tuple=()):
    """Yield authored position arrays once, retaining their source hierarchy."""
    if isinstance(obj,dict):
        for key,value in obj.items():
            if key in ('tone_positions','positions') and isinstance(value,list):
                for n,pos in enumerate(value,1):yield path+(key,n),pos
            else:yield from collect_positions(value,path+(key,))
    elif isinstance(obj,list):
        for n,value in enumerate(obj,1):yield from collect_positions(value,path+(n,))

def normalized_position(pos:dict,module:str,slice_key:str,path:tuple,ordinal:int)->dict:
    note=pos.get('authored_note_token',pos.get('note_token'))
    role=pos.get('authored_degree_role_token',pos.get('role_token'))
    if not isinstance(note,str) or not isinstance(role,str):raise CandidateError('POSITION_TOKEN_MISSING')
    if pos.get('canonical_event_id','missing') is not None:raise CandidateError('POSITION_CANONICAL_ID')
    return {'module':module,'slice_key':slice_key,'source_order':ordinal,'path_in_slice':list(path),
            'note_token':note,'role_token':role,'pick_token':pos.get('authored_picking_token'),
            'source_tab':pos.get('source_tab'),'source_refs':pos.get('source_refs'),
            'source_local_key':pos.get('source_local_tone_key',pos.get('source_local_position_key')),
            'canonical_event_id':None,'onset_q':None,'duration_q':None,'sounding_pitch':None}

def _source_map(txt:bytes,pdf:bytes)->dict:
    with valid_path(MAP_REL).open(newline='') as f:
        rows=[r for r in csv.DictReader(f,delimiter='\t') if r['level']=='64']
    if len(rows)!=1:raise CandidateError('SOURCE_MAP_ROW')
    r=rows[0]
    checks={'wbs_owner':'2.3.1.2.1','txt_path':TXT_REL.as_posix(),'txt_bytes':str(len(txt)),
            'txt_sha256':digest(txt),'pdf_path':PDF_REL.as_posix(),'pdf_bytes':str(len(pdf)),
            'pdf_sha256':digest(pdf),'review':'Pending','conversion_status':'not_converted',
            'representative_item_id':''}
    if any(r.get(k)!=v for k,v in checks.items()):raise CandidateError('SOURCE_MAP_DRIFT')
    if any(r.get(k)!='False' for k in ('stable_ids_assigned','runtime_eligible','imported','admitted')):
        raise CandidateError('SOURCE_MAP_ADMISSION')
    return {k:r[k] for k in checks}

def build_candidate(*,txt_data:bytes|None=None,pdf_data:bytes|None=None,index_data:bytes|None=None,
                    slice_overrides:dict[str,bytes]|None=None)->dict:
    txt=txt_data if txt_data is not None else valid_path(TXT_REL).read_bytes()
    pdf=pdf_data if pdf_data is not None else valid_path(PDF_REL).read_bytes()
    idx=index_data if index_data is not None else valid_path(INDEX_REL).read_bytes()
    for key,data in (('txt',txt),('pdf',pdf),('index',idx)):pin(data,key)
    lines=txt.decode('utf-8').splitlines()
    pages=[p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines)!=669 or len(pages)!=20:raise CandidateError('SOURCE_BOUNDARY')
    index=json.loads(idx)
    entries=index['module_candidate_union']
    if len(entries)!=12 or index['coverage_scope']['printed_position_count']!=640:
        raise CandidateError('INDEX_UNION')
    if index['coverage_scope']['module_candidate_pdf_pages']!=list(range(3,20)):
        raise CandidateError('INDEX_PAGES')
    if sorted(index['coverage_scope']['module_union'])!=list(EXPECTED):raise CandidateError('INDEX_MODULES')
    for record in index['source_only_references']['pdf_page_texts']:
        if record['extracted_text']!=pages[record['pdf_page']-1]:
            raise CandidateError('SOURCE_ONLY_PAGE_DRIFT')
    for span in index['source_only_references']['txt_line_spans']:
        if any(record['text']!=lines[record['line']-1] for record in span['lines']):
            raise CandidateError('SOURCE_ONLY_TXT_DRIFT')
    if index['source_authority']['txt']['sha256']!=digest(txt) or index['source_authority']['pdf']['sha256']!=digest(pdf):
        raise CandidateError('INDEX_SOURCE_DRIFT')
    if '640 sounding tones' not in txt.decode('utf-8') or '640' not in pages[0]:
        raise CandidateError('WORKLOAD_DECLARATION')
    for field in FIELDS:
        if field not in pages[19]:raise CandidateError('PDF_ONLY_LOG_FIELD')
    if any(field in '\n'.join(lines[634:]) for field in FIELDS):
        raise CandidateError('PDF_ONLY_LOG_STATUS')
    if 'Part 2' not in pages[7]:raise CandidateError('PDF_D_PART')
    if slice_overrides and any(k not in {e['candidate_key'] for e in entries} for k in slice_overrides):
        raise CandidateError('SLICE_OVERRIDE_KEY')
    modules={k:{'module':k,'slices':[],'positions':[]} for k in EXPECTED}
    all_positions=[];all_pages=[];spans=[];sources=[]
    for entry in entries:
        key=entry['candidate_key'];ref=entry['candidate_ref'];rel=Path(ref['path'])
        data=(slice_overrides or {}).get(key)
        if data is None:data=valid_path(rel).read_bytes()
        if len(data)!=ref['bytes'] or digest(data)!=ref['sha256']:
            raise CandidateError(f'PINNED_SLICE_DRIFT {key}')
        obj=json.loads(data)
        if entry['modules']==['H','I']:
            sections=[('H',obj['capstones'][0]),('I',obj['capstones'][1])]
        else:sections=[(entry['modules'][0],obj)]
        if key=='D-page-8' and obj['source_scope']['pdf_page_block']!='Part 1':
            raise CandidateError('D_CANDIDATE_PART_CHANGED')
        count=0
        for module,section in sections:
            raw=list(collect_positions(section))
            if module=='J':
                # The 12 recovery cards print two note/role positions but no TAB.
                cards=obj['recovery_cards']
                if len(cards)!=12:raise CandidateError('J_CARD_COUNT')
                card_positions=[]
                for card_n,card in enumerate(cards,1):
                    if card['printed_tone_count']!=2:raise CandidateError('J_CARD_TONES')
                    for side in ('from_tone','to_tone'):
                        tone=card[side]
                        card_positions.append((('recovery_cards',card_n,side),
                            {'note_token':tone['note_token'],'role_token':tone['role_token'],
                             'source_refs':tone['source_refs'],'canonical_event_id':None,
                             'source_tab':None}))
                raw=card_positions+raw
            for path,pos in raw:
                record=normalized_position(pos,module,key,path,len(modules[module]['positions'])+1)
                modules[module]['positions'].append(record)
                all_positions.append(record)
            count+=len(raw)
        if count!=entry['printed_position_count']:raise CandidateError(f'SLICE_COUNT {key} {count}')
        for module,_ in sections:
            modules[module]['slices'].append({'slice_key':key,'pdf_pages':entry['pdf_pages'],
                'txt_lines':entry['txt_lines'],'printed_position_count':len([p for p in modules[module]['positions'] if p['slice_key']==key]),
                'candidate_ref':ref,'structured_source_candidate':obj})
        all_pages.extend(entry['pdf_pages']);spans.append((entry['txt_lines'][0],entry['txt_lines'][1]))
        sources.append({'slice_key':key,'candidate_ref':ref,'result_ref':entry['result_ref']})
    if sorted(all_pages)!=list(range(3,20)):raise CandidateError('PAGE_UNION')
    if any(spans[i][1]>=spans[i+1][0] for i in range(len(spans)-1)):raise CandidateError('TXT_OVERLAP')
    if {k:len(v['positions']) for k,v in modules.items()}!=EXPECTED or len(all_positions)!=640:
        raise CandidateError('MODULE_POSITION_COUNT')
    if len([x for x in modules['J']['positions'] if x['source_tab'] is None])!=24:
        raise CandidateError('J_TAB_ABSENCE')
    # Preserve whole document, source-only maps/instructions, and prior bounded findings verbatim.
    return {'schema':'fathom-level064-whole-detached-candidate-v1','level':64,'wbs_id':'2.3.1.2.1',
        'source':{'txt_path':TXT_REL.as_posix(),'txt_bytes':len(txt),'txt_sha256':digest(txt),'txt_lines':669,
                  'pdf_path':PDF_REL.as_posix(),'pdf_bytes':len(pdf),'pdf_sha256':digest(pdf),'pdf_pages':20},
        'source_map_boundary':_source_map(txt,pdf),'p01_index_ref':{'path':INDEX_REL.as_posix(),
              'bytes':len(idx),'sha256':digest(idx)},'p01_slices':sources,
        'modules':modules,'positions':all_positions,'module_printed_position_counts':EXPECTED,
        'complete_written_workout_printed_positions':640,'txt_document_text':txt.decode('utf-8'),
        'pdf_page_texts':[{'page':i,'text':text} for i,text in enumerate(pages,1)],
        'source_only_reference_pages':[1,2,20],
        'pdf_only_practice_log_fields':list(FIELDS),
        'source_discrepancies':[
          {'code':'PDF_ONLY_PRACTICE_LOG_FIELDS','source':'PDF p20','txt_scope':'lines 635-669',
           'detail':'Seven practice-log column labels appear in PDF and are absent from TXT.'},
          {'code':'P01_D_PAGE8_PART_LABEL','source':'PDF p8','p01_slice':'D-page-8',
           'detail':'PDF labels Part 2; P01 candidate source_scope.pdf_page_block says Part 1.'}],
        'other_source_limits':[
          'P01 Module B page-5 visual review reported a clipped top header/banner.',
          'Module J has 24 recovery-card note/role positions with no printed TAB.',
          'Tuning is unspecified; no sounding pitch is inferred from fret tokens.',
          '640 is the source-described printed-position count, not a performed or pitch-verified result.'],
        'canonical_item_id':None,'canonical_variant_id':None,'fixed_bpm':None,'note_per_click':None,
        'onset_q':None,'duration_q':None,'performed_result':None,'runtime_eligible':False,
        'runtime_admitted':False,'imported':False,'admitted':False,'curriculum_signoff':False}

def write_candidate(path:Path)->dict:
    build=ROOT/BUILD_REL
    if path.suffix!='.json' or path.is_symlink() or path.parent.is_symlink() or path.parent.resolve()!=build.resolve() or not build.resolve().is_relative_to(ROOT.resolve()):
        raise CandidateError('OUTPUT_OUTSIDE_LANE_BUILD')
    if path.exists():raise CandidateError('OUTPUT_EXISTS')
    c=build_candidate();build.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(c,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    with path.open('xb') as f:f.write(data)
    return {'path':str(path),'bytes':len(data),'sha256':digest(data),'modules':10,'positions':640}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    print(json.dumps(write_candidate(p.parse_args().output),sort_keys=True))

if __name__=='__main__':main()
