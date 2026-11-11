"""Fake-only negative controls; importing originals is forbidden here."""
import importlib.abc
from pathlib import Path
import sys
import unittest

class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname == 'bmssp_native' or fullname.startswith('bmssp_native.'):
            raise AssertionError('REAL_NATIVE_IMPORT_IN_FAKE_TEST')
        return None


def run_tests():
    guard = RejectNative()
    sys.meta_path.insert(0,guard)
    try:
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[1]/'tests'))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1
    finally:sys.meta_path.remove(guard)
