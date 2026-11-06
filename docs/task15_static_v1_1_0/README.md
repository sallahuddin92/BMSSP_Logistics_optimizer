# Static Task 15 v1.1.0 tooling

These scripts never import or execute BMSSP. The generator reads frozen v1.0 and historical Task14 JSON; it writes a NEW external directory. The validator does not import generator code. It walks execution index -> original position -> source ID and checks independent invariants and deterministic construction.

`validate_protocol.py PROTOCOL --output NEW_JSON` performs strict local byte checks. `--portable` leaves external evidence explicitly UNVERIFIED. `--self-test` also runs ten in-memory corruption controls and dimensionless RNG/arithmetic fixtures, requiring the already installed NumPy1.24.4. No package installation is performed. `static_validation_results.json` is a static result snapshot, not benchmark evidence. Full original-file checks require the paths embedded in the frozen protocol; a Linux reviewer can verify schedule mathematics portably without claiming external hashes passed.

The generator and validator are independent of the future benchmark runner, which is NOT implemented or authorized. Preserve v1.0 files and original evidence. See the adjacent versioned protocol and amendment ledger for seeds, identities and unchanged acceptance gates.
