"""Defense in depth for this static entry only; no changes to production gates."""
import importlib.abc
from pathlib import Path
import sys
from .core import require

class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        require(not (fullname=='bmssp_native' or fullname.startswith('bmssp_native.')),'NATIVE_IMPORT_FORBIDDEN')
        return None

def audit(event,args):
    if event=='import':require(not str(args[0]).startswith('bmssp_native'),'NATIVE_IMPORT_FORBIDDEN')
    if event=='ctypes.dlopen':require('bmssp_native' not in str(args[0]),'NATIVE_DLOPEN_FORBIDDEN')
    if event=='subprocess.Popen':
        from .host import COMMANDS
        argv=args[1]
        require(isinstance(argv,(list,tuple)),'UNAPPROVED_PROCESS')
        approved=list(argv) in COMMANDS.values()
        if Path(str(argv[0])).name=='git':
            approved=all(x not in argv for x in ['push','commit','reset','checkout','fetch','pull']) and any(x in argv for x in ['rev-parse','branch','remote','diff','ls-files','status'])
        require(approved,'NATIVE_OR_UNAPPROVED_EXECUTION_FORBIDDEN')

def install():
    sys.meta_path.insert(0,RejectNative());sys.addaudithook(audit)
