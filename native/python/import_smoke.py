"""Executed by CTest against the actual compiled extension."""
import bmssp_native as native

graph = native.NativeGraph([0, 1, 2], [(2**64 - 1, 0, 1, 0.25), (2, 1, 2, 0.75)])
result = native.BMSSP2025Engine(graph).solve(0)
assert result.algorithm == "native_bmssp_2025"
assert result.distance(2) == 1
assert result.path(2)["edges"] == [2**64 - 1, 2]
assert result.diagnostics["recursive_calls"] > 0
assert result.diagnostics["frontier"]["pulls"] > 0
print(native.__file__, result.diagnostics)
