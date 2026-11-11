import argparse
import json
from pathlib import Path
import signal
import sys
from . import SYNTHETIC
from .errors import RunnerError,Interrupted
from .wire import canonical,FAULTS

SAFE={'synthetic-run','validate-bundle','self-test','plan'}


class Parser(argparse.ArgumentParser):
    def error(self,message):raise RunnerError('ARGUMENT',message)


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args and args[0] not in SAFE and args[0] not in {'-h','--help'}:
        print(canonical({**SYNTHETIC,'error':'UNSUPPORTED_OPERATION','operation':args[0]}).decode());return 2
    previous={}
    interrupt_seen=False
    try:
        parser=Parser(description='CohortA synthetic controller only; real execution is unavailable')
        parser.add_argument('operation',choices=sorted(SAFE));parser.add_argument('--output',type=Path)
        parser.add_argument('--bundle',type=Path);parser.add_argument('--unit');parser.add_argument('--timeout',type=float,default=2.0)
        parser.add_argument('--fault',choices=sorted(FAULTS|{'interrupted_session','corrupted_output','missing_completion_marker'}),default='none')
        parsed=parser.parse_args(args)
        if parsed.operation!='synthetic-run' and (parsed.unit is not None or parsed.fault!='none' or parsed.timeout!=2.0):
            raise RunnerError('ARGUMENT','unit/fault/timeout are synthetic-run options only')
        if parsed.operation in {'plan','validate-bundle'} and parsed.output is not None:
            raise RunnerError('ARGUMENT','--output is not used by this operation')
        if parsed.operation!='validate-bundle' and parsed.bundle is not None:
            raise RunnerError('ARGUMENT','--bundle is validate-bundle only')
        if parsed.operation=='synthetic-run':
            if parsed.output is None:raise RunnerError('ARGUMENT','fresh external --output required')
            from .controller import Controller
            def interrupted(signum,frame):
                nonlocal interrupt_seen
                if not interrupt_seen:
                    interrupt_seen=True;raise Interrupted('controller signal '+str(signum))
            for sig in [signal.SIGTERM,signal.SIGINT]:previous[sig]=signal.signal(sig,interrupted)
            result=Controller(parsed.output,[parsed.unit] if parsed.unit else None,parsed.fault,parsed.timeout).run()
            print(canonical({**SYNTHETIC,'status':result['status'],'error_code':result['error_code'],'output':str(parsed.output),'records':result['retained_query_records']}).decode())
            return 0 if result['status']=='SYNTHETIC_COMPLETE' else 130 if result['status']=='INTERRUPTED' else 3
        if parsed.operation=='validate-bundle':
            if parsed.bundle is None:raise RunnerError('ARGUMENT','--bundle required')
            from .bundle import validate_bundle
            print(canonical(validate_bundle(parsed.bundle)).decode());return 0
        if parsed.operation=='plan':
            from .frozen import Workload
            w=Workload();print(canonical({**SYNTHETIC,'A_units':[u['id'] for u in w.units],
                'session_slots':w.slots(w.units),'records':41472,'production_backend':'UNAVAILABLE'}).decode());return 0
        from .testing import run_tests
        return run_tests(parsed.output)
    except KeyboardInterrupt:
        print(canonical({**SYNTHETIC,'error':'SESSION_INTERRUPTED','detail':'interrupted before lifecycle receipt creation'}).decode());return 130
    except (RunnerError,OSError) as exc:
        code=exc.code if isinstance(exc,RunnerError) else 'FILESYSTEM_ERROR'
        print(canonical({**SYNTHETIC,'error':code,'detail':str(exc)}).decode());return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':raise SystemExit(main())
