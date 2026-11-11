from pathlib import Path
from .core import *
from .collect import PROTOCOL,BASE,protocol
KINDS=['current-toolchain-lock','current-sdk-inventory','python-pybind-closure','original-current-evidence-matrix','baseline-build-comparison','candidate-build-comparison','g1-g10-impact-matrix','g8-equivalence-feasibility','negative-tests','source-integrity']
DOCS=['controlled-equivalence-strategy','proposed-amendment-impact','independent-review-packet','reviewer-decision-template']

def tree_check(t):
    if t['status']=='MISSING_OR_UNAVAILABLE':require(not t['closure_complete'],'INCOMPLETE_CLOSURE');return
    rows=t['entries'];require(len({r['path'] for r in rows})==len(rows),'DUPLICATE_TREE_PATH')
    require(all(not Path(r['path']).is_absolute() and '..' not in Path(r['path']).parts for r in rows),'TREE_PATH_ESCAPE')
    identity=[{k:r[k] for k in ['path','type','size','mode','symlink_target','sha256']} for r in rows]
    require(sha(canonical(identity))==t['tree_sha256'],'CORRUPTED_TREE_IDENTITY')
    require(t['entry_count']==len(rows),'TREE_COUNT')
    complete=t['traversal_complete'] and not t['errors'] and all(r['sha256'] for r in rows if r['type']=='file')
    require(t['closure_complete']==bool(complete),'INCOMPLETE_CLOSURE')
    require(t['status']==('CURRENT_BYTES_VERIFIED' if complete else 'CURRENT_BYTES_PARTIAL'),'PARTIAL_AS_VERIFIED')

def semantics(items):
    lock=items['current-toolchain-lock'];require(lock['status']=='CURRENT_BYTES_PARTIAL' and lock['closure_complete'] is False,'INCOMPLETE_CLOSURE')
    require(lock['compiler']['sha256']=='1220c0afafa12a6ae599d097ee7cf8b87c6b4d8e3fbb9783cee6b319a80683ba','WRONG_COMPILER_IDENTITY')
    require(lock['missing'],'INCOMPLETE_CLOSURE')
    for tree in lock['trees'].values():tree_check(tree)
    require(items['current-sdk-inventory']==lock['trees']['sdk'],'SDK_CROSS_REFERENCE')
    require(items['python-pybind-closure']['pybind11_status']=='MISSING_OR_UNAVAILABLE','MISSING_PYBIND_AS_VERIFIED')
    matrix=items['original-current-evidence-matrix']
    require(matrix['historical_toolchain_byte_continuity'] is False,'HISTORICAL_CURRENT_CONFUSION')
    for row in matrix['records']:
        if row['historical_identity_status']in {'VERSION_ONLY','HISTORICAL_VERSION_ONLY'}:require(row['historical_sha256'] is None and not row['historical_byte_continuity_proven'],'HISTORICAL_CURRENT_CONFUSION')
    for variant in ['baseline','candidate']:
        build=items[variant+'-build-comparison'];require(build['byte_equivalence'] is False,'UNSUPPORTED_EQUIVALENCE')
        require(build['current_compiler']==lock['compiler'],'BUILD_COMPILER_CROSS_REFERENCE')
        cmd=build['original']['binding_compile_record']['command']
        require('-O3' in cmd and '-O0' not in cmd and '-ffast-math' not in cmd and '-fno-exceptions' not in cmd and '-arch arm64' in cmd,'CONTRADICTORY_BUILD_ARGUMENTS')
    g8=items['g8-equivalence-feasibility'];require(g8.get('actual_g8_pass',False) is False,'FORGED_G8_PASS')
    require(g8['status']=='BLOCKED' and g8['actual_comparison_performed'] is False,'FORGED_G8_PASS')
    require(g8['independent_evidence']==[],'MISSING_INDEPENDENT_EVIDENCE')
    require(g8['marker_window_subtraction_supported'] is False and g8['original_source_inline_mapping_complete'] is False,'UNSUPPORTED_EQUIVALENCE')
    require(items['g1-g10-impact-matrix']['gates'][7]['id']=='G8_codegen','GATE_ORDER')
    for item in items.values():no_approval(item)

def validate(bundle,repo):
    bundle=Path(bundle);receipt=read(bundle/'completion-receipt.json')
    require(set(receipt)=={'schema','authorization','protocol_sha256','baseline_commit','files','source_lock','package_status','scientific_recommendation'},'RECEIPT_FIELDS')
    require(receipt['schema']=='option-b-completion-1' and receipt['authorization']==AUTH,'FORGED_REVIEWER_APPROVAL');no_approval(receipt)
    require(receipt['protocol_sha256']==PROTOCOL and receipt['baseline_commit']==BASE,'STALE_EVIDENCE_BUNDLE');protocol(repo)
    expected={n+'.json' for n in KINDS}|{n+'.md' for n in DOCS}
    require(set(receipt['files'])==expected,'OUTPUT_SET')
    require({p.name for p in bundle.iterdir()}==expected|{'completion-receipt.json'},'OUTPUT_SET')
    items={}
    for name,digest in receipt['files'].items():
        path=bundle/name;require(not path.is_symlink() and path.stat().st_size<=134217728,'OUTPUT_BOUND_OR_LINK')
        require(file_sha(path)==digest,'CORRUPTED_OUTPUT_IDENTITY')
        if name.endswith('.json'):
            obj=read(path);require(set(obj)=={'schema','kind','authorization','data'},'CLOSED_FIELDS');require(obj['schema']=='option-b-1' and obj['kind']==name[:-5] and obj['authorization']==AUTH,'SCHEMA_OR_APPROVAL');no_approval(obj);items[name[:-5]]=obj['data']
    package=repo/'research/task15_option_b_review'
    if package.exists():
        names={str(p.relative_to(repo)) for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        require(names==set(receipt['source_lock']),'STALE_EVIDENCE_BUNDLE')
    for name,digest in receipt['source_lock'].items():require(file_sha(repo/name)==digest,'STALE_EVIDENCE_BUNDLE')
    for name,digest in items['source-integrity']['protected_files'].items():require(file_sha(repo/name)==digest,'PROTECTED_SOURCE_CHANGED')
    semantics(items)
    require(receipt['package_status']=='PASS' and receipt['scientific_recommendation']=='BLOCKED','UNSUPPORTED_EQUIVALENCE')
    return {'validated':True,'receipt_sha256':file_sha(bundle/'completion-receipt.json'),'files':len(expected),'scientific_recommendation':'BLOCKED','authorization':AUTH}
