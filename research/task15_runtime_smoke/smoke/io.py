"""Exclusive durable engineering receipts; no clock or measurement fields."""
import json
import os
from pathlib import Path
from . import MARKS


def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def publish(path,value):
    path = Path(path)
    with path.open('xb') as stream:
        stream.write(encode({**value,**MARKS}));stream.flush();os.fsync(stream.fileno())
    fd = os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def event(path,value):
    with Path(path).open('ab') as stream:
        stream.write(encode({**value,**MARKS}));stream.flush();os.fsync(stream.fileno())
