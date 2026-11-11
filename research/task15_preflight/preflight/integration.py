"""Static orchestration only. Scientific authorization never follows technical status."""
from pathlib import Path
import sys
import traceback
from .core import require,sha,canonical
from .evidence import verify
from .host import observe
from .readiness import matrix,cohorts,evaluate_foundations
from .outputs import DATA_KEYS,write
from task15_cohort_a_runner.frozen import protocol as load_protocol
from task15_harness.artifacts import inspect_identities,repository_identity,source_lock,inspect_storage,specifications
from task15_harness.analysis_environment import inspect_environment
from task15_harness.planning import compile_plan,validate_plan
from task15_harness.manifest import prepare_manifest,validate_manifest
from task15_harness.output import safe_destination


def own_source():
    root=Path(__file__).resolve().parents[1]
    files={str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in {'.py','.md','.json'}}
    return {'files':files,'identity_sha256':sha(canonical(files))}


def verify_paths(protocol):
    for identifier,path,_ in specifications(protocol):
        if identifier.startswith(('input/','binary/')):
            require(path.is_file() and not path.is_symlink() and path.resolve()==path.absolute(),'MISSING_OR_REDIRECTED_ARTIFACT:'+str(path))


def run(phase7,output):
    protocol=load_protocol();p=protocol.data();root=Path(phase7).absolute();output=Path(output).absolute()
    require(root.is_absolute() and root.exists(),'PHASE7_PATH')
    safe_destination(protocol,output)
    require(not output.exists() and output.parent.is_dir() and not output.resolve().is_relative_to(root.resolve()),'FRESH_EXTERNAL_OUTPUT')
    docs={k:{field:None for field in fields} for k,fields in DATA_KEYS.items()}
    manifest=None;errors=[];foundations=False
    docs['static-manifest-reference']={'manifest_file':None,'state':None,'reason':'NOT_PREPARED'}
    try:
        expected=p['analysis_environment_amendment']['python']
        require(sys.implementation.name=='cpython' and sys.implementation.cache_tag=='cpython-311' and sys.executable==expected['executable'],'VERIFIED_LOCAL_INTERPRETER_REQUIRED')
        docs['phase7-evidence-validation']['validation']=verify(root,protocol)
        verify_paths(protocol)
        identities=inspect_identities(protocol);environment=inspect_environment(protocol);repository=repository_identity(protocol)
        docs['original-artifact-identities']['identities']=identities
        docs['analysis-environment-status']['environment']=environment
        plan=compile_plan(protocol);validate_plan(protocol,plan)
        docs['protocol-and-plan-identity']={'protocol':{'canonical_sha256':protocol.identity,'version':p['version']},'plan':plan,'repository':repository,'harness_source_lock':source_lock()}
        storage=inspect_storage(protocol,output.parent,check_hardlinks=False)
        evaluate_foundations(identities,environment,repository,storage)
        require(repository['branch']==p['branch'] and repository['origin']==p['origin'],'REPOSITORY_BINDING')
        host=observe(p);docs['host-runtime-observations']={'observations':host,'storage':storage}
        require(host['interpreter']['architecture']=='arm64' and host['interpreter']['isolated'] and not host['injection_environment_names'] and not host['trace_or_profile_active'],'HOST_ISOLATION')
        manifest=prepare_manifest(protocol,state='AWAITING_APPROVAL',checked=True)
        validation=validate_manifest(protocol,manifest)
        docs['static-manifest-reference']={'manifest_file':'manifest.json','state':manifest['state'],'reason':'Existing harness schema/transitions only; no approval granted.'}
        docs['manifest-validation']['validation']=validation
        rows=matrix(p,host,storage)
        docs['calibration-prerequisites']['requirements']=rows
        docs['cohort-readiness-matrix']={'cohorts':cohorts(rows),'schedule_preserved':{'units':len(plan['units']),'session_order':p['design']['sessions'],'A_only_schedule_created':False}}
        blockers=[r for r in rows if r['status'] in {'PENDING','BLOCKED','UNSUPPORTED'}]
        docs['blockers-and-next-actions']={'blockers':blockers,'next_single_task':'Prepare an immutable diagnostic-support design/source whitelist and G1–G10/G8 evidence plan for independent review; no build, calibration or collection execution is authorized by this receipt.'}
        foundations=True
        partial=storage['status']!='STORAGE_CAPACITY_VERIFIED' or not host['selected_compiler_path_matches_protocol'] or any(v['returncode']!=0 for v in host['commands'].values())
        result='TECHNICAL_STATIC_PREFLIGHT_PARTIAL' if partial else 'TECHNICAL_STATIC_PREFLIGHT_PASS'
    except Exception as exc:
        errors.append({'type':type(exc).__name__,'message':str(exc),'traceback':''.join(traceback.format_exception(exc))})
        result='TECHNICAL_STATIC_PREFLIGHT_BLOCKED'
    docs['preflight-summary']={'technical_result':result,'static_foundations_verified':foundations,'errors':errors,'phase8_source_identity':own_source()}
    write(protocol,output,docs,manifest)
    return result
