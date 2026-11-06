from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import Iterable
from .artifacts import capacity, inspect_identities, inspect_storage, source_lock
from .errors import ControlError, require
from .integrity import canonical
from .manifest import SAFE_STATES, prepare_manifest, validate_manifest
from .output import create_bundle, read_bundle_json
from .planning import compile_plan, plan_counts, query_records, validate_plan
from .protocol import PACKAGE_ROOT, load_protocol
from .schedule import validate_schedule
from .simulation import simulate

SAFE = {'verify-protocol','validate-schedule','inspect-identities','plan','prepare-manifest',
        'validate-manifest','inspect-storage','simulate','self-test'}


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    if args_list and args_list[0] not in SAFE and args_list[0] not in {'-h','--help'}:
        print(canonical({'error': 'UNSUPPORTED_OPERATION', 'operation': args_list[0],
                         'execution_enabled': False}).decode())
        return 2
    parser = argparse.ArgumentParser(description='Task15 STATIC control plane; execution commands unavailable')
    parser.add_argument('operation', choices=sorted(SAFE))
    parser.add_argument('--repo', type=Path, default=PACKAGE_ROOT.parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--check-hardlinks', action='store_true', help='tiny private storage capability probe only')
    parser.add_argument('--state', choices=SAFE_STATES, default='DRAFT')
    parser.add_argument('--skip-external', action='store_true', help='all external identities NOT_CHECKED')
    parser.add_argument('--with-queries', action='store_true', help='stream full static query records with plan')
    parser.add_argument('--fail-query', help='synthetic simulator only')
    parser.add_argument('--interrupt-after', type=int, help='synthetic simulator only')
    args = parser.parse_args(args_list)
    try:
        require(not args.check_hardlinks or args.operation == 'inspect-storage',
                'ARGUMENT', '--check-hardlinks is only for inspect-storage')
        protocol = load_protocol(args.repo)
        op = args.operation
        if op == 'self-test':
            from .testing import run_tests
            return run_tests(args.output, protocol)
        if op == 'verify-protocol':
            value = {'status': 'VERIFIED_FROZEN_PROTOCOL', 'canonical_sha256': protocol.identity,
                     'execution_authorized': False, 'promotion_authorized': False,
                     'harness_source': source_lock()}
        elif op == 'validate-schedule':
            value = validate_schedule(protocol.data())
        elif op == 'inspect-identities':
            value = inspect_identities(protocol, checked=not args.skip_external)
        elif op == 'inspect-storage':
            value = {'capacity': capacity(protocol), 'inspection': inspect_storage(protocol, args.destination, check_hardlinks=args.check_hardlinks)}
        elif op == 'prepare-manifest':
            value = prepare_manifest(protocol, state=args.state, checked=not args.skip_external)
        elif op == 'validate-manifest':
            require(args.manifest is not None, 'ARGUMENT', '--manifest bundle required')
            value = validate_manifest(protocol, read_bundle_json(
                args.manifest, 'manifest.json', expected_payloads={'manifest.json'}))
        else:
            plan = compile_plan(protocol)
            validate_plan(protocol, plan)
            value = {'plan': plan, 'counts': plan_counts(protocol, plan)}
        if args.output is not None:
            filename = 'manifest.json' if op == 'prepare-manifest' else 'report.json'
            files: dict[str, bytes | Iterable[bytes]] = {filename: canonical(value)+b'\n'}
            if op == 'plan':
                files['plan.json'] = canonical(plan)+b'\n'
                if args.with_queries:
                    files['queries.jsonl'] = (canonical(r)+b'\n' for r in query_records(protocol, plan))
            elif op == 'simulate':
                files['synthetic-events.jsonl'] = (canonical(r)+b'\n' for r in simulate(
                    protocol, plan, args.fail_query, args.interrupt_after))
            create_bundle(protocol, args.output, files)
            print(canonical({'status': 'STATIC_OUTPUT_CREATED', 'path': str(args.output),
                             'operation': op, 'execution_enabled': False}).decode())
        else:
            require(op != 'simulate', 'ARGUMENT', 'synthetic events require a new --output directory')
            print(canonical(value).decode())
        if op == 'inspect-identities' and not value['all_verified']:
            return 3
        return 0
    except (ControlError, OSError) as exc:
        code = exc.code if isinstance(exc, ControlError) else 'FILESYSTEM_ERROR'
        print(canonical({'error': code, 'detail': str(exc), 'execution_enabled': False}).decode())
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
