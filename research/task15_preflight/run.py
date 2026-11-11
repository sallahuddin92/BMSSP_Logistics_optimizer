"""Bounded static-only preflight; no executable, source, approval or instrument override."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent
for p in [ROOT,ROOT.parent/'task15_cohort_a_runner',ROOT.parent/'task15_harness',ROOT.parent/'task15_road_readiness',ROOT.parent/'task15_runtime_smoke']:
    sys.path.insert(0,str(p))


def main(args=None):
    from preflight.core import require
    args=sys.argv[1:] if args is None else args
    try:
        if args==['self-test']:
            from preflight.testing import run_tests
            return run_tests()
        require(len(args)==5 and args[0]=='verify' and args[1]=='--phase7' and args[3]=='--output','UNSUPPORTED_OPERATION_OR_ARGUMENTS')
        require(Path(args[2]).is_absolute() and Path(args[4]).is_absolute(),'ABSOLUTE_PATH_REQUIRED')
        from preflight.integration import run
        result=run(args[2],args[4])
        print(json.dumps({'technical_result':result,'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending'},sort_keys=True))
        return 3 if result=='TECHNICAL_STATIC_PREFLIGHT_BLOCKED' else 0
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'error':str(exc),'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending'},sort_keys=True));return 2

if __name__=='__main__':
    from preflight.security import install
    install()
    raise SystemExit(main())
