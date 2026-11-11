"""Historical build provenance plus explicit process-local CLT/SDK reconciliation."""
import json
from pathlib import Path
import plistlib
import shlex
from .core import require,sha
from .tools import run,file_identity

ROOT=Path('/Users/sallahuddin/Projects/BMSSP_Logistics_optimizer-task14-evidence')
CLT='/Library/Developer/CommandLineTools'
XCODE='/Applications/Xcode.app/Contents/Developer'
COMPILER=CLT+'/usr/bin/clang++'
SDK=CLT+'/SDKs/MacOSX.sdk'


def archive(name,index):
    path=ROOT/name;data=path.read_bytes();require(name in index and sha(data)==index[name]['sha256'],'ARCHIVE_PROVENANCE:'+name)
    return data


def inspect_sdk(path):
    root=Path(path)
    if not root.is_dir():return {'path':str(root),'status':'BLOCKED','missing':['SDK_DIRECTORY']}
    files={};metadata={}
    for name in ['SDKSettings.json','SDKSettings.plist','System/Library/CoreServices/SystemVersion.plist']:
        f=root/name
        if f.is_file():
            data=f.read_bytes();files[name]=sha(data)
            value=plistlib.loads(data) if name.endswith('.plist') else json.loads(data)
            metadata[name]={k:value[k] for k in ['Version','CanonicalName','DisplayName','ProductVersion','ProductBuildVersion','BuildID'] if k in value}
    headers={}
    for name in ['vector','concepts','compare','coroutine','span','memory_resource','__config']:
        f=root/'usr/include/c++/v1'/name
        headers[name]={'present':f.is_file(),'sha256':sha(f.read_bytes()) if f.is_file() else None}
    for name in ['usr/lib/libSystem.tbd','usr/lib/libc++.tbd','usr/include/c++/v1/module.modulemap']:
        f=root/name
        if f.is_file():files[name]=sha(f.read_bytes())
    return {'path':str(root),'resolved_path':str(root.resolve()),'status':'VERIFIED' if len(metadata)==3 and all(v['present'] for v in headers.values()) else 'BLOCKED',
            'metadata':metadata,'file_sha256':files,'cxx20_header_availability':headers,
            'identity_scope':'Exact current selected metadata/header/library-stub bytes; not a historical whole-SDK content hash or a successful compile/ABI test.'}


