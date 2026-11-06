# Task 15 v1.2.0 — static diagnostic ordering amendment

These standard-library Python 3.11+ tools create and independently verify a
pre-data scheduling amendment. They implement no workers, profiler invocation,
calibration, graph/native loading, measurements or dispatcher. The existing
`research/task15_harness/` package, version 0.1.1 pinned to v1.1.0, is untouched.

## Authority and scientific choice

See the complete scientific comparison, 52-entry table, limitations and future
compatibility requirements in
[the v1.2.0 preregistration](../../docs/task15_tail_attribution_preregistration_v1.2.0.md).
The full protocol and ledger are versioned alongside it. SESSION_END preserves
session-filtered main order and each entry's conditions, then runs only that
session's assigned companions in original companion order. Neither fresh workers
nor late placement establishes timing neutrality. Stacks remain supplementary and
separate from ordinary A/B latency and timed C evidence. There is no new washout,
cooldown, retry, exclusion or source selection.

The historical global main source array interleaves assigned session labels.
Its bytes are unchanged. The inherited chronological main rule is filtering by
session before preserving that subsequence; requiring global source-array order
across chronological sessions would contradict the existing rule. Source-lane
indices in the resolved order retain both global and per-session provenance.

## Independent verification

`generate_amendment.py` copies the pinned v1.1.0 parent and deterministically emits
only the three v1.2.0 documents. Its nested session/lane walk constructs entries
and condition blocks. No seed or new experimental observation is used.
`validate_amendment.py` imports neither generator nor harness. It independently
joins original IDs to source metadata and stable-sorts by assigned session, lane
and original source index, then checks condition expansion and every field.
It also verifies canonical/file hashes, exact allowed parent projection, source
permutations, P2 balances, counts and all protected runtime/harness Git objects.
The new canonical and ledger identities are pinned in the static validator.

`test_amendment.py` contains classified negative mutations; most repair outer
hashes so semantic failures cannot be hidden by a stale digest. Compatibility is
checked by comparing all 138,696 structural jobs and query IDs with the unchanged
v1.1 harness: ordered jobs must be identical within each unit, primary unit order
must be identical, and only diagnostic cross-unit order adopts the amendment.
No native engine is imported. This is evidence of schedule compatibility, not
BMSSP correctness, performance, instrument eligibility or independent approval.

## Reproduction

Run from the repository root with an existing Python 3.11+ interpreter. No install,
package upgrade or network is required. `/NEW/EXTERNAL` denotes a new external
evidence destination whose parent exists; create its `regenerated` subdirectory
before generation. Paths shown here are examples.

```sh
python3 research/task15_ordering_v1_2/generate_amendment.py \
  --repo /Users/sallahuddin/Projects/BMSSP_Logistics_optimizer \
  --output-dir /NEW/EXTERNAL/regenerated
python3 research/task15_ordering_v1_2/validate_amendment.py \
  --repo /Users/sallahuddin/Projects/BMSSP_Logistics_optimizer \
  --docs /NEW/EXTERNAL/regenerated --output /NEW/EXTERNAL/regenerated-validation.json
python3 research/task15_ordering_v1_2/validate_amendment.py \
  --repo /Users/sallahuddin/Projects/BMSSP_Logistics_optimizer \
  --output /NEW/EXTERNAL/committed-validation.json
python3 -m unittest discover -s research/task15_ordering_v1_2 -p 'test_*.py' -v
PYTHONPATH=research/task15_harness python3 -m task15_harness self-test \
  --output /NEW/EXTERNAL/legacy-harness-tests
```

Generation refuses existing amendment filenames; validation result files use
exclusive creation. Compare regenerated document bytes with all three checked-in
v1.2.0 documents. Do not overwrite any historical protocol, ledger or evidence.
Read-only Git checks use controlled environment, disabled fsmonitor/hooks/external
diff/textconv, and protected-tree worktree checks; these are not general same-user
attack protection. The unsigned digests establish consistency, not authentication.

## Future harness locks and manifests

The protocol's `query_identity_policy` explicitly preserves the v1.1.0 identity
namespace. Do not replace that namespace with the new canonical hash when adapting
query IDs; carry the active v1.2.0 protocol hash as separate provenance. Unit IDs,
source ID strings, original positions and occurrence ordinals are unchanged.
Retain both original lanes for provenance and introduce the separately frozen
100-block resolved sequence for any later authorized scheduling implementation.

Future authorized adaptation must update loader version/files, protocol/parent/
ledger/Markdown constants, full historical-chain checks and closed schema; derive
new plan/source locks; adapt hash/ordering/compatibility tests; and create fresh
exclusive v1.2.0 manifests. Every old v1.1 manifest must fail as v1.2 authorization.
Even with the harness unchanged, manifests prepared at the parent repository
revision fail its repository-observation lock on the new amendment commit;
recompute observations rather than modifying historical manifests.

The current harness source lock and tree remain unchanged. A new protocol does not
silently repoint the loader or make old manifests execute anything. Independent
review is pending, signatures remain absent, and execution/promotion remain false.
All builds/G8/host/storage/calibration/authorization gates remain pending for a
separately authorized stage. STOP after amendment delivery.
