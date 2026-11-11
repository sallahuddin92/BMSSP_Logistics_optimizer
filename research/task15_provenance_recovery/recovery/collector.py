"""One finite recovery campaign over documented Task14 and directly referenced sources."""
import json
from pathlib import Path
import re
import shlex
import struct
from .core import component,current_file,digest,file_hash,require,canonical,compare_versions
from .sources import ARCHIVE,STAGE,VENV,COMMON,SUFFIXES,authenticated_index,archived,query,receipts,source_tar

SOURCE_FILES=('CMakeLists.txt','native/python/bindings.cpp','native/src/bmssp_2025.cpp','native/src/bmssp_bounded.cpp','native/src/symbolic_label.cpp')
SDK_ROOT=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk')
PHASE9=Path('/Users/sallahuddin/Projects/BMSSP-task15-phase9-diagnostic-60big8wa/delivery-inventory/toolchain-reconciliation.json')


def build_version(data):
    require(len(data)>=32 and struct.unpack_from('<I',data)[0]==0xfeedfacf,'MACHO_HEADER')
    count=struct.unpack_from('<I',data,16)[0];cursor=32
    def version(v):return f'{v>>16}.{(v>>8)&255}.{v&255}'
    result=[]
    for _ in range(count):
        command,size=struct.unpack_from('<II',data,cursor);require(size>=8 and cursor+size<=len(data),'LOAD_COMMAND_BOUND')
        if command==0x32:
            platform,minimum,sdk,ntools=struct.unpack_from('<4I',data,cursor+8);require(24+ntools*8<=size,'BUILD_VERSION_BOUND')
            tools=[]
            for i in range(ntools):
                tool,v=struct.unpack_from('<II',data,cursor+24+i*8);tools.append({'tool_id':tool,'version':version(v)})
            result.append({'platform':platform,'deployment_minimum':version(minimum),'sdk_version':version(sdk),'tools':tools})
        cursor+=size
    return result


def sdk_current(root):
    expected=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk')
    require(root.resolve()==expected.resolve(),'REDIRECTED_SDK_PATH')
    names=['SDKSettings.json','SDKSettings.plist','System/Library/CoreServices/SystemVersion.plist','usr/include/c++/v1/__config','usr/include/c++/v1/vector','usr/include/c++/v1/concepts','usr/include/c++/v1/compare','usr/include/c++/v1/coroutine','usr/lib/libSystem.tbd','usr/lib/libc++.tbd']
    entries={name:current_file(root/name) for name in names}
    return {'original_sdk_root':str(root),'resolved_path':str(root.resolve()),'files':entries,'selected_file_set_identity_sha256':digest(canonical(entries)),
            'scope':'EXPLICIT_METADATA_AND_RELEVANT_HEADER_SUBSET_ONLY_NOT_COMPLETE_SDK','whole_sdk_current_sha256':None}


