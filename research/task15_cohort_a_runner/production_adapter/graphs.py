"""Strict reader for archived export_native_probe_graphs.py text, without bindings."""
from dataclasses import dataclass
import hashlib
import math
import json
import re
from pathlib import Path
from . import require

INTEGER = re.compile(r'-?(?:0|[1-9][0-9]*)\Z')
DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


def integer(text, unsigned=False):
    require(bool(INTEGER.fullmatch(text)), 'INTEGER_FORMAT')
    value = int(text)
    require(0 <= value < 2**64 if unsigned else -2**63 <= value < 2**63, 'INTEGER_RANGE')
    return value


@dataclass(frozen=True)
class GraphInput:
    vertices: tuple
    edges: tuple
    sha256: str
    synthetic: bool


def parse_graph(data, expected_sha256, sources=(), *, synthetic=False):
    actual = hashlib.sha256(data).hexdigest()
    require(actual == expected_sha256, 'GRAPH_HASH')
    lines = data.decode('ascii').splitlines()
    require(bool(lines), 'GRAPH_HEADER')
    header = lines[0].split()
    require(len(header) == 2, 'GRAPH_HEADER')
    n, m = (integer(x, True) for x in header)
    require(len(lines) == n + m + 1, 'GRAPH_RECORD_COUNT')
    vertices = tuple(integer(x) for x in lines[1:n+1])
    require(len(set(vertices)) == n and tuple(sorted(vertices)) == vertices, 'VERTEX_ORDER_OR_DUPLICATE')
    known = set(vertices)
    require(all(type(x) is int and x in known for x in sources), 'SOURCE_MEMBERSHIP')
    edges = []
    ids = set()
    for line in lines[n+1:]:
        record = line.split()
        require(len(record) == 4, 'EDGE_FORMAT')
        eid = integer(record[0], True)
        u, v = integer(record[1]), integer(record[2])
        require(eid not in ids, 'DUPLICATE_EDGE')
        require(u in known and v in known, 'UNKNOWN_ENDPOINT')
        require(bool(DECIMAL.fullmatch(record[3])), 'WEIGHT_FORMAT')
        weight = float(record[3])
        require(math.isfinite(weight) and weight >= 0, 'WEIGHT_RANGE')
        ids.add(eid)
        edges.append((eid, u, v, weight))
    return GraphInput(vertices, tuple(edges), actual, synthetic)


def frozen_graph(inp):
    # Read and hash exactly the same bytes; no graph construction occurs here.
    for path_key, sha_key in [('graph_path','graph_sha256'), ('fixture_manifest_path','fixture_manifest_sha256'), ('query_file_path','query_file_sha256')]:
        data = Path(inp[path_key]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == inp[sha_key], 'FROZEN_INPUT_HASH')
        if path_key == 'query_file_path':
            query = json.loads(data)
            require(query['oracle_sources'][:4] == list(map(int, inp['path_targets'])), 'HISTORICAL_TARGET_SELECTION')
            require(query['snapshot_id'] == inp['snapshot_id'], 'HISTORICAL_SNAPSHOT')
    return parse_graph(Path(inp['native_export_path']).read_bytes(), inp['native_export_sha256'],
                       tuple(map(int, inp['source_positions'])))
