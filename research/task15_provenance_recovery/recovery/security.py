import importlib.abc
import sys
from .core import require
class RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        require(not fullname.startswith('bmssp_native'),'NATIVE_IMPORT_FORBIDDEN');return None

def audit(event,args):
    if event=='import':require(not str(args[0]).startswith('bmssp_native'),'NATIVE_IMPORT_FORBIDDEN')
    if event=='ctypes.dlopen':require('bmssp_native' not in str(args[0]),'NATIVE_DLOPEN_FORBIDDEN')
    if event=='subprocess.Popen':
        argv=args[1]
        allowed=len(argv)==3 and list(argv[:2]) in [['/usr/sbin/pkgutil','--pkg-info-plist'],['/usr/sbin/pkgutil','--files']]
        allowed=allowed or list(argv)==['/Library/Developer/CommandLineTools/usr/bin/ld','-v']
        allowed=allowed or len(argv)==5 and list(argv[:4])==['git','-C','/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer','show']
        require(allowed,'BUILD_QUERY_NETWORK_OR_UNAPPROVED_EXECUTION_FORBIDDEN')

def install():sys.meta_path.insert(0,RejectNative());sys.addaudithook(audit)
