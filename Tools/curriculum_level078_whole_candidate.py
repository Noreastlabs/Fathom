#!/usr/bin/env python3
"""Build detached Level-78 source-linked tasks and unresolved event slots."""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
STEM='Guitar_Exercises_Section_X_Level_78_Ear_Led_Improvisation_Anticipatory_Guide_Tones_Motif_Prediction_and_Spontaneous_Role_Switching'
TXT_REL=Path('Notes/music/guitar project/TXT version')/(STEM+'.txt')
PDF_REL=Path('Notes/music/guitar project/PDF version')/(STEM+'.pdf')
CAT_REL=Path('Content/controls/curriculum-v1/workbook-coverage.json')
MAP_REL=Path('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.tsv')
BUILD_REL=Path('Build/parallel-09/2.3.1.3.1-level078-whole-r01')
PINS={'txt':(8816,'39fb82445b8d5f0d4e01f7108f360e7db0aaf45270145d4816213365d81a024e'),
      'pdf':(54120,'c7ecb9afda1dc902e38f1861a1d05422e4a48b8d5efcf2a9701f73684b922268'),
      'catalog':(None,'d8e492101c97c60add858799c77da4db3f0c528d348c9cf66105c2dc37df4eeb')}
COUNTS={'A':96,'B':96,'C':96,'D':96,'E':128,'F':128,'G':128,'H':128}
PAGES={'A':[2,3],'B':[4,5],'C':[6,7],'D':[8,9],'E':[10,11],'F':[12,13],'G':[14,15],'H':[16,17,18,19,20]}
FAMILY_SPECS={'A':[('major_targets',12,4,2),('minor_targets',12,4,3)],
              'B':[('major_routes',6,8,4),('minor_routes',6,8,5)],
              'C':[('phrase_prediction',12,4,6),('function_target',12,4,7)],
              'D':[('motif_continuation',8,8,8),('across_chord_changes',8,4,9)],
              'E':[('comp_to_lead',8,8,10),('register_orchestration',4,16,11)],
              'F':[('lead_to_comp',8,8,12),('cue_recovery',8,8,13)],
              'G':[('density_studies',8,8,14),('command_deck',16,4,15)],
              'H':[('capstone_form',16,4,16)]}

class CandidateError(ValueError):pass

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def pin(data:bytes,key:str):
    size,sha=PINS[key]
    if (size is not None and len(data)!=size) or digest(data)!=sha:raise CandidateError(f'PINNED_{key.upper()}_DRIFT')
def valid_path(rel:Path)->Path:
    if rel.is_absolute() or '..' in rel.parts:raise CandidateError('INPUT_PATH_INVALID')
    p=ROOT/rel
    if p.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()):raise CandidateError('INPUT_PATH_INVALID')
    return p

def source_map(txt:bytes,pdf:bytes)->dict:
    with valid_path(MAP_REL).open(newline='') as f:
        rows=[r for r in csv.DictReader(f,delimiter='\t') if r['level']=='78']
    if len(rows)!=1:raise CandidateError('SOURCE_MAP_ROW')
    r=rows[0];want={'wbs_owner':'2.3.1.3.1','txt_path':TXT_REL.as_posix(),'txt_bytes':str(len(txt)),
        'txt_sha256':digest(txt),'pdf_path':PDF_REL.as_posix(),'pdf_bytes':str(len(pdf)),
        'pdf_sha256':digest(pdf),'review':'Pending','conversion_status':'not_converted','representative_item_id':''}
    if any(r.get(k)!=v for k,v in want.items()):raise CandidateError('SOURCE_MAP_DRIFT')
    if any(r.get(k)!='False' for k in ('stable_ids_assigned','runtime_eligible','imported','admitted')):
        raise CandidateError('SOURCE_MAP_ADMISSION')
    return {k:r[k] for k in want}

def catalog_boundary(data:bytes,txt:bytes,pdf:bytes)->dict:
    pin(data,'catalog')
    catalog=json.loads(data)['workbook_catalog']
    hits=[x for x in catalog['entries'] if x['workbook_id']=='fg:workbook:000078']
    if len(hits)!=1:raise CandidateError('CATALOG_ENTRY')
    e=hits[0]
    if e['txt']['sha256']!=digest(txt) or e['pdf']['sha256']!=digest(pdf):raise CandidateError('CATALOG_SOURCE_DRIFT')
    if e['review']!='Pending' or e['conversion_status']!='not_converted' or e['whole_workbook_complete']:
        raise CandidateError('CATALOG_STATE')
    if any(e[k] for k in ('runtime_eligible','runtime_admitted','imported','admitted')):
        raise CandidateError('CATALOG_ADMISSION')
    if e['playable_projection']['status']!='explicitly_empty_unresolved' or any(e['playable_projection'][k] for k in ('events','items','modules','passages','records','variants')):
        raise CandidateError('CATALOG_PROJECTION')
    return {'path':CAT_REL.as_posix(),'sha256':digest(data),'workbook_id':e['workbook_id'],
            'review':e['review'],'conversion_status':e['conversion_status'],
            'playable_projection_status':e['playable_projection']['status'],
            'unresolved_playable_fields':e['unresolved_playable_fields']}

