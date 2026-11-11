"""Dormant original-production adapter. No CLI entry point or execution approval."""
VERSION = '0.1.0'

class AdapterError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise AdapterError(code)


def production_gate():
    # Deliberately unconditional; no caller, manifest, environment or flag can approve.
    raise AdapterError('PRODUCTION_EXECUTION_DISABLED')
