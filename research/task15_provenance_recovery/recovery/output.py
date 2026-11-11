"""Small closed provenance manifest and durable exclusive publication."""
import os
from pathlib import Path
from .core import require,canonical,digest,read,validate_component,require_no_approval

DATA_KEYS={
 'historical-evidence-inventory':{'inventory'},'compiler-provenance':{'record'},'linker-provenance':{'record','current_version_query'},
 'sdk-header-provenance':{'record','current_selected_files'},'python-pybind-provenance':{'records','current_files'},
 'baseline-build-reconciliation':{'reconciliation'},'candidate-build-reconciliation':{'reconciliation'},
 'identity-continuity-matrix':{'records','common_toolchain','recovery_verdict'},'unresolved-historical-identities':{'missing','contradictions','stop_condition'},
 'negative-tests':{'tests_run','failures','errors','skipped','log','fixture_scope'}}
TOP={'schema','kind','scope','calibration_authorized','collection_authorized','scientific_acceptance','data'}


def envelope(kind,data):
    require(kind in DATA_KEYS and type(data) is dict and set(data)==DATA_KEYS[kind],'CLOSED_PROVENANCE_SCHEMA')
    value={'schema':'bounded-provenance-1','kind':kind,'scope':'READ_ONLY_HISTORICAL_PROVENANCE_ONLY','calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending','data':data}
    require_no_approval(value);return value


def publish(path,data):
    path=Path(path)
    with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def validate_bundle(root):
    root=Path(root);receipt=read(root/'completion-receipt.json')
    require(set(receipt)=={'schema','scope','recovery_verdict','implementation','files','source_lock','calibration_authorized','collection_authorized','scientific_acceptance'},'COMPLETION_SCHEMA')
    require(receipt['schema']=='bounded-recovery-completion-1' and receipt['implementation']=='VERIFIED','COMPLETION_SCHEMA')
    require_no_approval(receipt)
    expected={k+'.json' for k in DATA_KEYS}|{'scientific-decision-boundary.md','STARTED.json','recovery-events.jsonl'}
    require(set(receipt['files'])==expected and {f.name for f in root.iterdir()}==expected|{'completion-receipt.json'},'IMMUTABLE_INVENTORY')
    for name,h in receipt['files'].items():
        path=root/name;require(path.is_file() and not path.is_symlink() and digest(path.read_bytes())==h,'OUTPUT_HASH:'+name)
    for kind in DATA_KEYS:
        value=read(root/(kind+'.json'));require(set(value)==TOP and value['schema']=='bounded-provenance-1' and value['kind']==kind,'CLOSED_PROVENANCE_SCHEMA')
        require(set(value['data'])==DATA_KEYS[kind],'CLOSED_PROVENANCE_SCHEMA');require_no_approval(value)
    matrix=read(root/'identity-continuity-matrix.json')['data']
    require(matrix['recovery_verdict']==receipt['recovery_verdict'],'VERDICT_CONTRADICTION')
    for value in matrix['records']:validate_component(value)
    for kind in ['compiler-provenance','linker-provenance','sdk-header-provenance']:
        record=read(root/(kind+'.json'))['data']['record'];require(record in matrix['records'],'COMPONENT_CROSS_REFERENCE')
    return receipt
