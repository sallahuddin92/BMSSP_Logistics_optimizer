# Native foundation contracts

Task 4 provides graph storage, a reference Dijkstra, and verification infrastructure.
It does not provide BMSSP, a BMSSP fallback, Python integration, or road geometry.
The existing application remains independent and unchanged.

## Graph input, identity, and ownership

`Graph(vertices, edges)` accepts an explicit list of signed 64-bit external vertex
IDs and edges `{uint64 id, int64 from, int64 to, double weight}`. All endpoints
must be listed, including sinks and isolates. Duplicate vertex IDs and edge IDs
are rejected. Parallel edges, self-loops, zero weights, and negative external IDs
are valid. Negative, NaN, and infinite weights are invalid; negative zero is
canonicalized to positive zero. No connectivity or reverse edges are invented.

Vertices are sorted by external ID to assign dense `size_t` indices. Outgoing
CSR edges are ordered by original edge ID within each vertex. Edge IDs are
caller-supplied stable identities, not CSR offsets. Equivalent input permutations
produce identical mappings, traversal, and reference results. Original edges are
also indexed in ID order for path lookup. Storage costs O(V+E), with two edge
arrays; construction is O(V log V + E log E + E log V). External-ID and edge-ID
lookup use binary search; dense outgoing lookup is O(1), traversal O(outdegree),
without per-edge allocation.

Graph objects share `const` storage. Copies/results retain it without copying
adjacency. Spans and edge references require a graph owner to remain alive.
Concurrent queries may share storage; do not concurrently mutate the same Graph
handle or result. Moved-from handles may only be destroyed or assigned. Query
results own the graph snapshot plus independent distance/predecessor arrays;
there is no shared query state. Result reconstruction requires storage identity,
not merely a structurally similar separately constructed graph.

Counts and prefix sums use checked size arithmetic. Allocation counts are checked
against byte representability and vector limits. Iterator differences become
indices only after a successful lookup in a vector of representable size.
Allocation exhaustion propagates as `std::bad_alloc`; impossible sizes produce
`std::length_error`. Invalid graph content produces `std::invalid_argument`.
Unknown source, target, dense index, or edge IDs produce `std::out_of_range`.

## Numerical and Dijkstra query policy

Weights and distances are IEEE 754 binary64, in caller-defined consistent units.
Queries require round-to-nearest; other rounding modes are rejected. Do not build
with fast-math or configure flush-to-zero. The supported macOS/Linux toolchain
presets use normal IEEE arithmetic. This is a rounded machine-arithmetic oracle,
not an exact-real arithmetic implementation of a research theorem.

All labels start at positive infinity except source zero. Infinity exclusively
means unreachable in a successful result. Every scanned reachable outgoing edge
must have a representable finite candidate sum: invalid operands or overflow
abort the entire query with an exception, even if another path could avoid the
edge. No saturated/partial distance result escapes. The checked-add helper also
rejects a conservative `max - weight` overflow check. Underflow/ordinary rounding
follow binary64; subnormal edges are tested.

Relax only on strict numeric improvement. A binary heap orders exact
`(distance, dense vertex index)` pairs, stale entries are discarded, and CSR edge
order resolves parallel-edge traversal. Equal candidates retain the first
predecessor. This deterministic oracle policy deliberately differs from future
BMSSP's symbolic label/equality policy; do not reuse its relaxation semantics
silently. Source predecessor remains absent. Strict improvement from finalized
parents prevents predecessor cycles, including on zero-weight cycles.

Diagnostics count settled vertices, scanned edges, successful strict relaxations,
and queue pushes with checked counters. Each invocation allocates its own labels
and heap. With lazy duplicates the heap can use O(E) space; query storage is
O(V+E), and a general multigraph bound is O((V+E) log(V+E)). Graph data is not copied.

## Path contract

`reconstruct_path(graph, result, external_target)` returns status, distance,
external vertices, and original edge IDs. A reachable source-to-source path has
one vertex, no edges, and distance zero. An unreachable target has explicit
`PathStatus::unreachable`, positive infinity, and empty vectors.

The function checks snapshot identity, array dimensions, source state, target
label, predecessor presence, original edge existence, direction, and each label
transition. Traversal is capped at V links, so corruption cannot cause an infinite
loop. The returned path is reversed into source order and summed again using the
same checked addition policy. Its sum must equal the reported distance exactly;
there is no tolerance for invalid reachability, edges, chains, or stored labels.
Corruption is rejected with an exception, not a partial path. Only the requested
predecessor chain is inspected; reconstruction is not a full shortest-path proof
for an arbitrary caller-mutated result. Differential tests establish algorithm
correctness separately.

## Verification policy

Native tests run without network or third-party test libraries. Test checks remain
active in Release (no `assert` reliance). An independent test-only Bellman-Ford
uses raw input edges rather than CSR or production relaxation helpers. Integer
and quarter-unit randomized weights have exactly representable sums at tested
sizes: distance and reachability comparisons require exact equality. Returned
paths are additionally checked against raw original input edges. Decimal and
subnormal fixtures exercise the declared machine arithmetic separately.

If future tests compare different floating accumulation orders, justify any
absolute/relative bound from those fixtures before adding it. No blanket epsilon
may change queue ordering, relaxation, directed feasibility, or predecessor
validation. No mismatch percentage is acceptable.
