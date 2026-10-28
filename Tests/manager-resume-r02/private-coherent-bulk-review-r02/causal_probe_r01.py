"""Reproduce original stdin causal sequence; output must be a new file."""
from copy import deepcopy
import importlib.util, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('independent_probe_helpers',ROOT/'Tests/manager-resume-r02/private-coherent-bulk-review-r02/bulk_review_r01.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
m=q.module('Tools/fullscope-private-c-r01/coherent-level083-fixed-top-r65/fixed_top_model.py','independent_c_causal_r01')
key=q.read('Build/manager-resume-r02/private-coherent-bulk-review-r02/level083-original-oracle.json')[0]['package_key']
flow=m.FixedTopFlow(key);flow.set_top(flow.token(),q.top_choice(flow))
for _ in range(3):q.texture(flow)
def loss(report):
    report['duties']['melody_clear']='no'
    report['diagnosis']='Lost melody in full voicing: source requires immediate bass+melody reduction.'
tick=time.perf_counter();q.texture(flow,modify_report=loss);before=deepcopy(flow.__dict__)
choice=q.top_choice(flow);choice['diagnosis']='Rechoose register after diagnosed melody loss.'
flow.restart_top(flow.token(),choice);after=deepcopy(flow.__dict__);replacement=q.remaining(flow)
result={'model_sha256':'ac4b7929f4b52e990ad0a240c25df96096052281a36ab223852dc393f74ade1f','key':key,'failure_input':before['response_history'][-1]['report'],
        'before':{'state':before['state'],'stage_index':before['stage_index'],'recovery':before['recovery']},'restart_input':choice,
        'after':{'state':after['state'],'stage_index':after['stage_index'],'recovery':after['recovery']},'replacement_textures':replacement,'final_state':flow.state,
        'reduction_events_after_loss':sum(x['recovery'] for x in flow.history[len(before['history']):]),'history_retained':flow.history[:len(before['history'])]==before['history'],
        'elapsed_seconds':time.perf_counter()-tick,'physical_observation':False}
out=ROOT/sys.argv[1]
with out.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
