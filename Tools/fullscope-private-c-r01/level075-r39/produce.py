from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from transition_contract import KEYS,ROWS,PROFILES,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r39')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
reconciled=Path('Build/fullscope-private-c-r01/source-layout-r13/source-reconciliation-overlays.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
assert pin(reconciled)['sha256']=='601142999969d3c2c2b75547f5b57f4842fb1616a76f0b8f43491a82968a06da'
base_rows=[json.loads(x) for x in (R/base).read_text().splitlines()];r13=[json.loads(x) for x in (R/reconciled).read_text().splitlines()]
base_lines=list(range(44,53));rows=base_rows[43:52];rows[6:8]=r13[:2]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[11].extract_text();norm=lambda x:' '.join(x.split());lines=page.splitlines();matches=[]
for i,row in enumerate(ROWS):
    literal='\n'.join([row[1],row[2],row[3],'loop last bar + first bar']);assert page.count(literal)==1
    matches.append({'key':KEYS[i],'physical_page':12,'original_fields_text':literal,'text_stream_start_line':lines.index(row[1])+1,
        'effective_input':{**pin(reconciled if i in (6,7) else base),'jsonl_line':i-5 if i in (6,7) else base_lines[i]},
        'visibility':'r13 original underlayer, visually occluded' if i in (6,7) else 'original text-stream row; no new render'})
for text in ('15 RISK CELLS | 120 CONTACTS','Old section: 4 structural attacks','Cue:        received during attacks 3-4',
    'New section: 4 destination attacks','Repeat x 4 without extra count-in.','Then embed inside 4 bars before + 4 bars after.'):
    assert text in page
assert contract(0)['source_criterion'] in norm(page)
txtlines=(R/txt).read_text().splitlines();contexts=[]
for name,(start,chords,instruction) in PROFILES.items():
    header=f'{name}: bars {start}-{start+len(chords)-1}';h=txtlines.index(header)
    block=[header,'Chords: '+' | '.join(chords),instruction];assert txtlines[h:h+3]==block
    contexts.append({'profile':name,'original_txt_lines':block,'line_start':h+1,'line_end':h+3})
module='120 contacts. Loop the last bar of the old section and first bar of the new section. Reduce click support from every quarter to section starts only.'
assert module in txtlines
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'r13_reconciled_packet':pin(reconciled),
    'physical_page':12,'original_page_text':page,'matched_risk_rows':matches,
    'existing_loop_supplement':{'key':KEYS[8],'base_jsonl_line':52},'master_txt_profiles':contexts,
    'module_txt_instruction':module,'module_txt_line':txtlines.index(module)+1,
    'scope_note':'Click-reduction task is a separate existing page13 child, untouched. Current loop obligations come frompage12.',
    'method':'original PDF text stream and TXT exact joins; r13 visual/underlayer custody preserved by reference, no new rendered inspection'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.39';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'transition_contract.py'),'class':'TransitionFlow','pure_python_reference':True}
    if i in (6,7):
        for f in r['field_limitations']:
            if f['field']=='remaining_implementation':f['status']='Private complete manual source-choice contract added inr39; fixed playback/native realization not supplied.'
    r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_AND_EXTERNAL_CUE_REQUIRED',
        'reason':'Manual contract complete privately. Fixed source pitches/onsets/gates absent; chosen voiced realization and external cue are not actual app playback.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities'].update({'complete_manual_response_contract':True,'harmonic_attack_slots_without_fixed_pitch':8})
    r['provenance']['manual_r39']={'base_packet':pin(base),'base_jsonl_line':base_lines[i],
        'effective_prior':{**pin(reconciled if i in (6,7) else base),'jsonl_line':i-5 if i in (6,7) else base_lines[i]},
        'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending',
        'source_reconciliation_is_retained_r13_historical_snapshot':i in (6,7),'note_or_source_timing_invented':False}
    out.append(r)
packet=Path('Build')/L/'transition-risk-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'r13_reconciled_packet':pin(reconciled),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'transition_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':9,'source_supported_manual_contracts':9,'partial_unresolved':0,'unattempted':0,
    'source_contacts_added':0,'abstract_source_attack_slots':72,'new_official_keys':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
