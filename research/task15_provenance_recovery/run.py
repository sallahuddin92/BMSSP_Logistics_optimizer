"""No build/query/benchmark modes. Only the fixed bounded recovery or fake tests."""
from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parent
for p in [ROOT,ROOT.parent/'task15_cohort_a_runner',ROOT.parent/'task15_harness']:sys.path.insert(0,str(p))


def main(args=None):
    from recovery.core import require
    args=sys.argv[1:] if args is None else args
    try:
        if args==['self-test']:
            import unittest
            suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'));r=unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if r.wasSuccessful() and r.testsRun and not r.skipped else 1
        require(len(args)==3 and args[:2]==['recover','--output'] and Path(args[2]).is_absolute(),'UNSUPPORTED_OPERATION_OR_ARGUMENTS')
        from recovery.workflow import run
        verdict=run(args[2]);print(json.dumps({'recovery_verdict':verdict,'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending'},sort_keys=True));return 0
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'message':str(exc),'calibration_authorized':False,'collection_authorized':False},sort_keys=True));return 2

if __name__=='__main__':
    from recovery.security import install
    install();raise SystemExit(main())
