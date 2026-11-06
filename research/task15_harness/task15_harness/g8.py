"""Small SYNTHETIC fixture comparator, not an implementation of actual Mach-O G8."""
from __future__ import annotations
import re
from typing import Any
from .errors import ControlError, require

SUPPORTED = {'ret', 'stp', 'ldp', 'sub', 'add', 'cmp', 'ldr', 'str', 'mov', 'b', 'bl',
             'b.eq', 'b.ne', 'cbz', 'cbnz'}


def classify_synthetic(before: dict[str, Any], after: dict[str, Any],
                       policy: str = 'preserve_registers_immediates_frames') -> dict[str, Any]:
    require(policy == 'preserve_registers_immediates_frames', 'G8_UNSUPPORTED_NORMALIZATION', policy)
    require(all(x.get('label') == 'SYNTHETIC_G8_FIXTURE' for x in [before, after]),
            'G8_ACTUAL_PENDING', 'actual G8 comparison is specified, not enabled')
    def normalize(fixture: dict[str, Any]) -> list[tuple[str, str]]:
        instructions = fixture['instructions']
        positions = {int(x['address']): i for i, x in enumerate(instructions)}
        require(len(positions) == len(instructions) and all(int(x['address']) == fixture['entry']+4*i
                for i, x in enumerate(instructions)), 'G8_UNSUPPORTED_NORMALIZATION', 'instruction boundaries')
        out = []
        for ins in instructions:
            op = ins['opcode']
            require(op in SUPPORTED, 'G8_UNSUPPORTED_NORMALIZATION', op)
            operands = re.sub(r'\s+', '', ins['operands'])
            if op in {'b','bl','b.eq','b.ne','cbz','cbnz'}:
                pieces = operands.split(',')
                try:
                    address = int(pieces[-1], 0)
                except ValueError as exc:
                    raise ControlError('G8_UNSUPPORTED_NORMALIZATION', 'unresolved branch') from exc
                if address in positions:
                    pieces[-1] = f'block:{positions[address]}'
                else:
                    target = fixture.get('external_targets', {}).get(str(address))
                    require(type(target) is str and target.startswith('symbol:'),
                            'G8_UNSUPPORTED_NORMALIZATION', 'missing exact branch target')
                    pieces[-1] = target
                operands = ','.join(pieces)
            out.append((op, operands))
        return out
    a, b = normalize(before), normalize(after)
    if a != b:
        return {'class': 'M', 'reason': 'compute/register/immediate/branch/frame difference',
                'eligible': False, 'actual_G8': 'PENDING'}
    # Any link-address/alignment/loop/page difference needs review, never automatic acceptance.
    layout = (before['entry'], before['loop_headers'], before['instructions'], before.get('external_targets'))
    changed = layout != (after['entry'], after['loop_headers'], after['instructions'], after.get('external_targets'))
    return {'class': 'L' if changed else 'I',
            'reason': 'layout risk requires independent approval' if changed else 'identical synthetic fixture',
            'eligible': False, 'actual_G8': 'PENDING'}
