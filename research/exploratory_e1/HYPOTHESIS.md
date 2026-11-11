# E1-H1 — remove the singleton insertion staging allocation

Label: EXPLORATORY_BMSSP_PERFORMANCE. This is the only optimization hypothesis in E1. Declared after fresh baseline correctness, pilot/profile runs and three unprofiled CPU samples, before editing algorithm source.

Observed bottleneck: baseline sample records have 4261/4278/4279 main-thread samples. Ordinary allocator/new/delete exclusive samples account for 24.43%/22.91%/22.95%; BoundedFrontier::insert inclusive accounts for 23.28%/25.29%/25.24%. Those quantities overlap and must not be added. Symbolic comparison is also a hotspot (13.3–13.6% exclusive), but is not changed in E1. CPU samples are not calibrated wall-time fractions.

Root-cause hypothesis: each accepted singleton insert stages `{key,value}` through an initializer-list-created std::vector before fill moves the element into the PMR list. This unconditionally requires a short-lived general-heap buffer and an extra shared label ownership copy although the destination block and single entry are already known. This is one avoidable source of allocator pressure within the measured insertion hotspot; E1 does not assert it explains all insertion or allocator cost.

Smallest coherent change: replace only that singleton fill call in BoundedFrontier::insert with the same list append, key-location update and peak-key counter update. Keep batched fill, median selection/splitting, all validation, stable list iterators, fences, equality ordering, degree reduction, numeric checks, recursion and result projection unchanged.

Expected mechanism: eliminate one temporary vector allocation/free per accepted singleton insertion and its excess label shared_ptr copy. No retained data structure or topology-specific special case. Expected memory trade-off: lower transient requested bytes; unchanged retained frontier representation. Whole-process RSS may stay flat because allocator page retention/granularity dominates.

Correctness risks: preserve iterator identity/location updates, insertion order, peak_keys and split trigger; list pushback must still construct a stable owning label; exception unwinding must not introduce dangling handles. Existing frontier/algorithm/numerical/ownership tests, exact all100-position road gates and ASan/UBSan are required. No public API/diagnostic schema change is intended.

Falsification: reject this explanation if allocation diagnostics do not decrease, exact vectors/valid paths/work counters differ, or the controlled primary matrix does not reproduce a useful benefit without unjustified tail/memory/reliability regressions. A median improvement alone is insufficient. Do not implement a second hypothesis if this one fails or remains inconclusive.
