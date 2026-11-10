# Task15 v1.3 environment-provenance amendment

This narrow generator adds an identified CPython3.11.15/NumPy1.24.4 offline
reconstruction as a **TECHNICALLY_VERIFIED / SCIENTIFIC_ACCEPTANCE_PENDING**
candidate. It does not approve replacement, confirmatory analysis or execution.
The immediate scientific parent is v1.2; all earlier documents remain immutable.

Generate into a fresh external directory, never over existing documents:

```sh
python3 -B research/task15_environment_v1_3/generate_amendment.py --repo "$PWD" --evidence /Users/sallahuddin/Projects/BMSSP-task15-offline-reconstruction-jgt6c3vy --output /absolute/new/external/generated
python3 -B research/task15_environment_v1_3/validate_amendment.py --repo "$PWD" --output /absolute/new/external/verification.json
```

The generator authenticates the sealed reconstruction inventory/evidence,
binds actual bytes and uses the recorded fixed preparation timestamp for
reproducibility. The independent verifier imports neither generator nor harness.
Both operate without NumPy/native execution. The historical byte-identity and
publisher-authenticity limitations are explicit, not repaired by metadata claims.

The static harness0.3.0 consumes v1.3, plan3 and manifest3. Its former v1.2
loader is retained as `historical_v12.py` solely to validate the immutable
v1.0->v1.1->v1.2 chain. v1.2 manifest2 objects are historical and cannot be
silently upgraded. Scientific workload/query payloads and the v1.1 stable ID
namespace are unchanged; only active provenance and plan/manifest locks change.

Full oracle and synthetic environment checks are part of the separately
recorded phase evidence. No fixture expected values are regenerated, no runner
is implemented, and the A/B scheduling and G8 issues remain separate.
