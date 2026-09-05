# Standard installation and runtime evidence

The formal research MVP is the installed `hakimi-research` CLI. Runtime data,
snapshots, logs and reports belong in an independent user directory, selected
with the CLI output options or `HAKIMI_RESEARCH_HOME` (default
`~/.hakimi-research`). Importing modules or resolving the default directory does
not create it. Packaged example configuration, experiment specification and the
dependency lock are read-only resources under `hakimi_research/resources`.
The installed path does not need the repository's `outputs`, `examples`, archive,
or `configs` directories. The example describes inputs; it is not market data.

## Release acceptance

Run `python tools/verify_wheel.py` from the source checkout. For an offline
dependency installation, supply `--wheelhouse /path/to/exact/dependency/wheels`.
The build host requires a recent setuptools compatible with `pyproject.toml`.
The helper copies only current source and build inputs into a fresh staging
directory, builds a normal wheel, creates a fresh virtual environment without
system site packages, installs the exact dependency lock and the wheel, and runs
the console command and every root MVP test from an external directory.
`PYTHONPATH` and `PYTHONHOME` are removed from child processes. It writes a
`wheel-acceptance.json` receipt only after all checks pass. Temporary build,
environment and test evidence are retained at the printed location.

Editable installation and in-tree unit tests remain useful for development, but
do not satisfy this release gate. This gate verifies software behavior using
offline fixtures; it is not evidence of a real-market result or strategy merit.

## Evidence fields

Runtime evidence deliberately separates these observations:

| Field | Meaning |
| --- | --- |
| `dependency_lock` | Identity and exact-pin syntax of the lock bytes. |
| `environment_verified` | Actual installed distribution versions compared with every lock entry, plus Python support. `VERIFIED` is limited to this comparison. Missing packages, mismatches, invalid locks or unreadable metadata cannot pass. |
| `source_identity` | SHA-256 over a canonical map of the actual package Python, JSON and lock file bytes. A wheel carries a build receipt checked against the installed bytes; mismatch cannot be `BUILD_VERIFIED`, and an absent wheel receipt is separately `BUILD_MISSING`. This content identity includes uncommitted source changes. |
| `source_identity.git` | A separate runtime commit/worktree observation. Failure or timeout is `UNKNOWN`, never clean. A wheel has no runtime checkout. Its `build_receipt.git` preserves the original source checkout observation, bound to the staged and installed source byte identity. |
| `replay_verified` | Starts at `NOT_RUN`; hashing a result or checking dependencies never changes it to a successful replay. The runner must attach independently obtained replay evidence. |
| `statistical_status` | Starts at `NOT_ASSESSED`; software provenance does not imply sufficient sample size or strategy effectiveness. |
| `execution_permission` | Permanent research-only and account/order locks. |
| `machine_receipt` | Timestamp, platform, host, interpreter and installation location; these may differ across machines. |

The runner's portable computational result identity excludes the machine receipt.
Two reports can therefore have the same computational result and different
complete-report hashes. Source content identities and environment observations
should be compared separately when interpreting a replay.

## Atomic report persistence

Reports are serialized completely, written to a unique hidden staging file in
the destination directory, flushed and verified, then published with an atomic
hard link that refuses to replace an existing name. Identical bytes are an
idempotent retry. Different bytes for the same artifact name raise an error and
leave the old evidence intact. Filesystems without hard-link support fail closed.

An interruption before publication can leave a hidden `.staging-*.tmp` file;
it cannot leave a partial final JSON report. Readers should only discover final
`.json` artifacts, never staging files. A retry uses a new staging file and does
not require deleting the abandoned file. The implementation makes no promise of
Windows durability across hardware or power failure. Behavior tests cover
concurrent equal/different writes, process interruption, write/flush/publish
failures, invalid input and retry without evidence replacement.

Old reports and synthetic references are not regenerated or overwritten by these
changes. Legacy manifest verification is retained for historical references;
the formal runner exposes the separate runtime evidence above.
