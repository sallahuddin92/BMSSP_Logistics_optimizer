import hashlib
import json
from pathlib import Path

class ReviewError(ValueError):pass

def require(value,code):
    if not value:raise ReviewError(code)
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def pairs(items):
    out={}
    for k,v in items:require(k not in out,'DUPLICATE_JSON_KEY');out[k]=v
    return out

def read(path):
    value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs);canonical(value);return value

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):h.update(chunk)
    return h.hexdigest()
AUTH={'independent_reviewer_acceptance':'pending','protocol_amendment_approved':False,'diagnostic_construction_authorized':False,'calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending'}

def no_approval(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in AUTH:require(type(v) is type(AUTH[k]) and v==AUTH[k],'FORGED_REVIEWER_APPROVAL')
            require(k not in {'g8_pass','g8_approved','actual_g8_pass','reviewer_approved','authorized','execution_authorized','promotion_authorized'} or v is False,'FORGED_G8_PASS')
            no_approval(v)
    elif isinstance(value,list):
        for v in value:no_approval(v)
