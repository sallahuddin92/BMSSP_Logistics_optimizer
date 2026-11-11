"""Closed static scope. No native dispatch, clocks, approvals or execution overrides."""
import hashlib
import json
import math
from pathlib import Path

class PreflightError(ValueError):pass

def require(value,code):
    if not value:raise PreflightError(code)

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def pairs(items):
    out={}
    for k,v in items:
        require(k not in out,'JSON_DUPLICATE_KEY');out[k]=v
    return out

def read(path):
    path=Path(path);require(path.is_file() and not path.is_symlink(),'MISSING_OR_REDIRECTED_FILE:'+str(path))
    data=path.read_bytes()
    value=json.loads(data,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(PreflightError('JSON_NONFINITE')))
    canonical(value)
    return value

def boundary(value):
    if isinstance(value,dict):
        for k,v in value.items():
            require(k not in {'T0','T1','T2','T3','T4','T5','query_seconds','preprocessing_seconds','inclusive_seconds','exclusive_seconds'},'FAKE_OR_UNAUTHORIZED_CALIBRATION_DATA')
            require(k not in {'calibration_authorized','collection_authorized','execution_authorized','promotion_authorized'} or v is False,'FORGED_APPROVAL')
            require(k!='approval_signatures' or v==[],'FORGED_APPROVAL')
            boundary(v)
    elif isinstance(value,list):
        for item in value:boundary(item)

ROAD_MARKS={'scope':'ENGINEERING_ROAD_CORRECTNESS_ONLY','collection':'NOT_TASK15_COLLECTION','measurement':'MEASUREMENT_ELIGIBLE_FALSE','measurement_eligible':False}
def road_marks(value):
    require(all(value.get(k)==v and type(value.get(k)) is type(v) for k,v in ROAD_MARKS.items()),'MEASUREMENT_EXCLUSION')
    boundary(value)
