"""Explicit evidence-led allowlist, not recursive disk discovery."""
from pathlib import Path
import json
import os
import plistlib
import subprocess
import tarfile
from .core import require,digest,file_hash,current_file,read

ARCHIVE=Path('/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task14-evidence')
STAGE=Path('/private/tmp/bmssp-task14.i2derfl4')
VENV=Path('/private/tmp/bmssp-task6.ZTijar/venv')
PACKAGES=('com.apple.pkg.CLTools_Executables','com.apple.pkg.CLTools_macOS_SDK','com.apple.pkg.CLTools_SDK_macOS_NMOS','com.apple.pkg.CLTools_SDK_macOS_LMOS')
RECEIPT_ROOTS=('/var/db/receipts','/Library/Apple/System/Library/Receipts','/Library/Receipts')
COMMON=('run/toolchain.json','run/initial.json','run/baseline-verification.json','run/binary-hashes.json','baseline-source-hashes.json','candidate-source-hashes.json','run/baseline-source.tar','candidate-source.tar')
SUFFIXES=('compile_commands.json','CMakeCache.txt','CMakeFiles/4.3.3/CMakeCXXCompiler.cmake','CMakeFiles/CMakeConfigureLog.yaml',
          'CMakeFiles/bmssp_native.dir/link.txt','CMakeFiles/bmssp_native.dir/native/python/bindings.cpp.o','CMakeFiles/bmssp_native.dir/native/python/bindings.cpp.o.d',
          'CMakeFiles/4.3.3/CMakeDetermineCompilerABI_CXX.bin','CMakeFiles/4.3.3/CompilerIdCXX/a.out','CMakeFiles/4.3.3/CompilerIdCXX/CMakeCXXCompilerId.cpp')
ALLOWED=set(COMMON)|{'run/'+v+'/'+s for v in ('baseline','candidate') for s in SUFFIXES}|{'run/'+v+'-commands.json' for v in ('baseline','candidate')}|{'run/'+v+'-build.log' for v in ('baseline','candidate')}|{'run/'+v+'-configure.log' for v in ('baseline','candidate')}|{'run/'+v+'/python/bmssp_native.cpython-311-darwin.so' for v in ('baseline','candidate')}


def authenticated_index(p):
    path=ARCHIVE/'evidence-index.json';expected=p['evidence_files_used'][str(path)]['sha256']
    require(file_hash(path)==expected,'CORRUPTED_ARCHIVE_INDEX')
    return read(path),{'path':str(path),'sha256':expected,'anchor':'PREEXISTING_FROZEN_PROTOCOL'}


def archived(name,index):
    require(name in ALLOWED,'OUT_OF_SCOPE_ARCHIVE_SOURCE')
    path=ARCHIVE/name
    if not path.is_file() or name not in index:return None,{'path':str(path),'status':'UNAVAILABLE','reason':'Expected explicitly scoped artifact/index entry unavailable.'}
    data=path.read_bytes();require(digest(data)==index[name]['sha256'],'ALTERED_HISTORICAL_ARTIFACT:'+name)
    st=path.stat()
    return data,{'path':str(path),'archive_relative_path':name,'sha256':digest(data),'expected_sha256':index[name]['sha256'],'bytes':len(data),'status':'HISTORICALLY_VERIFIED',
                 'mtime_ns_current_metadata_only':st.st_mtime_ns,'timestamp_trust':'Current filesystem timestamp is corroboration only, not an independent build-time byte attestation.'}


def query(argv):
    allowed=(argv[:2]==['/usr/sbin/pkgutil','--pkg-info-plist'] or argv[:2]==['/usr/sbin/pkgutil','--files']) and len(argv)==3 and argv[2] in PACKAGES
    allowed=allowed or (len(argv)==5 and argv[:3]==['git','-C','/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer'] and argv[3]=='show' and argv[4].split(':',1)[0] in {'cafea0f36091396dff6ebd5efd88d59cd1e97f77','cb5e1b6dd1c7ac52755a29d6b7f411f9b68ee80e'} and argv[4].split(':',1)[-1] in {'CMakeLists.txt','native/python/bindings.cpp','native/src/bmssp_2025.cpp','native/src/bmssp_bounded.cpp','native/src/symbolic_label.cpp'})
    allowed=allowed or argv==['/Library/Developer/CommandLineTools/usr/bin/ld','-v']
    require(allowed,'OUT_OF_SCOPE_COMMAND')
    try:
        p=subprocess.run(argv,capture_output=True,stdin=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','LC_ALL':'C','LANG':'C'},timeout=15)
        require(len(p.stdout)+len(p.stderr)<8*1024*1024,'RECEIPT_OUTPUT_BOUND')
        return {'argv':argv,'returncode':p.returncode,'stdout_sha256':digest(p.stdout),'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace'),'error':None}
    except (OSError,subprocess.TimeoutExpired) as exc:return {'argv':argv,'returncode':None,'stdout_sha256':None,'stdout':'','stderr':'','error':{'type':type(exc).__name__,'message':str(exc)}}


def receipts():
    result=[]
    for package in PACKAGES:
        info=query(['/usr/sbin/pkgutil','--pkg-info-plist',package]);listing=query(['/usr/sbin/pkgutil','--files',package])
        metadata=plistlib.loads(info['stdout'].encode()) if info['returncode']==0 else None
        selected=[line for line in listing['stdout'].splitlines() if any(t in line for t in ['/bin/clang','/bin/ld','MacOSX26.5.sdk/SDKSettings','MacOSX26.5.sdk/usr/include/c++/v1/__config'])]
        listing['line_count']=len(listing['stdout'].splitlines());listing['selected_payload_paths']=selected;listing.pop('stdout')
        raw=[]
        for root in RECEIPT_ROOTS:
            for suffix in ('.plist','.bom'):
                identity=current_file(Path(root)/(package+suffix))
                if identity:raw.append(identity)
        result.append({'package_id':package,'metadata_query':info,'payload_listing_query':listing,'receipt_metadata':metadata,'current_receipt_files':raw,
                       'trust':'Current package receipt/installed timestamp/payload paths are not historical compiler or SDK byte continuity, even if installation predates the build.'})
    return result


def source_tar(path,expected_names):
    result={'members':[],'selected_source_hashes':{},'toolchain_payload_candidates':[]}
    with tarfile.open(path,'r:') as tf:
        members=tf.getmembers();require(len(members)<=4096,'SOURCE_TAR_MEMBER_BOUND')
        for member in members:
            name=member.name.removeprefix('./')
            require(not Path(name).is_absolute() and '..' not in Path(name).parts,'UNSAFE_SOURCE_ARCHIVE')
            result['members'].append({'name':name,'size':member.size,'mtime_claimed_by_archive':member.mtime,'is_regular':member.isfile()})
            if member.isfile() and name in expected_names:
                f=tf.extractfile(member);data=f.read();result['selected_source_hashes'][name]=digest(data)
            if member.isfile() and any(token in name for token in ['clang++','SDKSettings','pybind11/include','Python.framework']):result['toolchain_payload_candidates'].append(name)
    return result
