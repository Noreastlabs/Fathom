#!/usr/bin/env python3
"""Focused semantic and actual-snapshot checks; no native or shared writes."""
import importlib.util
import json
import pathlib
import sys
import hashlib
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--output',default='Build/manager-resume-r01/current-identity-union-intake-r01/validation-r01.json')
args=parser.parse_args()

root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools/manager-resume-r01/current-identity-union-intake-r01'))
from derive import allocation_candidate, head_candidate
count=0
def check(condition, why):
    global count
    if not condition:raise AssertionError(why)
    count+=1
def alt(revision,sha,parent=None):
    v={'content_revision':revision,'record_sha256':sha}
    if parent:v['lineage']={'kind':'revision','predecessor_revision':parent[0],'predecessor_sha256':parent[1]}
    return {'value':v,'evidence':[]}
check(head_candidate([alt(1,'A'),alt(2,'B',(1,'A'))])[0]['record_sha256']=='B','explicit chain')
check(head_candidate([alt(1,'A'),alt(1,'B')])[0] is None,'same revision conflict')
check(head_candidate([alt(1,'A'),alt(9,'B')])[0] is None,'never maximum revision')
check(head_candidate([alt(1,'A'),alt(3,'B',(1,'A'))])[0] is None,'revision skip')
check(head_candidate([alt(1,'A'),alt(2,'B',(1,'A')),alt(1,'C')])[0] is None,'disconnected history')
check(head_candidate([alt(1,'A'),alt(2,'B',(1,'A')),alt(2,'B',(1,'C'))])[0] is None,'divergent parent')
a={'value':{'legacy_level':3,'occurrences':{'a':'fg:item:000240:event:0001'},'variants':{'D':'fg:variant:000827'}}}
b={'value':{'legacy_level':3,'occurrences':{'a':'fg:item:000240:event:0001'},'variants':{'D':'fg:variant:000827','U':'fg:variant:000829'}}}
check(len(allocation_candidate([a,b])[0]['variants'])==2,'append retained')
bad=json.loads(json.dumps(b));bad['value']['variants']['D']='fg:variant:000999'
check(allocation_candidate([a,bad])[0] is None,'remap refused')
bad=json.loads(json.dumps(b));bad['value']['variants']['U']='fg:variant:000827'
check(allocation_candidate([bad])[0] is None,'alias refused')
bad=json.loads(json.dumps(b));bad['value']['legacy_level']=4
check(allocation_candidate([a,bad])[0] is None,'level remap refused')

base=root/'Build/manager-resume-r01/current-identity-union-intake-r01'
c=base/'candidate-r01';o=base/'observation-r03'
read=lambda p:json.loads(p.read_text())
summary=read(c/'candidate-summary.json')
check(summary['registry_items']==1188,'observed1188')
check(summary['lineage_candidates']==1187,'unresolved head retained')
check(summary['lineage_unresolved'][0]['item']=='fg:item:001130','exact unresolved head')
check(summary['head_methods']['DECLARED_REVISION_CHAIN_CANDIDATE']==120,'real chain count')
check(summary['registered_variants']==summary['allocated_variants']==7714,'reverse variant census')
reg=read(c/'registry-candidate.json')['entities']; ids={e['id'] for e in reg}
alloc=read(c/'allocation-candidate.json')['records']
for e in reg:
    check(e['parent'] is None or e['parent'] in ids,'parent exists:'+e['id'])
old=read(o/'allocation-observations.json')['entries']
for item, record in alloc.items():
    for previous in old[item]:
        for field in ['occurrences','variants']:
            for key,value in previous['value'][field].items():
                check(record[field][key]==value,'original source-local binding preserved')
proof=read(c/'selected-pilot-proof.json')
check(proof['observed_head']['record_sha256']=='de7b72f58de406164a7d03d6bfbf175d36a7e8c01b73ff8e48c08f276b877b50','exact pilot')
check(len(proof['retained_allocation']['occurrences'])==40,'40 occurrence labels')
check(len(proof['retained_allocation']['variants'])==12,'all12 variants retained')
check(proof['historical_native_evidence'][0]['selected_record'][0]['record_sha256']==proof['observed_head']['record_sha256'],'historical native exact body')
check(proof['controller_current_head_certified'] is False,'no authority escalation')
for p in c.iterdir():
    d=read(p)
    check(d['classification']=='PRIVATE_INTAKE_CANDIDATE','candidate classification')
check(read(c/'candidate-intake.json')['coverage']['all_held_and_permanent_reservations'] is None,'unknown not false/true')
for filename,ref in read(c/'candidate-intake.json')['components'].items():
    b=(root/ref['path']).read_bytes()
    check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'component pin')
report={'status':'PASS','checks':count,'synthetic_causal_refusals':8,'native_runs':0,'scope':'Conserved actual snapshot joins and bounded graph/append invariants; no assertion of global completeness.'}
out=root/args.output
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report))
