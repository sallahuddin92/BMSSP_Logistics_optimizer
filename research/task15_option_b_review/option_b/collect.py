"""Current-only inventory. Never imports native modules or executes build commands."""
import os,struct,subprocess,time
from pathlib import Path
from .core import *
from .tree import inventory,resolve_safe,content_hash,stamp,walk
BASE='2d529eebf9a5f9e01954bfcb8eab21233dccb5e3'
PROTOCOL='b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
P10=Path('/Users/sallahuddin/Projects/BMSSP-task15-phase10-provenance-3ylwbp0v/campaign')
P10_SHA='5e706bea4454791314955673d9e7e1d3f3910b49179a0ede6e84b105b42511ef'
CLT=Path('/Library/Developer/CommandLineTools')
PYTHON=Path('/opt/homebrew/Cellar/python@3.11/3.11.15_4')
CMAKE=Path('/opt/homebrew/Cellar/cmake/4.3.3')
ENV=Path('/Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy/environment')
ROOTS={'sdk':CLT/'SDKs/MacOSX26.5.sdk','compiler-binaries':CLT/'usr/bin','compiler-libraries':CLT/'usr/lib','compiler-headers':CLT/'usr/include','python':PYTHON,'analysis-environment':ENV,'cmake':CMAKE}
ALIASES=[Path('/opt/homebrew/opt/python@3.11')]
COMMANDS=[[str(CLT/'usr/bin/clang++'),'--version'],[str(CLT/'usr/bin/ld'),'-v'],[str(CMAKE/'bin/cmake'),'--version'],['/usr/bin/make','--version'],[str(PYTHON/'bin/python3.11'),'--version']]

