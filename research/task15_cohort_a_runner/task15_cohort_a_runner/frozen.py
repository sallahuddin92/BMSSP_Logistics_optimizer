"""Validated harness plan consumption and immutable historical-oracle reconciliation."""
from collections import Counter
from pathlib import Path
import sys
import hashlib
from .errors import require
from .wire import canonical,digest

REPO=Path(__file__).resolve().parents[3]
HARNESS=REPO/'research/task15_harness'
if str(HARNESS) not in sys.path:
    sys.path.insert(0,str(HARNESS))
from task15_harness.protocol import load_protocol
from task15_harness.errors import ControlError
from task15_harness.planning import compile_plan,query_records
from task15_harness.artifacts import source_lock

PROTOCOL='b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
NAMESPACE='6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f'
ORACLE_SHA='8dcc00537d586b61f97b0fb20dc489ca7e900c64c89bc5cb8b52afc4318be975'
PROVENANCE={'protocol_sha256','protocol_version','query_identity_namespace_sha256','resolved_diagnostic_order_sha256'}


def protocol():
    try:result=load_protocol(REPO)
    except ControlError as exc:
        from .errors import RunnerError
        raise RunnerError('FROZEN_PROTOCOL_REJECTED',str(exc)) from exc
    require(result.identity==PROTOCOL,'PROTOCOL_IDENTITY')
    return result


def oracle():
    import json
    file=HARNESS/'tests/fixtures/v1.1-query-oracle.json'
    require(hashlib.sha256(file.read_bytes()).hexdigest()==ORACLE_SHA,'HISTORICAL_ORACLE_HASH')
    return json.loads(file.read_text())


def variants(order):
    require(order in {'AB','BA'},'FROZEN_VARIANT_ORDER')
    return ['baseline','candidate'] if order=='AB' else ['candidate','baseline']


def expected_variant_records(p,unit,variant):
    """Worker-side frozen occurrence/ID checks, independent of controller stream."""
    row=next(r for r in p['design']['base_schedule'] if r['id']==unit['schedule_ref'])
    records=[]
    for region in row['regions']:
        inp=p['inputs'][region];positions=inp['source_positions'];occurrences=[];counts=Counter()
        for source in positions:
            counts[source]+=1;occurrences.append(counts[source])
        for phase,permutation in [('warmup',inp['warmup_positions']),('target',row['positions_by_region'][region])]:
            for execution,original in enumerate(permutation):
                identity=[NAMESPACE,unit['session_key'],unit['id'],phase,region,execution,original,variant]
                records.append({'query_id':digest(identity),'phase':phase,'region':region,
                    'execution_index':execution,'original_position':original,'source_id':positions[original],
                    'source_occurrence':occurrences[original]})
    return records


class Workload:
    def __init__(self):
        self.protocol=protocol();self.p=self.protocol.data();self.plan=compile_plan(self.protocol)
        self.units=[u for u in self.plan['units'] if u['cohort']=='A'];self.rows={r['id']:r for r in self.p['design']['base_schedule']}
        self.queries={u['id']:[] for u in self.units}
        for q in query_records(self.protocol,self.plan):
            if q['cohort']=='A':self.queries[q['trial_id']].append(q)
        require(len(self.units)==64 and len(self.plan['units'])==228,'COHORT_A_UNIT_COUNT')
        self.verify(self.units,[q for u in self.units for q in self.queries[u['id']]])

    def verify(self,units,records):
        old=oracle();groups={};ids=set();order=[]
        for q in records:
            require(q['cohort']=='A' and q['protocol_sha256']==PROTOCOL and q['protocol_version']=='1.3.0','QUERY_PROVENANCE')
            require(q['query_identity_namespace_sha256']==NAMESPACE,'QUERY_NAMESPACE')
            require(q['query_id'] not in ids,'QUERY_DUPLICATE');ids.add(q['query_id'])
            key=q['trial_id'];group=groups.setdefault(key,{'payload':hashlib.sha256(),'ids':hashlib.sha256(),'count':0})
            group['payload'].update(canonical({k:v for k,v in q.items() if k not in PROVENANCE})+b'\n');group['ids'].update(canonical(q['query_id'])+b'\n');group['count']+=1
            if not order or order[-1]!=key:order.append(key)
        require(order==[u['id'] for u in units],'QUERY_UNIT_ORDER')
        for key,g in groups.items():
            expected=old['by_unit'][key]
            require(g['payload'].hexdigest()==expected['ordered_scientific_payload_sha256'],'QUERY_SCIENTIFIC_PAYLOAD',key)
            require(g['ids'].hexdigest()==expected['ordered_query_ids_sha256'] and g['count']==expected['count'],'QUERY_ORDER_IDENTITIES',key)
        require(len(ids)==len(units)*648,'QUERY_COUNT')
        return {'units':len(units),'records':len(ids),'query_population_sha256':digest(sorted(ids)),
                'oracle_sha256':ORACLE_SHA,'ordered_units':[u['id'] for u in units]}

    def slots(self,selected):
        chosen={u['id'] for u in selected};slots=[]
        for session in self.p['design']['sessions']:
            for phase in session['cohort_phase_order']:
                ids=[u['id'] for u in self.plan['units'] if u['session_id']==session['session'] and u['session_kind']=='PRIMARY' and u['cohort']==phase]
                slots.append({'session':session['session'],'cohort':phase,'unit_ids':ids,
                    'selected_A_units':[x for x in ids if x in chosen],
                    'status':'NOT_EXECUTED' if phase=='B' else 'SYNTHETIC_STRUCTURE_ONLY',
                    'gate':'SCIENTIFIC_GATE_PENDING','relative_day':session['relative_day'],
                    'window':session['window'],'minimum_separation_seconds_not_waited':session['separation_from_previous_seconds_min'],
                    'fixed_idle_seconds_not_waited':session['fixed_idle_before_phase_seconds'],
                    'synthetic':True,'measurement_eligible':False})
        return slots