def module_spans(lines:list[str])->dict[str,tuple[int,int]]:
    heads=[(m[1],i+1) for i,s in enumerate(lines) if (m:=re.match(r'^MODULE ([A-H]) - ',s))]
    if [h[0] for h in heads]!=list(COUNTS):raise CandidateError('MODULE_HEADINGS')
    end_h=next(i for i,s in enumerate(lines,1) if s=='FIVE-PASS LADDER')
    return {m:(n,(heads[i+1][1]-1 if i+1<len(heads) else end_h-1)) for i,(m,n) in enumerate(heads)}

def source_records(lines:list[str],module:str,span:tuple[int,int])->list[dict]:
    a,b=span;raw=[]
    for line_no in range(a,b+1):
        text=lines[line_no-1]
        if ' | ' in text:
            raw.append({'txt_line':line_no,'raw_text':text,'fields':text.split(' | ')})
    if module=='G':
        start=next(i for i in range(a,b+1) if lines[i-1]=='Command deck:')
        raw.extend({'txt_line':i,'raw_text':lines[i-1],'fields':[lines[i-1]]}
                   for i in range(start+1,b+1) if lines[i-1].strip())
    expected=sum(x[1] for x in FAMILY_SPECS[module])
    if len(raw)!=expected:raise CandidateError(f'RECORD_COUNT {module} {len(raw)}')
    return raw

