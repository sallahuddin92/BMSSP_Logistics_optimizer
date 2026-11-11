"""Phase 6 regression scope: no native imports and no original road-input opens."""
from pathlib import Path
import importlib.abc
import json
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parent/'task15_cohort_a_runner'))
sys.path.insert(0,str(ROOT.parent/'task15_harness'))
from smoke import MARKS
from smoke.io import publish
from smoke.campaign import protocol
from production_adapter import require


class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname == 'bmssp_native' or fullname.startswith('bmssp_native.'):
            raise AssertionError('REGRESSION_NATIVE_IMPORT_FORBIDDEN')
        return None


def main():
    require(len(sys.argv) == 3 and sys.argv[1] in {'adapter','runner','harness','harness-scoped'},'REGRESSION_ARGUMENTS')
    mode,output = sys.argv[1],Path(sys.argv[2]).absolute()
    p = protocol()
    roadroot = str(Path(p['inputs']['seremban-small']['native_export_path']).parents[1])
    forbidden_attempts=[]
    def guard(event,args):
        if event == 'open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path = str(Path(os.fsdecode(args[0])).absolute())
            if path == roadroot or path.startswith(roadroot+'/'):
                forbidden_attempts.append(path)
                raise AssertionError('FROZEN_ROAD_INPUT_OPEN_FORBIDDEN')
    sys.addaudithook(guard)
    sys.meta_path.insert(0,RejectNative())
    if mode == 'runner':
        from task15_cohort_a_runner.testing import run_tests
        code = run_tests(output)
    elif mode == 'harness':
        from task15_harness.__main__ import main as harness_main
        code = harness_main(['self-test','--output',str(output)])
    else:
        output.mkdir(exist_ok=False)
        testroot = ROOT.parent/('task15_cohort_a_runner/adapter_tests' if mode == 'adapter' else 'task15_harness/tests')
        suite = unittest.defaultTestLoader.discover(str(testroot))
        def flatten(node):
            for child in node:
                if isinstance(child,unittest.TestSuite):yield from flatten(child)
                else:yield child
        excluded = {'test_adapter.AdapterTests.test_graph_real_exports_parse_only'} if mode == 'adapter' else {
            'test_control.ControlTests.test_41_skip_external_cannot_reach_static_verified',
            'test_v12.V12Tests.test_24_missing_modified_redirected_artifact_identities'}
        cases=list(flatten(suite))
        require(len(cases) == (35 if mode == 'adapter' else 107) and {c.id() for c in cases} >= excluded,'REGRESSION_TEST_INVENTORY')
        selected=unittest.TestSuite(c for c in cases if c.id() not in excluded)
        result=unittest.TextTestRunner(verbosity=2).run(selected)
        report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
                'successful':result.wasSuccessful() and not result.skipped,
                'explicitly_not_run':[{'test':name,'reason':'PHASE6_NO_FULL_ROAD_GRAPH_OPEN_AUTHORIZATION'} for name in sorted(excluded)]}
        publish(output/'tests.json',report)
        code=0 if report['successful'] and result.testsRun==(34 if mode == 'adapter' else 105) else 1
    require('bmssp_native' not in sys.modules,'REGRESSION_NATIVE_MODULE_PRESENT')
    publish(output/'phase6-boundary.json',{'mode':mode,'status':'PASS' if code==0 else 'FAIL','native_imports':0,'road_input_open_attempts':forbidden_attempts})
    require(not forbidden_attempts,'REGRESSION_ATTEMPTED_ROAD_OPEN')
    return code

if __name__ == '__main__':raise SystemExit(main())
