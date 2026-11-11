"""One actual collection, finite allowlist, explicit stop on unrecoverable continuity."""
import io
import os
from pathlib import Path
import shutil
import unittest
from task15_cohort_a_runner.frozen import protocol
from task15_harness.output import safe_destination
from .collector import recover
from .core import canonical,digest,require
from .output import DATA_KEYS,envelope,publish,validate_bundle

DECISION='''# Scientific decision boundary

Exact original compiler/linker/complete SDK/Python/pybind byte continuity is not
established by the available bounded evidence. Historical output/source hashes and
metadata are retained; this limitation is not an actual compiler mismatch.

## Option A — hold for stronger original evidence
Continue only if a newly identified, independently anchored original tool payload,
original component hash inventory, signed build-stage snapshot or equivalent
historical artifact becomes available. Identify and authorize that exact source
before a new recovery task. Do not repeat this search with broader scopes or new
filenames. No diagnostic build/calibration/collection is authorized meanwhile.

## Option B — independent review of a separately identified current toolchain
Seek independent scientific review of a concrete alternative: fully lock current
compiler/linker binaries, complete SDK/header/dependency inventory, exact Python/ABI
and pybind files, source and build argv; explain the missing historical continuity;
propose controlled source/build, semantic and code-generation equivalence evidence
under the frozen G1–G10/G8 criteria. Address original source/inline/compute mapping
and all-source diagnostic equivalence, ABI/layout and numeric flags explicitly.
A reproducible new build would not prove exact historical compiler identity.

If the strategy changes frozen scientific decisions, identities or acceptance
criteria, an explicit protocol amendment and new independent approval are required
BEFORE diagnostic construction. This task creates no amendment, approval or relaxed
G8 criterion. Existing reconstructed analysis-environment acceptance remains pending.
The current selected SDK/header subset is not a fully hermetic current-toolchain lock.

Neither option authorizes building originals or Cohort B, executing queries,
calibration, profiling or collection. Calibration/collection remain false.
'''


def run(output):
    p_obj=protocol();p=p_obj.data();root=Path(output).absolute();safe_destination(p_obj,root)
    require(not root.exists() and root.parent.is_dir(),'FRESH_EXTERNAL_EVIDENCE_REQUIRED')
    require(shutil.disk_usage(root.parent).free>=64*1024*1024,'BOUNDED_STORAGE_UNAVAILABLE')
    root.mkdir(mode=0o700)
    publish(root/'STARTED.json',canonical({'scope':'READ_ONLY_HISTORICAL_PROVENANCE_ONLY','campaigns':1,'protocol_sha256':p['identity']['sha256'],'automatic_retry':False})+b'\n')
    source_root=Path(__file__).resolve().parents[1]
    source_lock={str(f.relative_to(source_root)):digest(f.read_bytes()) for f in sorted(source_root.rglob('*')) if f.is_file() and f.suffix in {'.py','.md','.json'}}
    try:
        def record(value):
            with (root/'recovery-events.jsonl').open('ab') as stream:
                stream.write(canonical({'scope':'READ_ONLY_HISTORICAL_PROVENANCE_ONLY',**value})+b'\n');stream.flush();os.fsync(stream.fileno())
        record({'event':'SCOPE_LOCKED','automatic_retry':False})
        result=recover(p,record)
        suite=unittest.defaultTestLoader.discover(str(source_root/'tests'));log=io.StringIO()
        tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        require(tests.wasSuccessful() and tests.testsRun>=12 and not tests.skipped,'NEGATIVE_CONTROL_FAILURE')
        records=result['components'];by_name={c['component']:c for c in records}
        docs={'historical-evidence-inventory':{'inventory':result['historical_inventory']},'compiler-provenance':{'record':by_name['compiler']},
              'linker-provenance':{'record':by_name['linker'],'current_version_query':result['linker_current_version_query']},
              'sdk-header-provenance':{'record':by_name['sdk-and-headers'],'current_selected_files':result['sdk_current']},
              'python-pybind-provenance':{'records':[by_name['python-build-interpreter'],by_name['pybind11-build-headers']],'current_files':result['dependency_current']},
              'baseline-build-reconciliation':{'reconciliation':result['reconciliations']['baseline']},'candidate-build-reconciliation':{'reconciliation':result['reconciliations']['candidate']},
              'identity-continuity-matrix':{'records':records,'common_toolchain':result['common_toolchain'],'recovery_verdict':result['verdict']},
              'unresolved-historical-identities':{'missing':result['missing'],'contradictions':result['contradictions'],'stop_condition':'BOUNDED_SOURCES_EXHAUSTED_NO_FURTHER_SEARCH_WITHOUT_NEW_EVIDENCE'},
              'negative-tests':{'tests_run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'skipped':len(tests.skipped),'log':log.getvalue(),'fixture_scope':'Disposable deterministic source/hash fixtures; no native calls or repeated recovery.'}}
        payload={k+'.json':canonical(envelope(k,d))+b'\n' for k,d in docs.items()}
        payload['scientific-decision-boundary.md']=DECISION.encode()
        require(sum(len(data) for data in payload.values())<16*1024*1024,'BOUNDED_EVIDENCE_SIZE')
        require(all(digest((source_root/name).read_bytes())==h for name,h in source_lock.items()),'RECOVERY_SOURCE_CHANGED')
        for name,data in payload.items():publish(root/name,data)
        files={name:digest(data) for name,data in payload.items()};files['STARTED.json']=digest((root/'STARTED.json').read_bytes());files['recovery-events.jsonl']=digest((root/'recovery-events.jsonl').read_bytes())
        receipt={'schema':'bounded-recovery-completion-1','scope':'READ_ONLY_HISTORICAL_PROVENANCE_ONLY','recovery_verdict':result['verdict'],'implementation':'VERIFIED','files':files,'source_lock':source_lock,
                 'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending'}
        publish(root/'completion-receipt.json',canonical(receipt)+b'\n');validate_bundle(root)
        return result['verdict']
    except BaseException as exc:
        import traceback
        publish(root/'FAILED.json',canonical({'scope':'READ_ONLY_HISTORICAL_PROVENANCE_ONLY','error_type':type(exc).__name__,'message':str(exc),'traceback':''.join(traceback.format_exception(exc)),'automatic_retry':False})+b'\n')
        raise
