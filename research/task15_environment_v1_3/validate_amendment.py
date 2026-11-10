"""Independent v1.3 document verifier. Stdlib only; no generator/harness imports or execution."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
PARENT = 'c41e45bccb68abdf03bab40ea793837a7f508fde17634c1aa8b358a3d82fceb0'

def check(condition, code):
    if not condition:
        raise ValueError(code)
ACTIVE = 'b639d9960353f00c5a3d5efc58255206d5dd7d7f701311ebe7f715f5ad277ddd'
LEDGER_ID = '7363631745b5666dac6bf4b598ced4cc4373e9de491a10bbe3cd780e8e1bd800'
DOCUMENT_FILES = {'task15_tail_attribution_amendment_v1.3.0.json': 'cbfa8e49e8e8fe48df1711a24ca110cedaff382924d1ea97197774f7a8116f52', 'task15_tail_attribution_protocol_v1.3.0.json': 'd561f8c313400d72ffaa0290cb5df055a53ef270e79aa452dd91cfffba90bb0e', 'task15_tail_attribution_preregistration_v1.3.0.md': '45aa925620346fab8dc012623b1f9de2d37949b9afc7c5ecccee7585b887a659'}
ALLOWED = ['/analysis_environment_amendment', '/future_execution/active_protocol_file', '/future_execution/approval_gate', '/identity/sha256', '/statistics/bootstrap_execution_spec/numpy_version', '/version']

def encoded(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest(x):
    return hashlib.sha256(encoded(x)).hexdigest()

def file_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def identity(p):
    q = deepcopy(p)
    q['identity'].pop('sha256')
    return digest(q)

def differences(old, new, path=''):
    if type(old) is dict and type(new) is dict:
        result = []
        for key in sorted(old.keys() | new.keys()):
            ptr = path + '/' + key.replace('~', '~0').replace('/', '~1')
            result.extend([ptr] if key not in old or key not in new else differences(old[key], new[key], ptr))
        return result
    return [] if encoded(old) == encoded(new) else [path]

def verify(repo):
    docs = repo / 'docs'
    parent = json.loads((docs / 'task15_tail_attribution_protocol_v1.2.0.json').read_text())
    pfile = docs / 'task15_tail_attribution_protocol_v1.3.0.json'
    p = json.loads(pfile.read_text())
    md = docs / 'task15_tail_attribution_preregistration_v1.3.0.md'
    ledgerfile = docs / 'task15_tail_attribution_amendment_v1.3.0.json'
    ledger = json.loads(ledgerfile.read_text())
    for (name, expected) in DOCUMENT_FILES.items():
        check(file_hash(docs / name) == expected, 'FROZEN_DOCUMENT_BYTES')
    check(identity(parent) == parent['identity']['sha256'] == PARENT, 'PARENT_HASH')
    check(identity(p) == p['identity']['sha256'] == ACTIVE, 'ACTIVE_HASH')
    check(differences(parent, p) == ALLOWED, 'SCIENTIFIC_SCOPE')
    projection = deepcopy(p)
    for key in ['version', 'identity']:
        projection[key] = deepcopy(parent[key])
    projection.pop('analysis_environment_amendment')
    projection['statistics']['bootstrap_execution_spec']['numpy_version'] = parent['statistics']['bootstrap_execution_spec']['numpy_version']
    for key in ['active_protocol_file', 'approval_gate']:
        projection['future_execution'][key] = parent['future_execution'][key]
    check(projection == parent, 'SCIENTIFIC_FIELDS_CHANGED')
    unsigned = deepcopy(ledger)
    stored = unsigned.pop('identity_sha256')
    check(digest(unsigned) == stored == LEDGER_ID, 'LEDGER_HASH')
    check(ledger['changed_json_paths'] == ALLOWED and ledger['parent_canonical_sha256'] == PARENT and (ledger['new_canonical_sha256'] == ACTIVE), 'LEDGER_CHAIN')
    check(ledger['new_JSON_file_byte_sha256'] == file_hash(pfile) and ledger['new_MD_file_byte_sha256'] == file_hash(md), 'DOCUMENT_BYTES')
    a = p['analysis_environment_amendment']
    check(digest(a) == ledger['analysis_environment_amendment_sha256'], 'ENVIRONMENT_LOCK')
    check(a['python']['version'] == '3.11.15' and a['python']['architecture'] == 'arm64' and (a['numpy']['version'] == '1.24.4'), 'EXACT_RUNTIME')
    check(a['parent_canonical_sha256'] == PARENT and a['parent_version'] == '1.2.0', 'ENVIRONMENT_PARENT')
    for obj in [a['scientific_acceptance'], ledger]:
        check(obj['approval_signatures'] == [], 'APPROVAL_SIGNATURES')
        check(all((not value for (key, value) in obj.items() if key.endswith('_authorized'))), 'AUTHORIZATION')
    check(p['execution_authorized'] is False and p['promotion_authorized'] is False, 'AUTHORIZATION')
    check(a['provenance_limitations'] == {'historical_full_byte_identity_established': False, 'independent_publisher_authenticity_established': False, 'complete_numerical_equivalence_established': False, 'interpretation': a['provenance_limitations']['interpretation']}, 'PROVENANCE_LIMITATIONS')
    check(a['data_declaration']['worldwide_absence_of_task15_observations_established'] is False, 'DATA_SCOPE')
    check(p['design']['resolved_diagnostic_order']['query_identity_policy']['namespace_protocol_sha256'] == '6664cad958a863226925efdeac4ffc5fe220673e8cd7072c05cd6298facfb37f', 'QUERY_NAMESPACE')
    original = json.loads((docs / 'task15_tail_attribution_protocol.json').read_text())
    v11 = json.loads((docs / 'task15_tail_attribution_protocol_v1.1.0.json').read_text())
    check(identity(original) == original['identity']['sha256'], 'V10_HASH')
    check(identity(v11) == v11['identity']['sha256'], 'V11_HASH')
    check(v11['amendment']['parent_canonical_sha256'] == original['identity']['sha256'], 'V10_V11_CHAIN')
    check(parent['ordering_amendment']['parent_canonical_sha256'] == v11['identity']['sha256'], 'V11_V12_CHAIN')
    return {'status': 'PASS_STATIC_ENVIRONMENT_AMENDMENT', 'protocol_sha256': ACTIVE, 'parent_sha256': PARENT, 'ledger_sha256': stored, 'changed_paths': ALLOWED, 'scientific_projection_identical': True, 'query_namespace_preserved': True, 'approval_signatures': [], 'execution_authorized': False, 'source_evidence': 'authenticated by generator and harness identity checks; verifier does not execute environment', 'no_native_or_numerical_execution': True}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = verify(args.repo)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(result, sort_keys=True))
if __name__ == '__main__':
    main()
