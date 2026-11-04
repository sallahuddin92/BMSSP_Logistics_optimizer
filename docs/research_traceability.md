# Research target and remaining work

Target: Duan, Mao, Mao, Shu, Yin, *Breaking the Sorting Barrier for Directed
Single-Source Shortest Paths*, arXiv:2504.17033v2, 30 July 2025.
[Primary text](https://arxiv.org/html/2504.17033v2).
All code here is independently authored; no third-party algorithm code was copied.

## Verified paper contracts

| Mechanism | Requirement (2025 sections 2–3) |
|---|---|
| Degree reduction | Zero-weight vertex cycles preserve paths and bound in/out degree by two. |
| Labels | Order length, hop count, reversed vertex sequence; store predecessor-based ties. |
| BMSSP(l,B,S) | `|S| <= 2^(lt)`, labels below B, and complete-frontier coverage of incomplete vertices. |
| Completion | U=T_<B'(S) is complete; full B'=B or partial B'<B with workload Theta(k*2^(lt)). |
| BaseCase | Singleton complete source; bounded mini-Dijkstra stops at exhaustion or k+1 vertices. |
| FindPivots | k rounds; P subset S, W subset T_<B(S), size O(k*size(S)), size(P)<=size(W)/k. |
| Insert | Update a key/value, retaining the smaller value. |
| Pull | Extract up to M smallest keys and a separating boundary; exhaustion returns B. |
| BatchPrepend | Prepend keys below existing values, retaining minimum duplicates. |
| Recursion | Preserve coverage, monotone boundaries, disjoint completed child sets, and equality-valid edge reuse. |

Here T_<b(S) contains vertices below b whose selected shortest path visits S.
FindPivots does not promise all W complete: each relevant vertex is either complete
in W or covered by a complete pivot. BaseCase returns (B,U0) on exhaustion;
otherwise B'=max label in U0 and U contains only labels strictly below B'.
Use k=floor(log^(1/3)n), t=floor(log^(2/3)n), root level ceil(log(n)/t),
S={source}, B=infinity. Equality-valid relaxations must be reused across levels
(Remark 3.4); numeric strict-improvement alone is insufficient.

## Engineering implementation gates (not implemented research algorithms)

The CSR representation is usable for both original and transformed graphs; dense
indices are graph-local and are never original road IDs. Task 5 must add a separate
transformation object mapping transformed vertices to originals and each edge to
an optional original edge. Synthetic zero-weight edges need a distinct namespace;
path projection must remove them and verify the original directed sequence.
Isolated vertices stay explicit. Do not apply a source-reachability assumption to
unreachable application vertices without an explicit adapter.

Task 5 must introduce query-owned symbolic labels and bounds. Scalar distances in
the Dijkstra result are only an oracle interface. Pin the chosen tie policy to
section 2, including parallel-edge identity as an explicitly justified engineering
extension. Do not infer symbolic uniqueness from floating inequality. If binary64
collapses distinct path lengths, document the arithmetic model separately from
exact-real theoretical guarantees. Extend label/workspace types alongside existing
graph storage; changing storage is unnecessary.

Before adding recursive execution, specify typed bounded-call inputs and outputs,
parameter calculation (including tiny graphs), empty frontier behavior, and checked
level/workload arithmetic. Parameter powers must never rely on unchecked shifts.
Turn the coverage, return-set, and boundary obligations into small-graph oracle
checks. Source-completeness assumptions are proof obligations; they are not an
instruction to mark arbitrary frontier labels settled.

BaseCase needs its own bounded contract tests. The full-source Dijkstra function
must not be substituted as a BMSSP implementation. FindPivots needs explicit W/P
membership, tie-aware forest construction, early workload exit, and adversarial
fixtures. The frontier structure needs independent operation-sequence tests,
separating-boundary checks, duplicate-key handling, and amortized-work accounting.
Using a standard heap for everything cannot establish the desired complexity.

No degree transformation, symbolic label engine, BaseCase, FindPivots, specialized
frontier, bounded recursion, or BMSSP performance guarantee is delivered in Task 4.
The 2026 improvement is outside this implementation target. Existing Python/native
legacy code is preserved and is not evidence of any research mechanism.
