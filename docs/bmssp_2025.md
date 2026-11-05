# Native 2025 BMSSP engine

The native implementation targets arXiv:2504.17033v2 (30 July 2025), independently
authored from the supplied specification and primary paper. No external algorithm
implementation was copied. Task 5 kept the Python application independent. Task 6 adds the optional
`bmssp_native` binding and explicit native matrix selection documented in
[native_python.md](native_python.md); legacy routing and VRP remain available.

## Interfaces and ownership

`bmssp_2025(graph, external_source)` preprocesses and solves once.
`BMSSP2025Engine(graph)` retains an immutable degree reduction and supports multiple
independent `solve(source, options)` queries, including concurrent queries.
Results contain the existing original-graph `ShortestPathResult` and separate
`BMSSPDiagnostics`. No solver fallback exists. Reference Dijkstra is used only by
tests, the explicit CLI selection, and comparisons.

For component work, `BMSSPWorkspace` owns tentative labels, parameters, and counters.
`reset(source)` starts a fresh query, retaining vector capacity. Low-level routines
require degree at most two, a sound source-rooted label state, the paper's complete
frontier coverage assumption, valid unique frontier indices, and labels below B.
They reject invalid cardinality/parameters; mathematical coverage is checked by an
independent test observer, not assumed to be decidable from tentative labels alone.
Reset the workspace after an exception. No failed query returns a plausible partial
SSSP result. Normal bounded partial returns explicitly contain B' and U.

## Module contracts

- `degree_reduction`: allocates one port per edge incidence, with separate ports
  for parallel edges and both ends of a self-loop. Zero-weight directed cycles
  connect ports of the same original vertex. Singleton ports need no synthetic
  self-edge. Isolates remain explicit. Validation checks in/out degree, unique
  original-edge mapping, weights, representatives, and complete synthetic cycles.
- `symbolic_label`: immutable path snapshots order distance, hop count, reversed
  vertex sequence, then reversed original/transformed edge identities as a final
  parallel-edge refinement. Snapshots share an arena; raw parent views remain
  valid while a label owns that arena. Arena destruction is iterative, avoiding
  recursion proportional to path length. Comparisons never use pointer addresses
  as tie breakers. Label allocation is synchronized; each query has its own arena. Task 9 stores nodes in stable separately owned array slabs while retaining shared ownership and the mutex.
- `base_case`: local bounded mini-Dijkstra, singleton frontier, equality-valid
  relaxation, at most k+1 extracted vertices. It returns B on exhaustion; otherwise
  the largest extracted symbolic label is the exclusive boundary and is excluded
  from U. Lazy heap duplicates are discarded; this is not full-source Dijkstra.
- `find_pivots`: performs k frontier rounds, expands W only below B, and preserves
  Algorithm 1's updates beyond B. It returns early when W exceeds k*size(S).
  Otherwise a current-label tight predecessor forest is counted bottom-up in
  linear traversal work; large rooted trees identify pivots. W is not automatically
  classified complete.
- `bounded_frontier`: D0 prepend blocks and D1 insertion blocks retain unsorted
  items. A balanced map indexes D1 fences; key handles support Delete and duplicate
  minima. Deterministic median-of-medians selection splits blocks and selects Pull
  batches. BatchPrepend recursively partitions batches into ordered blocks.
  Pull returns at most M keys and the minimum remaining symbolic label, or B.
  Optional expensive validation checks ordering, fences, handles, and bounds.
- `run`: dispatches BaseCase, selects pivots, partitions via Pull, recurses,
  accumulates disjoint completed children, performs equality-valid outgoing
  relaxations, inserts/re-prepends the two boundary intervals, and finalizes W.
  Boundaries must be monotone and each nonempty recursive call must progress.
  Workload termination and parameter powers are checked/capped against graph size
  without unchecked shifts. Positive k/t clamps cover tiny inputs; n=1 dispatches
  the actual level-zero BaseCase.

## Explicit representation refinements

Nested calls can settle a vertex still stored with an older, larger immutable
snapshot in a parent D. After each child completes, its vertices are deleted from
that parent's D using the internal Delete operation described in Lemma 3.3's
construction. Their outgoing edges are then relaxed/reinserted as usual. This
retires redundant settled records and preserves coverage through their outgoing
frontier. A completed vertex lies strictly below the child boundary; each outgoing
edge is processed immediately. Its successor is either already below that boundary
or receives the usual future-frontier candidate. Thus deleting the old record
cannot remove the last covered entrance to an incomplete shortest path. This
bookkeeping does not run a different shortest-path solver. A seeded dense graph
and intermediate contract checks exercise this bookkeeping. Removing the check
or allowing backward boundaries is not an acceptable alternative.

`project_path` removes synthetic edges from a concrete transformed label and
validates the resulting original directed walk and weight. Actual BMSSP labels
are projected in integration tests. A transformed hop-optimal path can visit
different ports of the same original vertex; directly contracting all predecessor
pointers can therefore introduce zero-cost cycles. The full driver instead builds
an acyclic original predecessor tree by traversing original edges tight with the
BMSSP-computed distances. It never changes those distances. Every finite vertex
must be reached by this traversal or the query fails. The existing path validator
then checks original edge IDs, direction, and exact machine-arithmetic cost.

## Arithmetic and complexity limits

The implementation uses Task 4's checked IEEE binary64 arithmetic and requires
round-to-nearest. Positive infinity is a boundary/unreachable sentinel, never an
edge weight. Any encountered overflow aborts. There is no epsilon in ordering,
relaxation, coverage tests, or path validation. Equality-valid processing is
separate from a strict improvement: equal valid candidates are propagated even
when the label itself need not change (Remark 3.4).

This is an executable implementation of the recursive mechanisms, not a proof of
an O(m log^(2/3)n) implementation bound. In particular, full snapshot comparisons
can traverse path suffixes, the key dictionary is hash-based with expected rather
than deterministic worst-case lookup, CSR reconstruction sorts edges, and arenas
retain all query-created path nodes until their owners expire. Expensive optional
frontier validation/trace snapshots are outside performance measurements. These
costs invalidate a direct transfer of the paper's unit-cost complexity analysis.
The structural frontier is block-based, not a renamed global binary heap.

The paper's proofs assume exact real arithmetic with consistent symbolic path
ordering. Binary64 rounding does not satisfy all exact-real assumptions. Integer
and quarter-unit fixtures here have exact sums at the tested sizes. Additional
mixed-magnitude/decimal tests check empirical rounded-distance agreement and paths;
they are not a proof for every floating-point graph or a claim of exact-real
answers beyond representable arithmetic. No universal floating-point theorem or
speed advantage is claimed.

Diagnostics distinguish recursive calls, actual maximum call depth, BaseCase and
pivot work, equality-valid relaxations, completed events across levels, unique
root completion, original reachable count, transformation sizes, frontier
operations/splits/selection volume/retired keys, path-node allocations, and
preprocessing/query durations. Query time includes original-tree construction.


## Task 9 native allocation engineering

Frontier containers now use a private per-frame PMR pool; the D0/D1 lists, balanced
fences, key handles, partial selection and operation semantics are unchanged.
Workspace validity checks use dense epoch scratch that is dead before recursion;
parent/child completed sets and pivot forests are not shared. Symbolic comparison
ordering is unchanged. See [ownership, reproduction and benchmark contracts](native_performance_workflow.md)
and [measured Task 9 results](native_performance_validation.md).
