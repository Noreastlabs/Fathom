#!/usr/bin/env python3
"""Finite causal tests for symbolic source ownership; no native/audio simulation."""
import copy,hashlib,importlib.util,json,resource,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];LANE='fullscope-private-a-r01'
spec=importlib.util.spec_from_file_location('actions',ROOT/f'Tools/{LANE}/level048-symbolic-action-segments-r01/actions.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[json.loads(x) for x in (ROOT/f'Build/{LANE}/level048-r05/packet.jsonl').read_text().splitlines()][:5]
new=[json.loads(x) for x in (ROOT/f'Build/{LANE}/level048-r06/packet.jsonl').read_text().splitlines()][:5]
start=time.perf_counter();positive=[];negative=[]
for i,(r,n) in enumerate(zip(records,new),1):
 out=m.build(r)
 assert out==m.build(copy.deepcopy(r))==n['implementation']['symbolic_action_segments']
 assert sum(x['new_pick_attack'] for x in out['actions'])==r['implementation']['picked_attack_count']
 for action in out['actions']:
  if action['kind']=='hold':
   assert not action['new_pick_attack'] and action['owner_event_ordinal']==r['implementation']['sounding_events'][-1]['ordinal']
 final=out['contact_segments'][-1]
 assert (final['end_reason']=='printed_scope_ends_release_unselected')==(i in (3,4))
 assert not final['end_is_numeric_acoustic_noteoff']
 protocol=m.practice(r);gap=protocol['steps'][1]['source_prescribed_rehearsal_schedule'][1]
 assert gap=={'practice_bar':2,'kind':'full_bar_silence','source_beats':4,'sounded_events':[]}
 assert protocol['steps'][4]['replacement_event_ordinal']==r['implementation']['sounding_events'][-1]['ordinal']
 positive.append({'row':i,'deterministic_materialized_contract_equal':True,'source_picks_and_hold_end_policy':True,'silent_rehearsal_and_final_choice':True})
def orphan_hold(r):
 s=r['implementation']['symbolic_count_slots'][0];s.update(kind='hold',note='=',attack_mark='=',source_contact_ordinals=[])
def legato_after_rest(r):
 s=r['implementation']['symbolic_count_slots'][1];s.update(kind='rest',note='r',attack_mark='r',source_contact_ordinals=[])
 r['implementation']['symbolic_count_slots'][3]['attack_mark']='h'
 r['implementation']['sounding_events'][2].update(attack='hammer_on',pick_attack=False)
mutations=[('orphan initial hold',orphan_hold),
 ('legato after silence',legato_after_rest),
 ('unpicked destination re-picked',lambda r:r['implementation']['sounding_events'][1].update(pick_attack=True)),
 ('unpicked destination changes string',lambda r:r['implementation']['sounding_events'][1].update(string_label='G')),
 ('rest has an attack',lambda r:r['implementation']['symbolic_count_slots'][2].update(attack_mark='P')),
 ('hold receives a contact',lambda r:r['implementation']['symbolic_count_slots'][14].update(source_contact_ordinals=[11])),
 ('source event missing',lambda r:r['implementation']['sounding_events'].pop()),
 ('source note mismatch',lambda r:r['implementation']['symbolic_count_slots'][0].update(note='C#')),
 ('slot order scrambled',lambda r:r['implementation']['symbolic_count_slots'].reverse()),
 ('duplicated event join',lambda r:r['implementation']['sounding_events'].append(copy.deepcopy(r['implementation']['sounding_events'][0])))]
for name,change in mutations:
 r=copy.deepcopy(records[0]);change(r)
 try:m.build(r)
 except ValueError as e:negative.append({'case':name,'refusal':str(e)})
 else:raise AssertionError(name)
report={'status':'PASS','positive_finite_cases':positive,'causal_refusals':negative,
 'positive_cases':len(positive),'negative_cases':len(negative),'native_app_audio_tests':'NOT_RUN',
 'elapsed_seconds':time.perf_counter()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
p=ROOT/f'Results/{LANE}/level048-r06/action-tests.json'
with p.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','positive_cases':len(positive),'causal_refusals':len(negative),'report_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
