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
    require(len(case_ids) >= 56 and all(any(f'.test_{i:02d}_' in name for name in case_ids)
            for i in range(1, 46)), 'TEST_SCOPE', 'all required control cases must be discovered')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'scope': 'STATIC_AND_SYNTHETIC_ONLY', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'successful': result.wasSuccessful() and not result.skipped, 'case_ids': case_ids,
              'no_BMSSP_workload': True,
              'negative_controls': [record for module in ('test_control', 'test_delta')
                                    for record in getattr(sys.modules.get(module), 'NEGATIVE_RESULTS', [])]}
    if output is not None:
        create_bundle(protocol, output, {'tests.json': canonical(report)+b'\n',
                                        'tests.log': log.getvalue().encode()})
    print(log.getvalue(), end='')
    return 0 if result.wasSuccessful() and not result.skipped else 1
