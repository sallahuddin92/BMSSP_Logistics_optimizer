"""Protocol-derived prerequisite rows, not invented scientific acceptance states."""
from .core import require
STATUSES={'VERIFIED','PENDING','BLOCKED','UNSUPPORTED','NOT_APPLICABLE'}


def prerequisite(identifier,cohorts,status,reference,requirement,reason,next_action):
    require(status in STATUSES,'PREREQUISITE_STATUS')
    return {'id':identifier,'cohorts':cohorts,'status':status,'protocol_reference':reference,'requirement':requirement,'reason':reason,'next_action':next_action}


def evaluate_foundations(artifacts,environment,repository,storage):
    require(artifacts['all_verified'] is True,'FROZEN_ARTIFACT_VERIFICATION_FAILED')
    require(environment['live_identity_status']=='VERIFIED','RECONSTRUCTED_ENVIRONMENT_MISSING_OR_CHANGED')
    require(repository['runtime_matches_task14'] is True,'PROTECTED_RUNTIME_CHANGED')
    return 'VERIFIED' if storage['status']=='STORAGE_CAPACITY_VERIFIED' else 'BLOCKED'


def matrix(p,host,storage):
    rows=[]
    def add(i,cs,s,ref,req,reason,action):rows.append(prerequisite(i,list(cs),s,ref,req,reason,action))
    add('complete-frozen-calibration-specification','ABCD','PENDING','calibration',p['calibration'],'Exact complete frozen calibration object retained, including thresholds, fallbacks, loss rules, capacity, fixed counts and G1–G10; no new measurements.','Satisfy each cohort-applicable requirement under separate authorization.')
    add('original-artifacts-and-road-receipts','ABCD','VERIFIED','correctness_protection','Phase7 fixed original-road engineering receipt validation','All original variants and three graphs verified; not diagnostic equivalence coverage.','Retain immutable receipt identity.')
    for identifier,ref,req,cs in [
        ('A-external-clock','instruments[0].ordinary_cohort',p['instruments'][0]['ordinary_cohort'],'A'),
        ('B-endpoints','measurement_boundaries',p['measurement_boundaries'],'B'),
        ('clock-mapping-resolution-aperture-overhead','calibration.diagnostic_precision_gates',p['calibration']['diagnostic_precision_gates'],'ABCD'),
        ('fixed-empty-and-worker-calibration','calibration', {k:p['calibration'][k] for k in ['empty_endpoint_measurements','fixed_harness_calibration_clusters','per_cluster','no_bias_subtraction','if_B_gates_fail','instrumentation_difference_definition']},'ABCD'),
        ('instrument-fixed-calibration','calibration.per_instrument_fixed_calibration',p['calibration']['per_instrument_fixed_calibration'],'D'),
        ('allocation-reservation-and-count-coverage','calibration.allocation_capacity_assessment',p['calibration']['allocation_capacity_assessment'],'C'),
        ('diagnostic-loss-synchronization','calibration', {k:p['calibration'][k] for k in ['C_gate','D_gate','instrumentation_loss_rule']},'BCD')]:
        add(identifier,cs,'PENDING',ref,req,'No authorized calibration, endpoint, capacity or recording probe performed.','Implement/lock required support, obtain separate authorization, then execute only the frozen fixed calibration.')
    add('profiler-permission','D',host.get('permissions',{}).get('status','PENDING'),'instruments',{'runtime_permissions_required':True},'No recording/permission probe may be inferred from installed tools.','Obtain authorized permission/export/loss probe; unsupported access remains unsupported without replacement.')
    for index,item in enumerate(p['unsupported_instruments']):
        add('unsupported-'+str(index),'ABCD','UNSUPPORTED','unsupported_instruments',item,'Explicitly unsupported interpretation/API in frozen protocol.','Do not substitute this approach or invent support.')
    for instrument in p['instruments']:
        add('instrument-'+instrument['id'],'BCD' if instrument['id']!='elapsed' else 'ABCD','PENDING','instruments',instrument,
            'API/design requirements preserved; installed tooling does not prove runtime support/permissions/units/loss/synchronization.','Verify required APIs, permissions, export fields/units and loss/synchronization in a separately authorized probe.')
    for gate in p['calibration']['diagnostic_build_equivalence']['gates']:
        status='BLOCKED' if gate['id']!='G9_overhead' else 'PENDING'
        if gate['id']=='G6_A_isolation':
            add('G6-original-A-observed','A','VERIFIED','calibration.diagnostic_build_equivalence.gates',gate,'Phase7 originals/zero profiles and isolation were verified for six engineering calls only.','Recheck at every future authorized load; no collection approval.')
        add(gate['id'],'BCD',status,'calibration.diagnostic_build_equivalence.gates',gate,
            'No approved Phase8 diagnostic artifact identity/gate package; Phase7 originals are not diagnostic builds. G8 missing production-vs-diagnostic code-generation evidence blocks affected B/C/D, not original Cohort A artifact validity.',
            'Prepare immutable diagnostic source/build/layout/disassembly evidence; satisfy exact G1–G10 and independent Class L approval where applicable; never substitute diagnostic timing for A.')
    add('G8-original-A-applicability','A','NOT_APPLICABLE','calibration.diagnostic_build_equivalence','Original archived A binaries are not diagnostic variants.','Missing diagnostic G8 evidence is not an original A binary failure.','Keep A originals isolated; preserve complete eight-session A/B schedule.')
    add('storage-capacity','CD','VERIFIED' if storage['status']=='STORAGE_CAPACITY_VERIFIED' else 'BLOCKED','environment.storage_preflight',
        p['environment']['storage_preflight'],{'observed_free_bytes':storage['free_bytes'],'required_bytes':storage['required_bytes'],'space_reserved':False},'Provide >=512GiB free before C/D and monitor 16GiB stop threshold; no compression/reservation assumed.')
    add('selected-compiler-and-SDK','BCD','BLOCKED' if host.get('selected_compiler_path_matches_protocol') is False or host.get('commands',{}).get('sdk_version',{}).get('returncode',0) not in (0,None) else 'PENDING','environment',{'compiler_path':p['environment']['compiler_path'],'compiler':p['environment']['compiler'],'flags':p['environment']['flags']},'Current selected compiler path/SDK observations must be reconciled against pinned build identities; no rebuild or selection change occurred.','Resolve the recorded SDK lookup error and selected-vs-declared compiler discrepancy before diagnostic build equivalence; preserve original binaries.')
    add('host-power-toolchain-and-conflicts','ABCD','PENDING','environment',p['environment'],'Read-only observations saved; current snapshot does not verify stable power, absence of overlap, pin-compatible toolchain or runtime permission gates.','Reconcile observed compiler/SDK/OS, power and process observations before an authorized run; do not kill applications or alter settings.')
    for identifier,ref,req in [('protocol-acceptance','future_execution.approval_gate',p['future_execution']['approval_gate']),
                              ('analysis-environment-acceptance','analysis_environment_amendment',p['analysis_environment_amendment']['replacement']),
                              ('harness-independent-acceptance','future_execution.requirements',p['future_execution']['requirements']),
                              ('calibration-authorization','calibration.execution_now',False),('collection-authorization','execution_authorized',False)]:
        add(identifier,'ABCD','PENDING',ref,req,'No independent scientific acceptance or separate execution authorization exists.','Obtain the specifically required independent acceptance/authorization after technical prerequisites are satisfied.')
    return rows


def cohorts(rows):
    result={}
    for cohort in 'ABCD':
        result[cohort]={'artifact_validity':'VERIFIED' if cohort=='A' else 'BLOCKED',
                       'road_correctness_evidence':'VERIFIED' if cohort=='A' else 'PENDING',
                       'static_control_plane':'VERIFIED','host_readiness':'PENDING',
                       'diagnostic_build_readiness':'NOT_APPLICABLE' if cohort=='A' else 'BLOCKED',
                       'calibration_readiness':'PENDING' if cohort=='A' else 'BLOCKED',
                       'scientific_approval':'PENDING','actual_collection_permission':'BLOCKED',
                       'reason':'Original baseline/candidate are both Cohort A variants; original-road evidence does not establish diagnostic equivalence. Full eight-session A/B order and B/C/D gates retained.',
                       'prerequisite_ids':[r['id'] for r in rows if cohort in r['cohorts']]}
    return result
