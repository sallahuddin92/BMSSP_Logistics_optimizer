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

## Implemented modules and evidence (Task 5)

| Mechanism | Module | Independent verification |
|---|---|---|
| Degree reduction and projection | `degree_reduction.cpp` | degree_reduction_tests; actual-query projection in bmssp_tests |
| Symbolic ordering | `symbolic_label.cpp` | symbolic_label_tests; independent full-vector Bellman-Ford order |
| BaseCase | `bmssp_bounded.cpp::base_case` | bounded_tests: full/partial, strict B, symbolic zero boundaries |
| FindPivots | `bmssp_bounded.cpp::find_pivots` | bounded_tests: early exit, reduction, membership, coverage |
| Lemma 3.3 strategy | `bounded_frontier.cpp` | ordered reference model, mixed operations, splits, duplicate minima |
| Algorithm 3 | `bmssp_bounded.cpp::run` | intermediate coverage/completion oracle, disjointness and monotone bounds |
| Full original-graph SSSP | `bmssp_2025.cpp` | Dijkstra, independent Bellman-Ford, exhaustive integer simple-path oracle |

All listed mechanisms are executable. The retained paper contract table above
is the research specification, not a claim that all machine costs match its model.
See [bmssp_2025.md](bmssp_2025.md) for snapshot ownership, parallel-edge refinement,
explicit stale-record Delete bookkeeping, original tight-tree projection, checked
parameters, IEEE limitations, and concrete complexity deviations. Source-rooted
completeness is a mathematical precondition checked independently on test traces;
it is not inferred by labeling every visited vertex complete.

The 2026 improvement is not mixed into this implementation. No third-party
algorithm code was copied, no undisclosed solver fallback is used, and production
Python/API integration is explicit and optional; see [native_python.md](native_python.md).
