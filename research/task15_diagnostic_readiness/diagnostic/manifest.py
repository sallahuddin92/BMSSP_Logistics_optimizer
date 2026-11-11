"""Closed future B-build contract; source edits are insert-only at frozen anchors."""
from pathlib import Path
import difflib
import json
from .core import require,sha,canonical
from .tools import run

KEYS={'schema','variant','source_commit','production_binary_sha256','source_files','compiler','sdk','build_arguments','linker','dependencies','permitted_insertions','forbidden_compute_modifications','source_diff','diagnostic_binary','function_coverage','g8_claim','missing_prerequisites','scientific_approval','layout_risk_approved','calibration_authorized','collection_authorized'}
FORBIDDEN=['comparators','recursion','BaseCase','FindPivots','frontier','graph','degree reduction','numeric validation','k/t','shortest-path semantics','instruction reordering']


def original(commit,path):
    result=run(['git','show',commit+':'+path]);require(result['returncode']==0,'SOURCE_PROVENANCE');return result['stdout']


def whitelist(p,variant):
    commit=p['binaries'][variant]['source_commit'];items=[]
    definitions=[('native/src/bmssp_2025.cpp','    const auto start = Clock::now();','T2','before'),
                 ('native/src/bmssp_2025.cpp','    diagnostics.query_seconds = seconds(start);','T3','before'),
                 ('native/python/bindings.cpp','                const auto source = integer_id<ExternalVertexId>(input);','T1','after'),
                 ('native/python/bindings.cpp','                auto d = diagnostics(result.diagnostics);','T4','before')]
    for path,anchor,tag,position in definitions:
        text=original(commit,path);lines=text.splitlines(keepends=True)
        matches=[i for i,line in enumerate(lines) if line.rstrip('\n')==anchor]
        require(matches,'MISSING_SOURCE_INSERTION_ANCHOR:'+tag)
        # Only BMSSP's first wrapper occurrence; reference Dijkstra remains forbidden.
        line=next((i for i in matches if tag!='T2' or any('original_source = ' in v for v in lines[max(0,i-3):i])),matches[0])
        items.append({'file':path,'source_sha256':sha(text.encode()),'line':line+1,'anchor_sha256':sha(lines[line].encode()),'position':position,'allowed_line':f'    BMSSP_T15_MARK({tag});\n','tag':tag,
                      'scope':'Source whitelist only; not approval of a machine insertion window.'})
    return items


def validate_source_edits(p,variant,changes):
    allowed=whitelist(p,variant)
    require(type(changes) is list,'SOURCE_DIFF_SCHEMA')
    require(len({c['file'] for c in changes})==len(changes),'DUPLICATE_SOURCE_DIFF')
    for change in changes:
        require(set(change)=={'file','original_sha256','modified_text','unified_diff'},'SOURCE_DIFF_SCHEMA')
        source=original(p['binaries'][variant]['source_commit'],change['file'])
        require(sha(source.encode())==change['original_sha256'],'SOURCE_SHA')
        before=source.splitlines(keepends=True);after=change['modified_text'].splitlines(keepends=True)
        expected=''.join(difflib.unified_diff(before,after,fromfile=change['file'],tofile=change['file']))
        require(expected==change['unified_diff'],'SOURCE_DIFF_MISMATCH')
        for op,a,b,c,d in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
            if op=='equal':continue
            require(op=='insert','FORBIDDEN_COMPUTE_EDIT')
            candidates=[x for x in allowed if x['file']==change['file'] and a==(x['line'] if x['position']=='after' else x['line']-1)]
            require(candidates and after[c:d]==[candidates[0]['allowed_line']],'UNAPPROVED_SOURCE_INSERTION')
    return True