def recover(p,record=lambda value:None):
    index,index_identity=authenticated_index(p)
    names=list(COMMON)
    for variant in ['baseline','candidate']:
        names += ['run/'+variant+'/'+suffix for suffix in SUFFIXES]
        names += ['run/'+variant+'-commands.json','run/'+variant+'-build.log','run/'+variant+'-configure.log','run/'+variant+'/python/bmssp_native.cpython-311-darwin.so']
    raw={};inventory=[];contradictions=[]
    for name in names:
        data,source_record=archived(name,index);inventory.append(source_record);record({'event':'ARCHIVED_SOURCE_CHECKED','source':source_record})
        if data is not None:raw[name]=data
    for mandatory in ['run/toolchain.json','baseline-source-hashes.json','candidate-source-hashes.json','run/binary-hashes.json']:
        require(mandatory in raw,'UNAVAILABLE_ORIGINAL_ARTIFACT:'+mandatory)
    toolchain=json.loads(raw['run/toolchain.json']);historical_version=toolchain['compiler']['stdout'].splitlines()[0]
    compiler_path=toolchain['compiler']['argv'][0]
    require(compiler_path=='/Library/Developer/CommandLineTools/usr/bin/clang++','CONTRADICTORY_COMPILER_PATH')
    package_records=receipts()
    for item in package_records:record({'event':'PACKAGE_RECEIPT_CHECKED','package_id':item['package_id'],'metadata_sha256':item['metadata_query']['stdout_sha256'],'returncode':item['metadata_query']['returncode']})
    timestamps=[{'kind':'CURRENT_PACKAGE_RECEIPT_CLAIM','package_id':r['package_id'],'install_time_unix':r['receipt_metadata'].get('install-time') if r['receipt_metadata'] else None,
                 'source_sha256':r['metadata_query']['stdout_sha256'],'limitation':'Receipt observed now, not proof of bytes during Task14.'} for r in package_records]
    compiler=component('compiler','ORIGINAL_CXX_COMPILER',compiler_path,version=historical_version,current=current_file(compiler_path),sources=['run/toolchain.json','baseline/candidate compile_commands and CMake compiler metadata'],timestamps=timestamps)
    linker_query=query(['/Library/Developer/CommandLineTools/usr/bin/ld','-v'])
    linker=component('linker','ORIGINAL_LINKER','/Library/Developer/CommandLineTools/usr/bin/ld',current=current_file('/Library/Developer/CommandLineTools/usr/bin/ld'),sources=['baseline/candidate CMakeCache CMAKE_LINKER','original link.txt compiler driver','native LC_BUILD_VERSION linker tool versions'],timestamps=timestamps)
    sdk=sdk_current(SDK_ROOT)
    sdk_record=component('sdk-and-headers','ORIGINAL_APPLE_SDK_AND_CXX_HEADERS',str(SDK_ROOT),version=None,current=None,scope='EXPLICIT_METADATA_AND_HEADER_SUBSET_NOT_COMPLETE_SDK',sources=['original -isysroot command arguments','original extension LC_BUILD_VERSION'],timestamps=timestamps)
    sdk_record['current_identity_status']='UNVERIFIED'
    sdk_record['current_resolved_path']=str(SDK_ROOT.resolve())
    components=[compiler,linker,sdk_record];reconciliations={};retained=[];snapshots={};source_checks=[];sdk_versions=[];linker_versions=[]
    historical_binary_hashes=json.loads(raw['run/binary-hashes.json'])
    initial=json.loads(raw['run/initial.json'])
    require(initial['root']==str(STAGE),'BUILD_STAGE_PROVENANCE')
    for variant in ['baseline','candidate']:
        commit=p['binaries'][variant]['source_commit'];prefix='run/'+variant+'/'
        for mandatory in ['compile_commands.json','CMakeCache.txt','CMakeFiles/bmssp_native.dir/link.txt','CMakeFiles/4.3.3/CMakeCXXCompiler.cmake']:
            require(prefix+mandatory in raw,'UNAVAILABLE_ORIGINAL_ARTIFACT:'+prefix+mandatory)
        commands=json.loads(raw[prefix+'compile_commands.json']);cache=raw[prefix+'CMakeCache.txt'].decode();link=raw[prefix+'CMakeFiles/bmssp_native.dir/link.txt'].decode()
        metadata=raw[prefix+'CMakeFiles/4.3.3/CMakeCXXCompiler.cmake'].decode()
        cache_values=dict(re.findall(r'^([^#\n][^:\n]*):[^=\n]*=(.*)$',cache,re.M))
        actual_compiler=cache_values.get('CMAKE_CXX_COMPILER');actual_linker=cache_values.get('CMAKE_LINKER');actual_sdk=cache_values.get('CMAKE_OSX_SYSROOT')
        if not (actual_compiler==compiler_path and actual_linker==linker['original_absolute_path'] and actual_sdk==str(SDK_ROOT)):
            contradictions.append({'kind':'CONTRADICTORY_COMPILER_LINKER_SDK_RECORD','variant':variant,'compiler':actual_compiler,'linker':actual_linker,'sdk':actual_sdk})
        binding=next(c for c in commands if c['file'].endswith('/native/python/bindings.cpp'));argv=shlex.split(binding['command'])
        require(argv[0]==compiler_path and all(x in argv for x in ['-O3','-DNDEBUG','-std=c++20','-arch','arm64','-fPIC']) and shlex.split(link)[0]==compiler_path,'BUILD_COMMAND_CONTRADICTION')
        binary_name=prefix+'python/bmssp_native.cpython-311-darwin.so';binary=raw[binary_name];binary_sha=digest(binary)
        require(binary_sha==p['binaries'][variant]['sha256']==historical_binary_hashes[variant],'ORIGINAL_BINARY_IDENTITY')
        versions=build_version(binary);sdk_versions += [v['sdk_version'] for v in versions]
        linker_versions += [t['version'] for v in versions for t in v['tools'] if t['tool_id']==3]
        anchor={'component':'original-production-'+variant,'component_sha256':binary_sha,'kind':'ARCHIVED_COMPONENT_BYTES','independently_anchored':True,'artifact':binary_name,'index_sha256':index_identity['sha256']}
        components.append(component('original-production-'+variant,'ORIGINAL_PRODUCTION_EXTENSION',p['binaries'][variant]['path'],historical_sha=binary_sha,current=current_file(p['binaries'][variant]['path']),anchors=[anchor],sources=[binary_name,'run/binary-hashes.json','frozen protocol']))
        tar_name='run/baseline-source.tar' if variant=='baseline' else 'candidate-source.tar'
        snapshots[variant]=source_tar(ARCHIVE/tar_name,set(SOURCE_FILES))
        if variant=='baseline':require(digest(raw[tar_name])==initial['source_archive_sha256'],'INITIAL_SOURCE_ARCHIVE_IDENTITY')
        hashes=json.loads(raw[variant+'-source-hashes.json'])
        for name in SOURCE_FILES:
            sha_in_tar=snapshots[variant]['selected_source_hashes'].get(name)
            git=query(['git','-C',p['repository'],'show',commit+':'+name])
            matches=git['returncode']==0 and sha_in_tar==hashes[name]==git['stdout_sha256']
            if not matches:contradictions.append({'kind':'SOURCE_TO_COMMIT_PROVENANCE','variant':variant,'file':name,'tar_sha256':sha_in_tar,'source_inventory_sha256':hashes.get(name),'git_stdout_sha256':git['stdout_sha256'],'git_returncode':git['returncode']})
            source_checks.append({'variant':variant,'commit':commit,'file':name,'sha256':sha_in_tar,'archive_source':tar_name,'git_object_command':git['argv'],'matches_frozen_source':matches})
        tar_sha=digest(raw[tar_name]);tar_anchor={'component':'source-snapshot-'+variant,'component_sha256':tar_sha,'kind':'ARCHIVED_COMPONENT_BYTES','independently_anchored':True,'artifact':tar_name,'index_sha256':index_identity['sha256']}
        components.append(component('source-snapshot-'+variant,'ORIGINAL_SOURCE_SNAPSHOT',str(ARCHIVE/tar_name),historical_sha=tar_sha,current=current_file(ARCHIVE/tar_name),anchors=[tar_anchor],sources=[tar_name,variant+'-source-hashes.json']))
        for suffix in ['CMakeCache.txt','CMakeFiles/4.3.3/CMakeCXXCompiler.cmake','CMakeFiles/bmssp_native.dir/link.txt','CMakeFiles/bmssp_native.dir/native/python/bindings.cpp.o']:
            live=current_file(STAGE/variant/suffix);archived_record=next((r for r in inventory if r.get('archive_relative_path')==prefix+suffix),None)
            retained.append({'path':str(STAGE/variant/suffix),'current':live,'historical_artifact_sha256':archived_record['sha256'] if archived_record else None,
                             'matches_archived_artifact_bytes':live['sha256']==archived_record['sha256'] if live and archived_record else None,
                             'limitation':'Matching retained build artifact bytes are not compiler executable or input-header byte hashes.'})
        relevant_lines=[line for line in cache.splitlines() if any(x in line for x in ['Python_EXECUTABLE','_Python_INCLUDE_DIR','_Python_INTERPRETER_PROPERTIES','pybind11_DIR','pybind11_INCLUDE_DIRS','CMAKE_OSX_DEPLOYMENT_TARGET'])]
        dependency_file=raw.get(prefix+'CMakeFiles/bmssp_native.dir/native/python/bindings.cpp.o.d',b'').decode()
        dependency_paths=[token.rstrip('\\') for token in dependency_file.split() if any(x in token for x in ['pybind11','Python.framework','/usr/include/c++/v1/'])]
        configure_log=raw.get(prefix+'CMakeFiles/CMakeConfigureLog.yaml',b'').decode()
        reconciliations[variant]={'variant':variant,'source_commit':commit,'production_binary_sha256':binary_sha,'compiler_path':actual_compiler,'historical_compiler_version':historical_version,
            'cmake_compiler_version':re.findall(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"',metadata),'linker_path':actual_linker,'sdk_path':actual_sdk,'native_build_version':versions,
            'binding_compile_record':binding,'link_command':link,'configure_commands':json.loads(raw['run/'+variant+'-commands.json'])[0]['argv'],
            'dependency_configuration_lines':relevant_lines,'recorded_header_dependency_paths':dependency_paths,
            'configure_log_identity':digest(configure_log.encode()),'configure_log_provenance_lines':[l for l in configure_log.splitlines() if any(x in l for x in ['AppleClang','clang-2100','-isysroot',' -syslibroot','/usr/bin/ld','-platform_version'])][:100],
            'byte_continuity_status':'UNVERIFIED','meaning':'Commands/path/version/source/output provenance supported; complete compiler/linker/SDK/Python/header historical byte identities not supplied by these records.'}
    sdk_record['historical_version']=';'.join(sorted(set(sdk_versions))) or None;sdk_record['historical_identity_status']='VERSION_ONLY' if sdk_versions else 'UNVERIFIED'
    linker['historical_version']=';'.join(sorted(set(linker_versions))) or None;linker['historical_identity_status']='VERSION_ONLY' if linker_versions else 'UNVERIFIED'
    package_versions=json.loads(toolchain['packages']['stdout'])
    python_version=toolchain['python']['stdout'].strip();pybind_version=next((x['version'] for x in package_versions if x['name']=='pybind11'),None)
    python_path=str(VENV/'bin/python');pybind_path=str(VENV/'lib/python3.11/site-packages/pybind11/include/pybind11/detail/common.h')
    components.append(component('python-build-interpreter','ORIGINAL_PYTHON_BUILD_INTERPRETER',python_path,version=python_version,current=current_file(python_path),sources=['run/toolchain.json Python --version','baseline/candidate CMakeCache _Python ABI metadata']))
    components.append(component('pybind11-build-headers','ORIGINAL_PYBIND11_BUILD_HEADERS',pybind_path,version=pybind_version,current=current_file(pybind_path),scope='SELECTED_HEADER_NOT_COMPLETE_PACKAGE',sources=['run/toolchain.json archived pip listing','baseline/candidate bindings.cpp.o.d and CMake include paths']))
    dependency_current={str(VENV/name):current_file(VENV/name) for name in ['pyvenv.cfg','bin/python','lib/python3.11/site-packages/pybind11/include/pybind11/detail/common.h','lib/python3.11/site-packages/pybind11-2.11.1.dist-info/METADATA','lib/python3.11/site-packages/pybind11-2.11.1.dist-info/RECORD','share/cmake/pybind11/pybind11ConfigVersion.cmake']}
    python_headers=Path('/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/include/python3.11')
    dependency_current.update({str(python_headers/name):current_file(python_headers/name) for name in ['Python.h','patchlevel.h','pyconfig.h']})
    phase9=current_file(PHASE9)
    phase9_reference={'identity':phase9,'role':'Recent current-identity observation only; not historical Task14 compiler bytes.'}
    common_toolchain={'recorded_paths_and_versions_common':all(reconciliations['baseline'][k]==reconciliations['candidate'][k] for k in ['compiler_path','historical_compiler_version','cmake_compiler_version','linker_path','sdk_path']),
                      'historical_byte_identity_common_proven':False,'compiler_version_reconciliation':compare_versions([{'version':r['historical_compiler_version']} for r in reconciliations.values()])}
    # Attach independently checked metadata identities without mislabeling their
    # hashes as hashes of the tools described by those metadata records.
    metadata_names={'run/toolchain.json'}|{'run/'+v+'/'+suffix for v in ['baseline','candidate'] for suffix in ['compile_commands.json','CMakeCache.txt','CMakeFiles/4.3.3/CMakeCXXCompiler.cmake','CMakeFiles/bmssp_native.dir/link.txt']}
    provenance=[{'kind':'ARCHIVED_PATH_VERSION_METADATA_NOT_COMPONENT_BYTES','artifact':r.get('archive_relative_path'),'sha256':r.get('sha256'),'index_sha256':index_identity['sha256']} for r in inventory if r.get('archive_relative_path') in metadata_names and r.get('sha256')]
    for record in components:
        if record['historical_sha256'] is None:record['source_artifact_identities'].extend(provenance)
    missing=[{'component':c['component'],'missing':'Original component payload or independently anchored original-build SHA-256, not a hash computed now.','original_path':c['original_absolute_path']} for c in components if c['historical_sha256'] is None]
    return {'components':components,'historical_inventory':{'frozen_index':index_identity,'artifacts':inventory,'scope_allowlist':names,'installer_receipts':package_records,'retained_build_stage':retained,'source_archives':snapshots,'source_commit_checks':source_checks,'phase9_reference':phase9_reference,
            'scope_stop':'All listed evidence sources examined once. No filesystem-wide/user-file/cloud/network search, package installation or wider filename retry.'},
            'reconciliations':reconciliations,'sdk_current':sdk,'dependency_current':dependency_current,'linker_current_version_query':linker_query,'common_toolchain':common_toolchain,'missing':missing,
            'verdict':'HISTORICAL_PROVENANCE_UNRECOVERABLE_WITH_AVAILABLE_EVIDENCE' if missing else 'HISTORICAL_PROVENANCE_RECOVERED','contradictions':contradictions,
            'distinction':'Original binaries/source snapshots and build metadata are historically anchored. Missing original tool/header byte anchors are evidence limitations, not compiler mismatch or FAILED tooling.'}
