import json,subprocess,time
from pathlib import Path
from .core import *
from .collect import collect,history,protocol,BASE,PROTOCOL,ENV,PYTHON
from .validate import validate,KINDS,DOCS
from .documents import STRATEGY,REVIEWER,amendment,packet

REQUIRED_WORK=[
'Audited external diagnostic source diff and exact measurement whitelist; engine edits prohibited.',
'Every100positions/3graphs/eachvariant complete vectors, directed paths, counters and existing correctness gates; six-query evidence insufficient.',
'Exported API/header/object layout and CPython311 numeric/ABI comparison.',
'Close current dependencies; independently approve explicit alternative provenance amendment; preserve actual flags/defaults.',
'Recheck every frozen graph/source/position occurrence and original binary SHA.',
'Use only frozen production binaries in A; verify no preload/profiling/hooks.',
'Approve immutable original/current diagnostic manifests and source diffs before calibration.',
'Complete production-versus-diagnostic hot code/inline attribution and independently reviewed insertion-window analysis; unknowns Class M.',
'Separately authorized frozen clock/aperture/overhead/count/loss/timebase calibration; retain512GiB C/D requirement.',
'Independent signed/hashed G1–G9 outcomes and any Class L approval before collection.']

def source_lock(repo):
    return {str(p.relative_to(repo)):file_sha(p) for p in sorted((repo/'research/task15_option_b_review').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def protected(repo):
    require(subprocess.run(['git','diff','--quiet','--diff-filter=DMRTUXB',BASE,'--'],cwd=repo).returncode==0,'PROTECTED_SOURCE_CHANGED')
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=repo,text=True).splitlines()
    return {name:file_sha(repo/name) for name in names}

def prepare(repo,lock,hist,tests,regressions,protected_files):
    lock['next_step_authorization_boundaries']={'route1':{'action':'separately authorized diagnostic construction','authorized':False,'prerequisites':['independent specialist review','approved versioned G4/G7 alternative-provenance amendment','resolved current dependency closure','reviewed viable original-versus-diagnostic G8 method','separate construction authorization']},'route2':{'action':'separately scoped exploratory optimization with freshly declared baseline','authorized':False,'confirmatory_task15_remains_blocked':True,'pool_with_task15_confirmatory':False},'calibration_authorized':False,'collection_authorized':False}
    p=protocol(repo);gates=p['calibration']['diagnostic_build_equivalence']['gates'];records=hist['authenticated_outputs']['identity-continuity-matrix.json']['data']['records']
    normalized=[]
    current={'compiler':lock['compiler'],'linker':lock['linker'],'sdk-and-headers':{'status':lock['trees']['sdk']['status'],'tree_sha256':lock['trees']['sdk']['tree_sha256']},'python-build-interpreter':{'status':lock['trees']['python']['status'],'tree_sha256':lock['trees']['python']['tree_sha256']},'pybind11-build-headers':{'status':'MISSING_OR_UNAVAILABLE'}}
    for record in records:
        row={k:v for k,v in record.items() if not k.startswith('current_')}
        row['historical_identity_status']={'VERSION_ONLY':'HISTORICAL_VERSION_ONLY','HISTORICALLY_VERIFIED':'HISTORICAL_OUTPUT_VERIFIED'}[record['historical_identity_status']]
        row['phase10_current_observations']={k:v for k,v in record.items() if k.startswith('current_')}
        row['phase11_current_observation']=current.get(record['component'],{'status':'MISSING_OR_UNAVAILABLE','reason':'no new historical output inspection; Phase10 historical verification retained'})
        normalized.append(row)
    items={'current-toolchain-lock':lock,'current-sdk-inventory':lock['trees']['sdk'],
      'python-pybind-closure':{'status':'CURRENT_BYTES_PARTIAL','python_tree_sha256':lock['trees']['python']['tree_sha256'],'environment_tree_sha256':lock['trees']['analysis-environment']['tree_sha256'],'python_headers':str(PYTHON/'Frameworks/Python.framework/Versions/3.11/include/python3.11'),'pybind11_status':'MISSING_OR_UNAVAILABLE','pybind11_headers':str(ENV/'lib/python3.11/site-packages/pybind11/include'),'pybind11_cmake':str(ENV/'lib/python3.11/site-packages/pybind11/share/cmake/pybind11'),'historical_python_version':'3.11.15','historical_pybind_version':'2.11.1','historical_identity_status':'HISTORICAL_VERSION_ONLY','historical_bytes_recovered':False,'probe_scope':'selected current environment only; original absence inherited from authenticated Phase10, no old directory probes','runtime_closure_complete':False},
      'original-current-evidence-matrix':{'historical_toolchain_byte_continuity':False,'historical_receipt_sha256':hist['receipt_sha256'],'historical_verdict':hist['receipt']['recovery_verdict'],'records':normalized,'historical_status_vocabulary':{'HISTORICALLY_VERIFIED':'HISTORICAL_OUTPUT_VERIFIED','VERSION_ONLY':'HISTORICAL_VERSION_ONLY'},'separation':'Phase10 current observations are dated Phase10, not this current collection; only current-toolchain-lock supplies Phase11 current bytes.'},
      'g1-g10-impact-matrix':{'gates':[{**g,'status':'BLOCKED' if i in [1,3,6,7,9] else 'PENDING','required_work':REQUIRED_WORK[i]} for i,g in enumerate(gates)],'actual_gate_passes':[],'original_gates_unchanged':True,'storage_C_D_bytes':512*1024**3},
      'g8-equivalence-feasibility':{'status':'BLOCKED','actual_comparison_performed':False,'independent_evidence':[],'original_source_inline_mapping_complete':False,'marker_window_subtraction_supported':False,'actual_g8_pass':False,'class_I_L_M_exact_requirement':gates[7]['pass'],'unchanged_gate_feasible_with_available_evidence':False,'additional_requirements':['complete independently validated original hot/source/inline mapping and coverage','reviewed insertion-window tooling and tests','actual production-versus-diagnostic comparison for both variants','independent Class L layout-risk approval if needed'],'amendment_implication':'G4/G7 alternative provenance requires amendment. G8 unchanged remains blocked; any relaxation needs separate explicit amendment with restricted scientific claims.'},
      'negative-tests':{'option_b_tests':tests,'unchanged_static_fake_regressions':regressions},
      'source-integrity':{'baseline_commit':BASE,'protocol_canonical_sha256':PROTOCOL,'protected_files':protected_files,'native_builds':0,'native_queries':0,'calibration_runs':0,'collection_runs':0,'scope':'new Option B tooling/documents only'}}
    for variant in ['baseline','candidate']:
        original=hist['authenticated_outputs'][variant+'-build-reconciliation.json']['data']['reconciliation']
        require(original['production_binary_sha256']==p['binaries'][variant]['sha256'] and original['source_commit']==p['binaries'][variant]['source_commit'],'HISTORICAL_VARIANT_IDENTITY')
        items[variant+'-build-comparison']={'original':original,'historical_output_status':'HISTORICAL_OUTPUT_VERIFIED','historical_toolchain_status':'HISTORICAL_VERSION_ONLY','current_compiler':lock['compiler'],'current_linker':lock['linker'],'current_sdk_tree_sha256':lock['trees']['sdk']['tree_sha256'],'current_python_tree_sha256':lock['trees']['python']['tree_sha256'],'current_pybind11_status':'MISSING_OR_UNAVAILABLE','byte_equivalence':False,'assessment':'BLOCKED: historical byte continuity unproven; current closure incomplete; no diagnostic built or compared. Numeric defaults, ABI, exception/RTTI/LTO behavior must be verified, not inferred from recorded absence of flags.','numeric_exception_record':'Original binding command and configure verbose records retained verbatim; no added numeric/exception flags inferred.'}
    docs={'controlled-equivalence-strategy':STRATEGY,'reviewer-decision-template':REVIEWER,'proposed-amendment-impact':amendment(gates,p),'independent-review-packet':packet(items)}
    return items,docs

def write_bundle(bundle,repo,items,docs):
    bundle=Path(bundle);require(not bundle.exists(),'STALE_EVIDENCE_BUNDLE');bundle.mkdir(parents=True)
    total=0
    for kind,data in items.items():
        no_approval(data);raw=canonical({'schema':'option-b-1','kind':kind,'authorization':AUTH,'data':data})+b'\n';total+=len(raw);require(total<=134217728,'OUTPUT_BOUND');(bundle/(kind+'.json')).write_bytes(raw)
    for kind,data in docs.items():
        raw=data.encode();total+=len(raw);require(total<=134217728,'OUTPUT_BOUND');(bundle/(kind+'.md')).write_bytes(raw)
    receipt={'schema':'option-b-completion-1','authorization':AUTH,'protocol_sha256':PROTOCOL,'baseline_commit':BASE,'files':{f.name:file_sha(f) for f in sorted(bundle.iterdir())},'source_lock':source_lock(repo),'package_status':'PASS','scientific_recommendation':'BLOCKED'}
    (bundle/'completion-receipt.json').write_bytes(canonical(receipt)+b'\n');return validate(bundle,repo)
