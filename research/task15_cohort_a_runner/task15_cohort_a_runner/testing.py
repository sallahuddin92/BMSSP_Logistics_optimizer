"""Only this synthetic research package's tests; never discover backend/native tests."""
import io
import unittest
import sys
from pathlib import Path
from . import SYNTHETIC
from .wire import canonical
from .errors import require


def run_tests(output=None):
    evidence=None
    if output is not None:
        from .frozen import protocol
        from task15_harness.output import safe_destination
        from .errors import RunnerError
        output=safe_destination(protocol(),Path(output));evidence=output.with_name(output.name+'-executions')
        safe_destination(protocol(),evidence)
        if output.exists() or evidence.exists():raise RunnerError('OUTPUT_EXISTS_OR_UNAVAILABLE')
        evidence.mkdir()
    tests=Path(__file__).resolve().parents[1]/'tests';suite=unittest.defaultTestLoader.discover(str(tests),pattern='test_*.py')
    if evidence is not None:sys.modules['test_processes'].EVIDENCE_ROOT=evidence
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report={**SYNTHETIC,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'successful':result.wasSuccessful() and not result.skipped,'scope':'SYNTHETIC_REAL_SUBPROCESSES_AND_PROTOCOL_ONLY',
        'observed':[record for record in getattr(sys.modules.get('test_processes'),'OBSERVED',[])]}
    print(log.getvalue(),end='')
    if output is not None:
        from .frozen import protocol
        from task15_harness.output import create_bundle
        create_bundle(protocol(),output,{'tests.json':canonical(report)+b'\n','tests.log':log.getvalue().encode()})
    return 0 if report['successful'] and result.testsRun else 1
