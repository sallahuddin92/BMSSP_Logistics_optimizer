"""Serial one-response QUERY contract; not wired to the synthetic controller CLI."""
from dataclasses import dataclass, field
import struct
import weakref
import traceback
from . import VERSION, production_gate, require
from .fingerprints import evidence, canonical
from task15_cohort_a_runner.frozen import PROTOCOL, Workload

MAX_FRAME = 4 * 1024 * 1024


@dataclass
class Cluster:
    unit_id: str
    queries: list
    cursor: int = 0
    invalid: bool = False
    errors: list = field(default_factory=list)
    sequences: list = field(default_factory=list)

    def invalidate(self, error):
        self.invalid = True
        self.errors.append(error)

    @classmethod
    def frozen(cls, workload, unit_id, variant=None):
        require(unit_id in workload.queries, 'CLUSTER_NOT_COHORT_A')
        qs = workload.queries[unit_id]
        if variant is None:
            return cls(unit_id, qs)
        require(variant in {'baseline', 'candidate'}, 'VARIANT')
        chosen = [(i+1,q) for i,q in enumerate(qs) if q['variant'] == variant]
        return cls(unit_id, [q for _,q in chosen], sequences=[i for i,_ in chosen])


def prepare(binding, graphs):
    require(binding.synthetic is True and all(g.synthetic for g in graphs.values()), 'FAKE_INPUT_REQUIRED')
    prepared = {}
    for region, graph in graphs.items():
        ng = binding.NativeGraph(graph.vertices, graph.edges)
        require(tuple(ng.vertex_ids) == graph.vertices, 'NATIVE_VERTEX_ORDER')
        engine = binding.BMSSP2025Engine(ng)
        require(engine.metadata['preprocessing_count'] == 1, 'PREPROCESSING_COUNT')
        prepared[region] = (ng, engine)
    return prepared


class Worker:
    def __init__(self, workload, cluster, variant, binding, clock, graphs, runner_identity):
        # Dependency injection is restricted to fake-only graph fixtures.
        require(binding.synthetic is True and clock.synthetic is True, 'FAKE_BINDING_AND_CLOCK_REQUIRED')
        require(variant in workload.p['binaries'] and binding.variant == variant, 'WRONG_VARIANT')
        require(len(runner_identity) == 64, 'RUNNER_IDENTITY')
        self.p = workload.p
        self.cluster, self.variant, self.binding, self.clock = cluster, variant, binding, clock
        self.graphs, self.runner_identity = graphs, runner_identity
        self.prepared = prepare(binding, graphs)
        self.last_result = None
        self.busy = False
        self.synthetic = True
        self.binary_identity = {**self.p['binaries'][variant], 'variant': variant, 'load_status': 'FAKE_NOT_LOADED'}

    def query(self, request, write):
        require(not self.busy and not self.cluster.invalid, 'CLUSTER_INVALID_OR_BUSY')
        self.busy = True
        result = None
        proof = None
        t0 = t5 = None
        error = None
        accepted = None
        try:
            require(type(request) is dict and set(request) == {'op', 'sequence', 'query'}, 'REQUEST_SCHEMA')
            require(self.cluster.cursor < len(self.cluster.queries), 'QUERY_OVERFLOW')
            sequence = self.cluster.sequences[self.cluster.cursor] if self.cluster.sequences else self.cluster.cursor+1
            require(request['op'] == 'QUERY' and type(request['sequence']) is int and request['sequence'] == sequence, 'REQUEST_SEQUENCE')
            accepted = self.cluster.queries[self.cluster.cursor]
            require(canonical(request['query']) == canonical(accepted) and accepted['variant'] == self.variant, 'FROZEN_QUERY_IDENTITY')
            require(self.last_result is None or self.last_result() is None, 'PRIOR_RESULT_RETAINED')
            region = accepted['region']
            inp = self.p['inputs'][region]
            source = int(inp['source_positions'][accepted['original_position']])
            require(str(source) == accepted['source_id'], 'SOURCE_POSITION')
            ng, engine = self.prepared[region]
            require(source in self.graphs[region].vertices, 'SOURCE_MEMBERSHIP')
            solve = engine.solve
            t0 = self.clock.read()
            result = solve(source, profile=False)
            t5 = self.clock.read()
            require(type(t0) is int and type(t5) is int and 0 <= t0 <= t5, 'CLOCK_ORDER')
            try:
                self.last_result = weakref.ref(result)
            except TypeError:
                # Some pybind builds do not expose weakrefs. Sole ownership still ends below.
                require(not self.synthetic, 'FAKE_RESULT_WEAKREF_REQUIRED')
                self.last_result = None
            proof = evidence(result, ng, self.graphs[region], source, tuple(map(int, inp['path_targets'])), accepted['protocol'])
            self.cluster.cursor += 1
        except BaseException as exc:
            # No retry. Remove traceback frames which could retain native result/copies.
            error = {'type': type(exc).__name__, 'message': str(exc),
                     'traceback': ''.join(traceback.format_exception(exc))}
            exc.__traceback__ = None
            exc.__context__ = None
            exc.__cause__ = None
            self.cluster.invalidate(error)
            proof = None
        finally:
            result = None
            self.busy = False
        if self.last_result is not None and self.last_result() is not None:
            if error is None:
                error = {'type': 'AdapterError', 'message': 'RESULT_RELEASE_FAILED', 'traceback': ''}
                self.cluster.invalidate(error)
            proof = None
        response = {'schema': 'production-response-1', 'protocol_sha256': PROTOCOL,
                    'runner_version': VERSION, 'runner_sha256': self.runner_identity,
                    'unit_id': self.cluster.unit_id, 'variant': self.variant,
                    'binary': self.binary_identity, 'query': accepted, 'request': request,
                    'status': 'ERROR' if error else 'OK', 'cluster_invalid': self.cluster.invalid,
                    'invalidated_scope': 'ALL_THREE_REGIONS_BOTH_VARIANTS' if error else None,
                    'timing': {'T0': t0, 'T1': None, 'T2': None, 'T3': None, 'T4': None, 'T5': t5,
                               'outer_elapsed': t5-t0 if t5 is not None and t0 is not None else None,
                               'clock': dict(self.clock.metadata)},
                    'evidence': proof, 'error': error, 'synthetic': self.synthetic,
                    'measurement_eligible': False, 'measurement_unavailable_reason': 'EXECUTION_AND_CALIBRATION_PENDING',
                    'confirmatory_target_eligible': False, 'warmup_excluded': accepted is not None and accepted['phase'] == 'warmup'}
        validate_response(response)
        data = canonical(response)
        require(len(data) <= MAX_FRAME, 'RESPONSE_TOO_LARGE')
        try:
            write(struct.pack('!I', len(data))+data)  # One complete response after destruction.
        except BaseException as exc:
            self.cluster.invalidate({'type': type(exc).__name__, 'message': str(exc)})
            raise
        return response


