"""Phase 7 fixed-scope entry. No arbitrary source, graph, executable or performance mode."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent
for path in [ROOT,ROOT.parent/'task15_cohort_a_runner',ROOT.parent/'task15_runtime_smoke']:
    sys.path.insert(0,str(path))


def main(args=None):
    from production_adapter import require
    from roadcheck import MARKS
    args=sys.argv[1:] if args is None else args
    try:
        if args==['self-test']:
            from roadcheck.testing import run_tests
            return run_tests()
        if len(args)==3 and args[:2]==['run-fixed','--output']:
            from roadcheck.campaign import run
            return run(args[2])
        if len(args)==3 and args[0]=='_fixed-child':
            from roadcheck.campaign import fixed_child
            return fixed_child(args[1],args[2])
        require(False,'UNSUPPORTED_OPERATION_OR_ARGUMENTS')
    except Exception as exc:
        print(json.dumps({**MARKS,'status':'REJECTED','error_type':type(exc).__name__,'error':str(exc)},sort_keys=True))
        return 2

if __name__=='__main__':raise SystemExit(main())
