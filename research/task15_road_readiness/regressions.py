"""Execute the three original, unchanged deferred methods, with native imports denied."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent
for path in [ROOT,ROOT.parent/'task15_cohort_a_runner',ROOT.parent/'task15_cohort_a_runner/adapter_tests',
             ROOT.parent/'task15_harness',ROOT.parent/'task15_harness/tests',ROOT.parent/'task15_runtime_smoke']:
    sys.path.insert(0,str(path))
from roadcheck.testing import RejectNative
sys.meta_path.insert(0,RejectNative())
if __name__=='__main__':
    names=['test_adapter.AdapterTests.test_graph_real_exports_parse_only',
           'test_control.ControlTests.test_41_skip_external_cannot_reach_static_verified',
           'test_v12.V12Tests.test_24_missing_modified_redirected_artifact_identities']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun==3 and not result.skipped else 1)
