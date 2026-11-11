"""Isolated fake-binding tests; the production adapter has no executable entry point."""
from pathlib import Path
import importlib.abc
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'bmssp_native' or fullname.startswith('bmssp_native.'):
            raise AssertionError('Native imports forbidden in adapter tests')
        return None

if __name__ == '__main__':
    sys.meta_path.insert(0, RejectNative())
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent/'adapter_tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1)
