from __future__ import annotations
import io
from pathlib import Path
import unittest
import sys
from .output import create_bundle
from .errors import require
from .integrity import canonical
from .protocol import PACKAGE_ROOT, Protocol


def run_tests(output: Path | None, protocol: Protocol) -> int:
    """Only isolated control-plane unittest files; never discover native/backend tests."""
    loader = unittest.TestLoader()
    suite = loader.discover(str(PACKAGE_ROOT/'tests'), pattern='test_*.py')
    def cases(node):
        if isinstance(node, unittest.TestSuite):
            return [item for child in node for item in cases(child)]
        return [node.id()]
    case_ids = cases(suite)
    required_v12 = {f'.test_{i:02d}_' for i in range(1, 30)}
    require(all(any(name.startswith('test_v12.') and prefix in name for name in case_ids)
                for prefix in required_v12), 'TEST_SCOPE', 'all v1.2 integration controls required')
    require(len(case_ids) >= 85 and all(any(name.startswith(f'test_control.ControlTests.test_{i:02d}_') for name in case_ids)
            for i in range(1, 46)), 'TEST_SCOPE', 'all required control cases must be discovered')
    require(all(any(name.startswith('test_v13.') and f'.test_{i:02d}_' in name for name in case_ids)
                for i in range(1,23)), 'TEST_SCOPE', 'all v1.3 controls required')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'scope': 'STATIC_AND_SYNTHETIC_ONLY', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'successful': result.wasSuccessful() and not result.skipped, 'case_ids': case_ids,
              'no_BMSSP_workload': True,
              'negative_controls': [record for module in ('test_control', 'test_delta', 'test_v12', 'test_v13')
                                    for record in getattr(sys.modules.get(module), 'NEGATIVE_RESULTS', [])]}
    if output is not None:
        create_bundle(protocol, output, {'tests.json': canonical(report)+b'\n',
                                        'tests.log': log.getvalue().encode()})
    print(log.getvalue(), end='')
    return 0 if result.wasSuccessful() and not result.skipped else 1
