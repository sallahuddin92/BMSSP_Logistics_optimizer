import hashlib
import json
import os
from pathlib import Path
from . import MARKS


def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(data):return hashlib.sha256(data).hexdigest()

def publish(path,value):
    path=Path(path)
    with path.open('xb') as f:
        f.write(encode({**value,**MARKS}));f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def event(path,value):
    with Path(path).open('ab') as f:
        f.write(encode({**value,**MARKS}));f.flush();os.fsync(f.fileno())
