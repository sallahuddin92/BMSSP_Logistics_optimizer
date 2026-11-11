"""Static diagnostic-readiness support. Never compiles, loads or executes BMSSP."""
import hashlib
import json
from pathlib import Path

class DiagnosticError(ValueError):pass

def require(value,code):
    if not value:raise DiagnosticError(code)
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(path):return json.loads(Path(path).read_bytes())
MARKS={'scope':'STATIC_DIAGNOSTIC_READINESS_ONLY','calibration_authorized':False,'collection_authorized':False,'scientific_acceptance':'pending','measurement_eligible':False}
