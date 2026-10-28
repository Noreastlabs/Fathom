#!/usr/bin/env python3
"""Assemble a detached Level-72 A–K structured source workbook."""
from __future__ import annotations
import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
STEM='Guitar_Exercises_Section_IX_Level_72_D_Lydian_Dominant_G_Sharp_Altered_Tritone_Substitution_Applied_Dominants_and_Melodic_Minor_Improvisation_Synthesis'
TXT_REL=Path('Notes/music/guitar project/TXT version')/(STEM+'.txt')
PDF_REL=Path('Notes/music/guitar project/PDF version')/(STEM+'.pdf')
INDEX_REL=Path('Build/parallel-06/2.3-level072-whole-coverage-r01/index-01.json')
MAP_REL=Path('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv')
BUILD_REL=Path('Build/parallel-09/2.3.1.2.1-level072-whole-r01')
PINS={'txt':(24210,'9b025956b8a25c6f699056ee1f518c891c7234d63e8d90e33c365d08285e0703'),
      'pdf':(51052,'ec75af38d79de7bd02176315e872a7731f9af15df78e72d50fc81c5528075426'),
      'index':(37666,'9e82c33d8c416f46ead288b99b9c57321b2b39bf6da9e11ed2e365684a1c8a8c')}
EXPECTED={'A':80,'B':48,'C':80,'D':48,'E':40,'F':80,'G':80,'H':64,'I':32,'J':64,'K':24}

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

def source_map(txt:bytes,pdf:bytes)->dict:
    with valid_path(MAP_REL).open(newline='') as f:
        rows=[r for r in csv.DictReader(f,delimiter='\t') if r['level']=='72']
    if len(rows)!=1:raise CandidateError('SOURCE_MAP_ROW')
    r=rows[0]
    expected={'wbs_owner':'2.3.1.2.1','txt_path':TXT_REL.as_posix(),'txt_bytes':str(len(txt)),
              'txt_sha256':digest(txt),'pdf_path':PDF_REL.as_posix(),'pdf_bytes':str(len(pdf)),
              'pdf_sha256':digest(pdf),'review':'Pending','conversion_status':'not_converted','representative_item_id':''}
    if any(r.get(k)!=v for k,v in expected.items()):raise CandidateError('SOURCE_MAP_DRIFT')
    if any(r.get(k)!='False' for k in ('stable_ids_assigned','runtime_eligible','imported','admitted')):
        raise CandidateError('SOURCE_MAP_ADMISSION')
    return {k:r[k] for k in expected}

def pointer(obj:dict,raw:str):
    if not raw.startswith('/modules/'):raise CandidateError('POINTER_PATH')
    value=obj
    for token in raw.lstrip('/').split('/'):
        value=value[int(token)] if isinstance(value,list) else value[token]
    return value

def normalized_contact(contact:dict,record_key:str,module:str,ordinal:int)->dict:
    note=contact.get('printed_note');role=contact.get('printed_role') or contact.get('printed_degree')
    if not isinstance(note,str) or not isinstance(role,str):raise CandidateError('CONTACT_TOKEN')
    if not isinstance(contact.get('string'),str) or not isinstance(contact.get('fret'),int):
        raise CandidateError('CONTACT_TAB')
    if contact.get('onset_q','missing') is not None or contact.get('duration_q','missing') is not None:
        raise CandidateError('CONTACT_TIMING')
    return {'module':module,'qualified_source_key':record_key,'source_order':ordinal,
            'printed_note':note,'printed_role_or_degree':role,'printed_pick':contact.get('printed_pick'),
            'string':contact['string'],'fret':contact['fret'],'source_refs':contact['source_refs'],
            'canonical_event_id':None,'onset_q':None,'duration_q':None,'performed_result':None}

