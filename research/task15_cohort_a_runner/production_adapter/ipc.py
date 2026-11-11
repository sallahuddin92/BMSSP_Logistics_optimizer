"""Separate bounded, strict production framing; never reinterpret synthetic RPCs."""
import json
import struct
from . import require
from .worker import MAX_FRAME, validate_response


def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, 'JSON_DUPLICATE_KEY')
        out[key] = value
    return out


def decode(data):
    require(type(data) is bytes and len(data) >= 4, 'IPC_HEADER')
    size = struct.unpack('!I', data[:4])[0]
    require(0 < size <= MAX_FRAME and len(data) == size+4, 'IPC_FRAME_LENGTH')
    def forbidden(value):
        require(False, 'JSON_NONFINITE')
    value = json.loads(data[4:], object_pairs_hook=pairs, parse_constant=forbidden)
    from .fingerprints import canonical
    canonical(value)  # Also reject overflowing exponents.
    return value


def validate_reply(response, request, workload, runner_identity):
    validate_response(response)
    from .fingerprints import canonical, validate_evidence
    require(canonical(response['request']) == canonical(request) and canonical(response['query']) == canonical(request['query']), 'REPLY_QUERY')
    q = request['query']
    require(response['unit_id'] == q['trial_id'] and response['variant'] == q['variant'], 'REPLY_CLUSTER_VARIANT')
    require(response['runner_sha256'] == runner_identity, 'REPLY_RUNNER')
    binary = workload.p['binaries'][q['variant']]
    require(all(response['binary'][k] == v for k,v in binary.items()), 'REPLY_BINARY')
    require(response['query']['protocol_sha256'] == response['protocol_sha256'], 'REPLY_PROTOCOL')
    require(response['warmup_excluded'] == (q['phase'] == 'warmup'), 'REPLY_WARMUP')
    require(response['synthetic'] is True or response['binary'].get('dependency_resolution') == 'LOADED_IMAGES_VERIFIED', 'REPLY_LOAD_STATUS')
    if response['status'] == 'OK':
        validate_evidence(response['evidence'], q, workload.p['inputs'][q['region']])
    return response


def serve(worker, read_frame, write_frame):
    """One read, one complete response; no pipelining/retry or extra result RPCs."""
    try:
        while worker.cluster.cursor < len(worker.cluster.queries) and not worker.cluster.invalid:
            worker.query(decode(read_frame()), write_frame)
    except BaseException as exc:
        worker.cluster.invalidate({'type': type(exc).__name__, 'message': str(exc)})
        raise


class Coordinator:
    """Future serial parent contract; peer callbacks may be isolated process channels.

    A timeout/EOF/worker error invalidates both peers' complete three-region cluster.
    The caller retains raw input/output evidence and owns child termination. No retry.
    """
    def __init__(self, workload, unit_id, runner_identity, peers, invalidate_peers):
        from .worker import Cluster
        self.cluster = Cluster.frozen(workload, unit_id)
        self.workload, self.runner_identity = workload, runner_identity
        require(set(peers) == {'baseline','candidate'}, 'COORDINATOR_PEERS')
        self.peers, self.invalidate_peers = peers, invalidate_peers
        self.busy = False
        self.signatures = {}
        self.receipts = []

    def step(self):
        require(not self.busy and not self.cluster.invalid, 'CLUSTER_INVALID_OR_BUSY')
        require(self.cluster.cursor < len(self.cluster.queries), 'CLUSTER_COMPLETE')
        self.busy = True
        try:
            q = self.cluster.queries[self.cluster.cursor]
            request = {'op':'QUERY','sequence':self.cluster.cursor+1,'query':q}
            response = self.peers[q['variant']](request)
            self.receipts.append({'request':request,'response':response})
            validate_reply(response, request, self.workload, self.runner_identity)
            require(response['status'] == 'OK' and not response['cluster_invalid'], 'WORKER_QUERY_FAILED')
            proof = response['evidence']
            key = (q['region'], q['phase'], q['original_position'], q['source_occurrence'])
            signature = {k:proof[k] for k in ('distance_sha256','paths_sha256','work_sha256','materialization_count')}
            pair = self.signatures.setdefault(key, {})
            require(q['variant'] not in pair, 'DUPLICATE_QUERY_RESULT')
            require(all(previous == signature for previous in pair.values()), 'CROSS_VARIANT_CORRECTNESS_MISMATCH')
            pair[q['variant']] = signature
            self.cluster.cursor += 1
            if self.cluster.cursor == len(self.cluster.queries):
                require(all(set(pair) == {'baseline','candidate'} for pair in self.signatures.values()), 'INCOMPLETE_CORRECTNESS_PAIRS')
            return response
        except BaseException as exc:
            error = {'type':type(exc).__name__,'message':str(exc)}
            self.cluster.invalidate(error)
            self.invalidate_peers(error)
            raise
        finally:
            self.busy = False
