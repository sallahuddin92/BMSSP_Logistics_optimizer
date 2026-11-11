"""Small bounded provenance collector primitives; never promotes current hashes."""
import hashlib
import json
from pathlib import Path

class RecoveryError(ValueError):pass

def require(value,code):
    if not value:raise RecoveryError(code)
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def pairs(items):
    result={}
    for k,v in items:require(k not in result,'DUPLICATE_JSON_KEY');result[k]=v
    return result

def read(path):
    value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs);canonical(value);return value

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while data:=f.read(1024*1024):h.update(data)
    return h.hexdigest()
STATUSES={'HISTORICALLY_VERIFIED','CURRENT_IDENTITY_VERIFIED','VERSION_ONLY','UNVERIFIED','UNAVAILABLE'}
KEYS={'component','original_build_role','original_absolute_path','historical_version','historical_sha256','current_sha256','current_resolved_path','historical_identity_status','current_identity_status','identity_scope','identity_sources','source_artifact_identities','historical_timestamp_evidence','chain_of_evidence','trust_limitations','historical_byte_continuity_proven','contradictions'}


def component(name,role,path,*,version=None,historical_sha=None,current=None,sources=(),timestamps=(),scope='COMPLETE_COMPONENT_BYTES',anchors=(),available=True):
    # Only an independently anchored original payload or pre-existing explicit tool
    # hash record may populate historical_sha. A new collector's own hash never may.
    if historical_sha is not None:
        historical_anchor(name,role,historical_sha)
        require(any(a.get('independently_anchored') is True and a.get('component')==name and a.get('component_sha256')==historical_sha and a.get('kind') in {'ARCHIVED_COMPONENT_BYTES','PREEXISTING_COMPONENT_HASH_RECORD'} for a in anchors),'NO_INDEPENDENT_HISTORICAL_HASH')
    continuity=historical_sha is not None and current is not None and current['sha256']==historical_sha and scope=='COMPLETE_COMPONENT_BYTES'
    status='HISTORICALLY_VERIFIED' if historical_sha else 'VERSION_ONLY' if version else 'UNVERIFIED' if available else 'UNAVAILABLE'
    value={'component':name,'original_build_role':role,'original_absolute_path':path,'historical_version':version,'historical_sha256':historical_sha,
           'current_sha256':current['sha256'] if current else None,'current_resolved_path':current['resolved_path'] if current else None,
           'historical_identity_status':status,'current_identity_status':'CURRENT_IDENTITY_VERIFIED' if current else 'UNAVAILABLE',
           'identity_scope':scope,'identity_sources':list(sources),'source_artifact_identities':list(anchors),'historical_timestamp_evidence':list(timestamps),
           'chain_of_evidence':['Frozen protocol -> existing Task14 evidence-index SHA -> archived source/build records; current observations retained separately.'],
           'trust_limitations':['Current version/path/mtime/receipt or RECORD checksums do not prove unchanged bytes during the original build.','Archive anchoring establishes supported historical artifacts, not cryptographically timestamped independent eyewitness approval.'],
           'historical_byte_continuity_proven':continuity,'contradictions':[]}
    validate_component(value);return value


def validate_component(value):
    require(set(value)==KEYS,'COMPONENT_SCHEMA')
    require(value['historical_identity_status'] in STATUSES and value['current_identity_status'] in STATUSES,'IDENTITY_STATUS')
    if value['historical_sha256'] is None:
        require(value['historical_identity_status']!='HISTORICALLY_VERIFIED' and value['historical_byte_continuity_proven'] is False,'CURRENT_HISTORICAL_CONFUSION')
    else:
        historical_anchor(value['component'],value['original_build_role'],value['historical_sha256'])
        anchors=value['source_artifact_identities']
        require(any(a.get('independently_anchored') is True and a.get('component')==value['component'] and a.get('component_sha256')==value['historical_sha256'] and a.get('kind') in {'ARCHIVED_COMPONENT_BYTES','PREEXISTING_COMPONENT_HASH_RECORD'} for a in anchors),'NO_INDEPENDENT_HISTORICAL_HASH')
        require(value['historical_identity_status']=='HISTORICALLY_VERIFIED','HISTORICAL_CLASSIFICATION')
    require(value['historical_byte_continuity_proven'] is False or value['historical_sha256']==value['current_sha256'] and value['identity_scope']=='COMPLETE_COMPONENT_BYTES','UNSUPPORTED_CONTINUITY')
    return value


def current_file(path):
    p=Path(path)
    if not p.is_file():return None
    st=p.stat()
    return {'path':str(p),'resolved_path':str(p.resolve()),'sha256':file_hash(p),'bytes':st.st_size,'mtime_ns_current_metadata_only':st.st_mtime_ns}


def compare_versions(records):
    versions={r['version'] for r in records if r.get('version')}
    return {'status':'UNVERIFIED' if len(versions)>1 else 'VERSION_ONLY' if versions else 'UNAVAILABLE',
            'contradiction':len(versions)>1,'observed_versions':sorted(versions),'meaning':'A conflicting historical version is an observed contradiction; absent byte anchors are not a compiler failure.'}


def require_no_approval(value):
    if isinstance(value,dict):
        for k,v in value.items():
            require(k not in {'approved','g8_approved','layout_risk_approved','calibration_authorized','collection_authorized'} or v is False,'FORGED_PROVENANCE_APPROVAL')
            require(k!='scientific_acceptance' or v=='pending','FORGED_PROVENANCE_APPROVAL')
            require_no_approval(v)
    elif isinstance(value,list):
        for v in value:require_no_approval(v)


def historical_anchor(name,role,claimed_sha):
    # A new manifest's own hash/boolean is never an historical anchor. Only these
    # exact pre-existing Task14 objects may receive historical-byte classification.
    from task15_cohort_a_runner.frozen import protocol
    from .sources import authenticated_index,ARCHIVE
    p=protocol().data();catalog={}
    for variant in ['baseline','candidate']:
        catalog['original-production-'+variant]=('ORIGINAL_PRODUCTION_EXTENSION','run/'+variant+'/python/bmssp_native.cpython-311-darwin.so')
        catalog['source-snapshot-'+variant]=('ORIGINAL_SOURCE_SNAPSHOT','run/baseline-source.tar' if variant=='baseline' else 'candidate-source.tar')
    require(name in catalog,'COMPONENT_NOT_HISTORICALLY_ANCHORED')
    expected_role,path=catalog[name];require(role==expected_role,'HISTORICAL_ROLE_CONFUSION')
    index,_=authenticated_index(p)
    require(path in index and claimed_sha==index[path]['sha256'] and file_hash(ARCHIVE/path)==claimed_sha,'ALTERED_HISTORICAL_HASH')
    return True
