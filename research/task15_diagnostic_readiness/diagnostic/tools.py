"""Bounded, explicit read-only tool invocations; compiler invocation cannot compile."""
import os
from pathlib import Path
import subprocess
from .core import require,sha

ENV={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','LC_ALL':'C','LANG':'C'}
TOOL_NAMES={'nm','otool','llvm-objdump','dwarfdump','atos','clang++','clang','ld','xcrun','xcode-select','git','cmake'}


def file_identity(path):
    path=Path(path);require(path.is_file(),'MISSING_TOOL:'+str(path))
    return {'path':str(path),'resolved_path':str(path.resolve()),'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size}


def validate_command(argv):
    require(isinstance(argv,(list,tuple)) and bool(argv),'UNAPPROVED_TOOL')
    name=Path(argv[0]).name;require(name in TOOL_NAMES,'UNAPPROVED_TOOL')
    if name in {'clang','clang++'}:require(list(argv[1:]) in [['--version'],['-print-target-triple'],['-print-resource-dir']],'COMPILATION_FORBIDDEN')
    if name=='cmake':require(list(argv[1:])==['--version'],'BUILD_FORBIDDEN')
    if name=='ld':require(list(argv[1:]) in [['-v'],['--version']],'LINKING_FORBIDDEN')
    if name=='atos':require(list(argv[1:])==['-h'],'PROCESS_ATTACHMENT_FORBIDDEN')
    if name=='git':require(argv[1]=='show' and len(argv)==3,'GIT_MUTATION_FORBIDDEN')
    if name=='xcode-select':require(list(argv[1:])==['-p'],'GLOBAL_SELECTION_FORBIDDEN')
    if name=='xcrun':
        args=list(argv[1:])
        require(args in [['--show-sdk-path'],['--show-sdk-version'],['--sdk','macosx','--show-sdk-path'],['--sdk','macosx','--show-sdk-version']] or len(args)==2 and args[0]=='--find' and args[1] in TOOL_NAMES,'UNAPPROVED_XCRUN')
    return True


def run(argv,env=None,limit=16*1024*1024):
    validate_command(argv)
    actual={**ENV,**(env or {})}
    require(set(actual)<=set(ENV)|{'DEVELOPER_DIR','SDKROOT'},'ENVIRONMENT_OVERRIDE_FORBIDDEN')
    try:
        p=subprocess.run(argv,cwd=Path(__file__).resolve().parents[3],capture_output=True,stdin=subprocess.DEVNULL,text=True,env=actual,timeout=45)
        require(len(p.stdout.encode())+len(p.stderr.encode())<=limit,'TOOL_OUTPUT_CAP')
        return {'argv':argv,'environment':actual,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'error':None}
    except (OSError,subprocess.TimeoutExpired) as exc:return {'argv':argv,'environment':actual,'returncode':None,'stdout':'','stderr':'','error':{'type':type(exc).__name__,'message':str(exc)}}


def discover(name,developer=None):
    result=run(['/usr/bin/xcrun','--find',name],{'DEVELOPER_DIR':developer} if developer else None);require(result['returncode']==0,'TOOL_DISCOVERY:'+name)
    path=result['stdout'].strip();return file_identity(path),result