def validate_response(r):
    require(set(r) == set('schema protocol_sha256 runner_version runner_sha256 unit_id variant binary query request status cluster_invalid invalidated_scope timing evidence error synthetic measurement_eligible measurement_unavailable_reason confirmatory_target_eligible warmup_excluded'.split()), 'RESPONSE_SCHEMA')
    require(r['schema'] == 'production-response-1' and r['protocol_sha256'] == PROTOCOL, 'RESPONSE_IDENTITY')
    require(r['measurement_eligible'] is False and r['confirmatory_target_eligible'] is False, 'MEASUREMENT_FORBIDDEN')
    require(r['status'] in {'OK', 'ERROR'} and (r['status'] == 'ERROR') == (r['error'] is not None), 'RESPONSE_STATUS')
    require((r['status'] == 'OK') == (r['evidence'] is not None), 'RESPONSE_EVIDENCE')
    require(set(r['timing']) == {'T0','T1','T2','T3','T4','T5','outer_elapsed','clock'}, 'TIMING_SCHEMA')
    require(all(r['timing'][k] is None for k in ('T1','T2','T3','T4')), 'INVENTED_ENDPOINT')
    t = r['timing']
    require(all(t[k] is None or type(t[k]) is int and t[k] >= 0 for k in ('T0','T5')), 'TICK_TYPE')
    require(t['T5'] is None or t['T0'] is not None and t['T5'] >= t['T0'], 'TICK_ORDER')
    require(t['outer_elapsed'] == (t['T5']-t['T0'] if t['T5'] is not None and t['T0'] is not None else None), 'OUTER_ELAPSED')
    require(type(r['synthetic']) is bool and type(r['cluster_invalid']) is bool, 'RESPONSE_TYPES')
    if r['status'] == 'OK':
        require(t['T5'] is not None and not r['cluster_invalid'] and r['invalidated_scope'] is None, 'SUCCESS_STATE')
    else:
        require(r['cluster_invalid'] and r['invalidated_scope'] == 'ALL_THREE_REGIONS_BOTH_VARIANTS', 'ERROR_SCOPE')
        require(type(r['error']) is dict and set(r['error']) == {'type','message','traceback'} and all(type(v) is str for v in r['error'].values()), 'ERROR_SCHEMA')
    canonical(r)  # No NaN/Infinity in IPC; historical path hash alone uses Infinity.
    return r


def production_worker(workload, cluster, variant, runner_identity):
    """Future factory: exact originals, retained three-region engines, no CLI activation."""
    production_gate()
    require(cluster.sequences and all(q['variant'] == variant for q in cluster.queries), 'PER_PROCESS_VARIANT_CLUSTER_REQUIRED')
    from .native import NativeBinding, NativeClock
    from .graphs import frozen_graph
    binding = NativeBinding(workload.p, variant)
    graphs = {region: frozen_graph(inp) for region, inp in workload.p['inputs'].items()}
    prepared = {region: binding.prepare(graph) for region, graph in graphs.items()}
    worker = object.__new__(Worker)
    worker.p = workload.p
    worker.cluster, worker.variant, worker.binding, worker.clock = cluster, variant, binding, NativeClock()
    # Gated wrapper enforces the solve gate even if this factory is later refactored.
    class Engine:
        def __init__(self, engine): self.engine = engine
        def solve(self, source, *, profile=False): return binding.solve(self.engine, source, profile=profile)
    worker.prepared = {r: (g, Engine(e)) for r, (g,e) in prepared.items()}
    worker.graphs, worker.runner_identity = graphs, runner_identity
    worker.last_result, worker.busy, worker.synthetic = None, False, False
    worker.binary_identity = binding.identity
    return worker