def build_candidate(*,txt_data:bytes|None=None,pdf_data:bytes|None=None,index_data:bytes|None=None,
                    batch_overrides:dict[str,bytes]|None=None)->dict:
    txt=txt_data if txt_data is not None else valid_path(TXT_REL).read_bytes()
    pdf=pdf_data if pdf_data is not None else valid_path(PDF_REL).read_bytes()
    idx=index_data if index_data is not None else valid_path(INDEX_REL).read_bytes()
    for key,data in (('txt',txt),('pdf',pdf),('index',idx)):pin(data,key)
    lines=txt.decode('utf-8').splitlines()
    pages=[p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines)!=614 or len(pages)!=20:raise CandidateError('SOURCE_BOUNDARY')
    index=json.loads(idx)
    if index['source_pair']['txt']['sha256']!=digest(txt) or index['source_pair']['pdf']['sha256']!=digest(pdf):
        raise CandidateError('INDEX_SOURCE_DRIFT')
    if index['indexed_record_count']!=73 or index['indexed_printed_contacts']!=640 or index['indexed_module_count']!=11:
        raise CandidateError('INDEX_COUNTS')
    if index['exceptions'] or index['whole_workbook_complete'] or index['runtime_eligible']:
        raise CandidateError('INDEX_STATE')
    if '640 sounding tones' not in txt.decode('utf-8') or '640' not in pages[0]:
        raise CandidateError('WORKLOAD_DECLARATION')
    batches={};batch_refs=[]
    for ref in index['candidate_inputs']:
        path=ref['candidate_path'];data=(batch_overrides or {}).get(path)
        if data is None:data=valid_path(Path(path)).read_bytes()
        if len(data)!=ref['candidate_bytes'] or digest(data)!=ref['candidate_sha256']:
            raise CandidateError(f'PINNED_BATCH_DRIFT {path}')
        obj=json.loads(data)
        if obj['contact_count']!=ref['printed_contact_count'] or ''.join(obj['modules'])!=ref['modules']:
            raise CandidateError('BATCH_SCOPE')
        if any(obj[k] for k in ('admitted','imported','runtime_eligible','whole_workbook_complete')):
            raise CandidateError('BATCH_ADMISSION')
        if obj['canonical_ids'] is not None or obj['review']!='Pending':raise CandidateError('BATCH_IDENTITY')
        if obj['source']['txt_sha256']!=digest(txt) or obj['source']['pdf_sha256']!=digest(pdf):
            raise CandidateError('BATCH_SOURCE_DRIFT')
        batches[path]=obj;batch_refs.append(ref)
    if len(batches)!=3 or set(''.join(''.join(b['modules']) for b in batch_refs))!=set(EXPECTED):
        raise CandidateError('BATCH_UNION')
    modules={module:{'module':module,'candidate_path':entry['candidate_path'],
        'printed_contact_count':entry['printed_contact_count'],'record_count':entry['record_count'],
        'pdf_pages':entry['pdf_pages'],'structured_source_module':pointer(batches[entry['candidate_path']],entry['candidate_module_pointer'])}
        for module,entry in ((e['module'],e) for e in index['module_index'])}
    if list(modules)!=list(EXPECTED):raise CandidateError('MODULE_ORDER')
    ordered=[];contacts=[];seen=set()
    for source_order,entry in enumerate(index['source_order_entries'],1):
        module=entry['module'];key=entry['qualified_source_key'];path=entry['candidate_path']
        if key in seen or key!=module+'/'+entry['source_local_key']:raise CandidateError('RECORD_KEY')
        seen.add(key)
        record=pointer(batches[path],entry['candidate_record_pointer'])
        if record['local_key']!=entry['source_local_key'] or record['pdf_page']!=entry['source_pdf_page']:
            raise CandidateError('RECORD_POINTER')
        if record['txt_line_span']!=entry['source_txt_line_span'] or len(record['contacts'])!=entry['printed_contact_count']:
            raise CandidateError('RECORD_SCOPE')
        a,b=entry['source_txt_line_span']
        if not (1<=a<=b<=614) or not (1<=entry['source_pdf_page']<=20):raise CandidateError('RECORD_SOURCE_BOUNDARY')
        if record.get('printed_heading','') not in '\n'.join(lines[a-1:b]):
            # PDF-only headings in later batches are preserved but need not be identical to TXT.
            if module in 'ABCDEFGH':raise CandidateError('RECORD_HEADING_TXT')
        normalized=[]
        for local_order,c in enumerate(record['contacts'],1):
            refs=c['source_refs']
            if refs['pdf_page']!=entry['source_pdf_page'] or not (a<=refs['txt_note_line']<=b):
                raise CandidateError('CONTACT_PROVENANCE')
            n=normalized_contact(c,key,module,local_order)
            normalized.append(n);contacts.append(n)
        ordered.append({'source_order':source_order,'module':module,'qualified_source_key':key,
            'source_local_key':entry['source_local_key'],'pdf_page':entry['source_pdf_page'],
            'txt_line_span':entry['source_txt_line_span'],'contact_count':len(normalized),
            'contacts':normalized,'structured_source_record':record})
    if len(ordered)!=73 or len(contacts)!=640 or {m:sum(x['contact_count'] for x in ordered if x['module']==m) for m in EXPECTED}!=EXPECTED:
        raise CandidateError('WHOLE_COUNT')
    if [m['printed_contact_count'] for m in modules.values()]!=list(EXPECTED.values()):
        raise CandidateError('MODULE_COUNT')
    k=modules['K']['structured_source_module']
    if len(k['source_differences'])!=4 or len(k['practice_log_pdf_only']['labels'])!=8:
        raise CandidateError('K_SOURCE_DIFFERENCES')
    if any(label not in pages[19] for label in k['practice_log_pdf_only']['labels']):
        raise CandidateError('K_PDF_LOG')
    if 'C (B# over G#7)' not in txt.decode('utf-8'):
        raise CandidateError('SHARED_TRITONE')
    return {'schema':'fathom-level072-whole-detached-candidate-v1','level':72,'wbs_id':'2.3.1.2.1',
        'source':{'txt_path':TXT_REL.as_posix(),'txt_bytes':len(txt),'txt_sha256':digest(txt),'txt_lines':614,
                  'pdf_path':PDF_REL.as_posix(),'pdf_bytes':len(pdf),'pdf_sha256':digest(pdf),'pdf_pages':20},
        'source_map_boundary':source_map(txt,pdf),'coverage_index_ref':{'path':INDEX_REL.as_posix(),
                  'bytes':len(idx),'sha256':digest(idx)},'batch_refs':batch_refs,
        'modules':modules,'records':ordered,'contacts':contacts,'module_printed_contact_counts':EXPECTED,
        'record_count':73,'complete_written_workout_contacts':640,
        'txt_document_text':txt.decode('utf-8'),
        'pdf_page_texts':[{'page':i,'text':text} for i,text in enumerate(pages,1)],
        'source_only_front_matter_txt_span':[1,32],
        'source_differences':k['source_differences'],
        'pdf_only_practice_log':k['practice_log_pdf_only'],
        'three_pass_capstone':k['three_pass_capstone'],
        'source_count_interpretation':'640 distinct printed contacts; three performance passes do not multiply the written count.',
        'canonical_item_id':None,'canonical_variant_id':None,'fixed_bpm':None,
        'note_per_click':None,'onset_q':None,'duration_q':None,'performed_result':None,
        'runtime_eligible':False,'runtime_admitted':False,'imported':False,'admitted':False,
        'curriculum_signoff':False}

def write_candidate(path:Path)->dict:
    build=ROOT/BUILD_REL
    if path.suffix!='.json' or path.is_symlink() or path.parent.is_symlink() or path.parent.resolve()!=build.resolve() or not build.resolve().is_relative_to(ROOT.resolve()):
        raise CandidateError('OUTPUT_OUTSIDE_LANE_BUILD')
    if path.exists():raise CandidateError('OUTPUT_EXISTS')
    c=build_candidate();build.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(c,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    with path.open('xb') as f:f.write(data)
    return {'path':str(path),'bytes':len(data),'sha256':digest(data),'modules':11,'records':73,'contacts':640}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    print(json.dumps(write_candidate(p.parse_args().output),sort_keys=True))
if __name__=='__main__':main()
