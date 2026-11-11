"""Fixed Phase 6 entry point. Only run-fixed and fake self-test are public."""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parent/'task15_cohort_a_runner'))


def main(args=None):
    from production_adapter import require
    from smoke import MARKS
    args = sys.argv[1:] if args is None else args
    try:
        if args == ['self-test']:
            from smoke.testing import run_tests
            return run_tests()
        if len(args) == 3 and args[:2] == ['run-fixed','--output']:
            from smoke.campaign import run
            return run(args[2])
        if len(args) == 3 and args[0] == '_fixed-child':
            from smoke.campaign import fixed_child
            return fixed_child(args[1],args[2])
        require(False,'UNSUPPORTED_OPERATION_OR_ARGUMENTS')
    except Exception as exc:
        print(json.dumps({**MARKS,'status':'REJECTED','error_type':type(exc).__name__,'error':str(exc)},sort_keys=True))
        return 2

if __name__ == '__main__':raise SystemExit(main())
