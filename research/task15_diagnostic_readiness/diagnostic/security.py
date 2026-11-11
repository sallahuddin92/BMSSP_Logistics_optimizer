import importlib.abc
from pathlib import Path
import sys
from .core import require

class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        require(not fullname.startswith('bmssp_native'),'NATIVE_IMPORT_FORBIDDEN')
        return None

def audit(event,args):
    if event=='import':require(not str(args[0]).startswith('bmssp_native'),'NATIVE_IMPORT_FORBIDDEN')
    if event=='ctypes.dlopen':require('bmssp_native' not in str(args[0]),'NATIVE_DLOPEN_FORBIDDEN')
    if event=='subprocess.Popen':
        from .tools import validate_command
        validate_command(args[1])

def install():sys.meta_path.insert(0,RejectNative());sys.addaudithook(audit)
