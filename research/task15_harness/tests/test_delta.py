"""Independent static regression controls for Phase-1.1; no engine workloads."""
import ast
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from task15_harness.artifacts import inspect_storage, repository_identity
from task15_harness.errors import ControlError, require
from task15_harness.integrity import canonical, strict_json_bytes
from task15_harness.manifest import prepare_manifest, validate_manifest
from task15_harness.output import create_bundle, read_bundle, read_bundle_json, SUPPORTED_PAYLOAD_SETS
from task15_harness.planning import compile_plan, query_records, plan_counts
from task15_harness.protocol import PACKAGE_ROOT, PROTOCOL_HASH, Protocol, load_protocol
from task15_harness.simulation import simulate

NEGATIVE_RESULTS = []
SESSION_FIELDS = ('session_kind', 'session_id', 'schedule_ref_session', 'session_key')


def execution_facilities(source, allow_git=False):
    """Advisory AST lint, including simple import/assignment aliases and attributes.

    This is not a proof against dynamic Python or same-user attacks.
    """
    tree = ast.parse(source)
    aliases = {}
    def name(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return name(node.value) + '.' + node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'getattr':
            if len(node.args) == 2 and isinstance(node.args[1], ast.Constant):
                return name(node.args[0]) + '.' + str(node.args[1].value)
        return ''
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split('.')[0]] = item.name
                if item.name.split('.')[0] in {'ctypes', 'bmssp_native', 'native_graph', 'pickle', 'multiprocessing'}:
                    issues.append(item.name)
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = (node.module or '') + '.' + item.name
            if (node.module or '').split('.')[0] in {'ctypes', 'bmssp_native', 'native_graph', 'pickle', 'multiprocessing'}:
                issues.append(node.module)
    # Resolve simple assignment aliases before evaluating calls.
    for _ in range(2):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and name(node.value):
                        aliases[target.id] = name(node.value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = name(node.func)
        prohibited = (target.split('.')[0] in {'subprocess', 'ctypes', 'multiprocessing'}
                      or target in {'eval', 'exec', '__import__', 'builtins.eval', 'builtins.exec',
                                    'builtins.__import__', 'os.system', 'os.popen', 'importlib.import_module'}
                      or target.startswith(('os.exec', 'os.spawn', 'os.posix_spawn')))
        if prohibited:
            # Single fixed read-only Git metadata invocation, not arbitrary subprocesses.
            approved = (allow_git and target == 'subprocess.run' and node.args
                        and isinstance(node.args[0], ast.List)
                        and isinstance(node.args[0].elts[0], ast.Constant)
                        and node.args[0].elts[0].value == 'git'
                        and any(k.arg == 'env' and isinstance(k.value, ast.Name)
                                and k.value.id == 'environment' for k in node.keywords))
            if not approved:
                issues.append(target)
    return issues


class DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_protocol(PACKAGE_ROOT.parents[1])
        cls.frozen = cls.protocol.data()
        cls.plan = compile_plan(cls.protocol)

    def reject(self, code, action):
        with self.assertRaises(ControlError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        NEGATIVE_RESULTS.append({'case': self.id(), 'expected': code, 'observed': caught.exception.code,
                                 'scope': 'STATIC_OR_SYNTHETIC'})

    def test_bundle_adversarial_inventory(self):
        scenarios = [
            ('reviewer-unbound-manifest', {'other.json': b'{}', 'manifest.json': b'{}'},
             {'other.json': hashlib.sha256(b'{}').hexdigest()}, 'BUNDLE_PAYLOAD_SET'),
            ('unlisted-extra', {'manifest.json': b'{}', 'extra.json': b'{}'},
             {'manifest.json': hashlib.sha256(b'{}').hexdigest()}, 'BUNDLE_UNEXPECTED_PAYLOAD'),
            ('missing-manifest', {}, {'manifest.json': hashlib.sha256(b'{}').hexdigest()}, 'BUNDLE_PAYLOAD_MISSING'),
            ('tamper', {'manifest.json': b'changed'},
             {'manifest.json': hashlib.sha256(b'{}').hexdigest()}, 'BUNDLE_HASH'),
            ('bad-hash', {'manifest.json': b'{}'}, {'manifest.json': 'x'}, 'BUNDLE_HASH_FORMAT'),
            ('unsafe-name', {}, {'../manifest.json': '0'*64}, 'BUNDLE_PAYLOAD_NAME'),
            ('case-ambiguity', {}, {'Manifest.json': '0'*64}, 'BUNDLE_PAYLOAD_NAME'),
        ]
        for label, files, inventory, code in scenarios:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                for name, raw in files.items():
                    (folder/name).write_bytes(raw)
                (folder/'COMPLETED.json').write_bytes(canonical({'schema_version': '1',
                    'scope': 'CONTROL_PLANE_ONLY_NOT_MEASUREMENT', 'files_sha256': inventory}))
                self.reject(code, lambda: read_bundle_json(folder, 'manifest.json', expected_payloads={'manifest.json'}))

    def test_bundle_strict_marker(self):
        marker = {'schema_version': '1', 'scope': 'CONTROL_PLANE_ONLY_NOT_MEASUREMENT',
                  'files_sha256': {'manifest.json': '0'*64}}
        malformed = [[], None, {}, {**marker, 'unknown': 1}, {**marker, 'schema_version': 1},
                     {**marker, 'files_sha256': []}, {**marker, 'files_sha256': None}]
        malformed += [{k: v for k, v in marker.items() if k != missing} for missing in marker]
        raws = [canonical(m) for m in malformed]
        raws.append(b'{"schema_version":"1","scope":"CONTROL_PLANE_ONLY_NOT_MEASUREMENT",'
                    b'"files_sha256":{"manifest.json":"a","manifest.json":"b"}}')
        for raw in raws:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                (folder/'COMPLETED.json').write_bytes(raw)
                self.reject('BUNDLE_MARKER_SCHEMA', lambda: read_bundle(folder))

    def test_bundle_exact_consumed_bytes_and_aliases(self):
        for inventory in SUPPORTED_PAYLOAD_SETS:
            with self.subTest(inventory=inventory), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)/'bundle'
                create_bundle(self.protocol, folder, {name: b'{}' for name in inventory})
                self.assertEqual(set(read_bundle(folder)), set(inventory))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'bundle'
            create_bundle(self.protocol, folder, {'report.json': b'{}', 'plan.json': b'{}'})
            (folder/'plan.json').unlink()
            os.link(folder/'report.json', folder/'plan.json')
            self.reject('BUNDLE_PAYLOAD_REFERENCE', lambda: read_bundle(folder))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'bundle'
            create_bundle(self.protocol, folder, {'manifest.json': b'{}'})
            self.assertEqual(read_bundle_json(folder, 'manifest.json', expected_payloads={'manifest.json'}), {})
            # Mutation between inventory check and consumer read must also be caught.
            from task15_harness import output
            original = output.read_bundle
            def mutate(*args, **kwargs):
                result = original(*args, **kwargs)
                (folder/'manifest.json').write_bytes(b'{"changed":true}')
                return result
            with patch.object(output, 'read_bundle', side_effect=mutate):
                self.reject('BUNDLE_HASH', lambda: output.read_bundle_json(folder, 'manifest.json', expected_payloads={'manifest.json'}))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'bundle'
            create_bundle(self.protocol, folder, {'manifest.json': b'{}'})
            (folder/'manifest.json').unlink()
            (Path(tmp)/'outside').write_bytes(b'{}')
            (folder/'manifest.json').symlink_to(Path(tmp)/'outside')
            self.reject('BUNDLE_PAYLOAD_REFERENCE', lambda: read_bundle(folder))

    def test_all_session_domains_and_references(self):
        d = self.frozen['design']
        bases = {r['id']: r for r in d['base_schedule']}
        diagnostics = {r['id']: r for r in d['diagnostic_schedule']}
        stacks = {r['id']: r for r in d['allocator_stack_companions']}
        units = self.plan['units'] + self.plan['stack_companions']
        self.assertEqual(len(units), 228)
        grouping = Counter()
        mismatching_reference_sessions = 0
        for unit in units:
            if unit['diagnostic_id'] is None:
                kind, index = 'PRIMARY', bases[unit['schedule_ref']]['session']
            else:
                kind = 'DIAGNOSTIC'
                row = (stacks if unit['mode'] == 'allocation_stacks' else diagnostics)[unit['diagnostic_id']]
                index = row['diagnostic_session'] if unit['mode'] == 'allocation_stacks' else row['session']
                self.assertEqual(unit['schedule_ref'], row['schedule_ref'])
            reference = bases[unit['schedule_ref']]['session']
            self.assertEqual(tuple(unit[k] for k in SESSION_FIELDS), (kind, index, reference, f'{kind}/{index}'))
            grouping[unit['session_key']] += 1
            mismatching_reference_sessions += kind == 'DIAGNOSTIC' and index != reference
        self.assertGreater(mismatching_reference_sessions, 0)
        self.assertEqual(set(grouping), {f'PRIMARY/{i}' for i in range(8)} | {f'DIAGNOSTIC/{i}' for i in range(4)})
        by_id = {u['id']: u for u in units}
        count = 0
        for record in query_records(self.protocol, self.plan):
            unit = by_id[record['trial_id']]
            self.assertEqual({k: record[k] for k in SESSION_FIELDS}, {k: unit[k] for k in SESSION_FIELDS})
            self.assertTrue(record['paired_cluster_id'].startswith(unit['session_key']+'/'))
            self.assertNotIn('loaded_binary_sha256', record['expected_binary'])
            self.assertEqual(record['expected_binary']['load_status'], 'NOT_LOADED')
            count += 1
        self.assertEqual(count, 138696)
        self.assertEqual(plan_counts(self.protocol, self.plan)['query_record_count'], count)
        events = list(simulate(self.protocol, self.plan, interrupt_after=2))
        for event in events[:-1]:
            self.assertEqual(event['session_key'], 'PRIMARY/0')
            self.assertIn('schedule_ref_session', event)
        self.assertEqual(events[-1]['session_keys'], ['PRIMARY/0'])
        observed_sessions = set()
        cluster_identities = {}
        for event in simulate(self.protocol, self.plan):
            if event['event'] == 'SIMULATION_SUMMARY':
                self.assertEqual(set(event['session_keys']), set(grouping))
                continue
            identity = {k: event[k] for k in SESSION_FIELDS}
            observed_sessions.add(event['session_key'])
            if event['event'] == 'CLUSTER_VERDICT':
                self.assertEqual(identity, cluster_identities[event['cluster']])
            else:
                self.assertEqual(identity, {k: event['query'][k] for k in SESSION_FIELDS})
                cluster_identities[event['query']['paired_cluster_id']] = identity
        self.assertEqual(observed_sessions, set(grouping))
        self.assertEqual(len(cluster_identities), 180)

    @staticmethod
    def target_tuple(record):
        return tuple(record[k] for k in ('base_trial_id', 'region', 'execution_index',
                     'original_position', 'source_id', 'source_occurrence', 'variant', 'paired_execution_order'))

    def reconcile(self, actual, expected):
        require(actual == expected, 'STREAM_MISMATCH', 'independent frozen-tuple reconciliation')

    def independent_expected(self, row, region, subset=None):
        # Frozen arrays are the oracle; no planner helpers or generated orders used.
        sources = self.frozen['inputs'][region]['source_positions']
        occurrence_by_position = [sources[:pos+1].count(source) for pos, source in enumerate(sources)]
        result = []
        for execution in range(len(row['positions_by_region'][region])):
            position = row['positions_by_region'][region][execution]
            if subset is not None and position not in subset:
                continue
            order = row['P2_pair_orders_by_region'][region][execution]
            variants = {'AB': ('baseline', 'candidate'), 'BA': ('candidate', 'baseline')}[order]
            result.extend((row['id'], region, execution, position, sources[position],
                           occurrence_by_position[position], variant, order) for variant in variants)
        return result

    def test_complete_p2_emitted_stream_and_diagnostic_subsets(self):
        d = self.frozen['design']
        p2 = [r for r in d['base_schedule'] if r['protocol'] == 'P2']
        self.assertEqual(len(p2), 32)
        actual = defaultdict(list)
        emitted_primary_sequence = []
        for record in query_records(self.protocol, self.plan):
            if record['protocol'] == 'P2' and record['phase'] == 'target':
                actual[(record['trial_id'], record['region'])].append(self.target_tuple(record))
                if record['cohort'] == 'A':
                    emitted_primary_sequence.append(self.target_tuple(record))
        expected_primary_sequence = []
        for session in d['sessions']:
            for row in p2:
                if row['session'] == session['session']:
                    for region in row['regions']:
                        expected_primary_sequence.extend(self.independent_expected(row, region))
        self.reconcile(emitted_primary_sequence, expected_primary_sequence)
        primary_total = diagnostic_total = 0
        for region in self.frozen['inputs']:
            position_balance = defaultdict(Counter)
            session_balance = defaultdict(Counter)
            for row in p2:
                expected = self.independent_expected(row, region)
                self.reconcile(actual.pop((f'A/primary/{row["id"]}', region)), expected)
                primary_total += len(expected)
                pairs = expected[::2]
                self.assertEqual(len(pairs), 100)
                self.assertEqual(Counter(t[-1] for t in pairs), {'AB': 50, 'BA': 50})
                for t in pairs:
                    position_balance[t[3]][t[-1]] += 1
                    session_balance[(row['session'], t[3])][t[-1]] += 1
            self.assertEqual(set(position_balance), set(range(100)))
            self.assertTrue(all(c == {'AB': 16, 'BA': 16} for c in position_balance.values()))
            self.assertEqual(len(session_balance), 800)
            self.assertTrue(all(c == {'AB': 2, 'BA': 2} for c in session_balance.values()))
        bases = {r['id']: r for r in p2}
        for diagnostic in d['diagnostic_schedule'] + d['allocator_stack_companions']:
            companion = 'diagnostic_session' in diagnostic
            cohort = 'C' if companion else diagnostic['cohort']
            conditions = ['stack'] if companion else diagnostic['condition_order']
            row = bases[diagnostic['schedule_ref']]
            for condition in conditions:
                for region in row['regions']:
                    subset = self.frozen['cohorts']['C']['positions_by_region'][region] if cohort == 'C' else None
                    expected = self.independent_expected(row, region, subset)
                    self.reconcile(actual.pop((f'{cohort}/{diagnostic["id"]}/{condition}', region)), expected)
                    diagnostic_total += len(expected)
        # B primary is independently a complete copy of the frozen target order.
        for row in p2:
            for region in row['regions']:
                self.assertEqual(actual.pop((f'B/primary/{row["id"]}', region)), self.independent_expected(row, region))
        self.assertFalse(actual)
        self.assertEqual(primary_total, 19200)
        # 16 C clusters * two conditions * two variants * 41 positions,
        # plus four stack companions * two variants * 41 positions, plus D.
        self.assertEqual(diagnostic_total, 16*2*2*41 + 4*2*41 + 38400)
        small = next(i for i in self.frozen['inputs'].values() if len(set(i['source_positions'])) < 100)
        self.assertGreater(max(Counter(small['source_positions']).values()), 1)

    def test_independent_primary_occurrences_and_separate_lanes(self):
        d = self.frozen['design']
        bases = {r['id']: r for r in d['base_schedule']}
        self.assertEqual(len(bases), 64)
        count = 0
        for record in query_records(self.protocol, self.plan):
            if record['session_kind'] != 'PRIMARY' or record['phase'] != 'target':
                continue
            row = bases[record['base_trial_id']]
            original = row['positions_by_region'][record['region']][record['execution_index']]
            sources = self.frozen['inputs'][record['region']]['source_positions']
            self.assertEqual(record['original_position'], original)
            self.assertEqual(record['source_id'], sources[original])
            self.assertEqual(record['source_occurrence'], sources[:original+1].count(sources[original]))
            count += 1
        self.assertEqual(count, 64*2*3*100*2)
        # Verify each frozen lane independently; do not define a cross-lane order.
        main_expected = []
        companions_expected = []
        for session in sorted({r['session'] for r in d['diagnostic_schedule']}):
            for row in d['diagnostic_schedule']:
                if row['session'] == session:
                    main_expected.extend(f'{row["cohort"]}/{row["id"]}/{condition}' for condition in row['condition_order'])
            for row in d['allocator_stack_companions']:
                if row['diagnostic_session'] == session:
                    companions_expected.append(f'C/{row["id"]}/stack')
        self.assertEqual([u['id'] for u in self.plan['units'] if u['session_kind'] == 'DIAGNOSTIC'], main_expected)
        self.assertEqual([u['id'] for u in self.plan['stack_companions']], companions_expected)
        self.assertFalse(self.plan['collection_authorized'])
        self.assertEqual(self.plan['kind'], 'STATIC_EXECUTION_PLAN_NOT_EXECUTABLE')
        self.assertIn('Serialization order is not execution order', self.plan['ordering_caveat'])

    def test_stream_oracle_detects_corruptions(self):
        row = next(r for r in self.frozen['design']['base_schedule'] if r['protocol'] == 'P2')
        region = row['regions'][0]
        expected = self.independent_expected(row, region)
        emitted = [self.target_tuple(r) for r in query_records(self.protocol, self.plan)
                   if r['trial_id'] == f'A/primary/{row["id"]}' and r['region'] == region and r['phase'] == 'target']
        self.reconcile(emitted, expected)
        mutations = []
        swapped = emitted.copy(); swapped[0], swapped[1] = swapped[1], swapped[0]; mutations.append(swapped)
        reordered = emitted[2:4] + emitted[:2] + emitted[4:]; mutations.append(reordered)
        missing = emitted[1:]; mutations.append(missing)
        duplicate = emitted[:2]+emitted; mutations.append(duplicate)
        for column, value in ((0, 'wrong_trial'), (1, 'wrong_region'), (2, -1), (3, -1),
                              (4, 'wrong_source'), (6, 'wrong_variant'), (7, 'wrong_order'), (5, -1)):
            corrupted = emitted.copy(); entry = list(corrupted[0]); entry[column] = value
            corrupted[0] = tuple(entry); mutations.append(corrupted)
        for changed in mutations:
            self.reject('STREAM_MISMATCH', lambda: self.reconcile(changed, expected))

    def test_nonfinite_exponents_and_finite_numbers(self):
        for token in [b'1e999', b'-1e999', b'NaN', b'Infinity', b'-Infinity']:
            self.reject('JSON_NONFINITE', lambda: strict_json_bytes(token))
        self.assertEqual(strict_json_bytes(b'[1e-300,1e300,-1.25]'), [1e-300, 1e300, -1.25])
        self.assertEqual(self.protocol.identity, PROTOCOL_HASH)
        unsigned = deepcopy(self.frozen)
        unsigned['identity'].pop('sha256')
        self.assertEqual(hashlib.sha256(canonical(unsigned)).hexdigest(), PROTOCOL_HASH)

    def test_git_hostile_environment_and_invalid_repository(self):
        expected = repository_identity(self.protocol)
        hostile = {'GIT_DIR': '/no/such/git', 'GIT_WORK_TREE': '/no/such/tree',
                   'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'remote.origin.url',
                   'GIT_CONFIG_VALUE_0': 'hostile', 'GIT_CONFIG_SYSTEM': '/no/config',
                   'GIT_CONFIG_PARAMETERS': "'core.bare=true'"}
        with patch.dict(os.environ, hostile):
            self.assertEqual(repository_identity(self.protocol), expected)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Protocol(self.protocol._encoded, Path(tmp))
            self.reject('GIT_METADATA', lambda: repository_identity(bad))
        with patch('task15_harness.artifacts.subprocess.run', side_effect=FileNotFoundError('git absent')):
            self.reject('GIT_METADATA', lambda: repository_identity(self.protocol))

    def test_status_scope_and_private_hardlink_probe(self):
        draft = prepare_manifest(self.protocol, checked=False)
        report = validate_manifest(self.protocol, draft)
        self.assertEqual(report['status'], 'VALID_STATIC_MANIFEST_STRUCTURE')
        self.assertEqual(report['external_identity_verification'], 'NOT_CHECKED')
        self.assertFalse(report['future_execution_eligible'])
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = inspect_storage(self.protocol, folder, check_hardlinks=True)
            self.assertEqual(report['hardlink_capability']['status'], 'HARDLINK_SUPPORTED_AT_CHECK')
            self.assertEqual(list(folder.iterdir()), [])
            self.assertFalse(report['space_reserved'])
            self.assertEqual(report['verification_scope'], 'POINT_IN_TIME_FREE_SPACE_ONLY')
            with patch('task15_harness.artifacts.os.link', side_effect=OSError('denied')):
                report = inspect_storage(self.protocol, folder, check_hardlinks=True)
            self.assertEqual(report['hardlink_capability']['status'], 'UNSUPPORTED_OR_DENIED')
            self.assertEqual(list(folder.iterdir()), [])
        self.reject('STORAGE_DESTINATION', lambda: inspect_storage(self.protocol, None, check_hardlinks=True))

    def test_advisory_execution_scan_aliases_and_attributes(self):
        samples = ['import subprocess as s\ns.run(["anything"])',
                   'from subprocess import Popen as launch\nlaunch([])',
                   'import os as o\nf=o.system\nf("x")',
                   'import builtins as b\nb.exec("x")',
                   'import importlib as i\ni.import_module("bmssp_native")',
                   'import os\ngetattr(os,"system")("x")',
                   'import ctypes.util', 'from multiprocessing import Process']
        for source in samples:
            self.assertTrue(execution_facilities(source), source)
        for path in (PACKAGE_ROOT/'task15_harness').glob('*.py'):
            self.assertEqual(execution_facilities(path.read_text(), allow_git=path.name == 'artifacts.py'), [], path.name)
