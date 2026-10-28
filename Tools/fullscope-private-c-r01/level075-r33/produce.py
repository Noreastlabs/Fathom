from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime, hashlib, json, resource, time
from tab_contacts import KEYS, parse_tab, muted_verse_grid
R=Path(__file__).resolve().parents[3]; L=Path('fullscope-private-c-r01/level075-r33')
started=datetime.datetime.now(datetime.timezone.utc).isoformat(); tick=time.monotonic()
def pin(p):
    p=Path(p); b=(R/p).read_bytes(); return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p; assert not p.exists(); p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][9:13]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']); txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[3].extract_text(); text=(R/txt).read_text(); lines=text.splitlines()
norm=lambda x:' '.join(x.split())
assert '8 ROLE CELLS | 128 CONTACTS' in page and 'Standard tuning.' in page
role_table=[
 ['Foundation','Roots + shell','Verse','Leave upper register open'],
 ['Comping','Triads / 7th shells','Chorus','Support groove, avoid lead register'],
 ['Counterline','2-4 note answer','Pre / Bridge','Answer vocal-space only'],
 ['Lead','Motif + targets','Solo','Rhythm guitar reduces density'],
 ['Silence','Rest / cue watch','Transitions','Prepare next entrance']]
for entry in role_table: assert norm(' '.join(entry)) in norm(page)
module_txt='128 contacts. Practice foundation, comping, counterline, lead, and silence roles. Change density and register without changing tempo.'
assert module_txt in text
payloads=[]; overlay=[]
pending=[
 [{'disposition':'LABEL_VOICING_RECONCILIATION_REQUIRED','reason':'Clean-triad last labelG with printed e1/B0/G0 derives F4/B3/G3. Retain both; no fret or label repair.'},
  {'disposition':'IMPLEMENTATION_OR_INTERPRETATION_PENDING','reason':'No fixed count grid is printed for four clean-triad groups.'}],
 [],
 [{'disposition':'IMPLEMENTATION_OR_INTERPRETATION_PENDING','reason':'Sixteenth count line is printed, but eight compressedTABattack groups require explicit reviewed onset mapping; raw character widths are not a timing grid.'}],
 [{'disposition':'LEARNER_CHOICE_OR_INTERPRETATION_REQUIRED','reason':'Source says fill begins afterbeat3; no exact start fraction, gate or11note spacing is printed.'}]]
