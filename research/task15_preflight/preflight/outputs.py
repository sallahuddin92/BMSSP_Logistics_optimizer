"""Closed extension schemas and durable bundle validation; scientific manifest unchanged."""
from pathlib import Path
from .core import require,read,sha,canonical,boundary
from task15_harness.output import create_bundle,read_bundle

DATA_KEYS={
 'preflight-summary':{'technical_result','static_foundations_verified','errors','phase8_source_identity'},
 'phase7-evidence-validation':{'validation'},
 'protocol-and-plan-identity':{'protocol','plan','repository','harness_source_lock'},
 'original-artifact-identities':{'identities'},
 'analysis-environment-status':{'environment'},
 'host-runtime-observations':{'observations','storage'},
 'cohort-readiness-matrix':{'cohorts','schedule_preserved'},
 'calibration-prerequisites':{'requirements'},
 'blockers-and-next-actions':{'blockers','next_single_task'},
 'static-manifest-reference':{'manifest_file','state','reason'},
 'manifest-validation':{'validation'},
}
TOP={'schema','kind','scope','calibration_authorized','collection_authorized','scientific_acceptance','measurement_eligible','data'}
TECHNICAL={'TECHNICAL_STATIC_PREFLIGHT_PASS','TECHNICAL_STATIC_PREFLIGHT_PARTIAL','TECHNICAL_STATIC_PREFLIGHT_BLOCKED'}

def envelope(kind,data):
    value={'schema':'preflight-extension-1','kind':kind,'scope':'STATIC_PREFLIGHT_ONLY_NO_MEASUREMENTS',
           'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending','measurement_eligible':False,'data':data}
    validate_extension(value);return value

def validate_extension(value):
    require(set(value)==TOP and value['schema']=='preflight-extension-1' and value['kind'] in DATA_KEYS,'EXTENSION_SCHEMA')
    require(value['scope']=='STATIC_PREFLIGHT_ONLY_NO_MEASUREMENTS' and value['calibration_authorized'] is False and value['collection_authorized'] is False and value['scientific_acceptance']=='pending' and value['measurement_eligible'] is False,'FORGED_APPROVAL')
    require(type(value['data']) is dict and set(value['data'])==DATA_KEYS[value['kind']],'EXTENSION_DATA_SCHEMA')
    if value['kind']=='preflight-summary':require(value['data']['technical_result'] in TECHNICAL,'TECHNICAL_RESULT')
    if value['kind'] in {'phase7-evidence-validation','host-runtime-observations','original-artifact-identities','analysis-environment-status','manifest-validation','preflight-summary'}:
        boundary(value['data'])
    from task15_harness.integrity import schema_check
    schema_check(value,read(Path(__file__).resolve().parents[1]/'extension-1.schema.json'))
    canonical(value)
    return value

def write(protocol,root,documents,manifest):
    payloads={name+'.json':canonical(envelope(name,data))+b'\n' for name,data in documents.items()}
    if manifest is not None:payloads['manifest.json']=canonical(manifest)+b'\n'
    hashes={name:sha(raw) for name,raw in payloads.items()}
    payloads['hashes.json']=canonical({'schema':'preflight-hashes-1','files':hashes})+b'\n'
    create_bundle(protocol,root,payloads)
    validate_bundle(root)

def validate_bundle(root):
    root=Path(root);reference=read(root/'static-manifest-reference.json');validate_extension(reference)
    expected={k+'.json' for k in DATA_KEYS}|{'hashes.json'}
    if reference['data']['manifest_file']=='manifest.json':expected.add('manifest.json')
    else:require(reference['data']['manifest_file'] is None,'MANIFEST_REFERENCE')
    read_bundle(root,expected_payloads=expected)
    hashes=read(root/'hashes.json');require(set(hashes)=={'schema','files'} and hashes['schema']=='preflight-hashes-1','HASH_SCHEMA')
    require(set(hashes['files'])==expected-{'hashes.json'},'HASH_INVENTORY')
    for name,wanted in hashes['files'].items():require(sha((root/name).read_bytes())==wanted,'PREFLIGHT_PAYLOAD_HASH')
    for kind in DATA_KEYS:validate_extension(read(root/(kind+'.json')))
    summary=read(root/'preflight-summary.json')['data']
    if summary['technical_result']!='TECHNICAL_STATIC_PREFLIGHT_BLOCKED':
        require(reference['data']['state'] in {'DRAFT','STATIC_VERIFIED','AWAITING_APPROVAL'},'MANIFEST_STATE')
        manifest=read(root/'manifest.json');require(manifest['state']==reference['data']['state'] and manifest['authorization']['calibration'] is False and manifest['authorization']['execution'] is False and not manifest['authorization']['approval_signatures'],'MANIFEST_AUTHORIZATION')
        require(read(root/'phase7-evidence-validation.json')['data']['validation']['status']=='VERIFIED','EVIDENCE_NOT_VERIFIED')
        from task15_cohort_a_runner.frozen import protocol as frozen_protocol
        from task15_harness.manifest import validate_manifest
        validate_manifest(frozen_protocol(),manifest)
        from .integration import own_source
        require(summary['phase8_source_identity']==own_source(),'STALE_PREFLIGHT_SOURCE_LOCK')
        from .readiness import matrix,cohorts
        from task15_cohort_a_runner.frozen import protocol
        p=protocol().data()
        observed=read(root/'host-runtime-observations.json')['data']
        rows=matrix(p,observed['observations'],observed['storage'])
        require(read(root/'calibration-prerequisites.json')['data']['requirements']==rows,'PREREQUISITE_MATRIX_CHANGED')
        require(read(root/'cohort-readiness-matrix.json')['data']['cohorts']==cohorts(rows),'COHORT_MATRIX_CHANGED')
        require(all(r['status'] in {'VERIFIED','PENDING','BLOCKED','UNSUPPORTED','NOT_APPLICABLE'} for r in rows),'PREREQUISITE_STATUS')
    return summary