def validate(value,p,expected_compiler,expected_sdk,expected_build_arguments,require_artifact=True):
    require(type(value) is dict and set(value)==KEYS and value['schema']=='cohort-b-build-1','BUILD_MANIFEST_SCHEMA')
    require(value['variant'] in {'baseline','candidate'},'VARIANT')
    original_binary=p['binaries'][value['variant']]
    require(value['source_commit']==original_binary['source_commit'] and value['production_binary_sha256']==original_binary['sha256'],'PRODUCTION_PROVENANCE')
    require(value['compiler']==expected_compiler,'WRONG_COMPILER');require(value['sdk']==expected_sdk,'WRONG_SDK')
    require(value['build_arguments'] and value['linker'] and value['dependencies'] and value['source_files'],'MISSING_BUILD_PROVENANCE')
    import shlex
    for record in value['build_arguments']:
        require(type(record) is dict and set(record)=={'directory','command','file','output'},'BUILD_ARGUMENT_SCHEMA')
        argv=shlex.split(record['command'])
        require(argv and argv[0]==expected_compiler['path'] and all(x in argv for x in ['-O3','-DNDEBUG','-std=c++20','-fPIC']) and '-arch' in argv and argv[argv.index('-arch')+1]=='arm64','WRONG_BUILD_FLAGS')
        require('-isysroot' in argv and argv[argv.index('-isysroot')+1]==expected_sdk['path'],'WRONG_BUILD_SDK')
        require(not any(arg.startswith(('-Ofast','-ffast-math','-fno-exceptions','-fno-rtti','-flto','-march=','-mcpu=')) for arg in argv),'UNAPPROVED_NUMERIC_ABI_FLAGS')
    require(value['build_arguments']==expected_build_arguments,'EXACT_BUILD_ARGUMENT_PROVENANCE')
    require(value['permitted_insertions']==whitelist(p,value['variant']) and value['forbidden_compute_modifications']==FORBIDDEN,'SOURCE_WHITELIST_CHANGED')
    require(value['scientific_approval']=='pending' and value['layout_risk_approved'] is False and value['calibration_authorized'] is False and value['collection_authorized'] is False,'FORGED_APPROVAL')
    require(value['g8_claim'] is None,'FORGED_G8_PASS')
    validate_source_edits(p,value['variant'],value['source_diff'])
    for name,wanted in value['source_files'].items():require(sha(original(value['source_commit'],name).encode())==wanted,'SOURCE_FILE_IDENTITY')
    if require_artifact:
        artifact=value['diagnostic_binary'];require(type(artifact) is dict and set(artifact)=={'path','sha256'} and Path(artifact['path']).is_file(),'MISSING_DIAGNOSTIC_ARTIFACT')
        require(sha(Path(artifact['path']).read_bytes())==artifact['sha256'],'DIAGNOSTIC_SHA')
        require(not value['missing_prerequisites'],'MISSING_BUILD_PREREQUISITES')
    return True


def draft(p,variant,toolchain,sources):
    return {'schema':'cohort-b-build-1','variant':variant,'source_commit':p['binaries'][variant]['source_commit'],'production_binary_sha256':p['binaries'][variant]['sha256'],
            'source_files':{k:v['sha256'] for k,v in sources.items()},'compiler':toolchain['compiler'],'sdk':toolchain['sdk'],
            'build_arguments':toolchain['build_provenance'][variant]['compile_records'],'linker':{'identity':toolchain['linker'],'argv':toolchain['build_provenance'][variant]['link_command']},
            'dependencies':{'original_declarations':['/usr/lib/libc++.1.dylib','/usr/lib/libSystem.B.dylib'],'diagnostic_loaded_identities':'PENDING'},
            'permitted_insertions':whitelist(p,variant),'forbidden_compute_modifications':FORBIDDEN,'source_diff':[],
            'diagnostic_binary':None,'function_coverage':{'status':'BLOCKED','approved_machine_windows':[]},'g8_claim':None,
            'missing_prerequisites':['Independent reconciliation/lock of compiler/linker/complete SDK bytes and dependency/header mapping.','Original complete source/inline/function/compute-window mapping.','Diagnostic support header/source identity and source diff review.','Future diagnostic binary and G1–G10/G8 evidence.'],
            'scientific_approval':'pending','layout_risk_approved':False,'calibration_authorized':False,'collection_authorized':False}


def schema():
    props={k:{} for k in KEYS}
    props.update(schema={'enum':['cohort-b-build-1']},variant={'enum':['baseline','candidate']},g8_claim={'type':'null'},scientific_approval={'enum':['pending']},
                 layout_risk_approved={'type':'boolean','enum':[False]},calibration_authorized={'type':'boolean','enum':[False]},collection_authorized={'type':'boolean','enum':[False]},
                 source_diff={'type':'array','items':{'type':'object','required':['file','original_sha256','modified_text','unified_diff'],'properties':{k:{'type':'string'} for k in ['file','original_sha256','modified_text','unified_diff']},'additionalProperties':False}})
    return {'title':'Future Cohort B build identity contract; exact semantic/source validation required','type':'object','properties':props,'required':sorted(KEYS),'additionalProperties':False}


_BUILD_TOKEN=object()
class VerifiedBuildContext:
    def __init__(self,token,data):
        require(token is _BUILD_TOKEN,'UNVERIFIED_BUILD_CONTEXT')
        self._json=canonical(data)
    @property
    def data(self):return json.loads(self._json)

def attest_build(value,p,expected_compiler,expected_sdk,expected_build_arguments,independently_expected_manifest_sha256):
    require(sha(canonical(value))==independently_expected_manifest_sha256,'UNVERIFIED_BUILD_MANIFEST_LOCK')
    validate(value,p,expected_compiler,expected_sdk,expected_build_arguments,require_artifact=True)
    return VerifiedBuildContext(_BUILD_TOKEN,{'binary_sha256':value['diagnostic_binary']['sha256'],'variant':value['variant'],
        'compiler_lock_sha256':sha(canonical(expected_compiler)),'sdk_lock_sha256':sha(canonical(expected_sdk)),
        'build_arguments_sha256':sha(canonical(expected_build_arguments))})