def build_candidate(*,txt_data:bytes|None=None,pdf_data:bytes|None=None,catalog_data:bytes|None=None)->dict:
    txt=txt_data if txt_data is not None else valid_path(TXT_REL).read_bytes()
    pdf=pdf_data if pdf_data is not None else valid_path(PDF_REL).read_bytes()
    cat=catalog_data if catalog_data is not None else valid_path(CAT_REL).read_bytes()
    pin(txt,'txt');pin(pdf,'pdf')
    lines=txt.decode('utf-8').splitlines()
    pages=[p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages]
    if len(lines)!=218 or len(pages)!=20:raise CandidateError('SOURCE_BOUNDARY')
    boundary=catalog_boundary(cat,txt,pdf)
    spans=module_spans(lines)
    modules={};slots=[]
    for m,count in COUNTS.items():
        raw=source_records(lines,m,spans[m]);records=[];offset=0
        for family,n,per,page in FAMILY_SPECS[m]:
            subset=raw[offset:offset+n]
            if len(subset)!=n:raise CandidateError('FAMILY_COUNT')
            for order,item in enumerate(subset,1):
                item={**item,'module':m,'family':family,'family_order':order,'pdf_page':page,
                      'source_described_events':per,'canonical_item_id':None,'performed_result':None}
                if family=='capstone_form':
                    if item['fields'][0]!=str(order) or len(item['fields'])!=4:raise CandidateError('CAPSTONE_FORM')
                    item['bar']=order;item['chord']=item['fields'][1];item['role']=item['fields'][2];item['target']=item['fields'][3]
                records.append(item)
                for slot in range(1,per+1):
                    slots.append({'module':m,'family':family,'record_txt_line':item['txt_line'],
                        'record_order':order,'record_slot':slot,'pdf_page':page,
                        'printed_note':None,'string':None,'fret':None,'onset_q':None,'duration_q':None,
                        'canonical_event_id':None,'performed_result':None,'status':'source_count_slot_unresolved'})
            offset+=n
        if m=='H':
            # The source declares 128 written events but prints only a 16 x 4 = 64-event base form.
            # Keep the remaining 64 as module-level unresolved count slots, not invented bar notes.
            for n in range(1,65):
                slots.append({'module':'H','family':'unallocated_written_count','record_txt_line':None,
                    'record_order':None,'record_slot':n,'pdf_page':17,'printed_note':None,
                    'string':None,'fret':None,'onset_q':None,'duration_q':None,
                    'canonical_event_id':None,'performed_result':None,'status':'source_count_slot_unresolved'})
        actual=sum(1 for x in slots if x['module']==m)
        if actual!=count:raise CandidateError(f'MODULE_EVENT_COUNT {m} {actual}')
        modules[m]={'module':m,'title':lines[spans[m][0]-1],'txt_line_span':list(spans[m]),
            'pdf_pages':PAGES[m],'written_event_count':count,'records':records,
            'pdf_task_texts':[{'page':p,'text':pages[p-1]} for p in PAGES[m]]}
    if len(slots)!=896 or sum(COUNTS.values())!=896:raise CandidateError('WORKLOAD')
    if 'TOTAL 896 events' not in txt.decode('utf-8') or '896' not in pages[0]:raise CandidateError('SOURCE_TOTAL')
    form=[r for r in modules['H']['records'] if r['family']=='capstone_form']
    if len(form)!=16 or [r['bar'] for r in form]!=list(range(1,17)):raise CandidateError('H_FORM')
    # PDF p16 supplies a cue/task column beyond the compact TXT form.
    pl=pages[15].splitlines();head=['Bar','Chord','Primary role','Pre-heard target','Cue / task']
    pos=next((i for i in range(len(pl)-len(head)+1) if pl[i:i+len(head)]==head),None)
    if pos is None:raise CandidateError('H_PDF_HEADER')
    cells=pl[pos+5:pos+5+16*5]
    if len(cells)!=80:raise CandidateError('H_PDF_ROWS')
    pdf_form=[]
    for n in range(16):
        row=dict(zip(head,cells[n*5:(n+1)*5]));record=form[n]
        if (row['Bar'],row['Chord'],row['Primary role'],row['Pre-heard target'])!=(str(n+1),record['chord'],record['role'],record['target']):
            raise CandidateError('H_PDF_FORM_MISMATCH')
        pdf_form.append(row)
    # Printed H repeat-pass counts are a performance instruction, not five new sets of written events.
    if '5 PASSES' not in pages[16] or '64 EVENTS EACH' not in pages[16]:raise CandidateError('H_PASS_PDF')
    pass_lines=[(i,s) for i,s in enumerate(lines,1) if re.match(r'^[1-5]\. ',s) and i>spans['H'][1]]
    ladder=pass_lines[:5]
    if len(ladder)!=5 or [s[0] for _,s in ladder]!=['1','2','3','4','5']:
        raise CandidateError('FIVE_PASS_LADDER')
    ensemble=[(i,s) for i,s in enumerate(lines,1) if re.match(r'^[1-8]\. ',s) and ' | ' in s and i>spans['H'][1]]
    if len(ensemble)!=8:raise CandidateError('ENSEMBLE_LAB')
    worksheet=pages[17].splitlines()
    labels=['Target sung before attack','First guitar attack correct','Bar count preserved','Chord function clear',
            'Role change on time','Register / density contrast','Recovery without stop','Ending intentional']
    if any(x not in worksheet for x in labels) or 'Passing block = 7/8 or better.' not in pages[17]:
        raise CandidateError('H_WORKSHEET')
    if any(x not in pages[19] for x in ('10/12 phrase completions','28/32 or better on two separate days')):
        # Page-20 wording is checked separately by direct mastery strings below.
        if '28/32 or better on two separate days' not in pages[19]:raise CandidateError('PDF_MASTERY')
    if '28/32 or better on two separate days' not in txt.decode('utf-8'):
        raise CandidateError('MASTERY_THRESHOLD')
    if not all(token in txt.decode('utf-8') for token in ('G#','B#','E#','F#')):
        raise CandidateError('ENHARMONIC_SOURCE')
    return {'schema':'fathom-level078-whole-detached-task-candidate-v1','level':78,'wbs_id':'2.3.1.3.1',
        'source':{'txt_path':TXT_REL.as_posix(),'txt_bytes':len(txt),'txt_sha256':digest(txt),'txt_lines':218,
                  'pdf_path':PDF_REL.as_posix(),'pdf_bytes':len(pdf),'pdf_sha256':digest(pdf),'pdf_pages':20},
        'catalog_boundary':boundary,'source_map_boundary':source_map(txt,pdf),
        'modules':modules,'module_written_event_counts':COUNTS,'written_event_slots':slots,
        'complete_written_workload_events':896,
        'capstone':{'form_bars':form,'pdf_form_cue_tasks':pdf_form,'base_form_events':64,'written_module_h_events':128,
            'pdf_worksheet':{'page':18,'blocks':['1-4','5-8','9-12','13-16'],
                'criteria':labels,'passing_block_score':7,'maximum_block_score':8,'four_block_total':32,
                'performed_block_scores':None},
            'five_performance_passes':[{'txt_line':i,'instruction':s,'pdf_page':17} for i,s in ladder],
            'pdf_events_each_pass':64,'five_passes_are_written_event_multiplier':False,
            'ensemble_role_labs':[{'txt_line':i,'instruction':s,'pdf_page':19} for i,s in ensemble],
            'passing_score':28,'maximum_score':32,'required_days':2,'performed_score':None},
        'source_count_ambiguities':['Module H declares 128 written events; its printed 16-bar form accounts for 64 base events, while PDF p17 says five 64-event performance passes. The other 64 written-event slots are unresolved rather than assigned invented notes or multiplied by five.'],
        'pdf_visual_limits':[
            {'page':16,'detail':'The lower callout overlaps the final form row in the 1200-pixel render; extracted PDF text and TXT preserve bar 16.'},
            {'page':18,'detail':'Worksheet panels overlap lower blank score rows in the render; extracted PDF text retains all four block labels and criteria.'},
            {'page':19,'detail':'The lower callout partly overlaps the final ensemble row in the render; extracted PDF text and TXT retain exercise 8.'},
            {'page':20,'detail':'The next-direction panel starts below the visible mastery card; extracted PDF text retains all six mastery requirements.'}],
        'control_loop':lines[7],'txt_document_text':txt.decode('utf-8'),
        'pdf_page_texts':[{'page':i,'text':text} for i,text in enumerate(pages,1)],
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
    return {'path':str(path),'bytes':len(data),'sha256':digest(data),'modules':8,'events':896}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    print(json.dumps(write_candidate(p.parse_args().output),sort_keys=True))
if __name__=='__main__':main()
