"""Read-only inspect and synthetic self-test only. No build/workload/approval modes."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent
for p in [ROOT,ROOT.parent/'task15_cohort_a_runner',ROOT.parent/'task15_harness']:
    sys.path.insert(0,str(p))


def main(args=None):
    from diagnostic.core import require,MARKS
    args=sys.argv[1:] if args is None else args
    try:
        if args==['self-test']:
            from diagnostic.testing import run_tests
            return run_tests()
        require(len(args)==3 and args[:2]==['inspect','--output'] and Path(args[2]).is_absolute(),'UNSUPPORTED_OPERATION_OR_ARGUMENTS')
        from diagnostic.workflow import inspect
        result=inspect(args[2]);print(json.dumps({**MARKS,**result},sort_keys=True));return 0
    except Exception as exc:
        print(json.dumps({**MARKS,'implementation_status':'BLOCKED','error_type':type(exc).__name__,'error':str(exc)},sort_keys=True));return 2

if __name__=='__main__':
    from diagnostic.security import install
    install()
    raise SystemExit(main())
