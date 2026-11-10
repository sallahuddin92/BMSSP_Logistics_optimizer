"""Narrow deterministic v1.3 environment-provenance document generator. No imports of NumPy/native code."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

PARENT_HASH = 'c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'
PARENT_FILE_HASH = '4baf6b032fcb40a9859e1a12da319bf1a913f4634111358c53b51c5471b9bf2b'
PARENT_COMMIT = 'a8a021399da77935b7f66d1157bfac3d6fa93442'
EVIDENCE_MANIFEST_HASH = '1c7fcb2fc6d88d34d2d5915a7f1c3e2cc3ae886af070bad5f8c393e883b83890'
INVENTORY_ID = '7e170e5cce91bc4092db793b0023d3f2b1c55d5580c912e737a5bc6af7e8d728'
PREPARED_UTC = '2026-11-10T06:20:21.801530+00:00'
STEM = 'task15_tail_attribution_'
NUMPY_RULE = '1.24.4 exactly; only the identified offline reconstructed environment in analysis_environment_amendment is technically verified. Scientific acceptance remains pending before confirmatory use. No general install/upgrade or backend substitution is authorized.'
APPROVAL_GATE = 'v1.3.0 environment-provenance amendment is NOT_INDEPENDENTLY_APPROVED. The reconstructed environment is TECHNICALLY_VERIFIED and SCIENTIFIC_ACCEPTANCE_PENDING. No calibration, collection, confirmatory analysis or promotion authorization. A/B scheduling and diagnostic G8 remain separate unresolved gates.'


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()


def protocol_hash(p):
    q=deepcopy(p);q['identity'].pop('sha256');return digest(q)


def changed_paths(old,new,path=''):
    if type(old) is dict and type(new) is dict:
        result=[]
        for k in sorted(old.keys()|new.keys()):
            pointer=path+'/'+k.replace('~','~0').replace('/','~1')
            result.extend([pointer] if k not in old or k not in new else changed_paths(old[k],new[k],pointer))
        return result
    return [] if canonical(old)==canonical(new) else [path]


def authenticate(evidence):
    manifest=evidence/'evidence-manifest.json'
    if file_sha(manifest)!=EVIDENCE_MANIFEST_HASH:raise ValueError('RECONSTRUCTION_MANIFEST_HASH')
    for row in json.loads(manifest.read_text())['files']:
        f=evidence/row['path']
        if not f.resolve().is_relative_to(evidence.resolve()) or f.is_symlink() or f.stat().st_size!=row['bytes'] or file_sha(f)!=row['sha256']:raise ValueError('RECONSTRUCTION_EVIDENCE_CHANGED: '+str(f))
    inventory=json.loads((evidence/'environment-inventory.json').read_text());unsigned=deepcopy(inventory);stored=unsigned.pop('identity_sha256')
    if stored!=INVENTORY_ID or digest(unsigned)!=stored:raise ValueError('ENVIRONMENT_INVENTORY_HASH')
    for ref in inventory['evidence'].values():
        if file_sha(ref['path'])!=ref['sha256']:raise ValueError('ENVIRONMENT_REFERENCE_HASH')
    return inventory


def build(repo,evidence):
    parent_file=repo/'docs'/f'{STEM}protocol_v1.2.0.json'
    if file_sha(parent_file)!=PARENT_FILE_HASH:raise ValueError('PARENT_FILE_HASH')
    parent=json.loads(parent_file.read_text())
    if protocol_hash(parent)!=PARENT_HASH:raise ValueError('PARENT_HASH')
    inv=authenticate(evidence)
    def ref(name):
        p=evidence/name;return {'path':str(p),'sha256':file_sha(p)}
    installed=json.loads((evidence/'installed-record-verification.json').read_text())
    package_identity=digest([{'path':r['path'],'bytes':r['bytes'],'sha256':r['sha256']} for r in installed['entries']])
    for row in json.loads((evidence/'cache-record-verification.json').read_text())['entries']:
        if file_sha(Path(inv['numpy']['source'])/row['path'])!=row['sha256']:raise ValueError('SOURCE_CACHE_CHANGED')
    runtime=json.loads((evidence/'base-runtime-provenance.json').read_text())
    recovery=Path('/Users/sallahuddin/Projects/BMSSP-task15-analysis-recovery-6afr5dhi')
    recovery_manifest=recovery/'evidence-manifest.json'
    if file_sha(recovery_manifest)!='f307aa3e79560dd871363ba903bded27c451d1d372b4b09c690965d9fd239b3c':raise ValueError('RECOVERY_EVIDENCE_HASH')
    cache=Path(inv['numpy']['source']);dist=cache/'numpy-1.24.4.dist-info'
    a={'version':'1.3.0','kind':'ANALYSIS_ENVIRONMENT_PROVENANCE_ONLY','parent_version':'1.2.0',
       'parent_canonical_sha256':PARENT_HASH,'parent_commit':PARENT_COMMIT,'prepared_utc':PREPARED_UTC,
       'reason':'Original historical environment was not recovered intact; explicitly identify the exact-version offline reconstruction without changing scientific mathematics or granting scientific acceptance.',
       'historical_recovery':{'result':'FROZEN_ANALYSIS_ENVIRONMENT_NOT_RECOVERED','original_executable':'/private/tmp/bmssp-task6.ZTijar/venv/bin/python','scope':'bounded historical/project-specific paths; original launcher imported external user-site NumPy2.4.3; missing original environment configuration/package files','evidence_manifest':{'path':str(recovery_manifest),'sha256':file_sha(recovery_manifest)}},
       'replacement':{'environment_path':inv['environment'],'inventory':ref('environment-inventory.json'),'inventory_identity_sha256':INVENTORY_ID,'environment_file_lock':ref('environment-file-lock.json'),'installed_record_evidence':ref('installed-record-verification.json'),'copied_files':ref('copied-file-inventory.json'),'reconstruction_manifest':ref('evidence-manifest.json'),'procedure':ref('REPRODUCTION.md')},
       'python':{'implementation':'CPython','version':'3.11.15','architecture':'arm64','executable':inv['interpreter']['path'],'executable_sha256':inv['interpreter']['sha256'],'base_executable':inv['interpreter']['base']['invoked_path'],'base_executable_sha256':inv['interpreter']['base']['executable_sha256'],'base_runtime_path':runtime['framework_path'],'base_runtime_sha256':runtime['framework_sha256'],'provenance':ref('base-runtime-provenance.json'),'dependencies':ref('loaded-library-identities.json')},
       'numpy':{'version':'1.24.4','wheel_tag':'cp311-cp311-macosx_11_0_arm64','offline_source':str(cache),'metadata_sha256':file_sha(dist/'METADATA'),'wheel_sha256':file_sha(dist/'WHEEL'),'record_sha256':file_sha(dist/'RECORD'),'installed_file_identity_sha256':package_identity,'record_listed_files':878,'verified_hashes':877,'verified_sizes':877,'historical_binary_matches':17,'arm64_compatible_binaries':23,'cache_integrity_evidence':ref('cache-record-verification.json')},
       'technical_verification':{'status':'TECHNICALLY_VERIFIED','scope':'Finite synthetic frozen fixture/import/isolation/ABI coverage; not general numerical equivalence or historical byte identity. Recorded tests are prior evidence, not new performance observations.','numerical_results':ref('numerical-results.json'),'negative_controls':ref('negative-control-results.json'),'isolation_evidence':ref('import-isolation-inventory.json'),'sanitized_environment':ref('sanitized-execution-environment.json'),'frozen_fixture_path':'docs/task15_static_v1_1_0/bootstrap_vectors.json','frozen_fixture_sha256':file_sha(repo/'docs/task15_static_v1_1_0/bootstrap_vectors.json'),'primary_draw_vectors':2,'stratified_draw_vectors':2,'toy_ratio_checks':12,'hand_quantile_checks':6,'interval_checks':6,'serialization_checks':5,'negative_control_checks':13},
       'isolation_requirements':['Use the pinned environment executable in isolated mode with bytecode writes disabled.','Remove inherited Python/dynamic-loader redirection; disable user-site packages.','NumPy modules, metadata and bundled libraries must resolve inside this environment, never the cache, damaged historical environment or global user packages.','Reverify installed-file and shared base-runtime/dependency identities before future authorized use. No implicit backend substitution.'],
       'provenance_limitations':{'historical_full_byte_identity_established':False,'independent_publisher_authenticity_established':False,'complete_numerical_equivalence_established':False,'interpretation':'RECORD proves internal consistency, partial historical matches prove correspondence; neither authenticates publisher independently. The venv shares its locked Homebrew base runtime/stdlib.'},
       'scientific_acceptance':{'status':'SCIENTIFIC_ACCEPTANCE_PENDING','independent_approval_status':'NOT_INDEPENDENTLY_APPROVED','approval_signatures':[],'confirmatory_analysis_authorized':False,'execution_authorized':False,'calibration_authorized':False,'collection_authorized':False,'promotion_authorized':False,'requirement':'Independent acceptance of this identified replacement and amendment before confirmatory use; this package is not a signature. General no-upgrade/no-unapproved-install rules remain. A/B and G8 issues are unchanged.'},
       'data_declaration':{'classification':'PRE_DATA_WITHIN_REVIEWED_LOCAL_SCOPE','new_task15_performance_observations_used':False,'new_task15_performance_observations_generated_by_this_task':False,'basis':'Reviewed reconstruction/recovery evidence is synthetic/metadata only; this amendment task performs static and synthetic checks only.','worldwide_absence_of_task15_observations_established':False,'limitation':'Repository/local evidence cannot prove global absence of observations. A truthful independent data-status attestation remains required before scientific acceptance; do not backdate.'}}
    new=deepcopy(parent);new['version']='1.3.0';new['analysis_environment_amendment']=a;new['statistics']['bootstrap_execution_spec']['numpy_version']=NUMPY_RULE;new['future_execution']['active_protocol_file']='docs/'+STEM+'protocol_v1.3.0.json';new['future_execution']['approval_gate']=APPROVAL_GATE;new['identity']['sha256']=protocol_hash(new)
    markdown=f'''# BMSSP Task15 — v1.3.0 analysis-environment provenance amendment

Prepared UTC: {PREPARED_UTC}. Immediate parent v1.2.0 canonical `{PARENT_HASH}`, commit `{PARENT_COMMIT}`. Lineage v1.0 -> v1.1 -> v1.2 -> v1.3; earlier documents remain immutable.

This environment-only package changes no workload, schedule, estimand, RNG rule, threshold or diagnostic requirement. Active v1.3.0 canonical SHA-256: `{new['identity']['sha256']}`.

## Historical loss and identified reconstruction

The original `/private/tmp/bmssp-task6.ZTijar/venv/bin/python` environment was not recovered intact within the documented bounded scope. Its launcher exposed external NumPy2.4.3; it is not repaired. The separately authorized offline reconstruction is `{inv['environment']}` with inventory identity `{INVENTORY_ID}`. The machine-readable `analysis_environment_amendment` binds the actual inventory, installed-file locks, source distribution, procedure, interpreter/framework/dependency hashes and prior validation outputs.

Runtime remains CPython3.11.15 arm64 / NumPy1.24.4. Interpreter SHA-256 `{a['python']['executable_sha256']}`; NumPy installed-file identity `{package_identity}`. Offline source `{cache}`. All878 RECORD files/877 hashes/sizes,17 surviving binary correspondences and23 arm64 binaries were reported verified in authenticated reconstruction evidence. The tests covered frozen PCG64/quantiles/ratios/endpoints/serialization and13 negative controls. These are finite prior synthetic checks, not performance observations.

## Provenance and acceptance limits

Status: TECHNICALLY_VERIFIED / SCIENTIFIC_ACCEPTANCE_PENDING. Complete historical byte identity, independent publisher authenticity and universal numerical equivalence are not established. RECORD self-consistency is not independent authentication. The exact local provenance is disclosed for independent acceptance, not silently equated with the historical installation. General upgrades/installations remain prohibited; this package proposes only this identified replacement, subject to scientific acceptance before confirmatory use.

No formal independent approval is supplied. All execution/calibration/collection/confirmatory-analysis/promotion booleans remain false; signatures are empty. A/B scheduling and G8/B/C/D gates are separate and unchanged. No diagnostic builds, benchmarks, profiler, calibration, runner execution or Task16 are authorized.

## Data declaration

PRE_DATA_WITHIN_REVIEWED_LOCAL_SCOPE: no new Task15 performance observations used or generated by this task. Reviewed reconstruction evidence is synthetic/metadata only. Worldwide absence of observations is NOT established by local repository inspection. Independent truthful data-status attestation is pending; no backdating or invented signature.

## Scientific invariants and static integration

The parent scientific fields are retained exactly except the narrowly replaced environment permission/provenance string. PCG64 seeds15062026/15062027/15062028,100000replicates,draw order,NR quantiles,rational confidence endpoints,estimands,hypotheses,thresholds,failure/exclusion/no-replacement rules,G1–G10/G8,production binaries/graphs/source occurrences/cohorts/warmups/session/trial/SESSION_END ordering remain fixed.

Stable query namespace `6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f` remains distinct from active protocol provenance. Reconcile128primary+100diagnostic=228units,138696structural records,64Aunits/41472Arecords against the pre-edit and historical oracle. New loader/schema/manifest locks identify v1.3; v1.2 manifests are historical and cannot authorize v1.3. Static integration grants no native execution interface.
'''
    pbytes=json.dumps(new,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n';mdbytes=markdown.encode()
    ledger={'amendment_version':'1.3.0','kind':'ANALYSIS_ENVIRONMENT_PROVENANCE_ONLY','parent_version':'1.2.0','parent_commit':PARENT_COMMIT,'parent_canonical_sha256':PARENT_HASH,'new_canonical_sha256':new['identity']['sha256'],'new_JSON_file_byte_sha256':hashlib.sha256(pbytes).hexdigest(),'new_MD_file_byte_sha256':hashlib.sha256(mdbytes).hexdigest(),'analysis_environment_amendment_sha256':digest(a),'changed_json_paths':changed_paths(parent,new),'prepared_utc':PREPARED_UTC,'independent_approval_status':'NOT_INDEPENDENTLY_APPROVED','approval_signatures':[],'execution_authorized':False,'promotion_authorized':False,'calibration_authorized':False,'collection_authorized':False,'confirmatory_analysis_authorized':False,'new_task15_observations_used':False,'data_declaration':deepcopy(a['data_declaration']),'scientific_schedule_sha256':parent['design']['schedule_sha256'],'resolved_diagnostic_order_sha256':parent['design']['resolved_diagnostic_order_sha256'],'query_identity_namespace_sha256':parent['design']['resolved_diagnostic_order']['query_identity_policy']['namespace_protocol_sha256']}
    ledger['identity_sha256']=digest(ledger)
    return new,ledger,{STEM+'protocol_v1.3.0.json':pbytes,STEM+'preregistration_v1.3.0.md':mdbytes,STEM+'amendment_v1.3.0.json':json.dumps(ledger,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();_,_,files=build(args.repo,args.evidence);args.output.mkdir(parents=True,exist_ok=False)
    for name,data in files.items():
        with (args.output/name).open('xb') as f:f.write(data)
    print(json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in files.items()},sort_keys=True))


if __name__=='__main__':main()