for i, old in enumerate(rows):
    raw=old['source_payload']['pdf_region_text']; assert norm(raw) in norm(page)
    assert old['implementation']['events']==[]
    recovered=parse_tab(raw)
    assert len(recovered['events'])==(12,24,24,11)[i]
    source_lines=raw.splitlines(); tail=source_lines[-1]
    if i==1: recovered['events']=muted_verse_grid(old['package_key'],recovered['events'],tail)
    payload={'key':old['package_key'],'base_jsonl_line':i+10,'pdf_page':4,
             'label':old['source_payload']['printed_label'],'source_rows':recovered['rows'],
             'events':recovered['events'],'attack_group_count':recovered['attack_group_count'],
             'source_tail_instruction':tail,'fixed_bpm':None,'standard_tuning_printed':True,
             'timed_coordinate_class':'SOURCE_QUARTER_RELATIVE_NOT_NATIVE_VALIDATED' if i==1 else None,
             'pending':pending[i], 'simultaneous_group_rule':'same printed TAB column; group members are not sequential attacks'}
    payloads.append(payload)
    r=deepcopy(old); r['schema_version']='fathom-private-source-implementation.33'
    r['implementation']['events']=recovered['events']
    r['implementation']['source_contact_recovery']={k:v for k,v in payload.items() if k!='events'}
    r['implementation']['role_context']={'pdf_page':4,'table':role_table,'txt_module_line':lines.index(module_txt)+1,
                                         'txt_instruction':module_txt,'full_role_workflow_implemented':False,
                                         'silence_role_does_not_make_x_a_rest':True}
    r['unresolved_reasons']=pending[i]+[{'disposition':'PAGE_EXTENT_RECONCILIATION_REQUIRED',
        'reason':'8ROLECELLS/128CONTACTS header with four enumeratedcards;71printed string symbols are not128contacts. No addedkeys.'}]
    r['provenance']['contact_recovery_r33']={'base_packet':pin(base),'base_jsonl_line':i+10,
        'original_empty_events_were_unimplemented':True,'source_characters_recovered':True,
        'independent_source_review':'Pending','producer':'private producer C'}
    r['contract_capabilities'].update({'actual_fret_contacts':sum(e['fret'] is not None for e in recovered['events']),
        'ordered_pitch_or_contact_slots':len(recovered['events']),
        'muted_string_contacts':sum(e['kind']=='muted_string_stroke' for e in recovered['events']),
        'source_label_or_timing_review_pending':i!=1,'full_role_manual_workflow_complete':False})
    if i==1:
        r['contract_category']='TIMED_SOURCE_EVENT_CONTRACT'
        r['status']='PRIVATE_SOURCE_RELATIVE_EVENT_CONTRACT_PENDING_REVIEW'
        r['contract_capabilities']['timed_source_event_contract']=True
        r['timing_authority'].update({'printed_instruction_lines':[tail], 'onset_duration_resolved':True,
            'timed_source_slot_count':24,'timed_attack_group_count':8,'end_q':[4,1],
            'coordinate_class':'SOURCE_QUARTER_RELATIVE_NOT_NATIVE_VALIDATED',
            'sounded_gate_resolved':False,'span_semantics':'eighth-grid rhythmic slot, not measured sound duration',
            'producer_interpretations':['Pair the eight ordered and uniformly spaced TABattack groups with the eight explicit1&2&3&4&labels. Three stringcontacts share each attack.']})
    else:
        r['status']='SOURCE_CONTACTS_RECOVERED_INTERPRETATION_PENDING'
    overlay.append(r)
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),
    'method':'pypdf original text stream, no fresh visual QA','page':4,
    'literal_header':'8 ROLE CELLS | 128 CONTACTS','actual_card_count':4,
    'role_context_table':role_table,'module_txt_instruction':module_txt,'module_txt_line':lines.index(module_txt)+1,
    'cards':[{k:v for k,v in p.items() if k!='events'} for p in payloads],
    'source_contacts':71,'pitched_string_contacts':47,'muted_string_contacts':24,'rests':0})
payloadpath=Path('Build')/L/'source-contact-projection.json';write(payloadpath,{'cards':payloads})
packet=Path('Build')/L/'role-contact-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in overlay))
referral=Path('Results')/L/'source-questions.json'
write(referral,{'status':'PENDING_DISTINCT_SOURCE_DISPOSITION','original_pdf':pin(pdf),'original_txt':pin(txt),
    'base_packet':pin(base),'source_contact_projection':pin(payloadpath),'exact_keys':list(KEYS),
    'questions':[{'kind':'PAGE_EXTENT_RECONCILIATION','literal':'8 ROLE CELLS | 128 CONTACTS',
                  'actual':'four labeledTABcards;71string symbols,47numeric/24x','no_missing_key_invention':True},
                 {'kind':'LABEL_VOICING_RECONCILIATION','key':KEYS[0],'original_label':'G',
                  'printed_contacts':[{'string':'e','fret':1,'midi':65,'pitch':'F4'},
                                      {'string':'B','fret':0,'midi':59,'pitch':'B3'},
                                      {'string':'G','fret':0,'midi':55,'pitch':'G3'}],
                  'question':'How should the Clean-triad labelG and exact G/B/Fvoicing be represented? Preserve all source bytes; no G7rename/fret repair.'},
                 {'kind':'IMPLEMENTATION_INTERPRETATION_PENDING','key':KEYS[2],
                  'fact':'sixteenthcountline plus8TABgroups; exact onset mapping still requires finite interpretation'},
                 {'kind':'LEARNER_CHOICE_OR_INTERPRETATION_PENDING','key':KEYS[3],
                  'fact':'11ordered notes, startafterbeat3; exactspacing/startfraction notprinted'}],
    'source_conflict_count_increment':0,'source_acceptance':False,'canonical_ids':False})
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,
      'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      'base_packet':pin(base),'overlay':pin(packet),'source_projection':pin(payloadpath),
      'source_check':pin(source),'source_questions':pin(referral),
      'model':pin(Path('Tools')/L/'tab_contacts.py'),'exact_replaced_keys':list(KEYS),
      'attempted':4,'source_supported_timed_event_contracts':1,'partial_unresolved':3,'unattempted':0,
      'recovered_source_contacts':71,'pitched':47,'muted':24,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
