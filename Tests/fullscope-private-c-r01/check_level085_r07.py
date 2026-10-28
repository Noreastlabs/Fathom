from pathlib import Path
import json,hashlib,copy,datetime
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'Build/fullscope-private-c-r01/level085-r07/implementation-packet.jsonl';checks=0

def ck(v,m):
 global checks
 checks+=1
 if not v:raise ValueError(m)
def validate(rows):
 prior=[json.loads(s) for s in (ROOT/'Build/fullscope-private-c-r01/level085-r06/implementation-packet.jsonl').read_text().splitlines()];ck([x['package_key'] for x in rows]==[x['package_key'] for x in prior],'identity');nc=0
 for r in rows:
  p=r['implementation'].get('rhythm_contract')
  if not p:continue
  ck(not r['implementation']['canonical_ids_allocated'] and not r['implementation']['playback_admitted'],'admission')
  if p['kind']=='printed_sixteenth_hand_motion':
   t=r['implementation']['task']['table_fields'][0];d=dict(zip(t['columns'],t['values']));symbols=''.join(d['Grid'].split());ms=p['movements'];ck(len(ms)==16,'motion count')
   for i,m in enumerate(ms):
    ck(m['printed_symbol']==symbols[i],'printed symbol');ck(m['onset_q_fraction']==[i,4] and m['movement_duration_q_fraction']==[1,4],'sixteenth grid');ck(m['hand_direction']==('D' if i%2==0 else 'U'),'continuous D/U');ck(m['sounding_pitch_members'] is None and m['sounding_gate_q'] is None,'invented sounding members/gate')
   ck(p['contact_orders']==[i+1 for i,v in enumerate(symbols) if v!='-'],'contact vs air')
   ck([x['shape_kind'] for x in p['source_passes']]==['three-string triad','four-string shell'],'source voicing passes');nc+=len(p['contact_orders'])
  elif p['kind']=='note_length_ladder':
   ck(p['source_progression']==['G','C','D','G'],'source progression');ck(len(p['exact_fraction_variants'])==4,'known gate levels')
   for i,v in enumerate(p['exact_fraction_variants']):
    ck(v['percent_of_beat']==[100,75,50,25][i],'percent')
    for j,e in enumerate(v['measure_attacks']):ck(e['onset_q']==[j,1] and e['sounding_duration_q']==[[1,1],[3,4],[1,2],[1,4]][i],'gate fractions');ck(e['pitch_members'] is None,'invented voicing')
   ck(len(p['unquantified_source_levels'])==2,'percussive/mixed preserved')
  elif p['kind']=='drum_relative_attack_plan':
   for e in p['guitar_attacks']:ck(e['duration_q'] is None and e['pitch_members'] is None,'qualitative gate unfilled')
   count=p['source_count'];expected={'1, 3':[[0,1],[2,1]],'2, 4':[[1,1],[3,1]],'&1, &3':[[1,2],[5,2]],'a1, a3':[[3,4],[11,4]],'1/3 bass, 2/4 chord':[[0,1],[1,1],[2,1],[3,1]],'2-&2, 4-&4':[[1,1],[3,2],[3,1],[7,2]]};ck([e['onset_q'] for e in p['guitar_attacks']]==expected[count],'source relative onsets')
 ck(nc==72,'source 72 contacts per voicing pass');return True
rows=[json.loads(s) for s in P.read_text().splitlines()];validate(rows);positive=checks;ci=next(i for i,r in enumerate(rows) if '/modulec/' in r['source_identity']);bi=next(i for i,r in enumerate(rows) if '/moduleb/' in r['source_identity']);di=next(i for i,r in enumerate(rows) if '/moduled/' in r['source_identity']);cases=[('wrong_motion',lambda r:r[ci]['implementation']['rhythm_contract']['movements'][0].update(hand_direction='U')),('air_to_contact',lambda r:r[ci]['implementation']['rhythm_contract']['contact_orders'].append(2)),('invented_gate',lambda r:r[ci]['implementation']['rhythm_contract']['movements'][0].update(sounding_gate_q=.25)),('missing_shell_pass',lambda r:r[ci]['implementation']['rhythm_contract']['source_passes'].pop()),('percent_change',lambda r:r[bi]['implementation']['rhythm_contract']['exact_fraction_variants'][1]['measure_attacks'][0].update(sounding_duration_q=[1,2])),('drum_onset_change',lambda r:r[di]['implementation']['rhythm_contract']['guitar_attacks'][0].update(onset_q=[1,1])),('native_admission',lambda r:r[ci]['implementation'].update(playback_admitted=True))];negative=[]
for name,fn in cases:
 rs=copy.deepcopy(rows);fn(rs)
 try:validate(rs)
 except ValueError as e:negative.append({'case':name,'refused':True,'reason':str(e)})
 else:raise AssertionError(name)
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','positive_checks':positive,'total_assertions':checks,'negative_cases':negative,'packet_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'native_compiler_app_gui':'NOT_RUN'};p=ROOT/'Results/fullscope-private-c-r01/level085-r07/integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
