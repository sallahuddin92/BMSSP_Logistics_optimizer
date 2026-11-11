"""Useful original-binary analysis, static publication and explicit future G8 blockers."""
from pathlib import Path
import io
import shutil
import unittest
from .core import require,sha,canonical,MARKS
from .toolchain import reconcile
from .inventory import record_from_actual,GROUPS
from .manifest import draft,schema,validate
from .codegen import compare
from task15_cohort_a_runner.frozen import protocol
from task15_harness.output import create_bundle,read_bundle,safe_destination

MAX_EVIDENCE=64*1024*1024
MIN_FREE=256*1024*1024


def inspect(output):
    protocol_object=protocol();p=protocol_object.data();output=Path(output).absolute()
    safe_destination(protocol_object,output)
    require(not output.exists() and output.parent.is_dir(),'FRESH_EXTERNAL_OUTPUT_REQUIRED')
    free=shutil.disk_usage(output.parent).free;require(free>=MIN_FREE,'INSUFFICIENT_BOUNDED_ANALYSIS_STORAGE')
    source_root=Path(__file__).resolve().parents[1]
    sources={str(f.relative_to(source_root)):sha(f.read_bytes()) for f in sorted(source_root.rglob('*')) if f.is_file() and f.suffix in {'.py','.md','.json'}}
    tc=reconcile(p);inventories={};attested={};drafts={}
    for variant in ['baseline','candidate']:
        inventories[variant],attested[variant]=record_from_actual(p,variant)
        drafts[variant]=draft(p,variant,tc,inventories[variant]['source_identities'])
        validate(drafts[variant],p,tc['compiler'],tc['sdk'],tc['build_provenance'][variant]['compile_records'],require_artifact=False)
    # This is deliberately NOT a cross-variant G8 equivalence claim. Each original
    # has missing source coverage, so even its self-comparison must fail closed.
    self_checks={v:compare(attested[v],attested[v]) for v in attested}
    tests_path=Path(__file__).resolve().parents[1]/'tests'
    suite=unittest.defaultTestLoader.discover(str(tests_path));log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    require(result.wasSuccessful() and result.testsRun>=24 and not result.skipped,'IMPLEMENTATION_TEST_FAILURE')
    tests={'status':'VERIFIED','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
           'fixture_scope':'Deterministic nonexecuted ARM64 bytes; no original engine execution.','log':log.getvalue()}
    coverage={v:inv['coverage'] for v,inv in inventories.items()}
    archive={v:{'binary':inv['binary'],'macho':inv['macho'],'tools':inv['tools'],'commands':{k:r for k,r in inv['commands'].items() if k!='symbols'},
                'symbol_count':len(inv['symbols']),'debug_info_available':inv['debug_info_available'],
                'dependency_scope':'Original Mach-O declarations and versions only; no dlopen/runtime dependency re-probe in Phase9.'} for v,inv in inventories.items()}
    unresolved={'status':'BLOCKED','missing_diagnostic_artifacts':['baseline Cohort B diagnostic binary','candidate Cohort B diagnostic binary'],
                'original_coverage':coverage,'toolchain_exact_historical_byte_identity':tc['historical_exact_byte_continuity'],
                'G8_rule':next(g for g in p['calibration']['diagnostic_build_equivalence']['gates'] if g['id']=='G8_codegen'),
                'C_D_storage':{'required_bytes':512*2**30,'observed_free_bytes':free,'status':'BLOCKED' if free<512*2**30 else 'PENDING','satisfied_by_this_phase':False},
                'next_single_task':'Recover/independently establish an exact historical compiler/linker/SDK/header lock and original complete source/inline/compute-window mapping; only then separately authorize a controlled diagnostic build.'}
    capabilities={'status':'VERIFIED','classifications':['CLASS_I','CLASS_L','CLASS_M'],'byte_verified_synthetic_fixture_tests':tests['tests_run'],
                  'actual_production_vs_diagnostic_G8':{'status':'BLOCKED','classification':None,'reason':'No diagnostic artifacts. Originals lack verified complete source/inline/compute-window attribution.'},
                  'conservative_original_self_checks':self_checks,
                  'normalization':'Only verified branch/relocation address operands plus independent debug metadata; retains opcode, register, branch destination structure, immediates, order and encoding signatures.',
                  'limitations':['Approved marker-window subtraction is not implemented and is rejected, never silently normalized.','Current parser is little-endian thin arm64 Mach-O only; unknown instructions/relocations/boundaries fail closed.','Class L remains pending independent layout-risk approval.','Use mapping.attest_mapping with an independently expected reviewed mapping hash and fresh byte/tool evidence; no JSON PASS flag is trusted.']}
    docs={'toolchain-reconciliation.json':tc,'compiler-and-sdk-identities.json':{'status':tc['availability'],'compiler':tc['compiler'],'linker':tc['linker'],'sdk':tc['sdk'],'invocation_specification':tc['invocation_specification']},
          'archived-binary-identities.json':{'status':'VERIFIED','variants':archive},'symbol-coverage.json':{'status':'BLOCKED','required_groups':GROUPS,'variants':coverage},
          'original-codegen-inventory.json':{'status':'BLOCKED','variants':inventories},'diagnostic-build-manifest-schema.json':schema(),
          'g8-comparison-capabilities.json':capabilities,'unresolved-evidence.json':unresolved,'negative-test-results.json':tests,
          'diagnostic-build-drafts.json':{'status':'PENDING','variants':drafts}}
    payloads={name:canonical({**MARKS,'schema':'diagnostic-readiness-1','kind':name.removesuffix('.json'),'data':value})+b'\n' for name,value in docs.items()}
    payloads['diagnostic-build-manifest-schema.json']=canonical(schema())+b'\n'
    payloads['hashes.json']=canonical({'schema':'diagnostic-hashes-1','files':{name:sha(data) for name,data in payloads.items()}})+b'\n'
    payloads['completion-receipt.json']=canonical({**MARKS,'schema':'diagnostic-completion-1','implementation':'VERIFIED','toolchain_availability':tc['availability'],
             'original_binary_complete_G8_analyzability':'BLOCKED','comparator_implementation':'VERIFIED','actual_G8_equivalence':'BLOCKED',
             'files':{name:sha(data) for name,data in payloads.items()},'free_bytes_before_write':free,'maximum_payload_bytes':MAX_EVIDENCE,'readiness_source_lock':sources})+b'\n'
    require(all(sha((source_root/name).read_bytes())==digest for name,digest in sources.items()),'READINESS_SOURCE_CHANGED')
    require(sum(len(v) for v in payloads.values())<=MAX_EVIDENCE,'EVIDENCE_SIZE_BOUND')
    create_bundle(protocol_object,output,payloads);read_bundle(output,expected_payloads=set(payloads))
    return {'implementation':'VERIFIED','toolchain_availability':tc['availability'],'actual_G8_equivalence':'BLOCKED','output':str(output),'payload_bytes':sum(len(v) for v in payloads.values())}