def command(argv):
    require(argv in COMMANDS,'UNAUTHORIZED_EXECUTION_COMMAND')
    env={**os.environ,'DEVELOPER_DIR':str(CLT),'SDKROOT':str(CLT/'SDKs/MacOSX.sdk'),'PYTHONDONTWRITEBYTECODE':'1'}
    start=time.monotonic();r=subprocess.run(argv,env=env,capture_output=True,timeout=30)
    require(len(r.stdout)+len(r.stderr)<262144,'COMMAND_OUTPUT_BOUND')
    return {'argv':argv,'returncode':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace'),'elapsed_seconds':time.monotonic()-start}

def protocol(repo):
    p=read(repo/'docs/task15_tail_attribution_protocol_v1.3.0.json');v=read(repo/'docs/task15_tail_attribution_protocol_v1.3.0.json');v['identity'].pop('sha256')
    require(sha(canonical(v))==PROTOCOL and p['identity']['sha256']==PROTOCOL,'UNAUTHORIZED_PROTOCOL_MODIFICATION');return p

def history():
    require(file_sha(P10/'completion-receipt.json')==P10_SHA,'HISTORICAL_RECEIPT_IDENTITY')
    receipt=read(P10/'completion-receipt.json');out={}
    for name,digest in receipt['files'].items():
        require(Path(name).name==name,'HISTORICAL_PATH_ESCAPE');require(file_sha(P10/name)==digest,'HISTORICAL_OUTPUT_CORRUPTION')
        if name.endswith('.json'):out[name]=read(P10/name)
    require(receipt['recovery_verdict']=='HISTORICAL_PROVENANCE_UNRECOVERABLE_WITH_AVAILABLE_EVIDENCE','HISTORICAL_VERDICT_CHANGED')
    return {'receipt_sha256':P10_SHA,'receipt':receipt,'authenticated_outputs':out}

def macho(path):
    """Read only ARM64 load commands, bounded to 8 MiB; no dynamic loading."""
    with Path(path).open('rb') as f:
        head=f.read(8)
        if len(head)<8:return None
        magic,n=struct.unpack('>II',head);offset=0
        if magic in (0xcafebabe,0xcafebabf):
            require(n<=64,'MACHO_FAT_BOUND');stride=32 if magic==0xcafebabf else 20
            fat=f.read(n*stride);offset=None
            for i in range(n):
                cputype=struct.unpack_from('>I',fat,i*stride)[0]
                if cputype==0x100000c:offset=struct.unpack_from('>Q' if stride==32 else '>I',fat,i*stride+8)[0];break
            if offset is None:return None
        elif head[:4]!=b'\xcf\xfa\xed\xfe':return None
        f.seek(offset);header=f.read(32)
        if header.startswith(b'!<arch>\n'):return None # static archive slice, not a runtime image
        require(len(header)==32 and header[:4]==b'\xcf\xfa\xed\xfe','MACHO_HEADER')
        fields=struct.unpack('<8I',header);count,size=fields[4:6];require(count<=65536 and size<=8*1024*1024,'MACHO_COMMAND_BOUND')
        blob=f.read(size);require(len(blob)==size,'MACHO_TRUNCATED');at=0;deps=[];rpaths=[];versions=[]
        for _ in range(count):
            require(at+8<=size,'MACHO_COMMAND_BOUNDS');cmd,length=struct.unpack_from('<II',blob,at);require(length>=8 and at+length<=size,'MACHO_COMMAND_BOUNDS')
            part=blob[at:at+length]
            if cmd in (0xc,0x80000018,0x8000001f,0x80000023,0x8000001c):
                require(length>=12,'MACHO_STRING');start=struct.unpack_from('<I',part,8)[0];require(12<=start<length,'MACHO_STRING');s=part[start:].split(b'\0')[0].decode('utf8')
                (rpaths if cmd==0x8000001c else deps).append(s)
            if cmd==0x32 and length>=24:versions.append(list(struct.unpack_from('<4I',part,8)))
            at+=length
        require(at==size,'MACHO_COMMAND_TRAILING');return {'dependencies':deps,'rpaths':rpaths,'build_versions':versions,'cpu_type':fields[1]}

def collect():
    cache={};roots=list(ROOTS.values());trees={};start_stamps={}
    for name,path in ROOTS.items():
        print('Inventory '+name,flush=True)
        observations=[]
        try:start_stamps[name]={n:(stamp(st),link) for n,p,st,link in walk(path,observations)}
        except (OSError,ReviewError):start_stamps[name]=None
        trees[name]=inventory(path,name,roots,ALIASES,cache)
    # Exact selected SDK alias is recorded and resolved within the selected SDK only.
    pybind_names={r['path'] for r in trees['analysis-environment']['entries']}
    pybind_present=any(n.startswith('lib/python3.11/site-packages/pybind11/') for n in pybind_names)
    require(not pybind_present,'SELECTED_ENVIRONMENT_CHANGED_REVIEW_PYBIND_CLOSURE')
    sdk_alias={'path':str(CLT/'SDKs/MacOSX.sdk'),'target':os.readlink(CLT/'SDKs/MacOSX.sdk')}
    require(resolve_safe(CLT/'SDKs/MacOSX.sdk',[ROOTS['sdk']],[CLT/'SDKs/MacOSX.sdk'])==ROOTS['sdk'],'SDK_REDIRECTION')
    inputs={};queue=[]
    for tree in trees.values():
        for row in tree['entries']:
            if row['type']=='file' and row['sha256']:
                path=Path(tree['root'])/row['path'];inputs[str(path)]={'path':str(path),'sha256':row['sha256'],'status':'CURRENT_BYTES_VERIFIED'}
                queue.append(path)
    # System make is an explicitly named build input, not a directory search.
    make=Path('/usr/bin/make');inputs[str(make)]={'path':str(make),'sha256':content_hash(make,make.lstat(),cache)[0],'status':'CURRENT_BYTES_VERIFIED'};queue.append(make)
    dependencies=[];parsed=set();extra={};errors=[]
    allowed_formula={'openssl@3','readline','gettext','sqlite','xz','zstd','bzip2','zlib','libffi','mpdecimal','ncurses','expat','libunistring','berkeley-db@5','ca-certificates','python@3.11','cmake'}
    for path in queue:
        if str(path) in parsed:continue
        parsed.add(str(path))
        try:record=macho(path)
        except (OSError,ValueError,ReviewError) as exc:errors.append({'path':str(path),'error':str(exc)});continue
        if record is None:continue
        for dep in record['dependencies']:
            row={'loader':str(path),'declared':dep,'resolved':None,'sha256':None,'status':'MISSING_OR_UNAVAILABLE'}
            candidates=[]
            if dep.startswith('@loader_path/'):candidates=[path.parent/dep[len('@loader_path/'):]]
            elif dep.startswith('@rpath/'):
                candidates=[Path(r.replace('@loader_path',str(path.parent)))/dep[len('@rpath/'):] for r in record['rpaths'] if '@executable_path' not in r]
            elif dep.startswith('/'):candidates=[Path(dep)]
            for candidate in candidates:
                candidate=Path(os.path.normpath(str(candidate)))
                permitted=list(roots);aliases=list(ALIASES)
                # Expand only explicitly named dependencies; no global Homebrew scan.
                parts=candidate.parts
                if str(candidate).startswith('/opt/homebrew/opt/') and len(parts)>4 and parts[4] in allowed_formula:
                    alias=Path('/opt/homebrew/opt')/parts[4]
                    try:
                        raw=os.readlink(alias);target=Path(os.path.normpath(str(alias.parent/raw)))
                        require(str(target).startswith('/opt/homebrew/Cellar/'+parts[4]+'/'),'DEPENDENCY_ALIAS_ESCAPE');permitted.append(target);aliases.append(alias)
                    except (OSError,ReviewError):continue
                if str(candidate).startswith(('/usr/lib/','/System/Library/')):permitted.append(candidate)
                try:
                    resolved=resolve_safe(candidate,permitted,aliases)
                    require(resolved.is_file(),'DEPENDENCY_NOT_FILE');digest=content_hash(resolved,resolved.lstat(),cache)[0]
                    row.update(resolved=str(resolved),sha256=digest,status='CURRENT_BYTES_VERIFIED')
                    if str(resolved) not in inputs and str(resolved) not in extra:
                        extra[str(resolved)]={'path':str(resolved),'sha256':digest,'status':'CURRENT_BYTES_VERIFIED'};queue.append(resolved)
                        require(len(extra)<=2048,'DEPENDENCY_BOUND')
                    break
                except (OSError,ReviewError) as exc:row['reason']=str(exc)
            if row['status']!='CURRENT_BYTES_VERIFIED':row['reason']=row.get('reason','UNRESOLVED_RPATH_OR_EXECUTABLE_CONTEXT')+'; shared-cache images are not standalone byte identities; static closure excludes runtime dlopen/plugins'
            dependencies.append(row)
    versions=[command(c) for c in COMMANDS]
    compiler=resolve_safe(CLT/'usr/bin/clang++',roots,ALIASES)
    for name,path in ROOTS.items():
        observed_errors=[]
        try:
            final={n:(stamp(st),link) for n,p,st,link in walk(path,observed_errors)}
            if final!=start_stamps[name] or observed_errors:
                trees[name]['errors'].append({'code':'TREE_CHANGED_OR_INCOMPLETE_OVERALL_COLLECTION'});trees[name].update(status='CURRENT_BYTES_PARTIAL',closure_complete=False,traversal_complete=False)
        except (OSError,ReviewError) as exc:
            trees[name]['errors'].append({'code':'INCOMPLETE_OVERALL_COLLECTION','message':str(exc)});trees[name].update(status='CURRENT_BYTES_PARTIAL',closure_complete=False,traversal_complete=False)
    return {'status':'CURRENT_BYTES_PARTIAL','closure_complete':False,'sdk_alias':sdk_alias,'trees':trees,'compiler':inputs[str(compiler)],'linker':inputs[str(CLT/'usr/bin/ld')],'build_tools':versions,'additional_runtime_files':list(extra.values()),'runtime_dependencies':dependencies,'runtime_parse_errors':errors,'limits':{'max_entries_per_tree':200000,'max_additional_runtime_files':2048,'output_bytes':134217728},'missing':['current selected environment pybind11 headers and CMake package','historical pybind11 bytes unavailable per Phase10; not reopened','standalone bytes for shared-cache dependencies','dynamic dlopen/plugin closure not established'],'selection':{'DEVELOPER_DIR':str(CLT),'SDKROOT':str(CLT/'SDKs/MacOSX.sdk'),'scope':'process-local only; no builds or native loads'}}
