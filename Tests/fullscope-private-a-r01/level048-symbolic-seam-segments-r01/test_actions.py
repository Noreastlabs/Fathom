#!/usr/bin/env python3
"""Finite seam ownership checks, exact source joins and source-guidance retention."""
import copy,hashlib,importlib.util,json,resource,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];LANE='fullscope-private-a-r01'
spec=importlib.util.spec_from_file_location('actions',ROOT/f'Tools/{LANE}/level048-symbolic-seam-segments-r01/actions.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=[json.loads(x) for x in (ROOT/f'Build/{LANE}/level048-r06/packet.jsonl').read_text().splitlines()][5:9]
new=[json.loads(x) for x in (ROOT/f'Build/{LANE}/level048-r07/packet.jsonl').read_text().splitlines()][5:9]
start=time.perf_counter();positive=[];negative=[]
for i,(before,after) in enumerate(zip(old,new),6):
 out=m.build(before)
 assert out==m.build(copy.deepcopy(before))==after['implementation']['symbolic_action_segments']
 assert sum(x['new_pick_attack'] for x in out['actions'])==before['implementation']['picked_attack_count']
 for action in out['actions']:
  if action['kind']=='hold':
   previous=max((s for s in out['contact_segments'] if s['source_start']['bar']==action['source_position']['bar']),key=lambda s:s['event_ordinal'])
   assert action['owner_event_ordinal']==previous['event_ordinal'] and not action['new_pick_attack']
 assert out['picked_excitation_groups'][-1]['source_requires_silence_at_end']
 assert before['implementation']['sounding_events']==after['implementation']['sounding_events']
 mismatch=after['implementation']['source_seam_route']['target_guidance_reconciliation']
 assert mismatch['written_bar4_downbeat']['note']=='C'
 assert mismatch['written_C_sharp_arrival']['position']=={'bar':4,'beat':1,'phase':'offbeat'}
 assert mismatch['guidance_bar4_targets']==['C#','A'] and not mismatch['source_pitch_or_timing_repair_applied']
 assert len(after['unresolved_reasons'])==len(before['unresolved_reasons'])+1
 assert before['status']==after['status']
 positive.append({'row':i,'deterministic_contract_match':True,'hold_ownership_and_final_rest':True,
  'unaltered_literal_traversal_and_unresolved_guidance_retained':True})
def orphan(r):r['implementation']['symbolic_count_slots'][0].update(kind='hold',note='=',attack_mark='=',source_contact_ordinals=[])
def after_rest(r):
 r['implementation']['symbolic_count_slots'][1].update(kind='rest',note='r',attack_mark='r',source_contact_ordinals=[])
 r['implementation']['symbolic_count_slots'][2]['attack_mark']='h'
 r['implementation']['sounding_events'][2].update(attack='hammer_on',pick_attack=False)
mutations=[('orphan initial hold',orphan),('unpicked arrival after rest',after_rest),
 ('extra pick on arrival',lambda r:r['implementation']['sounding_events'][1].update(pick_attack=True)),
 ('unpicked cross-string jump',lambda r:r['implementation']['sounding_events'][1].update(string_label='G')),
 ('rest changed to attack',lambda r:r['implementation']['symbolic_count_slots'][5].update(attack_mark='P')),
 ('hold supplied a contact',lambda r:r['implementation']['symbolic_count_slots'][15].update(source_contact_ordinals=[12])),
 ('event omitted',lambda r:r['implementation']['sounding_events'].pop()),
 ('slot note disagrees with event',lambda r:r['implementation']['symbolic_count_slots'][0].update(note='C#')),
 ('harmonic R made into rest note',lambda r:r['implementation']['symbolic_count_slots'][0].update(note='r')),
 ('source bars reordered',lambda r:r['implementation']['symbolic_count_slots'].reverse())]
for name,mutate in mutations:
 bad=copy.deepcopy(old[0]);mutate(bad)
 try:m.build(bad)
 except ValueError as e:negative.append({'case':name,'refusal':str(e)})
 else:raise AssertionError(name)
report={'status':'PASS','positive_cases':positive,'causal_refusals':negative,
 'development_note':'Initial test script parse failed from an unparenthesized generator expression before executing checks or writing output. Corrected without changing source or producer payload.',
 'native_audio_app_tests':'NOT_RUN','elapsed_seconds':time.perf_counter()-start,
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
p=ROOT/f'Results/{LANE}/level048-r07/action-tests.json'
with p.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'positive':len(positive),'causal_refusals':len(negative),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
