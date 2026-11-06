# Proposed diagnostic cross-list ordering clarification

**PROPOSED ONLY — NOT ADOPTED. No change to protocol v1.1.0.**

The frozen main diagnostic list and allocator-stack companion list each have their
own order/session assignments. No cross-list interleaving rule is stated. This
control plane preserves them as two partial-order lanes. Its serialized main lane
followed by companion lane is a representation, not a newly prescribed experiment.
No execution dispatcher exists and no new randomized order was generated.

Before a future executable runner, independent review should determine whether a
cross-list rule is required. If needed, propose a versioned amendment explicitly
fixing companion placement relative to the main diagnostics within each assigned
session, with scientific rationale for temporal/allocator/cache comparability and
updated derived plan identities. Neither “append after each session” nor any other
option is adopted here. Original trial IDs, source order, controls and acceptance
thresholds remain frozen. Do not use a command flag to choose an interleaving after
seeing observations. This unresolved execution-order clarification does not prevent
static representation/verification of all specified work, but blocks treating this
partial plan as an independently approved executable schedule.