def reconcile(p):
    index_path=ROOT/'evidence-index.json'
    expected=next(v['sha256'] for k,v in p['evidence_files_used'].items() if k==str(index_path))
    require(sha(index_path.read_bytes())==expected,'TASK14_INDEX_IDENTITY')
    index=json.loads(index_path.read_bytes());historical=json.loads(archive('run/toolchain.json',index))
    commands={}
    commands['selected_developer']=run(['/usr/bin/xcode-select','-p'])
    for label,env in [('default',{}),('clt',{'DEVELOPER_DIR':CLT}),('xcode',{'DEVELOPER_DIR':XCODE})]:
        for suffix,args in [('compiler',['--find','clang++']),('sdk',['--sdk','macosx','--show-sdk-path']),('sdk_version',['--sdk','macosx','--show-sdk-version']),('default_sdk',['--show-sdk-path']),('default_sdk_version',['--show-sdk-version'])]:
            commands[label+'_'+suffix]=run(['/usr/bin/xcrun',*args],env)
    compiler=file_identity(COMPILER)
    for suffix,arg in [('version','--version'),('target','-print-target-triple'),('resource_dir','-print-resource-dir')]:commands['clt_'+suffix]=run([COMPILER,arg],{'DEVELOPER_DIR':CLT})
    selected=commands['default_compiler']['stdout'].strip()
    selected_identity=file_identity(selected)
    commands['selected_version']=run([selected,'--version'])
    linker=file_identity(CLT+'/usr/bin/ld')
    sdk=inspect_sdk(SDK);xcode_sdk=inspect_sdk(XCODE+'/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
    builds={}
    for variant in ['baseline','candidate']:
        database=json.loads(archive('run/'+variant+'/compile_commands.json',index))
        foundation=[r for r in database if '/native/' in r['file'] and any(r['file'].endswith('/'+n) for n in ['bmssp_2025.cpp','bmssp_bounded.cpp','symbolic_label.cpp','bounded_frontier.cpp','graph.cpp','degree_reduction.cpp','bindings.cpp'])]
        argv=[shlex.split(row['command']) for row in foundation]
        required=['-O3','-DNDEBUG','-std=c++20','-fPIC']
        flags_ok=all(a[0]==COMPILER and all(flag in a for flag in required) and a[a.index('-arch')+1]=='arm64' and a[a.index('-isysroot')+1]==SDK and not any(x in a for x in ['-ffast-math','-Ofast','-fno-exceptions','-fno-rtti']) for a in argv)
        cache=archive('run/'+variant+'/CMakeCache.txt',index).decode()
        config=json.loads(archive('run/'+variant+'-commands.json',index))
        link=archive('run/'+variant+'/CMakeFiles/bmssp_native.dir/link.txt',index).decode()
        compiler_file='run/'+variant+'/CMakeFiles/4.3.3/CMakeCXXCompiler.cmake'
        compiler_metadata=archive(compiler_file,index).decode()
        builds[variant]={'status':'VERIFIED' if flags_ok and len(foundation)==7 else 'BLOCKED','compile_records':foundation,'link_command':link,
            'configuration_argv':config[0]['argv'],'cache_sha256':sha(cache.encode()),'cache_relevant_lines':[l for l in cache.splitlines() if l.startswith(('CMAKE_CXX_','CMAKE_OSX_','CMAKE_BUILD_TYPE','CMAKE_SHARED_LINKER','CMAKE_MODULE_LINKER','Python_EXECUTABLE','pybind11_DIR'))],
            'compiler_metadata_sha256':sha(compiler_metadata.encode()),'compiler_metadata_relevant':[l for l in compiler_metadata.splitlines() if any(k in l for k in ['COMPILER_VERSION','COMPILER_TARGET','SYSROOT','IMPLICIT_INCLUDE','IMPLICIT_LINK'])],
            'missing_historical_identities':['compiler executable SHA-256 at original build','complete SDK/header bytes at original build','linker executable SHA-256 at original build'],
            'abi_limitations':'Original public bindings and lib identities remain pinned; current header presence/version does not prove identical historical libc++/compiler internals or layout. Original temporary Python/pybind include paths must not be silently remapped.'}
    versions_match=commands['clt_version']['stdout']==historical['compiler']['stdout']
    available=versions_match and 'arm64' in commands['clt_target']['stdout'] and sdk['status']=='VERIFIED' and commands['clt_sdk_version']['returncode']==0 and all(b['status']=='VERIFIED' for b in builds.values())
    return {'availability':'VERIFIED' if available else 'BLOCKED','historical_exact_byte_continuity':'BLOCKED','diagnostic_construction':'BLOCKED',
            'root_cause':{'selected_developer':commands['selected_developer']['stdout'].strip(),'selected_compiler_differs':selected!=COMPILER,
                          'historical_default_sdk_version_failed':historical['sdk_version']['exit_code']!=0,
                          'process_local_CLT_lookup_succeeds':commands['clt_sdk_version']['returncode']==0,
                          'explanation':'Default Xcode selection and CLT SDK lookup context are mixed. Explicit process-local DEVELOPER_DIR=CLT with --sdk macosx resolves CLT SDK metadata; original historical default SDK version query also failed. No global selection or SDK was changed.'},
            'compiler':compiler,'selected_compiler':selected_identity,'linker':linker,'sdk':sdk,'xcode_sdk_not_substituted':xcode_sdk,
            'compiler_version_matches_archive_exactly':versions_match,'commands':commands,'build_provenance':builds,
            'invocation_specification':{'status':'VERIFIED' if available else 'BLOCKED','environment':{'DEVELOPER_DIR':CLT,'SDKROOT':SDK},'compiler':COMPILER,'compiler_sha256':compiler['sha256'],'sdk_root':SDK,'target':'arm64',
                                        'argv_policy':'Use complete archived per-file argv/link command arrays, with explicitly reviewed source/output/dependency mappings only. No compilation performed.',
                                        'execution_authorized':False,'remaining_blockers':['No original-build executable/SDK byte hashes to prove continuity; current exact byte identities must be independently reconciled/locked.','Future diagnostic whitelist, source diff and complete G8 mapping are absent.','Original temporary pybind11/Python include mapping requires explicit provenance.']}}
