# The Resampling Null — NeurIPS 2026 Study Design

**Status:** selected submission-primary design; zero-spend local implementation
authorized; currency-bearing provider execution remains hash-gated

**Branch:** `codex/neurips-2026-empirical`

**Date:** 2026-07-28

**Internal deadline:** 2026-08-28; venue deadline 2026-08-29 23:59 AoE

## 1. Decision

The submission-primary study is:

> **The Resampling Null: Did Verification Help, or Did the Agent Just Get
> Another Try?**

It will test whether task-specific verifier feedback causally improves a frozen
tool agent beyond:

1. ordinary continuation without feedback;
2. an independent continuation from the same state;
3. a verifier-shaped but task-mismatched sham packet; and
4. the finite-sample resolution floor induced by stochastic decoding.

The empirical study uses two materially different open, objective environments:

- repository repair from SWE-bench-Live MultiLang; and
- stateful conversational/API work from the objective text subset of
  `tau2-bench` v1.0.1, referred to by the benchmark authors as τ³-bench.

The frozen primary subject is the official open-weight
`Qwen/Qwen3.6-35B-A3B-FP8`. A BF16 run is a distinct subject and may be used
only as a separately reported precision/provider replication.

This design supersedes the G1 gauge paper only as the submission-primary
workstream. It does not alter G1's results, revive the sealed Protocol-v2
program, or weaken any previous no-go.

## 2. Why this program

Three candidate programs were scored before implementation. Scores are out of
100 and use the weights in the header.

| candidate | novelty 25 | identification 25 | venue fit 15 | Aug-29 feasibility 15 | power / breadth 10 | artifact value 10 | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frontier replication of G1 gauge cards | 13 | 19 | 11 | 14 | 7 | 9 | 73 |
| Generic four-arm standard across unrelated interventions | 18 | 22 | 13 | 10 | 8 | 8 | 79 |
| Verification-feedback assay with a measured resampling null | 23 | 24 | 15 | 11 | 8 | 9 | **90** |

The first option is feasible but would remain a measurement-reliability paper
with a frontier-generalization patch. The second has breadth but risks becoming
a benchmark collection without one decisive estimand. The selected option has
one intervention, one causal decomposition, direct workshop fit, and two
objective domains.

The generic novelty claim is retired. Three 2026 papers already test placebo,
shape-matched, or compute-matched controls in small code repair, and recent
agent-evaluation work already studies repeated trials, paired noise floors, and
harness variance. The open claim is narrower and stronger:

> For frontier-capable, long-horizon tool agents, can correct task-specific
> verifier evidence be distinguished from a plausible mismatched report and a
> pooled two-replicate no-feedback continuation, while quantifying post-trigger
> seed sensitivity under exact state branching?

The literature audit that forced this narrowing is retained under
`build/research/neurips-2026-workshop/last30days/`.

## 3. Claims and non-claims

### 3.1 Claim of record

The strongest admissible positive claim is:

> On one frozen open-weight subject across two objective tool-agent settings,
> true verifier feedback produced a task-level success gain that cleared a
> verifier-shaped mismatched-report sham and the pooled two-replicate
> no-feedback condition, while the paired no-feedback branches established an
> admissible post-trigger resolution scale.

That claim requires every gate in section 9. A positive point estimate alone is
not enough.

### 3.2 Contributions

1. A four-arm, snapshot-paired causal protocol separating correct task-specific
   feedback from a mismatched-report control and pooled no-feedback
   continuation, while measuring post-trigger continuation gain and seed
   sensitivity.
2. A resampling-null resolution test that turns post-trigger continuation
   variation into an observed control distribution rather than an assumed zero.
3. A cross-setting empirical application to repository repair and stateful
   tool/API work with objective endpoint graders.
4. A lineage-aware, arm-blind artifact and inference contract that can be reused
   by agent benchmark authors.
5. If API credits become eligible, a secondary measurement audit asking whether
   blinded LLM judges recover the same causal verdict as objective graders.

### 3.3 Explicit non-claims

- This is not proof that verification generally helps every model or scaffold.
- It does not identify the effect of a human expert verifier.
- It does not call sham feedback semantically inert; its purpose is to isolate
  correct/task-relevant feedback from a plausible mismatched report.
- No four-arm contrast identifies packet form alone. A pure apparatus estimand
  would require a fifth neutral-format arm and is outside this study.
- It does not treat seeds, trajectories, issues from one repository, or telecom
  permutations as independent scientific units.
- It does not claim exact prompt-token equality between packet and no-packet
  arms. REAL and SHAM are token-matched; the packet/no-packet difference is the
  required sham-packet decomposition, not a pure apparatus estimand.
- It does not import the legacy scorer, modify 9to5, train model weights, or
  establish phenomenal consciousness.

## 4. Frozen external subjects

All revisions below are immutable inputs. A later upstream change creates a new
experimental subject and cannot be pooled silently.

### 4.0 Canonical derivation frame and three-commitment ceremony

Every commitment, seed derivation, HMAC ranking, assignment draw, capability,
and unblind permit uses one typed binary frame. No KDF input may use formatted
strings, delimiter concatenation, canonical JSON, or an implementation-defined
integer encoding.

```text
MAGIC = ASCII("pneuma-resampling-null-frame-v1") || 0x00

FRAME(tag, fields) =
      MAGIC
    || UINT32_BE(len(UTF8(tag))) || UTF8(tag)
    || UINT32_BE(number_of_fields)
    || concat(
           UINT8(type)
        || UINT32_BE(len(payload))
        || payload
       )

type 0x01 U64   : payload = UINT64_BE(value)
type 0x02 TEXT  : payload = UTF8(value)
type 0x03 BYTES : payload = the exact bytes
```

`U64` accepts an object whose exact type is integer, rejects booleans, and
requires `0 <= value <= 2^64 - 1`. A tag or `TEXT` value must be a non-empty
Python string already equal to its NFC normalization. It is encoded with strict
UTF-8 and rejects every Unicode `C*` general category, including controls,
format controls, private-use/unassigned code points, and lone surrogates. A tag,
text value, bytes value, or field count that cannot fit its unsigned 32-bit
length/count fails closed. Lowercase hexadecimal SHA-256 values are decoded to
32 raw bytes before entering a `BYTES` field. The frozen Python and Unicode
database versions are part of the runtime receipt.

The following known-answer vectors are normative:

```text
FRAME(
  "derive-seed-v1",
  [U64(7), TEXT("task-1"), TEXT("prefix")]
).hex =
706e65756d612d726573616d706c696e672d6e756c6c2d6672616d652d7631000000000e6465726976652d736565642d7631000000030100000008000000000000000702000000067461736b2d310200000006707265666978

SHA256(frame) =
d0f92ef02cc64124ae8d651ad65c1f799f94fac4bd9923804cefbec2928cb327

UINT64_FROM_BE(SHA256(frame)[0:8]) =
15058118438168183076

SHA256(FRAME(
  "commitment-v1",
  [TEXT("schedule-seed"), TEXT("kat-study"), U64(7)]
)) =
9bc37b258cc847128e49ed05681652da344723220886ec59193e53a1c8577760
```

Before roster ranking and before any prefix execution, the ceremony creates
three independently sampled values with `secrets.token_bytes`—32 bytes, eight
bytes interpreted as `UINT64_BE`, and 32 bytes—and three non-interchangeable
commitments:

| value | exact representation | commitment label | reveal/use contract |
| --- | --- | --- | --- |
| roster local nonce | 32 random bytes named `roster_local_nonce` | `roster-local-nonce` | the externally timestamped precommit precedes the public beacon; the eligibility manifest later reveals the nonce and proves the final roster seed derived from it and the authenticated beacon |
| schedule seed | one `U64` | `schedule-seed` | commitment is copied into the study manifest; schedule sealing reveals the integer and verifies it before deriving task/prefix/slot/order seeds |
| assignment master key | 32 random bytes | `assignment-master-key` | commitment is copied into the study manifest; only the trusted post-prefix assignment and unblind processes may read the key and verify it in memory |

For representation `V`, each commitment is:

```text
SHA256(FRAME(
    "commitment-v1",
    [TEXT(label), TEXT(study_id), V],
))
```

One canonical precommit binds the study ID, qualification-universe digest,
future beacon chain/round, and all three commitment digests:
`roster_local_nonce_commitment_sha256`,
`schedule_seed_commitment_sha256`, and
`assignment_master_key_commitment_sha256`. That exact precommit is externally
timestamped before the target beacon. Once timestamped, there is no replacement
nonce, commitment set, or beacon round.

The eligibility manifest binds its study ID, precommit and timestamp receipts,
authenticated beacon receipt, roster-local-nonce reveal receipt, final
`roster_seed`, complete accepted/rejected set, nested C120/C160 membership,
ordered reserves, group labels, and the roster bytes those fields produce. The
final seed used by the unchanged roster-ranking HMACs is:

```text
roster_seed = SHA256(FRAME(
    "roster-seed-v1",
    [
        BYTES(precommit_sha256),
        BYTES(roster_local_nonce),
        BYTES(beacon_chain_hash),
        U64(beacon_round),
        BYTES(beacon_randomness),
    ],
))
```

The eligibility manifest is a pre-study canonical source blob and contains no
study-manifest ArtifactRef, avoiding a reference cycle. For
`roster_kind = "eligible_confirmation"`, study sealing verifies that blob,
copies it under the run root, and requires a non-null
`eligibility_manifest_ref` to the exact copy. For
`roster_kind = "synthetic_fixture"`, the same manifest field is required to be
null and an eligibility source is forbidden. The study manifest independently
binds `roster_local_nonce_commitment_sha256`,
`schedule_seed_commitment_sha256`, and
`assignment_master_key_commitment_sha256`; one generic `seed_commitment` field
is forbidden. A reveal with the wrong representation, label, study ID, length,
commitment, precommit, or beacon receipt stops the transaction.

The beacon authority is drand default mainnet: chain hash
`8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce`,
scheme `pedersen-bls-chained`, group hash
`176f93498eac9ca337150b46d21dd58673ea4e3581185f869672e59fa4cb390a`,
genesis Unix time `1595431050`, and 30-second period. Round 1's normative
known-answer randomness is
`101297f1ca7dc44ef6088d94ad5fb7ba03455dc33d53ddb412bbc4564ed986ec`.
Verification uses official `drand-client` 1.4.2: package tar SHA-256
`81de34afba38520b461152bf032cfb5139bb6ced205bf9f50bc8216fdc394eef`,
integrity
`sha512-jeNJmrVplfgIA/GVndxxJ5mo8y63BS2pEdNhk1siU4pQ+z/BnxsqRnxjH9ag1ip887s12SEgo0MTZPbQNz27NA==`,
source commit `ef8c9260294f8699b5e8c27a6b764f8f0d768bea`, and extracted bundled
CJS SHA-256
`45cb65d533cc7e8527e9bba92df875c066511c3d6286adc7fcb293f0d03c7566`.

The precommit anchor is a cryptographically verified Sigstore bundle v0.3 with
exactly one RFC3161 timestamp and exactly one Rekor inclusion proof. Chronology
uses the verified TSA `genTime`, never Rekor `integratedTime`. The target round
must begin at least 24 hours after that `genTime`; approximately 48 hours
(`+5760` rounds) is preferred. Cosign is pinned to v3.1.2 Windows x64 SHA-256
`fe4d621d7ae5e900ee62089837c00f996ae9acb82027d573d1d157b6ee875cb2`
with companion Sigstore JSON SHA-256
`e8d7ea5dd91902b0c23e68a08136d9c43b3573a4974fdbdc89ba5a6890a4ab8b`.
Ceremony commands must be checked against the installed version before use;
remembered command syntax is not authority.

The assignment process verifies the 32-byte master key and derives exactly five
32-byte subkeys with RFC 5869 HKDF-SHA256:

```text
context = FRAME(
    "assignment-context-v1",
    [
        TEXT(study_id),
        BYTES(manifest_sha256),
        BYTES(schedule_sha256),
    ],
)

PRK = HKDF-Extract(
    salt = SHA256(context),
    IKM = assignment_master_key,
)

K_label = HKDF-Expand(
    PRK,
    info = FRAME("assignment-subkey-v1", [TEXT(label)]),
    L = 32,
)

label in {
    "donor",
    "allocation",
    "orientation",
    "capability",
    "unblind",
}
```

For HKDF-Expand at `L = 32`, the one RFC 5869 block is
`HMAC-SHA256(PRK, info || 0x01)`. With study ID `kat-study`, master key
containing the 32 consecutive bytes `0x00` through `0x1f`, manifest digest
`0x11` repeated 32 times, and schedule digest `0x22` repeated 32 times, the
normative subkeys are:

```text
donor      ba38f59248c6fddad640c1a047ee1ecf38a0420cc1546d2370f1b6534dc16517
allocation 225e87f89450b1297025d2de9c5871785fba25ec1c4c8ea2dc3b1cc0dbaffc29
orientation 1e69be341abf917e55156c95157c69fe70d3f0cd1d161fa6fbd11e189a8d6cf3
capability 64e481fc16011d95a1bdff96b43c5fbfc2c49df0b8203f56fca38e4a6fc8266a
unblind    19fd5926965155e44bc23ea0b2d804c7a1492a98183389e515eafb4b05290f6d
```

Neither the assignment master key nor any derived subkey may appear as an argv
value, environment variable, run-root file, scientific/operational record,
exception, log, telemetry event, worker input, or packet capability. A CLI may
receive only the path to an owner-only-readable key file outside the run root.
The trusted process opens it unbuffered, preallocates `bytearray(32)`, performs
one exact `readinto`, rejects a short read, attempts a one-byte `readinto` and
rejects extra data, and never copies the file. Workers receive only per-slot
opaque capability IDs; the already-frozen whole-block rerun contract may
replay the same work-order capability but cannot mint a replacement.

No public transaction accepts master/subkey bytes or a caller-implemented
secret source. The concrete trusted-controller `AssignmentSecretStore` is the
only component that opens the owner-only master-key file. It binds the already
open OS file identity plus manifest, schedule, run-root, and purpose into its
private registry, then mints a nominal, non-subclassable, purpose-scoped,
single-use `AssignmentSecretHandle` or `UnblindSecretHandle`. The store does
not read or validate key bytes, verify a commitment/context, derive a subkey,
or return a commitment verdict. Registry membership and unused state are
checked again at consumption; copied, stale, wrong-purpose, cross-context, or
reused handles reject.

At handle consumption, trusted core code independently fills that preallocated
master buffer, verifies the assignment-master-key commitment and exact
manifest/schedule HKDF context, and only then derives the purpose-appropriate
keys into private mutable application buffers. There is no public/frozen key
wrapper and no key-returning API. Assignment and confirmation verification
consume separately minted assignment handles and derive only `K_donor`,
`K_allocation`, `K_orientation`, and `K_capability`. Unblinding consumes an
unblind handle and derives only `K_unblind` long enough to recompute the framed
permit HMAC before parsing the clear assignment ledger. Handles expose neither
the master key nor any subkey, and no core scope derives all five subkeys.

One outer `finally` overwrites every application-owned master, subkey, overread,
and mutable transient buffer before closing the handle on every success and
failure path. Tests retain private references and verify all-zero contents
after normal completion and exceptions injected at read, commitment,
derivation, draw, verification, and publication boundaries. This is a
minimization guarantee for buffers the application owns, not a process-memory
erasure claim: Python's allocator/interpreter and `hmac`/`hashlib`/OpenSSL may
make immutable or internal copies that Python cannot reliably locate or scrub.
No such key material is intentionally persisted, serialized, logged, returned,
or placed in argv/environment. These entry points accept no generic secret
callback, caller-implemented key store, `PermitVerifier`, or lookalike handle;
an object whose `verify()` may be a no-op is not an authority boundary.

For all bounded draws:

```text
UNIFORM_BELOW(key, message_frame, upper):
    require type(upper) is int
    require 1 <= upper <= 2^64
    require len(key) == 32
    limit = 2^64 - (2^64 mod upper)
    for counter in 0 .. 2^64 - 1:
        digest = HMAC-SHA256(
            key,
            FRAME(
                "uniform-below-v1",
                [BYTES(message_frame), U64(counter)],
            ),
        )
        value = UINT64_FROM_BE(digest[0:8])
        if value < limit:
            return (value mod upper, counter)
    fail closed
```

For every admissible `upper`, rejection sampling gives every result exactly
`floor(2^64 / upper)` accepted 64-bit preimages. `upper > 2^64`, zero,
negative, a boolean, or any non-integer is rejected before the loop. In the
known-answer context above,
`UNIFORM_BELOW(K_allocation, FRAME("allocation-v1",
[TEXT("task-1")]), 12)` returns `(3, 0)`, and
`UNIFORM_BELOW(K_orientation, FRAME("orientation-v1",
[TEXT("task-1")]), 2)` returns `(0, 0)`.

### 4.1 SWE-bench-Live MultiLang

- Harness: `microsoft/SWE-bench-Live`
  `70ec57e852e3f2d195790fe71f553e272c691833`.
- Dataset: `SWE-bench-Live/MultiLang`
  `608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b`.
- Required RepoLaunch runtime/submodule:
  `microsoft/RepoLaunch`
  `7735b1e7363dd3bbc69bd0ef80db646a2ae391fd`.
- Dataset surface at that revision: 743 tasks, 381 literal repository strings,
  380 current GitHub repository IDs, one dataset configuration, and eight
  language splits. `vmware-tanzu/velero` and `velero-io/velero` resolve to one
  GitHub repository and therefore one root lineage; six other dataset names
  currently redirect after repository renames.
- License: harness, dataset, and RepoLaunch metadata are MIT. That does not
  license the 381 upstream repositories, their historical base commits, or
  their container contents. Every candidate must pass the base-commit license
  audit below.
- Primary endpoint: all registered `FAIL_TO_PASS` and `PASS_TO_PASS` checks pass
  with exact complete observation in a clean endpoint image. Missing, skipped,
  unparsed, or duplicate registered checks fail closed.

The current GitHub `isArchived` plus SPDX
`{MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Zlib}` scan is a diagnostic
proxy, not an eligibility result:

| split | tasks | literal repositories | proxy tasks | proxy root lineages |
| --- | ---: | ---: | ---: | ---: |
| C | 37 | 20 | 24 | 9 |
| C++ | 74 | 30 | 18 | 14 |
| C# | 87 | 32 | 75 | 26 |
| Go | 138 | 92 | 123 | 77 |
| Java | 109 | 60 | 85 | 44 |
| JavaScript | 93 | 43 | 78 | 35 |
| Rust | 94 | 41 | 73 | 28 |
| TypeScript | 111 | 63 | 78 | 45 |
| **total** | **743** | **381** | **554** | **278** |

Four repositories are currently archived. Current archive, rename, fork, or
license metadata never substitutes for evidence at the task's base commit.
There is no strict post-2026 task cutoff: a date-only filter leaves five
distinct C repositories and cannot support either tier. Contamination risk is
reported and bounded through public-artifact disclosure, lineage/date
sensitivities, and exact base-commit provenance rather than a fictional cutoff.
The harness environment also leaves material dependencies unpinned and carries
RepoLaunch as a submodule. The adapter manifest must resolve and hash a complete
dependency lock and the RepoLaunch commit above; a top-level harness commit
alone is not a runnable-environment receipt.

Eligible tasks must:

1. come from a non-archived repository with an unambiguous permissive
   MIT/Apache/BSD/ISC/Zlib-class license at the task's base commit;
2. resolve its official image to an immutable OCI
   `linux/amd64@sha256:<digest>` manifest/config/layer set and mirror those
   bytes provider-locally; all 743 upstream image references are currently
   untagged and digest-free, so the raw references are ineligible;
3. run in the hardened adapter with networking disabled, no credential,
   provider metadata, host-gateway, Docker-socket, or mutable host mount, and a
   separately isolated public `log_parser`; the official controller-side
   Python `exec` path is forbidden;
4. pass three independent fresh base/gold container pairs. In every pair, test
   and gold patches apply cleanly, the base reports at least one registered
   `FAIL_TO_PASS` failure, and gold reports every registered `FAIL_TO_PASS` and
   `PASS_TO_PASS` check exactly once as pass, with successful patch and test
   command exits;
5. produce identical parsed outcomes across all three pairs without external
   services, credentials, accelerators, parser escape, timeout, or resource
   exhaustion. The official same-container three-gold loop is not this gate;
6. pass roster-measured CPU, memory, disk, and timeout admission. The official
   hard-coded four CPU/16 GiB runtime is not inherited because some C++ tasks
   require about 50 GiB;
7. bind the complete row hash, base commit/tree, issue/PR IDs, date, image
   digests, parser/command/F2P/P2P digests, and license evidence; and
8. contribute at most one task per canonical root repository/mirrored-tree
   lineage to a confirmatory roster.

The minimum `C120` confirmation roster keeps the fixed allocation
9 C, 14 C++, 16 C#, 17 Go, 16 Java, 16 JavaScript, 16 Rust, and 16 TypeScript.
The current metadata proxy has zero confirmation-lineage slack in C and C++;
the disjoint pilot needs two additional root lineages per split. Even with zero
fixed reserves, C120 therefore needs at least 11 qualified C and 16 qualified
C++ lineages, while the proxy has 9 and 14. `C120` is currently
`FEASIBILITY_NO_GO`, not merely fragile. It becomes conditionally feasible only
if the full base-commit, image, isolation, and three-pair audit yields, for
every split `s`,
`eligible_s >= C120_quota_s + 2 pilot_s + fixed_reserve_s`.

`C160` is presently `FEASIBILITY_NO_GO`: the current proxy has only nine C
lineages. It becomes eligible for roster construction only if the base-commit
audit leaves enough confirmation candidates after two pilots and the
manifest-fixed reserve count in every split. The confirmation allocator then
assigns 12 per split and distributes the remaining 64 places by Hamilton
largest remainder over each split's post-pilot, post-reserve
`eligible_lineages - 12`, breaking ties by canonical split order
`C, C++, C#, Go, Java, JavaScript, Rust, TypeScript`. The final gate is
`eligible_s >= C160_quota_s + 2 pilot_s + fixed_reserve_s` for every split;
before Hamilton assigns any extra C places, C alone therefore needs at least
14 qualified lineages plus its fixed reserves.

The SWE eligibility manifest freezes every accepted and rejected row before
the draw. Within a split, the ranking key is:

```text
HMAC-SHA256(
    roster_seed,
    FRAME(
        "swe-roster-rank-v1",
        [
            TEXT(dataset_revision),
            TEXT(split),
            TEXT(root_lineage_id),
            TEXT(instance_id),
            BYTES(canonical_task_record_sha256),
        ],
    ),
)
```

The manifest freezes `fixed_reserve_s` for every split before tier selection;
that count may be zero but cannot be inferred from later failures. The 16
pilots, nested C120 membership, possible C160 extensions, fixed reserves, and
the order of every remaining eligible lineage are materialized and sealed in
one transaction. Subject outcomes, pilot efficacy, grader outcomes, or branch
failures can never replace a task. An execution failure is an adverse outcome
or a predeclared whole-tier no-go, not a roster redraw.

### 4.2 τ³-bench objective text subset

- Repository: `sierra-research/tau2-bench`.
- Annotated tag: `v1.0.1`; tag object
  `b711c1ead46f55111bf765cf44d5da8bacc2d28c`.
- Peeled commit:
  `fc0055dc4e0a316c3f83133267fbd6faaa770992`.
- License: MIT.
- Python contract: `>=3.12,<3.14`.
- Packaging caveat: `pyproject.toml` declares `1.0.1`, while the editable
  `tau2` entry in the pinned `uv.lock` still declares `1.0.0`. Commit, tag
  object, source blobs, lockfile blob, environment image, and installed
  dependency receipts are authoritative; an installed package version string
  alone is not.

The pinned data contain these objective components:

| domain / stratum | pinned tasks | confirmatory tasks | reward basis |
| --- | ---: | ---: | --- |
| airline | 50 | 50 | all `DB + COMMUNICATE` |
| telecom `mms_issue` base | 49 | 49 | all `ENV_ASSERTION` |
| telecom `mobile_data_issue` base | 36 | 36 | all `ENV_ASSERTION` |
| telecom `service_issue` base | 29 | 29 | 20 `ACTION + ENV_ASSERTION`; 9 `ENV_ASSERTION` |
| banking knowledge | 97 | 88 | 88 `DB`; 9 `ACTION` excluded |

Retail is excluded because 112 of 114 tasks depend on an LLM
`NL_ASSERTION`. Voice mode and API-backed retrieval are excluded. Telecom's
`tasks.json` contains 2,285 generated tasks; the 114-task base is obtained only
by exact membership in `split_tasks.json["base"]`, with uniqueness and the
49/36/29 family counts asserted. The pinned objective data pool is 261 task
definitions. The confirmatory pool is **252** after excluding the nine
banking `ACTION`-only tasks because the official action matcher ignores
requestor and can accept a predicted call that omits expected argument keys.

The primary τ³ endpoint is frozen to:

```text
evaluation_type = EvaluationType.ALL
mode = CommunicationMode.HALF_DUPLEX
strict_replay = True
evaluator_network_call_count = 0
```

`ALL_WITH_NL_ASSERTIONS`, `ALL_IGNORE_BASIS`, and every LLM evaluator are
forbidden. The primary reports the official v1.0.1 result, including the 20
unavoidable telecom `ACTION + ENV_ASSERTION` tasks. A separately frozen strict
integrity secondary is requestor-aware and requires a one-to-one match on
action name plus exact canonical argument-dictionary equality, with no missing
or extra keys; it never changes the official primary reward.

The preferred `C160` roster contains 44 airline, 58 telecom, and 58 banking
tasks. The `C120` roster contains 40 from each domain. A domain-stratified
deterministic HMAC chooses tasks. The nine τ³ pilots are three per domain and
disjoint from confirmation and reserves. Telecom pilots are exactly one
`mms_issue`, one `mobile_data_issue`, and one `service_issue`; the service
pilot is drawn from `ACTION + ENV_ASSERTION` so the official and strict action
paths are exercised before confirmation.

The nested telecom confirmation quotas are:

| tier | `mms_issue` | `mobile_data_issue` | `service_issue` | service component split |
| --- | ---: | ---: | ---: | --- |
| C120 | 17 | 13 | 10 | 7 `ACTION + ENV_ASSERTION`; 3 `ENV_ASSERTION` |
| C160 | 25 | 18 | 15 | 10 `ACTION + ENV_ASSERTION`; 5 `ENV_ASSERTION` |

C120 is roster-feasible if its qualification gates pass. C160 is eligible only
if at least 47 airline tasks qualify across its three pilots and 44
confirmation tasks and the manifest contains at most three ordered airline
reserves. A fourth required airline reserve or more than three airline
qualification losses records `FEASIBILITY_NO_GO` for C160; it never triggers a
post-outcome redraw.

Banking uses exactly `retrieval_variant="bm25"`, `top_k=10`,
`rank-bm25==0.2.2`, `numpy==2.3.5`, the pinned
`classic_rag_bm25_no_grep.md` at Git blob
`c6931d1a5eb1db4652f6084e13102fbe457cb3f3`, and no reranker, grep, dense
embedding, shell, API, sandbox, or `golden_retrieval`. The adapter loads the
698 pinned documents from Git tree
`3b9506137142d433153e001ce9d40c6f7c28a527` only after rejecting duplicate
IDs, orders them by canonical UTF-8 document ID, and resolves tied scores by
`(-score, document_id)`. It disables or content-keys the upstream global
document cache and seals the ordered-document digest. Model-visible search
results replace retrieval, post-processing, and total wall-time fields with one
frozen constant; raw timings remain out-of-band telemetry.

The user simulator is a frozen, locally served
`Qwen/Qwen3.5-9B` at
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`, greedy decoding, with prompt,
chat template, tool schema, global guideline, persona configuration, turn cap,
and per-call seed recorded. The controller calls the local server directly;
the upstream run-level `UserSimulator` seed and LiteLLM `drop_params` path are
not used. For role `user_simulator` and zero-based call index `k`, the server
seed uses the same controller-wide frame as the primary subject:

```text
seed_k = UINT64_FROM_BE(SHA256(FRAME(
    "call-seed-v1",
    [
        U64(slot_or_prefix_root_seed),
        TEXT("user_simulator"),
        U64(k),
    ],
))[0:8])
```

The root seed was derived from the schedule seed, controller task ID, and
prefix/slot role; the receipt binds the exact schedule digest. The root seed
and `k` must be in `[0, 2^64)`. The frame's strict text and length rules apply
before a model call. No decimal stringification, alternate normalization, or
delimiter-based concatenation is permitted.

The persisted receipt binds call index, input token IDs, seed, output token
IDs, tool-call bytes, model/tokenizer/template/prompt/tool-schema/container
digests, and state-before/state-after digests. A cold-process, cold-model-server
duplicate fixture must be byte-identical; a server that ignores the seed or
changes token IDs is a no-go. This differs from the official frontier
user-simulator setting and must be described as an internal, fully
reproducible objective setting rather than leaderboard parity.

The telecom adapter replaces the latent
`B{uuid.uuid4().hex[:8]}` draft-bill path with a deterministic
task/branch-local counter keyed by the frozen environment seed. Predicted and
gold replay receive the same generator implementation and receipt. The
official gold paths currently avoid the UUID branch because all 50 base
`refuel_data` actions target `C1001/L1002`, whose customer has draft bill
`B1003`; off-policy subject calls can reach it, so leaving the random path
latent is forbidden.

Before roster selection, every τ³ candidate must pass all of:

1. canonical task/schema parsing and the exact revision/blob/count assertions;
2. confirmatory reward-basis membership, no `NL_ASSERTION` basis, half-duplex
   text mode, and banking `DB`-only exclusion;
3. fresh environment reset, clone, snapshot, and restore byte equality;
4. official gold endpoint `1` and identical component output in three fresh
   processes under `ALL`, half-duplex, strict replay, and zero evaluator
   network calls;
5. requestor-aware strict-action secondary fixtures for telecom service tasks;
6. cold-process BM25 index/query byte equality, explicit tie fixtures, timing
   sanitization, and no unkeyed-cache reuse;
7. cold-start local simulator byte equality with accepted seed receipts;
8. off-policy tool fuzz proving deterministic telecom ID creation and complete
   environment replay;
9. a leakage audit proving description, ticket, task ID, evaluation criteria,
   gold actions/arguments, assertions/expected values, required documents,
   target DB state/hash, and issue notes remain controller-only; and
10. measured memory, disk, context, output-token, and wall-cap admission.

The τ³ eligibility manifest binds every accepted/rejected canonical task and
qualification receipt. Within each `(domain, issue_family_or_none,
reward_basis)` stratum, rank by:

```text
HMAC-SHA256(
    roster_seed,
    FRAME(
        "tau3-roster-rank-v1",
        [
            TEXT(peeled_commit),
            TEXT(domain),
            TEXT(issue_family_or_none),
            BYTES(FRAME(
                "tau3-reward-basis-set-v1",
                [TEXT(value) for value in sorted_reward_basis],
            )),
            TEXT(controller_task_id),
            BYTES(canonical_task_record_sha256),
        ],
    ),
)
```

The roster-local-nonce commitment, externally timestamped three-commitment
precommit, authenticated beacon receipt, and eligibility-manifest preimage hash
are sealed before the draw.
Pilots, nested C120 prefixes, C160 extensions, and all ordered reserves freeze
simultaneously. Controller task IDs—especially telecom IDs, which encode the
fault—never enter subject/simulator prompts, worker environment variables, or
artifact paths; workers receive opaque HMAC unit IDs. No subject, pilot, branch,
or endpoint outcome can cause replacement.

After the draw, the canonical eligibility manifest and its derived
`eligible_confirmation` roster must exist before study sealing. Study sealing
copies both and proves their accepted-set, tier, reserve, group, commitment, and
reveal equality. A post-seal alternate eligibility file has no authority: it is
not reachable from the study manifest and cannot be substituted into power or
schedule transactions.

The simulator is a separately metered serving subject. On AWS, the default
`g6e.12xlarge` schedule reserves one L40S for the 9B simulator during τ³ work,
leaving at most three one-GPU primary replicas; a separate `g6.xlarge` L4 is the
predeclared substitute. On Azure, τ³ replication requires an additional
`Standard_NV36ads_A10_v5` simulator node. If that node is not eligible or
available, the BF16 replication is SWE-only; simulator compute is never
hand-waved as free or replaced with precomputed interaction-dependent replies.

### 4.3 Model subject and serving stack

Primary model:

- `Qwen/Qwen3.6-35B-A3B-FP8`;
- Hugging Face revision
  `95a723d08a9490559dae23d0cff1d9466213d989`;
- Apache 2.0;
- official block-wise FP8 checkpoint;
- text-only, thinking-mode tool use;
- `vllm==0.19.0` candidate serving package;
- `--language-model-only`;
- `--reasoning-parser qwen3`;
- `--enable-auto-tool-choice`;
- `--tool-call-parser qwen3_coder`;
- multi-token/speculative decoding disabled;
- prefix caching disabled for the study unless the parity pilot proves
  byte-identical responses under the frozen seed contract.

The container image, CUDA, driver, PyTorch, vLLM source/wheel digest, tokenizer,
chat template, tool parser, packet template, packet normalization/truncation
policy, and neutral pad-unit set are frozen after a no-cost or bounded parity
test. Their byte-level references are sealed in the study manifest before
packet construction. A package version without an image/source digest is not a
reproducibility receipt.

The topology and context cap are deliberately not frozen before the memory
pilot. The official FP8 blobs occupy about 34.9 GiB, leaving a tight margin on a
48 GiB L40S. The predeclared ladder is:

1. L40S tensor parallelism 1 at 32,768 tokens;
2. L40S tensor parallelism 1 at 65,536 tokens;
3. two L40S GPUs with tensor parallelism 2 at 65,536 tokens; then
4. H100 94 GB tensor parallelism 1 at the largest validated cap not exceeding
   131,072 tokens.

The largest candidate that passes OOM, tool-call, output-parity, and p10
throughput gates is frozen before confirmation. A topology change is a subject
change because it can change kernels and numerics. BF16 contains about 67.0 GiB
of weight blobs and therefore defaults to Azure
`Standard_NC48ads_A100_v4`, two A100 80 GB GPUs with tensor parallelism 2.
Single-A100 BF16 is allowed only if a realistic-context OOM and byte-parity
pilot passes; it is not the planning assumption.

Seeded online serving is not assumed reproducible. Tier 1 tests
`VLLM_BATCH_INVARIANT=1` with fixed request order, concurrency, topology, and
per-call seeds. The gate requires repeated requests to produce identical token
IDs. If it fails, Tier 1 is a no-go under the displayed topology and hour
table. Concurrency-one/offline serving with
`VLLM_ENABLE_V1_MULTIPROCESSING=0` is a diagnostic fallback only; confirmation
may use it only after a new throughput measurement, hour/cost calculation,
manifest hash, and approval. If no mode passes the byte-equality fixture, the
empirical study records a serving feasibility no-go. The four-arm design uses
IID randomized slots and never depends on common-random-number coupling.

Sampling is benchmark-specific but arm-common:

- SWE: thinking mode, temperature 0.6, top-p 0.95, top-k 20,
  presence penalty 0.0, repetition penalty 1.0.
- τ³: thinking mode, temperature 1.0, top-p 0.95, top-k 20,
  presence penalty 1.5, repetition penalty 1.0.

These are the publisher-recommended precise-coding and general-task settings.
Every seed is generated before outcomes and stored in the sealed assignment
ledger.

Separate, non-pooled subjects:

- BF16 precision replication:
  `Qwen/Qwen3.6-35B-A3B`
  `995ad96eacd98c81ed38be0c5b274b04031597b0`;
- development-only local subject:
  `Qwen/Qwen3.5-9B`
  `c202236235762e1c871ad0ccb60c8ee5ba337b9a`;
- optional frontier API replication, only under a fresh preregistration and an
  eligible provider-specific approval.

FP8 and BF16 results are never pooled as if they were the same subject.

## 5. Experimental unit and branching

### 5.1 Unit

The randomized causal unit is one benchmark task definition. Repository is the
highest lineage for SWE. Domain and issue family are additional blocks for τ³.
Seeds and branches are repeated measurements nested inside the task.

Each task produces one common prefix and four continuations. The prefix is
created exactly once, so arm differences cannot be attributed to different
pre-intervention trajectories.

### 5.2 Trigger

The intervention trigger is the earliest completed tool boundary satisfying
either:

1. the first mutation/action has returned and the state is verifier-eligible;
   or
2. the fourth subject tool call has returned.

The trigger occurs only after a tool result is committed. It never interrupts a
command, transaction, or model response.

Tasks that terminate before a trigger form the fixed-denominator
`no_intervention_opportunity` stratum. They are not discarded, re-run with a
different trigger, or used to choose a more favorable subject.

For the primary intention-to-treat estimator, such a task is retained with
`Y_R = Y_S = Y_N = Y_Z = Y_0`, so it contributes zero arm contrast. Effects
conditional on reaching the trigger are preregistered secondary estimates and
cannot replace the fixed-roster result.

### 5.3 Snapshot

At the trigger, the controller records and hashes:

- task and benchmark revisions;
- complete arm-visible transcript;
- subject sampling state and remaining quotas;
- tool call/result ledger;
- environment state;
- filesystem/worktree diff for SWE;
- both environment databases, user-simulator state, transcript, and RNG state
  for τ³;
- container/image/runtime digests; and
- a disposable endpoint score of the prefix state.

SWE uses a committed filesystem/container layer plus a clean checkout receipt.
τ³ uses a canonical serialization followed by deep-copy/restore equality tests.
Model KV state is not treated as portable state; each branch reconstructs the
same tokenized context and the receipt records exact token IDs.

If a pre-trigger response queued multiple tool calls, the snapshot includes
those pending calls. Each branch executes them in the same frozen order before
the first packet-visible model call. They count against the post-trigger
tool-call and wall-clock caps. The four post-pending/pre-injection visible-state
and token-ID digests must still match.

Prefix scoring and verifier execution happen on disposable clones. Their cache,
filesystem, timing, and output cannot flow back into any focal branch.

#### 5.3.1 Controller evidence authority (DL-136)

The controller must prove the prefix transaction from sealed parent bytes; an
adapter method named `grade_clone`, an arbitrary returned `ArtifactRef`, or a
copied digest is not evidence. `run_prefix` therefore receives the sealed
schedule ref and task ID, reloads the schedule and manifest, follows the
manifest-pinned `provider_lane_plan_v2`, and derives the exact task, prefix
seed, lane, caps, subject contract, optional simulator contract, parser
contract, and meter contract internally. The selected task-lane row also pins
the canonical task input plus closed environment, restore, grader, verifier,
and isolation contracts. Every nested contract binds nominal implementation
type/build, runtime/container/source revisions, task/benchmark identity, and a
closed raw-evidence grammar; study sealing copies and validates every nested
ref. A supplied factory or client must attest exact equality to those
contracts. Naked `TaskSchedule`, `PrefixCaps`, task input, or structural
factory inputs have no scientific authority.

Each provider lane freezes separate primary-subject and simulator constraints.
Primary generated-token/model-call and subject-issued tool-call ceilings define
the causal allowance. Simulator tokens/calls have exact aggregate and per-call
ceilings;
simulator latency still consumes the common elapsed-wall allowance and its cost
enters the same provider closure. Unused prefix allowance never enlarges a
branch. A response that returns after its absolute controller deadline is a
timeout outcome even if provider cancellation was delayed.

Every primary and simulator dispatch uses the role/index-separated
`call-seed-v1` program with the scheduled prefix or slot root. Those roots were
already derived from the schedule seed, task ID, and prefix/slot role, and the
call receipt is bound to the exact schedule digest. This unified rule
supersedes the historical τ³-only `tau-user-call-seed-v1` frame. Every
dispatch first publishes an immutable intent containing role, next consecutive
role-local index, seed, request/input tokens, model contract, and deadline.
The terminal attempt separately parents that intent and is published exactly
once after completion/failure. A closed attempt union represents completion,
refusal, malformed response, provider error, infrastructure error, timeout
without response, and timeout with a late response. Missing response/output
refs are legal only when no bytes arrived; partial and late evidence remains
referenced. The controller re-tokenizes request and every available response
under the pinned tokenizer, derives counts, and rejects any
role/index/seed/model/token/usage mismatch. Final cost closure parents every
dispatch intent, terminal attempt, and pinned provider settlement. Prefix
index sealing fails until every intent has exactly one terminal attempt and
every attempt has final cost; assignment, packet construction, analysis, and
release cannot parent an unsettled candidate. Clients never self-certify
ArtifactRefs.

The pinned controller parser reconstructs and byte-compares the exact ordered
tool queue from raw provider bytes; omission, insertion, reorder, duplicate
call ID, or parser drift blocks the prefix index as pipeline-invalid. A valid
terminal-with-remainder state is retained as adverse
`no_intervention_opportunity` / `malformed_action` evidence in a distinct
`terminal_unexecuted_remainder`; its branch-pending queue is empty. A
branchable trigger has an empty terminal remainder and retains its exact
executable queue separately. The controller owns
the completed-tool count, cumulative `mutation_has_returned`, and boundary
order. Each completed boundary binds the executed call ID, canonical call
bytes, result bytes, edge-local mutation commit, state-after verifier
eligibility, explicit episode-terminal state, failure kind, and elapsed
evidence. After every validated result it updates cumulative state, gives
terminal/failure/deadline checks precedence, and triggers at the first
remaining nonterminal boundary where
`(mutation_has_returned and verifier_eligible_after)` or the fourth
subject-issued tool call has completed. A terminal boundary cannot retain
branch-pending calls. Every non-`none` failure boundary is terminal, and every
terminal boundary is the last boundary; execution after failure is invalid
evidence. Clean text-only termination comes from the environment's
explicit terminal state; a model `finish_reason` is never sufficient.

Primary/simulator model-call counters increment at dispatch, including failed
attempts. Generated-token counters include every controller-tokenized partial
or complete output. Completed-tool counters increment only after a validated
boundary; attempted and pending calls remain in the ledgers. Allowance is
checked before and after each action; crossing the absolute deadline always
yields timeout.

The controller writes one closed canonical composite snapshot envelope with
exact schema/study/task/schedule/task-input/environment/isolation refs;
environment bytes; distinct branch-pending and terminal-unexecuted arrays;
visible context/digest; exact token
IDs/digest; boundary and provider-attempt ledgers; primary/simulator counters
and remaining quotas; cumulative mutation/terminal/failure state;
stateless-client attestations; and runtime/container/source revisions. Every
duplicated outer field must byte-equal the envelope. Restore reproduces
environment bytes, queue, visible state/tokens, terminal state, and all
interaction-dependent τ³ simulator transcript/state/RNG. Subject and simulator
clients are stateless seeded call clients. Before any provider dispatch, a
verified initial snapshot/fresh-restore gate must pass for the canonical task.
Failure there is pipeline-invalid and blocks prefix sealing rather than
deleting or adversely scoring a randomized task. Later provider/simulator/tool
failures freeze the last verified state and retain raw clone grade/verifier
evidence. The synthetic environment is a
closed named type with no simulator handle. A confirmation environment can
emit simulator context but cannot hold simulator credentials or reach its
endpoint; only the controller can call the simulator.

Grade and verifier execution each start from a separate new environment
instance and writable root, record distinct instance/process/root and restore
receipts, restore-check the same composite snapshot, verify visible state and
exact token IDs, and return closed raw evidence containing no ArtifactRef. The
controller alone stores evidence and constructs grade/verifier receipts.
Neither transaction receives or may alias the live environment object.
Synthetic exact types prove distinct objects/roots; confirmation requires a
manifest-pinned no-shared-writable-state qualification.

The local controller artifact store is a concrete final root-confined,
no-follow, create-exclusive, fsynced component, not a caller protocol.
Confirmation may use only a manifest-qualified nominal equivalent. After
close, the controller constructs a new resolver and reopens every write,
requiring independently supplied expected role and expected media type and
recomputing path, bytes, length, and SHA-256. JSON controller records use
exactly `application/json`; raw provider response, tool result, environment
snapshot, grade evidence, and verifier evidence use exactly
`application/octet-stream`. Media tokens are canonical lowercase
`type/subtype` values with no parameters or whitespace, never silently
normalized. Once a digest file is created, any write/sync/close/reopen/read/
stat/identity/verification failure aborts the transaction, attempts every
still-owned close once, unlinks the digest, fsyncs the role directory, and
preserves the primary plus every cleanup failure. Ownership is relinquished
before a close attempt because a raised close may already have closed and
recycled the descriptor; cleanup reopens the role directory rather than
double-closing uncertain state. The cost closure reloads
every dispatch intent, terminal attempt, and settlement event, including
partial/late failures, before prefix-index sealing.
The local zero-spend path emits a typed zero-attempt/zero-cost or
attempt-bound zero-cost closure; it does not treat missing evidence as zero.

The prefix receipt records schedule-bound caps, exact token-ID and
provider-attempt refs, the boundary ledger ref, distinct primary/simulator
counters, and a terminal failure kind. Raw `y0_grade.artifact_ref` and
`verifier_receipt.verifier_artifact_ref` remain direct closed grade/verifier
evidence edges used by downstream outcome and packet consumers. Separate
required `grade_execution_receipt_ref` and
`verifier_execution_receipt_ref` edges make each snapshot-bound restore
instance/process/writable-root receipt reachable for independent reload and
cross-checking. Artifact validation decodes the task mapping through exact
runtime `ToolCall`, grade, verifier, caps, counter, seed, and frozen-prefix
records; runtime exceptions fail closed as record-validation errors. The task
and nested verifier schedule digests both equal the enclosing
`payload.schedule_ref.sha256`. `NO_INTERVENTION_OPPORTUNITY` is valid only when the composite
snapshot has `episode_terminal == true`; `FIRST_ELIGIBLE_MUTATION` and
`FOURTH_TOOL_CALL` are valid only for a nonterminal composite snapshot. A cap,
timeout, malformed action,
refusal, model error, or infrastructure error before a branchable boundary is
retained as `no_intervention_opportunity` with its adverse terminal kind.
Ordinary termination uses `none` and copies clone-derived `Y_0`. For every
adverse no-trigger, the raw clone grade remains audit evidence but scientific
`Y_0.success`, partial reward, and all four outcomes are forcibly zero. This
preserves the fixed denominator without pretending operational failure is
natural task completion or allowing a pre-failure successful snapshot to
become a successful outcome.

#### 5.3.2 Executable synthetic prefix closure (DL-139)

DL-139 narrows S02C to `synthetic_validation`. It may execute only exact local
deterministic fixture calls and returns one canonical
`prefix_candidate_receipt` ArtifactRef wrapping the validated receipt mapping.
It cannot execute confirmation, provider/model/network
or credential access, spend, branches, assignment, packet construction,
prefix-index publication, a scientific experiment, an empirical result, or a
claim. S02D remains a separate transaction: it independently reloads every
candidate parent and raw blob, verifies selected-schedule coverage, chronology,
ordering, caps, and cost closure, and alone seals the prefix index.

The S02C entry accepts only `run_root`, `schedule_ref`, and `task_id`. A closed
local registry internally constructs the exact final environment binder,
subject, optional simulator, fresh zero-position meter, and all codecs from
sealed typed descriptors and program bytes. Caller fixtures, stores/loaders,
caps, scripts, plugins, subclasses, structural substitutes, and hidden
configuration are forbidden. The controller constructs the exact final
`ControllerArtifactStore`, closes it after all candidate artifacts are
written, then uses an exact fresh resolver to reopen the wrapper and every
reachable artifact with independent expected role, media, and bytes.

Subject and simulator expose only an `invoke` taking controller-rendered request
bytes, intent digest, role/index/seed/model digest, remaining typed caps, and
deadline and returning the raw observation. The meter exposes only one labeled
read bound to the sealed program digest. The factory supplies sealed command
and binding logic only; the controller creates/fstats the root and owns the
IPC, direct `Popen`, and PID before binding the handle. That handle has only
start, snapshot, restore, visible-context, distinct role-safe
append-assistant-turn and append-simulator-turn operations, execute-tool, four
separate mutation/eligibility/terminal/failure queries, two-argument
terminate-with-exact-pending-queue, grade, verify, and close operations; tool
execution returns only ID/raw bytes.
The constructed factory, subject, simulator, and meter each carry frozen program bytes/digest
that must exactly equal the canonical task program before qualification.

`PrefixExecutionAuthority` exposes the exact schedule authority, manifest
tokenizer ref, complete ordered source-revision refs, and frozen typed
descriptors for subject, optional simulator, parser, meter, environment
factory, grader, verifier, tokenizer, request renderer, provider-event codec,
and settlement codec. DL-140 defines one exact descriptor with one explicit
implementation-source ref and stable pre/post source reads. This is limited
cooperative-local source provenance, not Python code-object, bytecode, deployed
execution, production, provider, model, network, or confirmation attestation.

The selected `prefix_task_input_v1` has exactly one required
`synthetic_execution_program_ref` to a closed
`synthetic_prefix_program_v1`; inline alternatives reject. It fixes the
expected trigger, exact tool-schema ref, one ordered role-bearing provider
transcript, tool
observations, grade/verifier results, exact failure injection or `none`, and a
named clock trace. There is no caller script. A program expected to trigger
must pin a canonical nonempty synthetic tool schema, and every named tool must
exist in it. The expected trigger is checked only after execution against the
controller-derived result; it never selects or overrides the trigger.

A raw provider observation closes role, role-local index, call seed, model
contract digest, optional response bytes, conditional exact typed
`SubjectTurn`, optional reported output-token IDs, reported count, canonical
provider-event bytes, and a closed completion-kind claim. Request rendering,
tokenization, request/input-token storage, and dispatch-intent storage and
verification all occur before invocation. Response and token IDs co-occur;
their absence requires zero count and no typed turn. The controller parses
every full raw response and compares the complete typed turn—text, ordered
queue, generated count, and finish reason—and independently reconstructs token
IDs/count. It derives attempt status from raw response/parser/refusal/event/
clock evidence; a fixture completion kind or count is never authority.

Initial restore qualification is outside prefix time. Exactly one
`prefix_epoch` clock read occurs after it; every later read has a sealed label,
uint64 value, exact order, and nondecreasing value. Deadline addition rejects
uint64 overflow. `now >= deadline` before an action forbids starting it;
completion equal to the deadline is on time and completion greater than it is
late. Grade/verify time is excluded. Observed used time preserves overshoot,
while each remaining quota is `max(0, cap - used)` rather than an equality
assertion.

`FailureKind` adds exact `MODEL_CALL_CAP` and `TURN_CAP`. Generated-token,
model-call, and turn exhaustion map to `TOKEN_CAP`, `MODEL_CALL_CAP`, and
`TURN_CAP` for both primary and simulator; primary completed subject-issued
tool exhaustion maps to `TOOL_CAP`. Deadline, refusal, parser, model, and
transport failures map exactly to `TIMEOUT`, `REFUSAL`, `MALFORMED_ACTION`,
`MODEL`, and `INFRASTRUCTURE`. There is no retry. DL-140 defines inclusive
discrete maxima and exact post-completion precedence; equality cannot
invalidate an admitted action or its trigger. An initially clean terminal task is a legal natural
no-trigger candidate with zero attempts. Calls count at dispatch, tokens count
controller-tokenized received bytes, and turns count only parser-valid typed
turns, including a parser-valid refusal. Completion exactly at deadline may
produce the observed terminal state or trigger; otherwise no next action can
start and the controller terminates with timeout.

The controller's single
`terminate(failure_kind, pending_queue)` transition freezes the last verified
state, makes the adverse state terminal, preserves the actual non-`none`
failure, clears the branch queue, and preserves any known pending queue in
exact order as `terminal_unexecuted_remainder`. Therefore any adverse stop may
carry a known terminal remainder; it is not forced to malformed action.
Natural clean termination has failure `none` and no remainder. A branch trigger
is nonterminal and has no terminal remainder.

One required `CompositeSnapshotEnvelope.initial_restore_qualification_ref` is
the only route to a closed `InitialRestoreQualificationReceipt`. That receipt
binds schedule, selected task, task input, environment/isolation contracts,
initial environment snapshot, observed resnapshot digest/length, visible and
token refs plus explicit digests, both queues, terminal/failure state, live and
fresh-restore controller-observed identities, and exact `verified = true`.
Fresh validation compares exact resnapshot bytes, not only digest/length, and
a verified qualification requires failure `none` while allowing a clean
terminal state. Qualification failure is pipeline-invalid and emits no
candidate.

Exact `GradeExecutionReceipt` and `VerifierExecutionReceipt` records each
parent a purpose-specific `SnapshotRestoreReceipt` plus their direct raw
evidence. The restore receipt binds
all schedule/task/input/environment/isolation ancestry, final composite and
environment snapshots, observed resnapshot digest/length, both queues,
visible/token refs and explicit digests, terminal/failure state,
controller-observed identity, and exact verified result. All repeated state
equals the composite snapshot, and the exact observed resnapshot bytes are
freshly compared. Raw grade/verifier refs retain their DL-137 direct-evidence
semantics.

`EnvironmentProcessIdentity` is a closed frozen record of exact nonnegative
instance ordinal, one normalized nonempty root-confined relative writable
path, exact nonnegative root `fstat` device/inode, and positive real child PID
observed from the controller's own spawn. Exact fixtures are subprocess-backed.
Live, initial-restore, grade, and verifier environments remain pairwise
disjoint by object, PID, and root device/inode through their last checks;
caller strings and logical IDs prove nothing.

The source-provenanced tool fixture returns only executed call ID and raw result
bytes. The controller separately queries post-action mutation commit, verifier
eligibility, terminal state, and failure, and obtains elapsed time from the
meter. It alone constructs tool-result/boundary evidence, checks parser queue
order and ID, and applies terminal/failure/deadline precedence before trigger.

Synthetic provider events are compact canonical
`synthetic_provider_event_v1` JSON binding role/index/seed, model contract,
dispatch intent, completion kind, nullable response digest, observed time, and
zero cost. Post-attempt compact canonical
`synthetic_provider_settlement_v1` binds the same identity plus intent,
attempt, event, `final = true`, fixed synthetic currency, and exact zero cost.
The acyclic pair binds intent/event/attempt/finality. Any attempt requires
`AttemptBoundZeroCostClosure`; zero-attempt closure is legal only with no
dispatch.

CAS remains no-overwrite. `EEXIST` enters a verified idempotent-reuse path:
independently reopen with no-follow semantics and verify canonical role/media/
path, regular-file identity, hash, length, and exact bytes before returning the
same ref. Mismatch or collision fails and never unlinks the pre-existing blob.
Canonical role has exactly one DL-138 media type; caller metadata cannot invent
another binding. DL-138 post-create cleanup remains unchanged for a blob
created by the current call.

The implementation is reviewed in four internal slices: contracts/source
provenance plus CAS reuse; initial restore plus subprocess identities;
provider/simulator/tool loop; and final snapshot plus grade/verify/fresh-
resolver candidate. The prioritized falsification matrix rejects: non-synthetic
authority or injection/source drift; root/PID/inode aliasing or restore drift;
intent-order/status/turn/token/event/settlement inconsistencies; clock order,
overflow, boundary, overshoot, cap, and precedence errors; queue loss or
environment-self-certified tool state; EEXIST mismatch; and any return before
fresh resolution or any S02C publication/branch/network/spend path.

#### 5.3.3 DL-140 executable-uniqueness and handoff repair

DL-140 repairs the exact S02C review rejection and supersedes conflicting
DL-139 prose.

Discrete model-call, parsed-turn, and completed-tool caps are inclusive maxima:
`used >= cap` blocks only the next same-dimension action. An admitted action
that reaches equality remains valid. Only token and wall usage can newly
overshoot after completion; equality is valid. After a completed tool, explicit
failure, environment terminal state, deadline/wall overshoot, and token
overshoot precede the trigger. Model/turn exhaustion cannot block its queued
tools, and tool four at a cap of four yields `FOURTH_TOOL_CALL` unless an
earlier failure/terminal/overshoot or eligible-mutation trigger wins.

S02C stores compact canonical `application/json` under role
`prefix_candidate_receipt` with exactly
`record_kind = "frozen_prefix_candidate_v1"`, `schema_version = "1"`, and one
`receipt` mapping decoded through the exact runtime `FrozenPrefixReceipt`
validator. After store close, a fresh resolver reloads that wrapper and its
whole graph; `run_prefix` returns only its ref. S02D accepts only unique wrapper
refs in selected-schedule order, independently reloads/decodes and checks exact
coverage, chronology, caps, trigger, isolation, and cost, then embeds the
decoded receipts and alone seals the prefix index.

The program contains one ordered provider transcript. The environment's
independent `simulator_context() -> bytes | None` query chooses each actor:
non-null requires simulator and null requires primary. Transcript role is only
a consistency check. The controller then checks actor-local caps, renders and
verifies request bytes/input tokens/intent, invokes once, and validates all raw
evidence before mutation. A simulator turn has no tools and uses only the
simulator append operation; a primary turn uses only the assistant append
operation and then executes its ordered queue. Actor-local indexes, seeds,
tokens, model calls, turns, and aggregate/per-call caps remain separate.

The entry is exactly
`run_prefix(*, run_root: Path, schedule_ref: ArtifactRef, task_id: str) ->
ArtifactRef`. A closed registry internally constructs every fixture and codec
at program/transcript/clock position zero. No caller executable object or
configuration exists.

Each registry key is one exact frozen `ImplementationDescriptor` containing
purpose, nominal type, build, nullable-by-purpose request/response/snapshot/
restore/evidence grammars, runtime/container identities, and one explicit
manifest-member `implementation_source_ref`. The mapping is one-to-one to an
exact final constructor. The controller reads both ref and registered local
source through no-follow regular-file fds, compares exact bytes/hash/length and
unchanged pre/post `fstat` identity/size/mtime before construction, and repeats
the check after last use. A change after import/read fails. This is
cooperative-local source provenance under a no-concurrent-mutation assumption;
it does not prove Python code-object, bytecode, or deployed execution identity
and cannot authorize confirmation or claims.

The controller allocates live/initial/grade/verifier roots create-exclusively
under a held no-follow operational workspace dirfd. An existing candidate name
is stale and skipped by bounded suffix search, never opened/reused/cleaned.
For each new root the controller keeps its fd, owns IPC, directly retains
`Popen`, and observes PID; the factory only supplies sealed command/binding
logic. All four processes/root fds survive through final pairwise identity and
`poll() is None` checks. After receipt observation and fresh candidate
resolution, success and failure both close IPC/handles/fds, terminate/wait
(closed-policy kill/wait if needed), then verify each still-held root fd,
remove controller-created contents through it, remove the exact child through
the held parent dirfd, and close root/workspace fds. Stale roots are never
opened or cleanup targets. Primary and all cleanup failures are aggregated;
cleanup failure blocks return.

`prefix_task_input_v1.synthetic_execution_program_ref` is required exactly
once with role `synthetic_execution_program` and media `application/json`; it
is copied and recursively closed during manifest sealing. Its canonical object
has exactly record kind/version, task ID, post-hoc expected trigger, tool
schema, one provider transcript, tool observations, grade/verifier result,
failure injection, and clock trace. Each provider row closes role/index/seed/
model, expected canonical request ref and equal digest, exact input token IDs,
optional response ref, conditional typed turn/output IDs/count, canonical
event bytes, and completion claim. Expected trigger is only a post-execution
consistency check.

Event transport is one of `response`, `provider_error`,
`infrastructure_error`, or `timeout_no_response`; parser result is `turn`,
`refusal`, `malformed`, or `not_applicable`. Event observed time must equal the
controller meter's named completion read, and the table uses that controller
read rather than a client clock claim. The status table is:

| observed time | response | transport | parser | result |
|---|---:|---|---|---|
| `> deadline` | yes | response/provider-error/infrastructure-error | validated | timeout-late-response |
| `> deadline` | no | provider-error/infrastructure-error/timeout-no-response | not-applicable | timeout-no-response |
| `<= deadline` | no | provider-error | not-applicable | provider-error |
| `<= deadline` | no | infrastructure-error | not-applicable | infrastructure-error |
| `<= deadline` | yes | provider-error | validated | provider-error |
| `<= deadline` | yes | infrastructure-error | validated | infrastructure-error |
| `<= deadline` | yes | response | refusal | refusal |
| `<= deadline` | yes | response | malformed | malformed-response |
| `<= deadline` | yes | response | turn | completed |

Every unlisted combination is pipeline-invalid. Equality is on time.
Timeout-no-response at/before the deadline is inconsistent. Late status
dominates while retaining response/partial/token/event bytes. “Validated”
means parser-derived turn/refusal/malformed, never not-applicable. Response presence
requires controller-equal output IDs/count and an exact typed turn for
turn/refusal; absence requires null IDs/turn and zero count; malformed requires
no typed turn. Request/input tokens, full typed text/queue/finish reason,
event, actor identity, and completion claim all equal controller derivation.
Any mismatch, including simulator tools, fails before environment mutation.

The required RED matrix covers equality/overshoot/fourth-tool precedence,
immutable candidate/S02D ordering, controller-derived actor interleaving,
simulator-tool rejection and cap isolation, absence of caller fixtures, stable
source reads without execution-attestation overclaim, stale-root/liveness/
cleanup behavior, every table row and excluded combination, deadline equality,
late evidence retention, and raw/typed rejection before mutation.

#### 5.3.4 DL-141 publication destination and loader partition

S02D's exact entry is
`seal_prefix_index(*, run_root, schedule_ref, candidate_refs, out) ->
ArtifactRef`. `out` is an exact normalized absolute path strictly under the
resolved run root, reached through held no-follow dirfds. It cannot contain
symlink or `..` components or lie under `controller-artifacts/`,
`controller-workspace/`, or operational `prefix-environments/`. Publication is
create-exclusive/no-overwrite, complete-write plus file fsync, close, parent
fsync, and reopen verification. Existing targets fail; applicable recovery
remains under the existing publication protocol. S02C cannot call the sealer or
write that destination.

Recursive loading is partitioned by one closed, startup-validated role
registry. `scientific_parent` contains exactly prefix schedule and study
manifest roles with their exact record kinds. `controller_artifact` contains
exactly the explicit controller role-to-media registry, including the candidate
wrapper and every S02C-created evidence role. `authority_asset` contains
exactly the explicit manifest-sealing authority role-to-media registry,
excluding the scientific parents and including task/provider/contracts/
tokenizer/prompt/tool/program/request-response/source/clock/watchdog/isolation
assets. The three sets are disjoint and have no default.

Scientific parents use a fresh scientific-record loader, controller artifacts
use a fresh `ControllerArtifactResolver`, and authority assets use a separately
fresh `AuthorityRefReader`. Each gets exact role/media/kind expectations and
enforces its own canonical path/root identity. The controller resolver never
loads authority or scientific refs. Unknown roles, cross-class paths/roles,
media drift, path/ref aliasing, or one ref assigned to multiple classes reject.

S02C traverses from the candidate wrapper; S02D traverses again from the
schedule and every ordered candidate with entirely new loader instances. Exact
decoders discover every nested ref into a `ref -> load_class` visited map.
Before return/publication every reachable ref has been loaded successfully by
exactly one class. Missing, duplicate, opaque, or unknown nested refs reject.

#### 5.3.5 DL-142 exact authority-leaf and same-open closure

DL-142 closes the gap between DL-141's no-opaque-leaf rule and the actual
authority registry. A closed `AUTHORITY_ASSET_DECODER_BY_ROLE` must cover every
registered authority role without a generic fallback. Existing scientific
task/provider/contract validators and exact synthetic program/leaf codecs are
reused. Foreign task inputs and their program edges are validated independently
instead of receiving only a canonical-JSON walk. `source_revision` is the sole
opaque-byte role and carries no semantic or execution claim beyond its exact
ref and verified bytes.

Synthetic validation gives the seven formerly untyped JSON roles explicit
version-1 closed records:

| role | literal record kind | exact payload |
| --- | --- | --- |
| `tokenizer` | `synthetic_tokenizer_asset_v1` | nonempty `tokenizer_id` |
| `prompt_template` | `synthetic_prompt_template_asset_v1` | nonempty `template_id` |
| `tool_schema` | `synthetic_tool_schema_asset_v1` | ordered unique closed tool-name rows |
| `clock_source` | `synthetic_clock_asset_v1` | nonempty `clock_id` |
| `watchdog_source` | `synthetic_watchdog_asset_v1` | nonempty `watchdog_id` |
| `isolation_qualification` | `synthetic_isolation_qualification_asset_v1` | nonempty `qualification_id` |
| `deep_authority_asset` | `synthetic_deep_authority_leaf_v1` or `synthetic_deep_authority_link_v1` | respectively one nonempty `value_id` or one exact same-role `nested_ref` |

Every row also has exactly `schema_version: "1"` and no other field. These
record kinds are synthetic-only; confirmation must register reviewed
role-specific decoders and cannot pass through structural similarity.

Grade bytes directly carry exactly an integer 0/1 success, finite exact-float
partial reward, and exact-Boolean infrastructure failure. Verifier bytes
directly carry exactly one nonnegative exact-integer finding count. Codecs
decode those values from evidence before comparing them with every owning
program. Program-to-leaf attribution is occurrence-aware, so set/dict collapse
cannot hide contradictory shared refs.

Fresh traversal binds the verified bytes and physical identity of each file
from one held no-follow descriptor with stable pre/post `fstat`; a later reopen
cannot supply the alias identity. All reader cleanup follows relinquish-before-
uncertain-close and causal primary-plus-cleanup aggregation. This strengthens
only cooperative-local reconstruction and makes no hostile-filesystem or
executed-code attestation claim.

#### 5.3.6 DL-143 cooperative S02D publication concurrency

S02D publication is cooperative-local. `seal_prefix_index` acquires an
exclusive nonblocking advisory lock on its held run-root descriptor before
fresh traversal and retains it through create-exclusive publication, reopen
verification, any rollback, and all transaction cleanup. Every in-scope S02D
prefix-index writer/recovery operation uses and honors that same lock.
Contention rejects before traversal or mutation.

Rollback under the lock uses a no-replace quarantine move to bind the named
source before identity/content verification and removal. A missing or changed
source detected before quarantine is ownership loss: preserve the unowned name,
return an explicit rollback residual, and fail closed. This does not claim
security against arbitrary same-UID or kernel-interposed namespace mutation.
POSIX has no compare-and-unlink-by-inode operation; a hostile mutator can act
between any user-space check and a later rename, unlink, or restore syscall.
Repeated checks cannot close that syscall gap and would be security theater.
The guarantee is exact only for cooperating local writers holding the root
transaction lock. Normal replacement-before-operation detection remains
mandatory.

#### 5.3.7 DL-144 exact commit point and shared tool transition

The S02D transaction remains pre-commit until graph traversal, create-exclusive
publication, file/parent durability, reopen semantic verification, every
required namespace-mutating rollback, and every ordinary descriptor cleanup
has succeeded under one continuously held exclusive root lock. Releasing that
lock is the final non-mutating action. A pre-commit loss of proven lock
continuity forbids further unlink, rename, restoration, or publication unless
exclusive ownership is nonblockingly reacquired; failure to reacquire returns
an explicit residual and fails closed.

Successful semantic verification plus ordinary cleanup is the commit point.
After it, explicit unlock or final lock-descriptor close failure is a committed-
publication cleanup error: retain the verified target and perform no rollback
or other namespace mutation. `close` may release the advisory lock and still
raise, so user space cannot safely infer that a subsequent rollback is
protected. DL-143's former lock-through-all-cleanup wording is superseded by
this exact phase boundary. The guarantee remains cooperative-local only.

Root-descriptor acquisition is causally guarded from successful `flock`
onward, including the immediately following `fstat`. Any pre-commit acquisition
failure closes the descriptor once, aggregates cleanup failure without masking
the primary, leaves no publication, and releases the cooperative lock for a
later transaction.

One shared pure completed-tool transition implements both selected and
all-occurrence replay precedence:

1. tool failure;
2. clean terminal, rejecting any queued remainder;
3. after-tool wall timeout;
4. token overshoot;
5. first cumulative eligible mutation;
6. fourth completed tool;
7. continue.

The same shared pre-tool transition classifies deadline and tool-cap stops.
Occurrence replay derives cumulative mutation and trigger, stops at the first
terminal or trigger transition, rejects any later row/read/observation through
exact exhaustion, and compares the derived trigger with the sealed program
claim. This removes independent policy ladders without expanding S02D's
scientific authority.

### 5.4 Assignment prefix view

Post-prefix donor matching consumes a canonical `AssignmentPrefixView`, not the
prefix-receipt object. For each task the view contains only:

- canonical task ID, benchmark, stratum, lineage, and registered group labels;
- trigger/no-trigger class;
- normalized verifier/checker or evaluator-component class;
- objective finding count;
- normalized report token count; and
- the telecom issue family.

It contains no `Y_0` grade or partial reward, success bit, model/tool/resource
counter, wall time, provider cost, provider event, raw snapshot/verifier/grade
ArtifactRef, finding text, packet text, endpoint byte, or branch field. The
allowlist is implemented by constructing a new frozen record field by field;
serializing a prefix record and deleting a denylist is forbidden. A caller
cannot submit the view. Its internal builder reloads each typed verifier
receipt, reconstructs the normalized component class and both integer counts
from the referenced verifier bytes, and checks task metadata against the
schedule.

Precomputed count/length bands and a claimed
`cross_family_component_match_available` bit are forbidden from the view. The
manifest-pinned assignment program contains strictly increasing non-negative
integer arrays `finding_count_band_upper_bounds` and
`report_length_band_upper_bounds`. The band for `x` is the zero-based index of
the first bound strictly greater than `x`, or the array length when no bound is
greater. Candidate construction and verification independently derive these
indices from the raw counts; booleans, negative values, duplicate/unsorted cut
points, or caller-supplied bands fail closed. Telecom cross-family availability
is derived per focal task from the complete canonical candidate graph after
every other exact gate and before same-family fallback edges are admitted.
Tasks and group labels use the canonical ordering in section 9.1, and the view
digest is stored in the assignment ledger.

The donor solver may depend on this view. The 12-way allocation and N/Z
orientation may depend only on their separately derived subkeys, the canonical
task ID, and the already-frozen manifest/schedule context; they do not consume
the view digest or prefix-index digest. Metamorphic validation replaces every
excluded field and raw reference while preserving the allowlisted values and
must reproduce donor candidates, donor mapping, allocation indices, and
orientation bits byte for byte. Changing an allowlisted matching feature may
change only the donor result. Opaque slot capabilities separately bind the
prefix-index digest, so an excluded-field mutation changes capabilities and
ancestry without becoming an arm-assignment input.

## 6. Arms

Every arm receives the identical post-trigger subject model-call, generated
token, tool-call, wall-clock, disk, network, and candidate/selection caps.
There is no best-of selection. The endpoint is the direct result of that arm.

| arm | injected evidence | continuation sampling |
| --- | --- | --- |
| `REAL` | correct task-specific verifier packet | one IID opaque branch slot |
| `SHAM` | shape- and token-matched packet derived from another lineage | one IID opaque branch slot |
| `NONE` | no message and no verifier evidence | one IID opaque branch slot |
| `RESAMPLE` | no message and no verifier evidence | one IID opaque branch slot |

For each frozen prefix, the controller creates four branch slots with IID
preregistered seed streams and a randomized execution-order/hardware schedule.
A uniform within-task draw assigns the multiset `{REAL, SHAM, NO_PACKET,
NO_PACKET}` over its 12 possible slot allocations, then a fair coin labels the
two no-packet slots NONE and RESAMPLE solely for the resampling audit. Both
draws occur before any continuation. The allocation is sealed and never
depends on a branch outcome.

Every primary-subject and τ³ user-simulator call derives its seed from the
scheduled prefix root or continuation-slot root, role, and call index through
the section-4.0 framed, domain-separated SHA-256 program.
The ordered per-call seed receipt is persisted. Both prefix and continuation
loops invoke the simulator through an explicit controller-owned seeded
interface; environment adapters may expose simulator context and apply a
returned turn but may not call a simulator internally. Adapters and serving
processes cannot choose replacement seeds.

`NONE` and `RESAMPLE` are exchangeable no-treatment replicates. Their mean is
the no-feedback continuation condition; their paired disagreement is the
empirical resampling null. The study makes no common-random-number claim for
REAL versus SHAM.

REAL and SHAM have the exact same subject-token length under the frozen
tokenizer, packet schema, field count, severity distribution, and continuation
sampling distribution. They differ in whether the findings apply to the focal
task.

The study does not pretend the no-payload arms have the same input length as the
packet arms. The estimand `SHAM - mean(NONE, RESAMPLE)` measures the net effect
of a mismatched report, including extra prompt tokens, misinformation, and the
generic instruction to reconsider work. It is not a pure apparatus effect.

### 6.1 Post-trigger quotas

Initial caps, frozen before pilot execution:

| benchmark | generated tokens | subject tool calls | wall clock |
| --- | ---: | ---: | ---: |
| SWE | 32,768 | 32 | 60 minutes |
| τ³ | 16,384 | 16 turns/tool calls | 30 minutes |

The common prefix has the same caps available before the trigger, but unused
prefix allowance does not enlarge an arm's post-trigger allowance. Cap binding,
timeout, refusal, malformed tool calls, and premature finish are outcomes.

## 7. Verifier and sham construction

### 7.1 SWE verifier

The verifier runs the task's pinned target and regression checks on a disposable
clone of the prefix state. The REAL packet may include:

- pass/fail status by registered check identifier;
- normalized compiler, assertion, or runtime failure class;
- a bounded log excerpt;
- regression status; and
- verifier resource/timeout status.

It never includes test source, gold patch content, future commits, or an
unbounded traceback. The final endpoint runs the complete registered F2P/P2P
checks again in a fresh digest-pinned grader image and rejects any missing
check. SWE-bench-Live MultiLang publishes the gold patch, test patch, commands,
parser, and check sets and has no private hidden-test layer. Those public
answer-bearing fields remain controller-only until unblinding. This is an
intervention study, not a leaderboard submission; giving registered verifier
feedback mid-trajectory is the treatment and must be stated plainly without
calling the endpoint private, hidden, or contamination-free.

### 7.2 τ³ verifier

The verifier evaluates the eligible objective components against the cloned
prefix environment and transcript. The REAL packet reports:

- component type and satisfied/unsatisfied state;
- a policy-safe reason code;
- the relevant action or communication category; and
- bounded current-state evidence.

Expected final values and hidden task answers are not emitted. Task IDs,
description, ticket, evaluation criteria, golden actions and arguments,
assertion arguments/expected values, required-document identities, target DB
hash/diff, and task issue metadata are controller-only. No LLM judge or network
call creates a primary verifier finding.

### 7.3 Sham donor

A deterministic constrained minimum-cost perfect matching selects one donor
from another eligible lineage for every triggered task. No-trigger tasks remain
randomized ITT units but never need or receive a donor. Matching input is only
the triggered subset of the sealed `AssignmentPrefixView`:

- SWE: same language, check runner/failure class, failure-count band, and log
  length band; different repository.
- τ³: same domain, evaluator-component multiset, failure-count band, and report
  length band; different task and, for telecom, different issue family where
  possible.

For each telecom focal task, same-family candidates are absent when at least one
cross-family candidate satisfies every other exact constraint. They become
eligible only when that focal task's exact candidate set has no cross-family
member. For `ACTION + ENV_ASSERTION`, every eligible task is `service_issue`,
so the per-focal fallback records
`cross_family_component_match_unavailable`. It may not relax component, domain,
lineage, derangement, collision, or token-parity gates. An empty candidate set
for a triggered focal task is a no-go; no roster redraw follows.

For canonical triggered focal tasks `i` and triggered candidate donors `d`,
create binary
`x[i,d]`. Candidate enumeration and the exact binary-integer program require:

```text
sum_d x[i,d] = 1                         for every focal i
sum_i x[i,d] = 1                         for every donor d
x[i,i] = 0
x[i,d] = 0                               for same-lineage or ineligible edges
x[i,d] + x[d,i] <= 1                     whenever both directed edges exist
```

The solver lexicographically minimizes, using exact integer objectives:

1. the number of permitted telecom same-family fallbacks;
2. total absolute objective-finding-count difference;
3. total absolute normalized-report-token-count difference.

It must return `OPTIMAL`, not merely feasible or time-limited. Solver
interchange has one closed, backend-independent grammar. Problem and solution
objects use `canonical_json_bytes(value, indent=None)`: sorted keys, compact
separators, strict UTF-8, no BOM, exactly one final LF, and non-finite numbers
disabled. Parsing followed by canonical reserialization must reproduce the raw
bytes. Identifiers obey section 4.0's NFC/Unicode rules, SHA-256 values are
lowercase 64-hex, all costs are exact non-negative integers, booleans are not
integers, floats are forbidden, and unknown fields fail.

The exact problem shape is:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "backend_receipt_sha256": "<sha256>",
  "constraints": {
    "forbid_same_lineage": true,
    "forbid_self": true,
    "forbid_two_cycle": true,
    "one_incoming": true,
    "one_outgoing": true
  },
  "edges": [
    {
      "donor_task_id": "<id>",
      "focal_task_id": "<id>",
      "primary_cost": [0, 0, 0],
      "tie_hmac_sha256": "<sha256>"
    }
  ],
  "fixed_edges": [["<focal-id>", "<donor-id>"]],
  "focal_task_ids": ["<id>"],
  "record_kind": "exact_matching_problem_v1",
  "stratum_key": ["<component>"]
}
```

`focal_task_ids` is the triggered stratum in canonical prefix-view order.
`edges` contains every and only eligible edge, grouped by that focal order and
then by `(raw tie-HMAC bytes, strict UTF-8 donor ID)`. The primary problem has
empty `fixed_edges`; a tie trial appends one focal/donor pair to the already
fixed focal prefix. Fixed edges are ordered, unique on both sides, eligible,
and enforced together with the five constant-true constraints. Program and
backend digests must resolve through the manifest-pinned assignment program.

The exact solution shape is:

```json
{
  "backend_receipt_sha256": "<sha256>",
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "objective": [0, 0, 0],
  "problem_sha256": "<sha256>",
  "record_kind": "exact_matching_solution_v1",
  "status": "OPTIMAL"
}
```

For `OPTIMAL`, the objective is the exact three-integer vector and the mapping
is a complete permutation in focal order. For `INFEASIBLE`, the objective is
`null` and the mapping is empty; no other status is representable. Verification
hashes the canonical problem, checks both authority digests, independently
checks feasibility/objective, and reruns the same solver. A backend-native log
is neither solver input nor proof.

The zero-spend core exposes no injected or structural solver protocol.
Triggered confirmation consumes only an exact nominal,
non-subclassable `ConfirmationMatchingBackendSession` opened by the trusted
`ConfirmationPreflightRegistry`; it is never a caller-supplied scientific
argument. The registry binds the session to the exact
manifest/schedule/prefix tuple, manifest-pinned backend authority and receipt,
one private registry nonce, one transaction, and the canonical solve
sequence. The session accepts exactly the algorithm-derived primary,
tie-trial, and final problems in order, launches the pinned runner for each,
returns signed closed invocation receipts, and closes once with the complete
ordered transcript. Copied/lookalike/stale sessions, subclasses, unexpected
problem/order/count, solve after close, or second close reject.

A bounded exhaustive solver remains reachable only through a test-only
registry session for small hostile synthetic fixtures. It cannot serve
C120/C160 or satisfy an eligible-confirmation manifest. The repository
contains no scalable live adapter, so confirmation remains unavailable until a
separately reviewed benchmark-adapter implementation plan selects, implements,
and pins one before the study manifest and any prefix. Supplying an object
afterward cannot repair absent authority. Any triggered confirmation stratum
without the exact live session fails before ledger creation; all-no-trigger
confirmation and every synthetic transaction require no session or proof.

Among primary-cost-optimal solutions, selection is unique without relying on
solver discovery order. For every edge compute:

```text
tie[i,d] = HMAC-SHA256(
    K_donor,
    FRAME("donor-tie-v1", [TEXT(task_id_i), TEXT(task_id_d)]),
)
```

In canonical focal order, try candidates in `(tie bytes, canonical donor ID)`
order and fix the first edge for which the exact solver proves an optimal
completion with the already-frozen objective vector. Retain every attempted
problem/solution, including infeasible and higher-objective trials. Thus an
HMAC collision is resolved by canonical donor ID. Task ordering is
`(benchmark, stratum, lineage, task_id)` by strict UTF-8 bytes; group labels are
ordered `language`, `domain`, `issue_family`, then by value bytes. Candidate
rows use the explicit focal/tie order. No locale, hash-map insertion order, or
solver-native tie breaker has authority.

Each confirmation stratum emits one canonical
`application/vnd.pneuma.assignment-matching-proof+json` blob with exactly:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "backend_receipt_sha256": "<sha256>",
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "final_problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
  "final_solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"},
  "primary_problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
  "primary_solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"},
  "proof_kind": "confirmation_exact_v1",
  "schema_version": "1",
  "stratum_key": ["<component>"],
  "tie_steps": [
    {
      "focal_task_id": "<id>",
      "ordered_candidates": [["<tie-sha256>", "<donor-id>"]],
      "selected_donor_task_id": "<id>",
      "trials": [
        {
          "donor_task_id": "<id>",
          "problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
          "solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"}
        }
      ]
    }
  ]
}
```

ArtifactRef sizes above are illustrative positive values and use the existing
closed definition. There is one tie step per focal. Its ordered candidates are
complete after removing only donors already consumed by the previous fixed-edge
prefix; the verifier derives that removal, while the donor receipt retains the
full pre-fixing candidate set. Its trials are exactly the non-empty prefix
through the first `OPTIMAL` trial retaining the primary objective. Every trial
problem contains the prior chosen fixed edges plus that candidate. The final
problem fixes the complete mapping, and its optimal solution, proof mapping,
ledger, and receipts must agree.

Synthetic fixtures emit a different, fully recomputable proof. Order tasks by
`(HMAC-SHA256(K_donor, FRAME("synthetic-order-v1",
[BYTES(view_sha256), TEXT(stratum_key_0), ..., TEXT(task_id)])), task_id)`;
try cyclic offsets `1..n-1`; for each offset check same lineage before a
reciprocal two-cycle in canonical focal order; select the first valid offset.
The exact closed blob is:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "canonical_focal_task_ids": ["<id>"],
  "cycle_order": [{"order_hmac_sha256": "<sha256>", "task_id": "<id>"}],
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "offset_trials": [{"failure_code": null, "offset": 1, "valid": true}],
  "proof_kind": "synthetic_cyclic_offset_v1",
  "schema_version": "1",
  "selected_offset": 1,
  "stratum_key": ["<component>"]
}
```

`offset_trials` is every integer from one through the selected offset.
Invalid rows carry exactly `"same_lineage"` or
`"reciprocal_two_cycle"` for the first violation; the selected valid row has
`null`. No valid offset means fail without publishing a ledger. This proof uses
the same strict canonical-JSON contract and cannot be relabeled as
confirmation.

The ledger has exactly one proof per triggered matching stratum, ordered
canonically; `matching_proof_refs` is unique and empty iff every task is
no-trigger. Every matched receipt points to its stratum proof and an N/A
receipt never does. Artifact-root verification parses the proof, recursively
follows every problem/solution ref, rebuilds the view/candidate graph, and
reruns the exact mode. It rejects skipped candidates/offsets, incomplete
coverage, non-permutation, self/same-lineage edges, reciprocal two-cycles,
relaxed constraints, changed objectives/mappings, noncanonical bytes, or
cross-mode relabeling.

Every selected-schedule task emits one closed `DonorMatchReceipt` arm. A triggered task
uses `kind = "matched"` and contains assignment mode, matching algorithm,
task/donor IDs and lineages, stratum key, prefix-view digest, the complete
ordered candidate IDs/costs/fallback codes/tie digests, chosen cost, and
matching-proof ArtifactRef. A no-trigger task uses only
`kind = "not_applicable_no_trigger"`, task ID, trigger reason, and prefix-view
digest; donor, candidate, cost, fallback, proof, and packet fields are
forbidden. `TaskAssignment.donor_match_kind` is required:
`matched` requires non-null, distinct donor ID/lineage, and
`not_applicable_no_trigger` requires both donor fields null. The receipt set is
non-empty, unique by focal task, and exactly
selected-schedule-covering; matched receipts alone exactly cover the triggered set and
reproduce its donor permutation. N/A tasks still receive the independently
drawn 12-way allocation, N/Z orientation, and four prefix-bound capabilities.
Tests reject a donor or packet ref on N/A and reject N/A on a triggered task.

The ledger mode is closed to `synthetic_derangement` and
`confirmation_lineage_matching`. The local synthetic mode uses
`synthetic_cyclic_offset_v1` only on fixture strata after proving at least three
distinct eligible lineages; its receipt says synthetic and can never be
re-labeled. Confirmation mode requires
`exact_constrained_min_cost_v1` and the optimality proof above for every
triggered stratum; the all-no-trigger exception carries no matching algorithm
execution or proof.

Task-specific identifiers are represented as typed references—repository/file,
symbol, test/check, database entity, policy/action, or task record—and replaced
only by the same reference type before injection. The donor assignment is a
derangement: no task donates to itself, no two-task reciprocal pair is allowed
within a block, and the map is frozen before branch outcomes.

The packet builder truncates bounded evidence and uses deterministic neutral
padding to make REAL and SHAM exactly equal in tokenizer length. Both packets
receive the same formatting and padding algorithm. Every truncation records the
original digest/token count, retained token count, rule ID, and omitted count;
nothing is silently dropped. Each packet-pair receipt binds focal/donor
verifier digests, assignment digest, identifier-map digest, tokenizer digest,
normalized findings, padding search, and collision result. All packet-pair
receipts are sealed into one packet-index digest before any branch starts. Raw
real and donor packets remain encrypted at rest. A branch worker may decrypt
only its opaque slot's packet inside the isolated subject-only guidance
boundary; packet text and the decryption capability remain unavailable to the
analysis author until unblinding.

DL-135 strengthens “binds” above to mean independent byte reconstruction, not
receipt agreement. A manifest-pinned internal normalizer derives canonical
typed focal and donor finding blobs directly from the sealed verifier
ArtifactRefs. A canonical typed identifier-map blob deterministically derives a
third, distinct normalized SHAM blob. Canonical policy, pad-unit, template, and
tokenizer contracts are loaded from their ArtifactRefs; the audit reconstructs
the registered tokenizer, reruns truncation/rewrite/collision/padding/rendering,
decrypts packet artifacts only inside a trusted audit boundary, and requires
byte-equal artifacts and receipts. Naked findings, a caller-provided tokenizer,
claimed collision sets, or receipt booleans have no sealing authority.
Synthetic fixture normalizer/tokenizer implementations are closed and named;
confirmation fails closed until separately reviewed SWE and tau normalizers,
tokenizer loaders, and decrypt-for-audit adapters are pinned before the
manifest. An all-no-trigger roster may be sealed from exact typed
marker/roster/ancestry/config-byte closure because every packet-specific gate is
vacuous; every triggered candidate remains non-authoritative until the complete
recomputation path succeeds.

### 7.4 Manipulation and detectability gates

Before confirmation:

1. every REAL finding must validate against its objective verifier artifact;
2. every SHAM packet must be false or irrelevant for the focal prefix under a
   collision checker;
3. a blinded packet classifier must have cross-validated AUROC whose upper 95%
   task-lineage bootstrap bound is below 0.60;
4. token count, field count, severity, truncation, and formatting distributions
   must satisfy the preregistered balance checks; and
5. manual or independent blind audit must find no arm-revealing identifier in
   the fixed audit sample.

Failure is `packet_invalid`; it blocks confirmation rather than inviting a
post-hoc rewrite after outcomes.

## 8. Outcomes and estimands

### 8.1 Primary outcome

`success` is the benchmark's objective binary endpoint:

- SWE: all target and regression checks pass in the clean final grader.
- τ³: all eligible objective components pass under v1.0.1.

All allocated blocks remain in ITT. An arm-specific infrastructure or model
failure is zero. A preregistered, arm-blind provider-outage receipt created
before any endpoint is readable may trigger one full four-arm rerun with the
identical snapshot, seeds, and allocation. If that rerun cannot complete, all
four outcomes are zero through a fail-closed finalizer that validates both
attempts and the original pre-endpoint outage, emits four adverse-zero
execution receipts, and never calls the endpoint grader. No allocated task is
excluded or replaced.

Workers therefore stop at sealed unscored terminal snapshots. The controller
seals every completed terminal receipt in its chronological attempt; no
superseded or partial-attempt receipt is discarded. It seals four final
completion/failure receipts and any one-time outage/rerun decision before a
grader may read an endpoint. No rerun interface accepts a graded receipt. A
no-intervention prefix launches no branch worker and records four copies of
`Y_0`.

For arm `a`, let
`f_a = 1/2 * (mean_i failure_SWE,i,a + mean_i failure_TAU,i,a)`.
The registered differential-failure gate is
`max_(a,a') |f_a - f_a'| <= 0.02`. Larger imbalance marks the pipeline invalid;
it never licenses task deletion.

### 8.2 Primary estimands

Let `Y_R`, `Y_S`, `Y_N`, and `Y_Z` denote REAL, SHAM, NONE, and RESAMPLE task
success. Let `Y_0` denote the disposable prefix-state score.

```text
no_feedback = (Y_N + Y_Z) / 2

content effect       Δ_content     = Y_R - Y_S
causal excess        Δ_excess      = Y_R - no_feedback
sham-packet effect       Δ_sham_packet = Y_S - no_feedback
continuation gain        Δ_continuation = no_feedback - Y_0
total verifier gain      Δ_total = Y_R - Y_0
resampling drift         Δ_null = Y_Z - Y_N
```

The two co-primary estimands are `Δ_content` and `Δ_excess`. Both must clear the
registered resolution gate. `Δ_continuation`, `Δ_sham_packet`, and `Δ_null`
are required decompositions, not optional diagnostics. `Δ_sham_packet`
combines packet form, extra tokens, mismatched content, and any misinformation
cost; it is not a pure apparatus estimand.

The primary cross-setting estimator gives SWE and τ³ equal weight, then averages
within benchmark over its fixed task roster. Benchmark-specific estimates are
always reported. Raw rows are never pooled as if the environments were one
exchangeable population.

### 8.3 Secondary outcomes

- benchmark-native partial reward;
- target-test gain and regression creation for SWE;
- evaluator-component gain for τ³;
- completion, refusal, malformed-action, timeout, and cap-binding rates;
- generated tokens, model calls, tool calls, verifier runtime, endpoint runtime,
  and wall clock;
- state-edit distance and action-path divergence after the intervention;
- packet acknowledgement and cited-finding rate; and
- arm-blinded judge score and reliability, if the API sidecar runs.

## 9. Inference, resolution, and verdicts

### 9.1 Finite-roster estimand and assignment

Index benchmark `b` in `{SWE, TAU}`, frozen task-prefix block
`i = 1, ..., n_b`, and four opaque continuation slots `j = 1, ..., 4`. Before
any continuation outcome, each slot receives an independently generated,
digest-bound seed stream and execution-order/hardware-lane label. Let
`Y_bij(a)` be the binary endpoint slot `j` would produce under
`a` in `{R, S, 0}`—REAL, SHAM, or no packet—conditional on the frozen task,
prefix, packets, software, quotas, and slot. Branch isolation and no
interference are required validity conditions.

Each task schedule serializes four slots in canonical ordinal order `0,1,2,3`.
The array position is the slot ordinal. `execution_order` is a separate
permutation field and never reorders the serialized array or changes treatment
mapping. Using token order `NO_PACKET < REAL < SHAM`, the frozen allocation
table is:

| index | slot 0 | slot 1 | slot 2 | slot 3 |
| ---: | --- | --- | --- | --- |
| 0 | NO_PACKET | NO_PACKET | REAL | SHAM |
| 1 | NO_PACKET | NO_PACKET | SHAM | REAL |
| 2 | NO_PACKET | REAL | NO_PACKET | SHAM |
| 3 | NO_PACKET | REAL | SHAM | NO_PACKET |
| 4 | NO_PACKET | SHAM | NO_PACKET | REAL |
| 5 | NO_PACKET | SHAM | REAL | NO_PACKET |
| 6 | REAL | NO_PACKET | NO_PACKET | SHAM |
| 7 | REAL | NO_PACKET | SHAM | NO_PACKET |
| 8 | REAL | SHAM | NO_PACKET | NO_PACKET |
| 9 | SHAM | NO_PACKET | NO_PACKET | REAL |
| 10 | SHAM | NO_PACKET | REAL | NO_PACKET |
| 11 | SHAM | REAL | NO_PACKET | NO_PACKET |

For canonical task ID `t`, draw:

```text
(allocation_index, allocation_counter) =
    UNIFORM_BELOW(
        K_allocation,
        FRAME("allocation-v1", [TEXT(t)]),
        12,
    )

(orientation_bit, orientation_counter) =
    UNIFORM_BELOW(
        K_orientation,
        FRAME("orientation-v1", [TEXT(t)]),
        2,
    )
```

Let `q0 < q1` be the two no-packet slot ordinals in the selected row. Bit `0`
means `q0 = NONE, q1 = RESAMPLE`; bit `1` means
`q0 = RESAMPLE, q1 = NONE`. This is the only NONE/RESAMPLE convention. An
`AllocationReceipt` stores the task ID, slot IDs by ordinal, table index, both
accepted counters, orientation bit, and four capabilities. A verifier indexes
the table and applies the bit to reconstruct the full arm map; a separately
claimed `slot_arms` mapping has no authority.

The ledger serializes assignments, allocation receipts, and donor receipts in
the schedule's canonical task order. Within a task, slot IDs, arms, and
capabilities are ordinal `0..3`, never execution order. Candidate, solver, and
proof rows follow section 7.3's explicit focal/tie/offset orders. A permutation
that describes the same abstract map but changes bytes is rejected.

Each opaque capability is:

```text
HMAC-SHA256(
    K_capability,
    FRAME(
        "slot-capability-v1",
        [
            TEXT(study_id),
            BYTES(manifest_sha256),
            BYTES(schedule_sha256),
            BYTES(prefix_index_sha256),
            TEXT(task_id),
            TEXT(slot_id),
            TEXT(arm),
        ],
    ),
)
```

All four capabilities per task and all capabilities globally must be unique.
For the section-4.0 known-answer context, prefix digest `0x33` repeated 32 times,
task `task-1`, slot `slot-0`, and arm `REAL`, the capability is
`37004070f63a631313c50aceb2d14db47eaa731d8635455d4d69cabd1818b7e2`.

The registry, manifest roster/eligibility, completed power final, selected
schedule membership, three commitments, prefix/slot seeds, canonical task/slot
order, randomized execution order, and provider schedule are digest-bound
before prefixes. After exact selected-schedule coverage of all common prefixes
and verifier artifacts is frozen, the matching ledger is sealed and each
scheduled task receives its separate 12-way and orientation draw, all before a
packet or branch-continuation artifact exists. Arm draws do not consume `Y_0`,
counters, timing, cost, raw references, donor identity, candidate ordering, or
any branch field. Roster and provider schedules may be blocked by benchmark,
language, domain, or declared replication block; arm allocations are not
coupled across tasks.

The finite-roster effects give each benchmark weight one half and average over
the four frozen seed/slot realizations:

```text
tau_content =
    sum_b [1 / (2 n_b)]
    * sum_i [1/4 * sum_j {Y_bij(R) - Y_bij(S)}]

tau_excess =
    sum_b [1 / (2 n_b)]
    * sum_i [1/4 * sum_j {Y_bij(R) - Y_bij(0)}]
```

Their unbiased observed estimators use
`d_content,bi = Y_R - Y_S`,
`d_excess,bi = Y_R - (Y_N + Y_Z)/2`, and
`hat_tau_k = sum_b [1/(2 n_b)] sum_i d_k,bi`.

The branch slot is the treatment-assignment unit; task prefix is the randomized
block and analysis cluster. With one prefix per task, inference is conditional
on those realized prefixes and measures post-trigger continuation variation,
not whole-run randomness or an unrestricted population of unseen
repositories. For a task that terminates before the trigger, all three
potential outcomes equal its terminal prefix grade. It remains in the primary
ITT analysis with zero contrast. Trigger-eligible effects are secondary.
Provider placement is not randomized into the primary effect; a different
kernel, precision, or provider is a separate replication block.

The analysis loads the immutable roster only through study-manifest ancestry
and rejects missing/extra task rows or changed benchmark, language/domain, or
issue-family membership before computing any statistic. A claimed roster
digest without the referenced bytes has no authority.

### 9.2 Finite-sample sharp-null tests

Exact Fisher tests are reported for sharp unit-level nulls; they are not called
confidence procedures for weak average-effect nulls.

For `H_content^sharp: Y_ij(R) = Y_ij(S)` for every slot, the test conditions on
the two slots occupied by `{R, S}` and independently swaps R/S within each task.
Its one-sided statistic is `hat_tau_content`.

For `H_excess^sharp: Y_ij(R) = Y_ij(0)` for every slot, the test conditions on
the SHAM slot and independently chooses which of the other three slots receives
REAL, with probability one third. Its one-sided statistic is
`hat_tau_excess`.

Exact product-randomization tails are computed by enumeration or dynamic
programming where feasible. Otherwise a valid Monte Carlo Fisher test uses
999,999 digest-bound draws, add-one p-values
`(1 + count(T* >= T_obs)) / (B + 1)`, and a reported Monte Carlo standard
error. Because the scientific alternative is the intersection
`{tau_content > 0 AND tau_excess > 0}`, the sharp-null decision is an
intersection-union test: both local one-sided p-values must be at most 0.05;
that conjunction needs no multiplicity correction.

An omnibus Fisher test of
`H_all^sharp: Y_ij(R) = Y_ij(S) = Y_ij(0)` redraws the full 12-way allocation
within every task, recomputes studentized `T_content` and `T_excess`, and uses
`max(T_content, T_excess)`. Its max-T p-value is exact for that global sharp
null only when enumerated, and otherwise is a valid add-one Monte Carlo Fisher
test. Define
`T_k = hat_tau_k / sqrt(Var_pi(hat_tau_k | unordered slot outcomes))`; if the
conditional variance is zero, set `T_k = 0` when `hat_tau_k = 0` and block the
test otherwise. The omnibus result is not a test or interval for weak average
nulls.

### 9.3 Simultaneous average-effect lower bounds

Average-effect inference uses a benchmark-stratified, task-cluster,
Romano-Wolf single-step multiplier max-t procedure. Let
`d_bi = (d_content, d_excess)'`, `bar_d_b` be its benchmark mean, and:

```text
S_b =
    1 / (n_b - 1)
    * sum_i (d_bi - bar_d_b)(d_bi - bar_d_b)'

V_hat = 1/4 * sum_b S_b / n_b
se_k  = sqrt(V_hat[k,k])
```

For each of 99,999 frozen Rademacher multiplier draws:

```text
G* =
    1/2 * sum_b 1/n_b
    * sum_i xi_bi * sqrt(n_b/(n_b-1)) * (d_bi - bar_d_b)

Z*_k = G*_k / se_k
M*   = max(Z*_content, Z*_excess)
```

Sort the `B = 99,999` realized max statistics and take the 1-based order
`min(B, ceil((B + 1) * 0.95))`, without interpolation, as `c_0.95`. The
simultaneous one-sided bounds are
`L_k = hat_tau_k - c_0.95 * se_k`. These bounds are
asymptotically valid/Neyman-conservative under independent randomized task
blocks; they are not finite-sample exact. A zero/non-finite standard error or a
failed no-interference receipt blocks a positive claim.

The positive claim requires:

- both local Fisher p-values—enumerated exact or add-one Monte Carlo—at most
  0.05;
- both simultaneous average-effect lower bounds above zero;
- both point estimates at least the practical screen `delta_star = 0.05`;
- both point estimates strictly above `r95`;
- non-negative point estimates in each benchmark separately; and
- for every co-primary contrast `k` and preregistered sensitivity group `h`
  (SWE language; τ³ domain and telecom issue family), the equal-benchmark
  estimator recomputed after deleting `h` and renormalizing within that
  benchmark satisfies `hat_tau_k^(-h) >= -0.05`; and
- the maximum pairwise difference among equal-benchmark-weighted arm-specific
  infrastructure-failure rates is at most 0.02.

`delta_star` is a preregistered observed-effect screen, not a confidence claim
that either effect is at least five percentage points. The paper may say the
effects were positive and large enough to resolve under this design; it may not
say a five-point minimum was established unless both simultaneous lower bounds
themselves exceed 0.05.

The secondary endpoint family is exactly
`(sham_packet, continuation, total)`. The same task-cluster Rademacher draws
produce marginal one-sided add-one multiplier p-values, Holm-adjusted across
these three, and a separate three-contrast single-step max-t 95% lower-bound
family. Holm adjusts p-values, not bounds. Benchmark-specific families use Holm
correction separately. Confidence
intervals, exact discordant-pair counts, and all estimates are reported
regardless of significance.

### 9.4 Resampling-null resolution

NONE and RESAMPLE are exchangeable no-payload replicates assigned to IID frozen
continuation slots. Let `D_bi = Y_biZ - Y_biN` and
`w_bi = 1 / (2 n_b)`. The analysis reports:

```text
q0  = sum_bi w_bi * |D_bi|

R(epsilon) =
      |sum_bi w_bi * epsilon_bi * D_bi|

r95 = inf {
          r : Pr_epsilon[R(epsilon) <= r] >= 0.95
      },
      with
          epsilon_bi independently in {-1, +1}
```

`q0` is the observed per-task no-feedback discordance. `r95` is the
aggregate label-swapped placebo-contrast scale. The sign-flip distribution is
exact under exchangeability of the two no-payload labels. When
`n_SWE = n_TAU = n` and `m` controls are discordant, it is the 0.95 quantile of
`|2K - m| / (2n)` for `K ~ Binomial(m, 1/2)`; otherwise the implementation uses
an exact weighted convolution. `q0` and `r95` are not confidence intervals,
semantic-verifier uncertainty, or minimum detectable effects.

`Δ_null = sum_bi w_bi D_bi` is only a randomized-label balance diagnostic.
There is no mean-equivalence gate: cancellation could make one pass under
maximal unit-level instability. Failure of either co-primary point estimate to
exceed both `delta_star` and `r95` produces `UNRESOLVED_RESAMPLING`, even when a
conventional p-value for REAL is small.

### 9.5 Power and roster tier

Before any confirmation outcome exists, deterministic P0 evaluates C120 and
C160 with the production assignment, local sharp tests, `q0/r95`, point gates,
and verdict logic. A synthetic roster may validate code/runtime conditionally,
but it has no tier-selection authority. The decisive P0 run occurs only after
the eligible registry freezes exact C120/C160 membership plus every SWE
language, τ³ domain, and telecom issue-family label, and it executes all
corresponding leave-one-group gates. The powered alternative is frozen at
full-roster ITT effects
`(tau_content, tau_excess) = (0.15, 0.15)` in each benchmark.

Power authority is never a caller-selected string. Before a screen, a trusted
controller writes one closed canonical
`application/vnd.pneuma.power-authority+json` blob. It is a referenced blob,
not a thirteenth scientific record kind, and has exactly one of these arms:

```json
{
  "authority_kind": "synthetic_validation",
  "manifest_ref": {"byte_count": 1, "media_type": "application/json", "relative_path": "<relative>", "role": "study_manifest", "sha256": "<sha256>"},
  "roster_ref": {"byte_count": 1, "media_type": "application/json", "relative_path": "<relative>", "role": "power_roster", "sha256": "<sha256>"},
  "schema_version": "1",
  "tier_membership_sha256": "<sha256>"
}
```

or:

```json
{
  "authority_kind": "roster_bound_selection",
  "eligibility_manifest_ref": {"byte_count": 1, "media_type": "application/json", "relative_path": "<relative>", "role": "eligibility_manifest", "sha256": "<sha256>"},
  "manifest_ref": {"byte_count": 1, "media_type": "application/json", "relative_path": "<relative>", "role": "study_manifest", "sha256": "<sha256>"},
  "roster_ref": {"byte_count": 1, "media_type": "application/json", "relative_path": "<relative>", "role": "power_roster", "sha256": "<sha256>"},
  "schema_version": "1",
  "tier_membership_sha256": "<sha256>"
}
```

The displayed positive byte counts are illustrative; every object uses the
shared closed `ArtifactRef`. Both arms require the roster ref to equal the
study manifest's roster ref. The synthetic arm additionally requires the
manifest's `eligibility_manifest_ref` to be null. The roster-bound arm requires
its eligibility ref to byte-equal the manifest's non-null
`eligibility_manifest_ref`; neither its sealing transaction nor its CLI accepts
another eligibility path/ref. From the referenced roster bytes both arms
reconstruct exactly this digest payload:

```json
{
  "rows": [
    {
      "benchmark": "<SWE-or-TAU>",
      "groups": [{"kind": "<language-domain-or-issue_family>", "value": "<value>"}],
      "task_id": "<canonical-id>",
      "tiers": [120, 160]
    }
  ],
  "schema_version": "1"
}
```

Rows are unique and sorted by strict UTF-8 `(benchmark, task_id)`, `tiers` is a
strictly increasing non-empty subset of `[120, 160]`, and groups are unique in
the section-9.1 kind/value order. The exact field set is closed.
`tier_membership_sha256` is
`SHA256(canonical_json_bytes(payload, indent=None))`; the authority blob's value
must equal this recomputation. The synthetic arm
additionally requires the roster's closed `roster_kind` to be
`synthetic_fixture` and forbids an eligibility ref. The roster-bound arm
requires `roster_kind = "eligible_confirmation"`, reloads the base-commit
eligibility manifest only through the study manifest, verifies its study ID,
commitment/reveal, accepted/rejected, reserve, roster, and group derivation, and
proves that its accepted-task set and nested C120/C160 membership reproduce the
roster and every registered group label exactly. A caller cannot convert one
arm to the other by changing `authority_kind`, nor fabricate a post-seal
eligibility source: the required references and their closed payloads would
fail.

Every `screen`, `shard`, `selection`, `validation`, and `final` power report
parents this authority ArtifactRef plus the exact grid ArtifactRef and the exact
screen-topology ArtifactRef. Its displayed `decision_authority`, `roster_ref`,
and tier-membership digest are derived mirrors and must be reproduced from the
authority blob at every stage. The grid and screen topology are copied and
content-addressed into the study manifest before the first screen; every power
stage requires its refs to equal the manifest's `power_grid_ref` and
`power_screen_topology_ref`. Downstream producers reload them through those refs
and require byte equality with every parent. Every stage also persists the
grid-derived RNG-contract digest and its stage/phase-derived kernel ID; screens
freeze the generation's shard count and every descendant rechecks it. No CLI or
library call accepts a free decision-authority, roster label, RNG seed, kernel,
execution mode, or post-screen shard count.

For each benchmark, the nuisance tuple is:

- no-feedback success `p0` in `{0.10, 0.40, 0.70}`;
- exact trigger opportunity `gamma` in `{0.60, 0.75, 0.90}`; and
- latent within-task equicorrelation `rho` in `{0.00, 0.40, 0.80}`.

The Cartesian product across SWE and τ³ contains 27 × 27 = 729 alternative
cells. On a no-trigger block, P0 draws `B ~ Bernoulli(p0)` and sets
`(R, S, N, Z) = (B, B, B, B)`. On a triggered block, it draws a four-variate
Gaussian copula with equicorrelation `rho` and thresholds it to marginals:

```text
p_R = p0 + 0.15 / gamma
p_S = p_N = p_Z = p0
```

These choices keep every probability in `[0.10, 0.95]` and make each
benchmark's expected ITT content and excess effects exactly 0.15. For each
benchmark, set `m_b = gamma * n_b` exactly; every registered combination makes
`m_b` integral. Uniformly select an exact-size triggered subset through
deterministic multivariate-hypergeometric counts over the roster's joint
sensitivity-group cells. A digest-pinned deterministic normal-rectangle
implementation precomputes the 16 triggered Bernoulli-pattern probabilities
and draws each cell's counts as `Multinomial(m_cell, pi_trigger)`. For that
cell's no-trigger tasks, draw
`U_cell ~ Binomial(n_cell - m_cell, p0)`, assign `U_cell` to pattern `1111`, and
assign the remainder to `0000`. These cell counts feed the same scalar/
vectorized sufficient-statistics gate kernel used by final analysis. P0 uses a
counter-based PRNG and 20,000 datasets per cell.

For power simulation only, the 99,999-draw multiplier critical value is
replaced with its deterministic two-dimensional Gaussian-max analogue:
`r = V_hat_CE / (se_C se_E)` and `c` solves
`Phi_2(c, c; r) = 0.95`. The worst five C160 cells, selected by the lowest
unrounded alternative gate-pass estimate (ties by frozen cell order) before
any confirmation outcome, must validate this
approximation against the full multiplier routine on 2,000 outer datasets.
Validation passes only if every selected cell's absolute difference between
Gaussian-max and full-multiplier gate-pass rates is at most 0.01 and both
methods choose the same roster tier. Otherwise P0 runs the full multiplier
routine on every cell under a separately screened
`full_multiplier_fallback` phase or records the authority-appropriate terminal
arm: roster-bound `FEASIBILITY_NO_GO` or nondecisive synthetic
`synthetic_validation_failed`. Failed and superseded attempts remain in the
final report's ancestry. The first fallback screen must parent the latest
completed, failed Gaussian validation for the same authority/grid/topology;
that typed ref closes the Gaussian phase, so no later Gaussian generation is
legal. Later fallback validation/finalization derive that ref only through the
screen and reject a replacement. A successful fallback emits a phase-specific
validation receipt that checks full ordered cell coverage, raw counts, numeric
receipts, and tier decision directly; it does not fabricate or reuse a Gaussian
worst-five selection.

The numeric contract is frozen:

- `rho` is latent-Gaussian equicorrelation, not observed Bernoulli
  correlation;
- triggered 16-pattern probabilities use the one-factor representation and
  96-point Gauss-Hermite quadrature;
- probability sum and every recovered marginal must be within `1e-10`;
- the bivariate-normal CDF uses 128-point Gauss-Legendre quadrature over
  Plackett's correlation integral;
- Gaussian-max correlations `+1` and `-1` use the analytic one-sided-normal and
  two-sided-normal limits, respectively;
- the Gaussian-max root uses bisection tolerance `1e-10` and at most 200
  iterations; and
- separate one-sided Clopper-Pearson lower/upper inversions receive the full
  registered tail probability, use binomial-tail bisection tolerance `1e-12`,
  and use at most 200 iterations.

The manifest-pinned grid contains every scientific `PowerConfig` number above
plus exactly this public RNG subobject:

```json
{
  "bit_generator": "numpy.random.Philox",
  "contract_id": "power-philox-v1",
  "counter_fields": [
    "draw_domain",
    "phase",
    "cell_id",
    "replicate_index",
    "draw_kind",
    "draw_index"
  ],
  "counter_frame": "power-rng-counter-v1",
  "draw_domains": ["screen", "grid", "validation"],
  "draw_kinds": [
    "screen_trigger_partition",
    "screen_triggered_pattern",
    "screen_no_trigger_success",
    "grid_trigger_partition",
    "grid_triggered_pattern",
    "grid_no_trigger_success",
    "gaussian_validation_trigger_partition",
    "gaussian_validation_triggered_pattern",
    "gaussian_validation_no_trigger_success",
    "multiplier_rademacher"
  ],
  "integer_encoding": "unsigned-big-endian",
  "key_fields": [
    "root_u64",
    "authority_kind",
    "tier_membership_sha256_raw32",
    "grid_content_sha256_raw32"
  ],
  "key_frame": "power-rng-key-v1",
  "numpy_version": "2.3.5",
  "root_u64": 7640891576956012809
}
```

Array order is normative. Unknown RNG fields or another root, version,
algorithm, frame label, field/domain/kind order, or integer encoding reject the
grid.
`rng_contract_sha256` is
`SHA256(canonical_json_bytes(rng_subobject, indent=None))`. Each stochastic
operation constructs a fresh generator with:

```text
key_digest = SHA256(FRAME(
    "power-rng-key-v1",
    [
        U64(root_u64),
        TEXT(authority_kind),
        BYTES(hex_decode(tier_membership_sha256)),
        BYTES(hex_decode(grid_content_sha256)),
    ],
))
key = UINT128_FROM_BE(key_digest[0:16])

counter = UINT256_FROM_BE(SHA256(FRAME(
    "power-rng-counter-v1",
    [
        TEXT(draw_domain),
        TEXT(phase),
        TEXT(cell_id),
        U64(replicate_index),
        TEXT(draw_kind),
        U64(draw_index),
    ],
)))

generator = numpy.random.Generator(
    numpy.random.Philox(counter=counter, key=key)
)
```

`UINT128_FROM_BE` and `UINT256_FROM_BE` mean unsigned big-endian conversion of
exactly 16 and 32 bytes. `draw_domain` is closed to `screen`, `grid`, or
`validation`; `phase` is the report's closed phase. A screen uses domain
`screen`, every canonical cell ID, and replicates `0..199`. A production or
fallback shard uses domain `grid`, the screen's phase, every canonical cell ID
assigned to that worker, and replicates `0..19999`. Gaussian validation uses
domain `validation`, phase `gaussian_approximation`, the five frozen cell IDs,
and outer replicates `0..1999`. Full-multiplier validation uses the same
mapping with phase `full_multiplier_fallback` and its full ordered cells.
Generation, shard count, and shard index are intentionally absent from both
key and counter: they are execution/ancestry metadata, never scientific
randomness. Cell ordinal `j mod shard_count` only routes a logical cell to a
worker. Repartitioning, resuming, or incrementing the immutable screen
generation therefore reproduces byte-identical merged counts for the same
authority-kind/scientific-roster/grid/phase. Rescreening also reuses the
identical fixed screen draws; timing consumes no additional random stream.

`authority_kind` is the closed, manifest-derived
`synthetic_validation` or `roster_bound_selection` arm.
`tier_membership_sha256` is recomputed from the exact canonical scientific
roster payload in section 9.1, and `grid_content_sha256` is recomputed from the
closed canonical grid bytes. The key frames their decoded raw 32-byte digests,
not hex text. Study ID, timestamps, manifest/authority ArtifactRef identity,
relative paths, and screen-topology metadata are deliberately absent. Resealing
scientifically identical roster/grid bytes under another study/path/topology
therefore cannot refresh the draws; changing authority kind, scientific roster
membership, or scientific grid content does.

`draw_kind` is closed to `screen_trigger_partition`,
`screen_triggered_pattern`, `screen_no_trigger_success`,
`grid_trigger_partition`, `grid_triggered_pattern`,
`grid_no_trigger_success`, `gaussian_validation_trigger_partition`,
`gaussian_validation_triggered_pattern`,
`gaussian_validation_no_trigger_success`, and `multiplier_rademacher`.
For partition/pattern/success calls, `draw_index` is the canonical joint-group
cell ordinal. For multiplier weights it is
`multiplier_ordinal * selected_task_count + canonical_task_ordinal`. Each fresh
generator performs exactly one corresponding pinned NumPy distribution call.
Selection and finalization consume no random bytes but persist and recheck the
same RNG-contract digest. No seed, generator, skip count, or cherry-picked
counter is caller input, and an operator cannot obtain a fresh scientific draw
by abandoning an attempt, changing topology, or incrementing generation.

Kernel selection is also closed and derived:

| stage | parent screen phase | `kernel_id` |
| --- | --- | --- |
| screen | `gaussian_approximation` | `power-screen-gaussian-v1` |
| shard | `gaussian_approximation` | `power-grid-gaussian-v1` |
| selection | `gaussian_approximation` | `power-worst-five-selection-v1` |
| validation | `gaussian_approximation` | `power-gaussian-vs-multiplier-validation-v1` |
| final | `gaussian_approximation` | `power-final-gaussian-v1` |
| screen | `full_multiplier_fallback` | `power-screen-full-multiplier-v1` |
| shard | `full_multiplier_fallback` | `power-grid-full-multiplier-v1` |
| validation | `full_multiplier_fallback` | `power-full-grid-validation-v1` |
| final | `full_multiplier_fallback` | `power-final-full-multiplier-v1` |

`selection` is forbidden for the fallback phase. A stage reloads its parent
screen and derives the one legal row; a free `mode`/kernel string or a
cross-phase relabel fails.

P0 first screens 200 datasets per cell on the declared CPU topology. The
projected full-grid wall time must be at most 12 hours and the screen must
reproduce numeric fixture digests before the 20,000-dataset run starts.
The screen freezes a positive `shard_count`; all shard, selection, validation,
and selected-final references must reproduce it. Otherwise the implementation
is vectorized/partitioned and re-screened under an incremented immutable
generation, which may declare a different count without mutating the failed
screen. A Gaussian screen forbids `fallback_trigger_ref`. A fallback screen
requires it, reloads it as the maximal-generation completed Gaussian
validation for the same authority/grid/topology whose approximation gate
failed, and persists it in `parent_refs`; once sealed, it forbids another
Gaussian screen. If a roster-bound attempt remains
infeasible, the study records `FEASIBILITY_NO_GO`; if a synthetic-validation
attempt remains infeasible, it records the distinct nondecisive
`synthetic_validation_failed` finalization described below. Every power
artifact records its authority ref, derived decision authority, derived roster
and membership digest, grid ref, screen-topology ref, RNG-contract digest,
phase, generation, stage, derived kernel ID, and frozen shard count and, for
shards, shard index. A final report carries the common RNG-contract digest plus
the selected/terminal phase's derived kernel ID and shard count. The complete
power/type-I report parents every attempt. Its closed finalization is a
phase-specific completed chain, a roster-bound terminal feasibility no-go, or a
synthetic-only terminal validation failure, always without fabricated
downstream refs. Once final is sealed, the authority accepts no later attempt
stage or second final.

Finalization is authority-discriminated. A roster-bound completed chain has
`selected_tier` 120 or 160 and `decision = "GO"`. A synthetic-validation
completed chain has `selected_tier = null` and
`decision = "CONDITIONAL_ONLY"`. A `feasibility_no_go` has
`selected_tier = null` and `decision = "NO_GO"` and is legal only for
`roster_bound_selection`. A `synthetic_validation_failed` finalization has
`selected_tier = null`, `decision = "CONDITIONAL_ONLY"`, a terminal
attempt/stage, and a closed nondecisive failure reason; it is legal only for
`synthetic_validation`. The final report's authority blob and every selected
parent must reproduce these fields exactly.

The terminal reason enum is closed to
`gaussian_screen_exhausted`, `full_multiplier_screen_exhausted`,
`numeric_fixture_failed`, `runtime_bound_exceeded`, `attempt_incomplete`, and
`power_or_type_i_gate_failed`; the synthetic-only arm additionally permits
`synthetic_validation_gate_failed`. `attempt_incomplete` is reserved for an
attempt whose required next stage never completed. A persisted, schema-valid
`validation` record is definitionally completed and can never be described as
`attempt_incomplete`; an incomplete validation attempt names the last completed
pre-validation stage instead. A completed, schema-valid roster-bound validation
with decision `NO_GO` and no selected tier must finalize at stage `validation`
with `power_or_type_i_gate_failed`. A completed synthetic validation that fails
its registered machinery/approximation checks uses
`synthetic_validation_failed` at stage `validation` with
`synthetic_validation_gate_failed`.

Power finalization is a hard pre-prefix transaction. `seal_prefix_schedule`
accepts the final power-report ArtifactRef, reloads its complete attempt
ancestry, and stores `power_final_ref`, `schedule_authority`,
`selected_tier`, and `selected_membership_sha256`. A confirmation schedule
requires a roster-bound `completed_chain` with `decision = "GO"` and tier 120
or 160. It reloads the manifest-pinned eligibility/roster bytes and includes
exactly the tasks whose tier list contains that selected tier. A synthetic
schedule requires a synthetic `completed_chain` with
`decision = "CONDITIONAL_ONLY"` and null tier and includes the complete closed
fixture roster. A feasibility no-go, synthetic validation failure, incomplete
attempt, mismatched authority, or post-seal eligibility file cannot schedule a
prefix.

The selected-membership digest has exactly this preimage:

```json
{
  "rows": [
    {
      "benchmark": "<SWE-or-TAU>",
      "groups": [{"kind": "<language-domain-or-issue_family>", "value": "<value>"}],
      "task_id": "<canonical-id>"
    }
  ],
  "schedule_authority": "<synthetic_validation-or-roster_bound_selection>",
  "schema_version": "1",
  "selected_tier": 120
}
```

For synthetic authority, `selected_tier` is JSON null. Rows are unique and
strict-UTF-8 sorted by `(benchmark, task_id)` and group labels use the frozen
kind/value order. `selected_membership_sha256` is
`SHA256(canonical_json_bytes(preimage, indent=None))`. The schedule task array
may use its registered execution ordering, but its task/group set must
reproduce this preimage exactly. Every prefix receipt, assignment, packet,
task block, projection, and analysis covers the selected schedule membership,
not an unselected manifest superset. Because schedule sealing validates an
existing final ArtifactRef, the selected power result is hash-ancestral to
every prefix and therefore cannot be chosen from observed outcomes.

The type-I audit uses the same 729 nuisance pairs for each of three boundaries:

```text
A: both null
   p_R = p_S = p_N = p_Z = p0

B: content null, excess +0.15
   p_R = p_S = p0 + 0.15/gamma
   p_N = p_Z = p0

C: excess null, content +0.15
   p_R = p_N = p_Z = p0 + 0.15/gamma
   p_S = p0
```

The tier passes only when simultaneous exact-binomial Monte Carlo bounds
establish:

```text
min_theta P_theta(
    all statistical CAUSAL_CONTENT gates pass
    | alternative and nonstatistical gates pass
) >= 0.80

max_theta P_theta(
    statistical CAUSAL_CONTENT decision
    | either co-primary null and nonstatistical gates pass
) <= 0.05
```

For the 729 alternative cells, every one-sided Clopper-Pearson lower bound uses
tail probability `0.05 / 729`. For the 3 × 729 = 2,187 null-boundary cells,
every upper bound uses `0.05 / 2,187`. This is joint intersection power and a
familywise type-I audit, not marginal power for either contrast. The ordered
cell manifest, numeric routines, simulation count, validation cells, RNG
mapping, and raw counts are digest-bound. P0 also runs adversarial fixtures
with asymmetric sham harm, differential branch failure, and no-feedback
marginal imbalance; those must fail the applicable validity gate but do not
enter sample-size selection.

The preferred tier is `C160`, 160 tasks per benchmark. `C120`, 120 tasks per
benchmark, is the minimum. Preliminary planning says 120 paired binary units
per benchmark have about 80% power only for effects near 17 points at
discordance 0.40; that estimate is not a registered power result. If the exact
simulator or eligible roster cannot support the minimum tier, the study records
a feasibility no-go instead of shrinking into an anecdote. When a completed
roster-bound validation establishes that neither tier passes the registered
power/type-I gates, its reason is `power_or_type_i_gate_failed`.

Tier selection may use only frozen power output, eligible-roster size, verified
credit, measured p10 throughput, and calendar feasibility. It may not use pilot
arm efficacy.

### 9.6 Verdict taxonomy

Let `hat_tau_sham = SHAM - no_feedback`. It receives the registered one-sided
task-cluster multiplier lower bound `L_sham` from the three-contrast secondary
max-t family and a separately Holm-adjusted one-sided multiplier p-value. Let
`U_content` and `U_excess` be simultaneous
one-sided 95% upper bounds constructed by the same task-cluster max-t method.
Verdicts execute in the order below; `FEASIBILITY_NO_GO` is emitted only by
pre-outcome power/roster/runtime checks, never as a fallback from observed
outcomes.

| verdict | definition |
| --- | --- |
| `FEASIBILITY_NO_GO` | before outcomes, the powered roster/runtime cannot be completed |
| `PIPELINE_INVALID` | packet, snapshot, assignment, no-interference, grader, or differential-failure gate fails |
| `HARMFUL_OR_MISDIRECTING` | for content or excess, the point estimate is at most -0.05 and its simultaneous upper bound is below zero |
| `CAUSAL_CONTENT` | both co-primary contrasts and every registered statistical/resolution/admissibility gate pass |
| `SHAM_PACKET_ONLY` | CAUSAL_CONTENT fails; `hat_tau_sham >= 0.05`, `hat_tau_sham > r95`, the three-family Holm-adjusted sham p-value is at most 0.05, `L_sham > 0`, and content fails at least one of its registered finite-SE/sharp/lower/materiality/resolution/benchmark/sensitivity gates |
| `UNRESOLVED_RESAMPLING` | no earlier outcome verdict applies and a primary SE is invalid or a co-primary point estimate fails `delta_star`/`r95` |
| `RESAMPLING_CONSISTENT` | the valid, resolved remainder: observed REAL gains do not clear the registered inferential controls |

Every verdict is publishable. None authorizes changing endpoints or deleting
failed blocks.

## 10. Pilot and confirmation separation

Pilot rosters are disjoint from confirmation and reserve rosters:

- SWE: 16 pilot tasks, two per language, each from a unique repository.
- τ³: nine pilot tasks, three per domain; telecom contributes one MMS, one
  mobile-data, and one `ACTION + ENV_ASSERTION` service task.

Before the first pilot starts, one eligibility-manifest transaction seals:

1. every accepted/rejected task and qualification receipt;
2. the already-published roster-local-nonce commitment, its label/study
   binding, externally timestamped three-commitment precommit, authenticated
   beacon, verified nonce/final-seed derivation, and ranking implementation
   digest;
3. the complete pilot roster;
4. nested C120 confirmation membership;
5. any eligible C160 extension; and
6. every ordered reserve.

The same frozen bytes drive the roster-bound P0 simulation. A pilot task,
subject outcome, endpoint result, or apparent effect cannot cause a task
replacement or reorder a reserve. A system-level pilot failure blocks the
implementation generation; after repair, the complete pilot repeats on the
same roster under an incremented immutable implementation generation, or the
tier records `FEASIBILITY_NO_GO`.

Pilot outputs can validate:

- snapshot byte equality;
- tool parser and context reconstruction;
- verifier correctness;
- sham detectability;
- trigger opportunity;
- environment/grader flakiness;
- p10 episodes per GPU-hour;
- disk, memory, and network demand; and
- fixed budget adequacy.

Pilot efficacy is labeled and excluded from confirmation. No arm-specific pilot
effect may select a model, benchmark, endpoint, task, reserve, sample tier, or
analysis.

After pilot validation, a fresh context seals:

1. the validated implementation and dependency digests;
2. the already-frozen eligibility manifest and immutable
   pilot/C120/C160/reserve membership;
3. the three distinct commitment values from section 4.0, the assignment
   program/matching-backend digest, and the provider-lane plan;
4. the statistical-analysis source and expected synthetic fixtures;
5. the exact cloud execution manifest; and
6. the preregistration timestamp and digest.

Before confirmation prefixes, the manifest-pinned roster-bound power chain
must close as a completed `GO` final and select C120 or C160. Schedule sealing
parents that final, derives the exact selected membership, and only then
verifies and reveals the schedule seed; the assignment master key remains
unread. Confirmation then runs and seals every scheduled common prefix and
verifier artifact without exposing branch endpoints. After the prefix index
proves exact selected-schedule coverage, the trusted assignment transaction
verifies the master-key commitment, constructs the allowlisted prefix view,
materializes matched donor proofs for triggered tasks plus typed no-trigger N/A
receipts, 12-way arm allocations, N/Z coins, and prefix-bound capabilities,
then discards key buffers. The already-sealed
program constructs and audits every token-matched packet pair, seals the final
packet-index digest, and seals the already-frozen analysis source/config/
projection-schema digest before any branch continuation. A human may inspect
only completeness/validity receipts during that transition, not prefix scores,
verifier content, packet text, allocation, key material, or branch outcome.

Confirmation bytes remain encrypted and unavailable to analysis authors until
the analysis hash and artifact completeness receipt are sealed.

## 11. Optional objective-versus-judge sidecar

If OpenAI and Anthropic credits become verified and eligible, a post-hoc compute
action may run a separately preregistered, arm-blind measurement sidecar.

The judge receives only the final artifact, task statement, frozen rubric, and
objective evidence permitted by the benchmark. It never receives arm labels,
packet text, provider placement, or causal hypotheses. Order is randomized.

The sidecar uses:

- two frozen rubric wordings;
- one OpenAI model and one Anthropic model;
- deterministic or provider-supported seeded settings where available;
- the provider Batch API where compatible; and
- a fixed disagreement-adjudication sample chosen before judge results.

It reports ICC, `ndc`, wording/provider variance, and whether the judge-derived
causal verdict matches the objective verdict. Task/repository is the bootstrap
unit. It reuses the useful measurement-system idea from G1 only after repairing
G1's pooling, bootstrap-unit, calibration-split, provenance, and artifact
defects.

Judge results are secondary and cannot rescue a failed objective claim.

## 12. Artifact and blinding contract

### 12.1 Required records

Every scientific JSON root is validated by one registered schema:

```text
resampling-study-manifest.schema.json
resampling-prefix-schedule.schema.json
resampling-prefix-receipt.schema.json
resampling-assignment-ledger.schema.json
resampling-packet-index.schema.json
resampling-task-block.schema.json
resampling-blinded-projection.schema.json
resampling-analysis-freeze.schema.json
resampling-analysis.schema.json
resampling-power-report.schema.json
resampling-unblind-receipt.schema.json
resampling-artifact-root.schema.json
```

Before Task 3 is implemented, the Task-2 schemas are amended in place; this is
a `0.1.0` pre-release correction, not a second record family. The closed
payload contract requires:

- `resampling_study_manifest`: all frozen source ArtifactRefs plus the exact P0
  grid and declared screen-topology ArtifactRefs, a required
  `eligibility_manifest_ref` discriminated as non-null for
  `eligible_confirmation` and null for `synthetic_fixture`,
  `commitment_scheme = "resampling-null-key-ceremony-v1"` and the exact
  `roster_local_nonce_commitment_sha256`,
  `schedule_seed_commitment_sha256`, and
  `assignment_master_key_commitment_sha256` fields;
- `resampling_prefix_schedule`: `manifest_ref`, completed `power_final_ref`,
  closed `schedule_authority`, derived `selected_tier`,
  `selected_membership_sha256`, verified `schedule_seed`, and non-empty
  canonical `tasks`; assignment-program and provider-lane assets are loaded
  through the manifest and are not free inputs;
- `resampling_prefix_receipt`: `schedule_ref` and non-empty
  `task_receipts`;
- `resampling_assignment_ledger`: `manifest_ref`, `schedule_ref`,
  `prefix_index_ref`, manifest-equal `matching_program_ref`, assignment-key
  commitment, assignment-prefix-view digest, closed assignment mode,
  exact `matching_proof_refs`, and non-empty `assignments`,
  `allocation_receipts`, and
  `donor_match_receipts`; and
- `resampling_artifact_root`: the full record/blob entries plus the verified
  typed semantic-ancestry closure described below.

Assignment mode is an enum, never an arbitrary non-empty string. The three
assignment arrays are unique by task ID, have `minItems: 1`, cover exactly the
selected schedule membership once, and agree on donor, table
index/orientation, slot order, arm map, commitments, and parents.
`DonorMatchReceipt` is a closed `oneOf`:
`matched` has the full candidate/proof payload, while
`not_applicable_no_trigger` forbids donor/candidate/proof/packet fields.
`TaskAssignment` has the matching closed `donor_match_kind` discriminator:
matched requires non-null donor ID/lineage and N/A requires both null.
Matched receipts and donor permutations cover exactly the triggered subset;
the N/A arm covers exactly the no-trigger subset; their union covers the roster.
Matching-proof refs are unique and empty iff the triggered subset is empty;
otherwise they cover every triggered matching stratum exactly once.
The prefix view forbids precomputed count/length bands and claimed telecom
fallback availability; validators derive them from parent bytes and the
manifest-pinned program. Matching proof, exact problem, and exact solution
blobs are not new scientific record kinds, but their media types select the
closed section-7.3 grammar; validators require canonical bytes and recursively
follow every nested ArtifactRef. Its candidate rows are closed schema
definitions; the synthetic
algorithm/mode pair and confirmation algorithm/mode pair cannot cross. Prefix
receipts likewise have `minItems: 1` and exact selected-schedule coverage.
The power-authority blob is handled identically: its media type selects the
closed section-9.5 two-arm grammar, it is recursively followed from every power
stage, and it is never registered as a scientific record kind.

Raw model/tool streams, snapshots, patches, logs, and binary blobs are not
standalone records; a schema-valid parent carries their digest, size, media
type, and relative artifact name. Every task block and study envelope therefore
emits canonical, hash-linked coverage for:

- study manifest;
- external revision/license receipt;
- task registry and lineage;
- assignment and seed ledger;
- prefix trajectory and snapshot receipt;
- true verifier artifact;
- REAL/SHAM packet and donor receipt;
- branch trajectory and resource counters;
- endpoint grader output;
- infrastructure/adverse-event receipt;
- provider cost receipt; and
- analysis projection.

`resampling-packet-index` is a closed staged record: `candidate` contains
complete pair/no-intervention receipts and encrypted artifact refs; `sealed`
parents the candidate and adds the passed audit gates. Branches accept only
`sealed`. `resampling-power-report` likewise uses closed stages
`screen`, `shard`, `selection`, `validation`, and `final`. Every stage requires
`authority_ref`, the derived decision-authority/roster/membership mirrors,
`grid_ref`, `screen_topology_ref`, and `rng_contract_sha256`. Every non-final
stage also carries the phase/stage-derived `kernel_id` and screen-frozen
`shard_count`; final carries the selected/terminal derived kernel/count. All
are reloaded rather than trusted. The screen payload is phase-discriminated:
Gaussian forbids a fallback trigger, while fallback requires the failed
Gaussian-validation ArtifactRef and includes it in `parent_refs`. The final
stage has a closed four-arm finalization:
Gaussian completed, full-multiplier completed, roster-only
`feasibility_no_go`, or synthetic-only `synthetic_validation_failed`.

A triggered task block embeds every chronological attempt and all terminal
receipts completed within it, including superseded first attempts and partial
failed second attempts. It also embeds four outcome-source terminal receipts,
four execution receipts, the chosen-attempt index, optional outage receipt, and
validity-event references. Those embedded records carry final-snapshot, grade,
provider-event, adverse-event, and provider-cost ArtifactRefs. A no-trigger
block uses a distinct closed schema arm with no branch receipts and four copied
`Y_0` outcomes.

The blinded projection never embeds `BranchOutcome`. Its closed
`BlindedOutcome` contains only binary success/prefix success, finite partial
reward, infrastructure-failure bit, and exact nonnegative model-call,
tool-call, generated-token, and wall-clock counters. ArtifactRefs, paths,
packet/grade/source receipts, arm/donor/key fields, and hidden source identities
are forbidden. The projection also carries
`projection_candidate_sha256`, which validators recompute from its typed
schedule/task-block ancestry and the stripping rule; it is not a free digest.
Every projected slot outcome's prefix-success value must equal the row-level
prefix value reconstructed from that same task block.

Scientific records receive one injected `frozen_created_at` from the study
manifest; code never reads the wall clock while constructing their digest.
Operational event timestamps live in a separate non-scientific receipt chain.
Only artifact-root-relative POSIX names may enter scientific records; absolute
paths and output directories are excluded. Two self-tests with the same frozen
clock must therefore hash identically.

The artifact root recursively follows every ArtifactRef from every scientific
record, verifies the referenced raw bytes/size/media metadata, and hashes the
union of scientific records and referenced blobs. Dangling, conflicting, or
unlisted refs fail closed, including the deepest blob referenced only through
an embedded task-block receipt. Reference shape alone is insufficient: every
record-kind validator reloads the referenced parent under the same run root,
checks its expected record kind and digest, and proves nested semantic ancestry
and exact selected-schedule coverage. In particular, schedule must descend from
manifest;
the manifest must own the only eligible-confirmation eligibility ref; schedule
must descend from one completed power final and reproduce its authority,
selected tier, and selected membership; every nested prefix/verifier receipt
must descend from that schedule;
assignment must descend from the same manifest/schedule/prefix trio and its
matching/allocation receipts must reproduce its task assignments; packet,
freeze, task-block, projection, unblind, and analysis parents must resolve to
that same selected-membership chain. A schema-valid but unrelated scientific
record cannot satisfy an ArtifactRef.

The branch-bearing chronology is enforced both when each record is written and
when the root is verified:

```text
study manifest with roster/eligibility/grid/topology refs
-> typed power-authority blob
-> screen
-> immutable shards
-> phase-appropriate selection/validation
-> authority-discriminated completed final report
-> selected-membership prefix schedule
-> complete prefix/verifier receipt
-> assignment ledger
-> candidate packet index
-> sealed packet index
-> analysis freeze
-> task blocks
-> capability-minimal blinded-projection candidate (ephemeral, non-scientific)
-> trusted ancestry-validated blinded-projection seal
-> unblind receipt
-> analysis
-> artifact root
```

No candidate/sealed packet, analysis freeze, task block, projection, unblind,
analysis, or other branch-derived scientific record may be created before the
assignment ledger exists and validates. A task block additionally requires the
sealed packet index and analysis freeze. No prefix schedule can exist until the
referenced power final has completed successfully under the authority
appropriate arm. The power chain consumes no endpoint bytes. A file timestamp
does not establish order; typed hash ancestry and fail-closed transaction
prerequisites do.

Manifest, schedule, prefix-index, assignment,
projection, freeze, analysis, and unblind kinds are singleton. Packet indexes
have exactly one candidate and one sealed identity; task blocks are unique by
task ID with exact selected-schedule coverage. A power chain has one screen,
selection, validation, and shard set per append-only
`(power_authority_ref, phase, generation)` attempt, where phase is
`gaussian_approximation` or `full_multiplier_fallback`. Duplicate identities
within an attempt fail closed, but failed attempts remain immutable and later
generations are retained; each screen freezes its shard count and RNG/kernel
mirrors. A fallback screen additionally parents the latest completed failed
Gaussian validation, and its existence closes later Gaussian attempts.
Exactly one final report per authority parents every
attempt and closes as a phase-discriminated Gaussian completed chain,
full-multiplier completed chain, roster-only terminal feasibility no-go, or
synthetic-only terminal validation failure. The authority identity is the
power-authority ArtifactRef, not the mirrored string. The Gaussian arm requires
its worst-five selection/approximation validation. The full-multiplier arm
instead derives its fallback trigger from its selected screen, requires the
full-grid completeness/numeric/tier-validation receipt, and forbids a Gaussian
selection or later trigger override.
A persisted validation stage is completed; no final arm may call it
`attempt_incomplete`. Final is terminal for the authority; only a completed
final may parent a schedule.
Determinism probes and nested artifact roots never share the result-of-record
root.

Large raw artifacts remain under ignored `build/research/` roots. A reviewed,
de-identified, license-compliant release bundle is promoted intentionally.

### 12.2 Capability separation

- The power controller receives only the study manifest and its referenced
  authority/grid/topology inputs. It derives numeric configuration, public RNG,
  kernel, and partition contracts, consumes no prefix/branch endpoint, and
  publishes the one completed or failed final report before schedule sealing.
- The schedule controller receives the schedule-seed reveal, manifest ref, and
  completed power-final ref. It loads task, roster, eligibility,
  assignment-program, and provider-lane assets only through that manifest;
  derives the selected membership from the final; and cannot read the
  assignment master key, verifier artifacts, arm IDs, or endpoint outcomes.
- The assignment controller loads the schedule only through its ArtifactRef,
  reloads the manifest through the schedule, and loads the prefix index only
  through its ArtifactRef. It may read the master key after complete
  prefix/verifier freeze, construct only the allowlisted assignment prefix
  view, map arms, and emit commitments/receipts; it cannot read branch endpoint
  outcomes. It and the confirmation verifier consume separately minted,
  registry-held `AssignmentSecretHandle` values from the concrete section-4.0
  `AssignmentSecretStore`; the latter cannot claim arm/capability
  reconstruction without that keyed authority. At each handle's consumption,
  trusted core code uses exact `readinto` on a preallocated 32-byte mutable
  buffer, rejects short/extra data, independently verifies the master
  commitment and context, derives only the four assignment-purpose subkeys
  into private mutable buffers, and follows section 4.0's single-use,
  deterministic application-buffer wipe, and honest library-copy boundary.
- The canonical clear assignment-ledger JSON persists only in an owner-only
  controller scientific run root backed by transparent encryption at rest.
  Trusted assignment, preparer, verifier, and unblind processes see its normal
  plaintext `Path`, so schema, digest, and artifact-root scans work unchanged.
  That controller root is never copied, mounted, or shared with branch-worker
  identities or the analysis author before unblinding. An envelope-object
  adapter is optional only if it presents the same trusted plaintext `Path`
  view; the core does not assume a new resolver.
- The two and only two operational storage-policy receipts are fixed at
  `operational/storage-policy/prefix.json` and
  `operational/storage-policy/assignment.json`; both remain outside the
  scientific JSON/digest. Before either scientific install, the controller
  writes and fsyncs exactly one non-authoritative
  `StorageTransactionIntent` at
  `operational/storage-policy/intents/{prefix,assignment}.json`. The intent
  embeds the transaction binding, immutable lease ID, begin, strictly ordered
  renewals, confirmation-signed or closed-local-test non-releasing end, exact
  prepared scientific path/digest, final generation/expiry, and complete
  measured storage tuple. Every renewal
  precedes the prior expiry and preserves the tuple; end is fresh, retains the
  final generation/sequence, carries `releases_lease = false`, and forbids later
  renewal. The intent file is replaceable only before scientific install and
  is never a receipt or acceptance marker.
- The controller next proves enough remaining lease lifetime for scientific
  install, scientific-parent fsync, and one registry commit call. It installs
  and fsyncs the exact prepared science under the same live lease, then presents
  the original nominal handle, canonical intent bytes/digest, and exact
  scientific path/digest to the registry. Before final expiry, the registry
  rechecks the complete tuple and current time and prepares one canonical
  `StoragePublicationCommit`. The proof binds a unique commit ID/time, intent
  digest, scientific path/digest, final lease tuple,
  `commit_recorded = true`, `lease_consumed = true`, and
  `release_required = true`. The registry signs its confirmation arm, then
  atomically stores those exact proof bytes, the unique commit ID, and
  `end_observed -> committed_consumed` state before responding or attempting
  release. No second commit or reuse is possible; release failure leaves
  durable committed-consumed state with idempotent cleanup and cannot mutate
  the proof.
- `registry_commit_id` is 64 lowercase hex, unique across every stored commit
  proof, and never freed by terminal cleanup. Confirmation draws 32
  registry-CSPRNG bytes and collision retries before commit; `local_test` uses
  `SHA256(b"local-test-storage-commit-v1\x00" || intent_digest_bytes)`.
- Every confirmation storage attestation and publication-commit signature is
  Ed25519 over compact canonical object bytes with its own
  `attestation_signature_ed25519_hex` field omitted, using the exact
  manifest-contract `registry_attestation_public_key_ed25519_hex`. That key is
  required to differ from the measurement
  `evidence_verifier_public_key_ed25519_hex`; neither role can authorize the
  other. The closed `local_test` contract sets both keys null and its
  observation/commit arms contain no signature field. Alternate
  canonicalization, extra/missing fields, wrong/reused key, or signature-arm
  mismatch rejects.
- Only that durable commit proof authorizes the fixed receipt. The receipt
  embeds the exact intent and proof and verifies every cross-binding, including
  the required confirmation registry signature; the unsigned closed
  `local_test` arm is accepted only by synthetic tests. The controller or
  recovery constructs identical canonical receipt bytes, fsyncs a
  same-directory temporary file, installs it once at the fixed path, and fsyncs
  the parent. The outer receipt verifies
  `fresh_at_publication_commit = true`,
  `publication_commit_recorded = true`,
  `publication_commit_consumes_lease = true`, and
  `fixed_receipt_is_acceptance_marker = true`. Local acceptance is exactly the
  canonical scientific file plus this validating fixed receipt with a
  recomputing scientific digest. The receipt does not claim its own
  install preceded lease expiry; the nested commit proof establishes that the
  scientific bytes were durably committed while fresh. The fixed receipt and
  post-science intent are immutable and remain outside scientific closure.
- Crash recovery is closed. Before scientific install, an intent may be
  replaced under the transaction lock only after proving the science path
  absent and the registry commit nonexistent, then atomically transitioning
  `end_observed -> aborted_consumed`, invalidating the old handle, and
  attempting release. After scientific install but before registry commit,
  science is permanently quarantined and recovery cannot request commit. After
  durable registry commit but before fixed-receipt fsync, recovery may fetch
  only the already recorded proof by its closed intent/lease binding and
  deterministically finalize the same receipt; acceptance begins only when the
  receipt and exact science are durable. Missing proof, intent or science
  mismatch, free recovery fields, replay, or second terminal transition
  rejects. Confirmation requires measured encryption, ACL/IAM, and
  continuous-lease evidence; synthetic `local_test` records false
  enforcement/null measurement fields and cannot satisfy confirmation.
- The intent, confirmation-signed or closed-local-test commit proof, fixed
  receipt, canonical implementation, and replay establish this ordering only
  under the trusted controller OS, filesystem, clock, registry, and signing-key
  boundary; they are not an external timestamp. Tests inject expiry, release,
  tuple swap, and crash at every boundary from end through registry commit and
  receipt fsync. They
  require quarantine before commit, deterministic proof-only finalization after
  commit, the exact two-file local acceptance predicate, and idempotent cleanup
  for a committed proof whose release attempt failed.
- A trusted preparer may resolve the clear ledger and packet index into four
  one-slot work orders. Each run worker receives only one opaque slot
  capability, its frozen snapshot/seed/caps, and at most one generically named
  subject-guidance artifact; it cannot read arm names, donor mappings,
  packet-pair receipts, the clear ledger, or other branches.
- Projection is two-phase. A capability-minimal projector receives only an
  opaque schedule view plus stripped task/slot outcomes. Each outcome is a
  closed analysis-visible primitive containing success, prefix success, finite
  partial reward, infrastructure-failure bit, and exact nonnegative resource
  counters; it contains no ArtifactRef/path, packet/grade/source ref, arm,
  donor, key, or hidden source identity. The projector has no `run_root`,
  ArtifactRef resolver, assignment/outcome source type, key provider, packet
  type, or clear assignment ref and emits only an ephemeral closed
  `BlindedProjectionCandidate` with A/B/C/D labels. The trusted controller's
  `seal_blinded_projection` transaction separately reloads the schedule,
  freeze, original task blocks, clear assignment ledger, packet seal, and every
  nested parent through its encrypted plaintext `Path`; proves complete
  semantic ancestry; reconstructs the same stripped view; byte-compares the
  candidate; and only then writes the singleton scientific blinded projection.
  The candidate is never a scientific record and is never stored under the run
  root. The analysis author receives only the sealed projection.
- Only the hash-gated unblinder receives both opaque projection and clear
  ledger. The entry point consumes one registry-held, single-use
  `UnblindSecretHandle` minted by the concrete section-4.0
  `AssignmentSecretStore`. Trusted core code reads exactly 32 bytes from the
  handle's already-open file, independently verifies the master commitment and
  manifest/schedule context, derives only `K_unblind` in memory, and internally
  recomputes the framed permit HMAC binding study ID, manifest, schedule,
  prefix, assignment ledger, projection, analysis freeze, and expected task
  count before it parses the ledger. It zeroes the master/subkey buffers and
  all other application-owned mutable key buffers in an outer `finally`, while
  making no claim that Python/OpenSSL internal copies are scrubbable. It accepts
  no caller-provided verifier, raw-key API, generic `secret` HMAC, or
  assignment-purpose handle.
- The analysis author cannot access the unblinding key until source and
  synthetic expected outputs are sealed.
- A context that reads confirmation outcome bytes is outcome-tainted and cannot
  alter confirmatory code, task filters, or verdict rules.

The first run after unblinding is the result of record. A correction requires an
append-only deviation and a new artifact; it never overwrites the original.

## 13. Exact cloud architecture

No provider resource is authorized by this section. Prices are 2026-07-28
planning observations and must be re-queried at each action freeze.

The hour and cost model is valid only if Tier 1 proves:

1. FP8 Qwen3.6 serves on one L40S with the frozen context/concurrency cap;
2. BF16 Qwen3.6 serves on two A100 80 GB GPUs with tensor parallelism two;
3. AWS sustains four concurrent SWE subject replicas and three concurrent τ³
   subject replicas plus one user-simulator replica;
4. the frozen vLLM deterministic/batch-invariant mode passes byte equality;
5. forced interruption restores every arm-visible byte at a completed
   boundary; and
6. projected content-addressed durable bytes, p99 boundary delta, upload time,
   object requests, and attached GB-hours at C160 and Tier 3 fit the 2,000
   GB-month and fixed request/infrastructure allowances;
7. the independent AWS and Azure lease-expiry kill drills remove every tagged
   compute, pool, disk, endpoint/IP, and sibling container without relying on
   the study controller;
8. the exact AWS private/public network path and all endpoint/NAT charges pass
   bootstrap and metering;
9. the exact Azure VNet/subnet, node-communication mode, public-IP
   configuration, outbound/endpoints, DNS/firewall, and charges pass bootstrap
   and metering;
10. benchmark containers fail negative probes for IMDS, node credentials,
   managed identity, and Docker-socket access;
11. Azure seals SKU/image/node-agent/allocation/quota receipts and successfully
    allocates one exact node of every requested family;
12. the A10 simulator passes realistic-context OOM and throughput gates; and
13. every storage/network/log/registry/API billing dimension has an admission
    meter whose in-flight worst case fits the frozen cap.

Failure of any item invalidates the topology, hour table, and cost table. It
requires a newly priced and hashed manifest before confirmation.

### 13.1 AWS primary path

Region: `us-east-1`.

Services:

- AWS Batch managed EC2 compute environment, min vCPU 0, with a custom GPU AMI
  pinned by AMI ID and root-snapshot ID plus a bootstrap SHA-256, one-instance
  maximum, and one whole-instance job per node. The On-Demand environment pins
  `instanceTypes=[g6e.12xlarge]`, `maxvCpus=48`, and
  `allocationStrategy=BEST_FIT`; exactly one runnable controller job requests
  48 vCPUs, all four GPUs, and allocatable memory. Any Spot environment also
  pins the exact type/max-vCPU/job shape, seals its allocation strategy, and
  proves and independently guards one-node behavior in a separately
  hash-approved Tier-3 preflight whose hours debit the Tier-3 cap. Tier 1
  remains On-Demand only. Any future non-`BEST_FIT` On-Demand environment
  reserves the documented possible one-instance `maxvCpus` overshoot;
- EC2 `g6e.12xlarge`, 4 × L40S 48 GB and 384 GiB host RAM, reserved as one
  privileged controller allocation requesting all four GPUs, allocatable
  vCPUs, and allocatable memory so no unrelated Batch job can share the node;
- four TP1 subject replicas for SWE, or three TP1 subject replicas plus one
  frozen Qwen3.5-9B user-simulator replica for τ³; this concurrency assumption
  is invalid unless the Tier-1 gate passes;
- host Docker exposed only to the privileged controller, with the
  instance-store devices enumerated, formatted, and mounted as Docker's data
  root—striped only when enumeration finds more than one device, for
  approximately 3.8 TB total local NVMe;
- unique names, networks, work directories, and cleanup receipts for every
  benchmark container, with no provider credential exposed inside it;
- benchmark containers receive neither the Docker socket nor cloud
  credentials, and their network namespaces block IMDS. The controller uses a
  minimal per-run role restricted to its content-addressed storage prefix plus
  consistent `GetItem` on the exact run lease key/table; it cannot renew the
  lease. The independent watcher has a separate write/termination identity. A
  negative IMDS/credential/socket and least-privilege probe is part of Tier 1;
- ECR for digest-pinned controller, model-server, simulator, and harness
  images;
- one-AZ private networking with an action-manifested endpoint set for ECR API,
  ECR DKR, S3, DynamoDB lease reads, ECS control/agent/telemetry, CloudWatch
  Logs, and whichever of STS/EC2 the measured bootstrap requires; alternatively,
  a newly priced public/NAT path. Gateway/interface endpoint policies restrict
  the study role to its exact resources. Endpoint hourly and data-processing
  charges are explicit meters, never hidden inside “no NAT”;
- S3 Standard for durable manifests, checkpoints, provider-local OCI archives,
  and final artifacts, with a manifest-bound lifecycle-policy ID, absolute
  deletion date, and abort-incomplete-multipart rule. Any intermediate
  transition additionally freezes the destination price, minimum duration,
  retrieval charges, and final deletion date;
- content-addressed local NVMe caches, with bounded gp3 only when a measured
  image working set exceeds instance storage;
- CloudWatch Logs with fixed retention; and
- AWS Budgets alarms plus a controller-enforced multi-resource watchdog;
- an independently deployed EventBridge Scheduler + Lambda stop path with a
  DynamoDB lease and a minimal termination role. On expiry or a missing fresh
  lease it cancels/terminates Batch work, disables and drains the queue/
  compute environment, terminates every tagged study instance, removes tagged
  volumes/endpoints after artifact recovery, deletes the compute environment,
  and verifies zero tagged billable resources; and
- node boot sweepers and exit traps that kill every study sibling container.
  No fresh watchdog lease means no new model or API call.

Every model, package, and benchmark-image byte is staged provider-locally by
digest before confirmation. A no-NAT job is eligible only after the exact
endpoint set above passes a measured bootstrap; otherwise public/NAT
networking and all hourly/data-processing charges enter a newly hashed
manifest.

Current rates:

- `g6e.12xlarge`: $10.49264/hour On-Demand;
- historical Spot planning observation: $4.467/hour, currently non-authoritative
  because its AZ, UTC query response, product description, and digest were not
  retained;
- S3 Standard: $0.023/GB-month;
- gp3: $0.08/GiB-month.

The pinned MultiLang dataset is about 254 MiB compressed. A deterministic
40-image metadata sample—five per split—measured compressed layer sets from
0.695 to 14.150 GiB, median 1.801 GiB, mean 2.932 GiB, with only about 9%
observed cross-image layer deduplication. Quota-weighted planning points are
about 352 GiB of cold compressed pulls for C120 and 470 GiB for provisional
C160, or about 321/428 GiB after sample-like deduplication. These exclude
unpacked layers, writable branches, test logs, snapshots, and provider
replication. They justify retaining—not lowering—the 3 TB working-disk gate
until roster-specific image receipts replace the sample projection.

The admission controller reads each task's declared and observed cgroup memory
and disk use. It starts a branch only when the admitted set plus a 20% reserve
fits at or below 307.2 GiB combined RSS/cache and 3.0 TB working disk; ECS/OS
use remains inside that reserve. Sustainable four-/three-way concurrency is a
Tier-1 measurement, never assumed for repositories near the reported 50 GB task
requirement.

Although each L40S is marketed as 48 GB, AWS documents roughly 44 GiB usable
per GPU on G6e. The Tier-1 OOM receipt therefore measures against usable
device memory, not nominal capacity. The 32K/65K ladder is a deliberate
deadline/budget compromise below Qwen's recommended 128K context and must be
reported as such if selected.

Confirmation is On-Demand. Spot is eligible only for a Tier-3 expansion after
the forced-interruption gate passes and a fresh AZ-specific
`DescribeSpotPriceHistory` response (UTC timestamp, product description, raw
response, and digest) is sealed. Until then all AWS Tier-3 expected and
reserved planning uses On-Demand.

No SageMaker endpoint, EKS cluster, marketplace model image, persistent idle
GPU, or cross-AZ artifact path is planned.

### 13.2 Azure replication/fallback path

Region: `East US`.

Services:

- separate Azure Batch pools: dedicated Tier-1/precision pools and Tier-3 Spot
  pools, each scale-to-zero with one task slot and at most one whole-node study
  allocation per VM. Dedicated and Spot target-node counts are explicit and
  never mixed behind one price;
- an action-manifested VNet/subnet, simplified node-communication mode,
  `publicIPAddressConfiguration`, and exact outbound path to Batch, ACR,
  Blob/lease, and required control planes. NAT versus service/private
  endpoints, DNS/firewall rules, hourly/data charges, and measured bootstrap
  receipts are frozen before use;
- a pool-scope elevated, idempotent start task that installs/validates the
  pinned host Docker/runtime/driver stack, preserves
  `AZ_BATCH_NODE_ROOT_DIR`, inspects `lsblk`/`findmnt`, and mounts only
  positively identified unclaimed temporary devices. It never generically
  formats “the NVMe disk”; the before/after device, filesystem, and mount
  receipt is sealed;
- non-container, pool-administrator Batch study tasks that launch only
  digest-pinned sibling host containers, avoiding Docker inside a Batch
  container or nested virtualization;
- `Standard_NC40ads_H100_v5` for same-FP8 provider parity/fallback;
- `Standard_NC48ads_A100_v4`, 2 × A100 80 GB under TP2, for the separately
  labeled BF16 precision replication;
- `Standard_NV36ads_A10_v5` for the Qwen3.5-9B τ³ user simulator whenever a
  τ³ H100 or A100 subject block runs;
- Azure Container Registry Basic for digest-pinned images, with a
  watcher-owned explicit repository/registry deletion action, absolute
  deadline, and receipt (Basic has no native untagged-manifest retention
  policy);
- flat-namespace (`HNS=false`) Blob Storage Hot LRS for
  manifests/checkpoints/artifacts, with manifest-bound lifecycle policy,
  absolute deletion date, and explicit version/soft-delete retention. Any
  intermediate tier transition freezes its destination/minimum-duration/
  retrieval pricing through final deletion;
- ephemeral/local disk for replaceable cache; and
- Cost Management advisory thresholds aligned with the action/provider hard
  stops enforced by the independent watcher;
- a separate pool/start-task `AcrPull` identity or short-lived repository-scoped
  pull token used only to hydrate digest-pinned images. Its digest/pull/revocation
  receipt is sealed before benchmark siblings start, and those siblings cannot
  reach the credential;
- a least-privileged controller identity restricted to the exact run
  container/prefix plus read-only access to the exact Storage lease; it cannot
  renew the lease, and sibling containers cannot reach its token/IMDS path;
- an independently deployed Function or Automation stop path with a Storage
  lease and termination-only managed identity. On expiry or missing lease it
  terminates tasks/jobs, sets both dedicated and Spot targets to zero, deletes
  every manifest-listed immutable pool/backing-resource ID, and verifies that
  exact node/disk/IP/endpoint set is gone. It never assumes backing-resource
  tag propagation; if resource tags are used for discovery, the manifest must
  prove `poolAllocationMode=UserSubscription`; and
- benchmark containers with no Docker socket, managed identity, IMDS access, or
  provider credential, proven by a recorded negative probe.

Current rates:

- H100 NVL 94 GB: $6.98/hour On-Demand, $1.40298/hour Spot;
- 2 × A100 80 GB: $7.346/hour On-Demand, $1.357541/hour Spot;
- A10 24 GB: $3.20/hour On-Demand, $0.59136/hour Spot; and
- flat-namespace Blob Hot LRS: $0.0208/GB-month.

The retired Batch Low Priority label/rate is not an execution option; Tier 3
uses explicit Spot pools.

H100 parity is substitute-only for Tier 2 when AWS primary capacity is
unavailable. In Tier 3 it is an optional additive, preregistered parity slice
already included in the displayed Tier-3 reservation. A100 BF16 output is a
distinct replication block.
The simulator VM is costed for the same τ³ wall time as its subject VM; if it is
unavailable, τ³ is omitted from that replication rather than silently sharing
or changing the user model.

Before the first Azure action, a read-only gate seals the current East-US
`list-skus` response, exact `imageReference`, `nodeAgentSkuId`, Batch allocation
mode, and regional/family dedicated/Spot quotas. Quota is not treated as
capacity. A separately priced, hash-approved Tier-1 reservation then allocates
one exact node of each requested family and seals its allocation receipt.
Those receipts are mandatory before any Tier-2/Tier-3 Azure reservation. NCads
A100 v4 is a material availability risk for net-new deployments; inability to
allocate the exact NC48 node drops the BF16 block unless a separately priced,
hashed, and approved substitute topology passes Tier 1. The A10 simulator also
has an explicit realistic-context OOM/throughput gate because its 24 GB device
margin is tight.

Azure is a parity/precision slice, not an automatic full-confirmation fallback.
At the registered wall-clock caps, a full C120 Azure replacement would reserve:

```text
H100 FP8:
1.5 * (900 * 6.98 + 300 * 3.20) + 341.60 = $11,204.60

A100 BF16:
1.5 * (900 * 7.346 + 300 * 3.20) + 341.60 = $11,698.70
```

Both exceed the user-reported Azure face value before that value is verified.
Full Azure substitution therefore needs a new budget and approval. No Azure ML
managed online endpoint, AKS cluster, public load balancer, or permanent GPU
pool is planned.

### 13.3 Durable boundary and interruption contract

After every completed model response or tool result, the controller writes a
content-addressed checkpoint containing:

- transcript bytes and exact token IDs;
- per-call subject and simulator seed schedules;
- tool invocation/result receipt;
- repository diff plus every mutable non-git workspace artifact required for
  exact reconstruction;
- τ³ databases, simulator state, transcript, and RNG state;
- runtime, container, image, model, and tokenizer digests; and
- cumulative token, call, wall-clock, and cost counters.

The reservation/watchdog meter covers instance/node hours, attached
GiB-hours, durable byte-hours, snapshot/version/soft-delete byte-hours,
incomplete multipart-upload bytes, ECR/ACR byte-hours, object operations,
log-ingest bytes, egress bytes, interface-endpoint/public-IP hours, and every
API billing dimension. Fixed miscellaneous allowances are worst-case
reservations, not enforceable caps by themselves. Provider budget alerts are
delayed advisory signals and never substitute for the independent stop path.
Storage and supported registry/log lifecycle-policy IDs, absolute expiry
dates, abort-incomplete-multipart rules, and version/soft-delete retention are
frozen before upload. ACR Basic instead uses the watcher-owned explicit delete
action and deadline above. The storage reservation and watcher stay active
until a verified final-deletion receipt, unless the remaining retention horizon
is fully reserved. A storage-class transition alone never releases a
reservation; destination-tier and minimum-duration costs remain reserved
through verified final deletion.

The checkpoint is uploaded to S3 or Blob, verified by hash, and followed by an
atomic completion marker before the next boundary starts. A local marker is
insufficient. A resumed branch retains task, arm, sample ID, and seed schedule
and appends an attempt receipt. Restore must match the prior boundary receipt
before the next model call. Any mismatch invalidates the entire four-arm task
block; one failed arm is never silently replaced.

Model KV state is reconstructed from recorded token IDs. A server restart,
instance replacement, provider change, GPU topology change, or kernel change is
not presumed reproducible. Online vLLM uses `VLLM_BATCH_INVARIANT=1`,
per-request seeds, and frozen request order/concurrency only after the exact
Qwen3.6 byte-equality fixture passes. A failure is a Tier-1 no-go for the
displayed concurrency and cost model. Concurrency-one/offline execution is
eligible only after a newly measured, recosted, hashed, and approved manifest.
The study makes no common-random-number claim.

### 13.4 API path

OpenAI and Anthropic are restricted to the blinded secondary sidecar or a fresh
frontier replication. They do not create primary verifier findings or primary
outcomes.

Planning models and standard input/output rates per million tokens:

- OpenAI `gpt-5.6-luna`: $1 / $6; Batch $0.50 / $3;
- OpenAI `gpt-5.6-terra`: $2.50 / $15; Batch $1.25 / $7.50;
- Claude Haiku 4.5: $1 / $5; Batch $0.50 / $2.50;
- Claude Sonnet 5 introductory: $2 / $10; Batch $1 / $5 through
  2026-08-31.

Only de-identified, license-permitted excerpts may leave the compute account.

Each API action manifest also freezes cache-read/write charging,
long-context/tool/regional premiums, retry count, and per-request input/output
ceilings. Admission enforces:

```text
charged
+ reserved_worst_case_cost_of_every_in_flight_request
+ proposed_request_worst_case
    <= action_cap
```

A post-response check is insufficient because it can discover an overrun only
after billing.

## 14. Costed execution tiers

### 14.1 Cap-derived hours

One task consumes one prefix plus four continuations. The registered wall caps
give:

```text
SWE subject-hours per task = 5 * 1.0 = 5.0
τ³ subject-hours per task  = 5 * 0.5 = 2.5
```

Four SWE subjects share an AWS node. Three τ³ subjects share it while the
fourth GPU serves the user simulator.

| roster | SWE subject-hours | AWS SWE instance-hours | τ³ subject-hours | AWS τ³ instance-hours | total AWS instance-hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| C120 | 600 | 150 | 300 | 100 | **250** |
| C160 | 800 | 200 | 400 | 133.3333 | **333.3333** |

These are cap-derived schedule hours, not optimistic token-throughput
estimates. The reservation multiplier covers startup, verifiers, graders,
admission-control loss, bounded retry, and scale-down lag:

```text
unbuffered_compute = instance_hours * current_On_Demand_rate

reserved_total =
    1.50 * unbuffered_compute
    + object_block_registry_log_request_egress_allowance
    + API_caps
```

Tier-3 AWS planning expected uses On-Demand until the interruption gate and a
sealed current AZ-specific Spot query both pass. Azure planning expected uses
the current official Retail Spot observations but remains conditional on
capacity/eligibility. Every reservation uses all-On-Demand; a lower
all-eligible-Spot scenario is reported separately and never used for admission.

### 14.2 Fixed allowances

```text
Tier-2 AWS:
2,000 GB-month S3   = 2,000 * 0.023 = $46.00
2,000 GiB-month gp3 = 2,000 * 0.08  = $160.00
ECR/log/request/egress cap                  = $200.00
AWS infrastructure allowance               = $406.00

Tier-3 incremental AWS infrastructure       = $506.00

Tier-3 Azure:
2,000 GB-month Blob = 2,000 * 0.0208 = $41.60
managed disk/ACR/log/request/egress cap     = $300.00
Azure infrastructure allowance             = $341.60
```

Tier 1 uses $20 AWS and $30 Azure infrastructure allowances.

### 14.3 Tiers

| tier | exact scope | planning expected | reserved worst case |
| --- | --- | ---: | ---: |
| 0 | local registry, schemas, simulator, fake model, and local 9B work | $0 | $0 |
| 1 | AWS 12 h g6e OD; Azure 8 h H100 OD, 8 h NC48 A100 OD, and 16 h A10 OD; $50 infrastructure | $341.72 | **$487.58** |
| 2-C120 | AWS C120, 250 g6e OD hours; $406 AWS infrastructure; OpenAI cap $200; Anthropic cap $50 | $3,279.16 | **$4,590.74** |
| 2-C160 | AWS C160, 333.3333 g6e OD hours; same infrastructure and API caps | $4,153.55 | **$5,902.32** |
| 3 | one disjoint 80-task-per-benchmark expansion roster on AWS; Azure H100 and BF16 reuse the same fixed 24-task-per-benchmark subset of that roster; OpenAI $1,500; Anthropic $350 | **$5,014.23** with AWS OD and current Azure planned Spot; $4,009.96 conditional all-eligible-Spot scenario | **$9,764.78** |

Arithmetic of record:

```text
Tier 1 AWS expected =
    12 * 10.49264 + 20
    = $145.91168

Tier 1 AWS reserved =
    1.5 * (12 * 10.49264) + 20
    = $208.86752

Tier 1 Azure expected =
    8 * 6.98 + 8 * 7.346 + 16 * 3.20 + 30
    = $195.808

Tier 1 Azure reserved =
    1.5 * (8 * 6.98 + 8 * 7.346 + 16 * 3.20) + 30
    = $278.712

C120 expected =
    250 * 10.49264 + 406 + 200 + 50
    = $3,279.16

C120 reserved =
    1.5 * (250 * 10.49264) + 406 + 200 + 50
    = $4,590.74

C160 expected =
    (1,000 / 3) * 10.49264 + 406 + 200 + 50
    = $4,153.54667

C160 reserved =
    1.5 * ((1,000 / 3) * 10.49264) + 406 + 200 + 50
    = $5,902.32
```

Tier 3 freezes one 80-task-per-benchmark roster disjoint from pilot and
confirmation. AWS runs that roster. H100 and BF16 both reuse the same fixed
24-task-per-benchmark subset of those 80 tasks, so the provider/precision
slices consume no additional task definitions. Tier 3 uses exactly `500 / 3`
AWS g6e instance-hours (166.6667 when displayed); each Azure subject slice uses
180 VM-hours, and their τ³ slices
jointly use 120 A10 simulator hours:

```text
Tier-3 AWS expected =
    (500 / 3) * 10.49264 + 506
    = $2,254.773333...

Tier-3 AWS reserved =
    1.5 * ((500 / 3) * 10.49264) + 506
    = $3,129.16

Tier-3 Azure expected =
    180 * 1.40298
    + 180 * 1.357541
    + 120 * 0.59136
    + 341.60
    = $909.45698

Tier-3 Azure reserved =
    1.5 * (
        180 * 6.98
        + 180 * 7.346
        + 120 * 3.20
    )
    + 341.60
    = $4,785.62

Tier-3 total expected =
    2,254.773333... + 909.45698 + 1,500 + 350
    = $5,014.230313...

Conditional eligible-Spot scenario =
    ((500 / 3) * 4.467 + 506)
    + 909.45698 + 1,500 + 350
    = $4,009.95698

Tier-3 total reserved =
    3,129.16 + 4,785.62 + 1,500 + 350
    = $9,764.78
```

Tier 3 is not automatic. If selected before unblinding, selection may use only
funding, quota, throughput, and artifact-completeness data. If selected after
unblinding, it is a newly preregistered, disjoint exploratory replication and
cannot be merged into the original confirmatory test.

### 14.4 Cumulative planning stops

| completed scope | cumulative expected | cumulative worst (rounded cents) | rounded kill cap |
| --- | ---: | ---: | ---: |
| Tier 1 | $341.72 | $487.58 | **$500** |
| Tier 1 + C120 | $3,620.88 | $5,078.32 | **$5,100** |
| Tier 1 + C160 | $4,495.27 | $6,389.90 | **$6,400** |
| Tier 1 + C120 + Tier 3 | $8,635.11 | $14,843.10 | **$14,900** |
| Tier 1 + C160 + Tier 3 | $9,509.50 | $16,154.68 | **$16,200** |

Full-plan provider-local ceilings, using C160, are:

| provider | full-plan worst (rounded cents) | provider kill cap |
| --- | ---: | ---: |
| AWS | $8,990.35 | **$9,100** |
| Azure | $5,064.33 | **$5,100** |
| OpenAI | $1,700.00 | **$1,700** |
| Anthropic | $400.00 | **$400** |

These are ceilings, not entitlements. A sidecar whose provider remains
unverified is skipped and its cap remains unreserved. The face values are
pending, have spendable value zero, and are not fungible across providers.

## 15. Spend and action gate

Before every currency-bearing provider action:

1. verify portal balance, expiry, eligible services, Spot/Batch eligibility,
   region, billing currency, applicable tax/fees, and whether credits cover
   those tax/fees;
2. read quotas and published availability signals without mutation; capacity
   is proved only by a separately reserved, approved Tier-1 allocation receipt;
3. re-query every unit price;
4. freeze provider, region, SKU, pool/instance count, maximum instance-hours,
   API input/output tokens, uploaded bytes, object requests, attached GB-hours,
   actual billing currency, FX source/timestamp/buffer, tax/fee treatment and
   uncovered-cash amount, durable/snapshot/version/soft-delete/multipart bytes, registry bytes,
   log-ingest and egress bytes, endpoint/public-IP hours, job timeout,
   AMI/root-snapshot/bootstrap and image/model/dataset digests, output prefix,
   checkpoint cadence, supported lifecycle-policy IDs, explicit ACR-deletion
   action, absolute retention/expiry/deletion dates, multipart-abort and
   version/soft-delete rules, retry ceiling, API
   cache/context/tool/region premiums, and the independent lease-based stop
   watcher plus teardown verification;
5. calculate expected, all-On-Demand reserved worst case, provider cumulative
   worst, and project cumulative worst;
6. prove both invariants:

```text
provider_settled
+ provider_active_reservations
+ proposed_provider_reservation
    <= verified_eligible_provider_balance

project_settled
+ project_active_reservations
+ proposed_reservation
    <= applicable_cumulative_tier_stop
```

All invariant terms use the frozen conservative USD-equivalent conversion.
Any tax, fee, or FX exposure not covered by credits enters both the
provider/project worst-case reservation and an explicit cash-liability field;
nominal credit coverage alone is insufficient.

7. verify the spend-ledger digest;
8. hash the exact action manifest;
9. obtain the repository's one-use approval for that exact hash;
10. append the reservation before resource creation;
11. start the independent multi-resource watchdog, which refuses admission when
    current usage plus all in-flight worst cases plus proposed work would cross
    any frozen compute, storage, network, log, endpoint, request, or API billing
    cap; and
12. append settlement and release the unused reservation only after
    artifact-copy, compute/network teardown, and final storage-deletion
    receipts pass, or after the remaining frozen retention horizon is fully
    reserved.

Budget alerts do not enforce a stop. Batch timeouts and pool/compute-environment
maxima are defense in depth, not the hard-stop authority: provider timeout
termination can be best-effort and does not prove detached sibling cleanup.
The independent lease watcher plus provider teardown verification is the
hard-stop path. A Spot eviction, capacity substitution, TP/context change,
extra retry, added node, or provider substitution is not an implicit retry
unless its exact behavior was already frozen; otherwise it needs a newly
priced, hashed, and approved action.

The current state is:

- verified eligible AWS balance: $0;
- verified eligible Azure balance: $0;
- verified eligible OpenAI balance: $0;
- verified eligible Anthropic balance: $0;
- settled economic cost: $0; and
- active reservation: $0.

Pending credits do not bypass the gate. Broad autonomy is not silently converted
into approval of an unknown future hash.

## 16. Kill and pivot rules

Before confirmation, stop or narrow if:

- SWE C120 cannot instantiate the exact
  `9/14/16/17/16/16/16/16` confirmation quotas from qualified root lineages
  plus two disjoint pilots and the manifest-fixed reserves in every split after
  the complete base-license, OCI-digest, offline-isolation, and
  three-independent-pair audit;
- SWE C160 cannot instantiate its 12-per-split plus Hamilton confirmation
  allocation plus two disjoint pilots and the manifest-fixed reserves in every
  split;
- τ³ C120 lacks its three frozen pilots per domain plus
  `40/40/40` confirmation roster;
- τ³ C160 has fewer than 47 qualified airline tasks across pilot and
  confirmation, requires more than three airline reserves, or lacks its
  `44/58/58` confirmation roster;
- any benchmark image remains mutable/digest-free, a parser can escape its
  isolation boundary, evaluator network-call count is nonzero, or a registered
  F2P/P2P/evaluator component is missing;
- trigger opportunity is below 60%;
- gold/regression flakiness exceeds 2%;
- snapshot restoration differs in any arm-visible byte/token/state;
- REAL correctness or SHAM collision validation fails;
- packet detectability exceeds its gate;
- differential infrastructure failure exceeds two percentage points;
- measured p10 throughput cannot finish confirmation by 2026-08-18;
- the P0 simulator reports less than 80% power for the registered target effect
  at `C120`; or
- verified eligible funding cannot cover the exact worst case.

The zero-credit fallback is a methods-and-feasibility paper built from the
validated local controller, synthetic recovery experiments, the existing G1
negative evidence, and a clearly labeled small 9B pilot. It must not masquerade
as the powered cross-benchmark result.

Terminal-Bench 2.1 at
`5c8eadf1f393183288fa08b8f73ca9a469cc5e00` is the first robustness fallback:
it is objective, Apache 2.0, operationally clean, and has 89 tasks. It is not
primary because the unit ceiling and frontier saturation weaken power.

## 17. Schedule

| dates | irreversible output |
| --- | --- |
| Jul 28–30 | design, novelty ledger, exact revisions, implementation plan |
| Jul 30–Aug 3 | schemas, registry, power simulator, assignment, synthetic model |
| Aug 2–6 | SWE/τ³ adapters, snapshot forks, verifier/SHAM builder, failure tests |
| Aug 5–7 | local 9B pilot, detectability and artifact audit |
| Aug 7–8 | freeze dependencies, preregistration, task roster, analysis hash |
| Aug 8–10 | eligible Tier-1 cloud parity/throughput only |
| Aug 10–18 | confirmation and any pre-unblinding replication |
| Aug 18–21 | artifact completeness, unblind, analysis, robustness |
| Aug 21–25 | 4–9 page paper, supplement, anonymous release bundle |
| Aug 25–27 | independent red team, clean-clone reproduction, PDF inspection |
| Aug 28 | submission target and one-day failure buffer |
| Aug 29 | emergency-only venue buffer; no new scientific degrees of freedom |

## 18. Sources of record

- Workshop:
  `https://who-verifies-the-agents.github.io/`
- SWE-bench-Live:
  `https://swe-bench-live.github.io/`
- Pinned SWE-bench-Live MultiLang dataset and card:
  `https://huggingface.co/datasets/SWE-bench-Live/MultiLang/tree/608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b`;
  `https://huggingface.co/datasets/SWE-bench-Live/MultiLang/blob/608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b/README.md`
- Pinned SWE-bench-Live harness, evaluation contract, endpoint, and validation:
  `https://github.com/microsoft/SWE-bench-Live/tree/70ec57e852e3f2d195790fe71f553e272c691833`;
  `https://github.com/microsoft/SWE-bench-Live/blob/70ec57e852e3f2d195790fe71f553e272c691833/evaluation/README.md`;
  `https://github.com/microsoft/SWE-bench-Live/blob/70ec57e852e3f2d195790fe71f553e272c691833/evaluation/evaluation.py`;
  `https://github.com/microsoft/SWE-bench-Live/blob/70ec57e852e3f2d195790fe71f553e272c691833/evaluation/validation.py`
- Pinned RepoLaunch Linux runtime and dynamic parser:
  `https://github.com/microsoft/RepoLaunch/blob/7735b1e7363dd3bbc69bd0ef80db646a2ae391fd/launch/core/platforms/linux.py`;
  `https://github.com/microsoft/RepoLaunch/blob/7735b1e7363dd3bbc69bd0ef80db646a2ae391fd/launch/scripts/parser.py`
- τ³-bench v1.0.1:
  `https://github.com/sierra-research/tau2-bench/tree/v1.0.1`
- τ³ annotated release, peeled commit, license, and package contract:
  `https://github.com/sierra-research/tau2-bench/releases/tag/v1.0.1`;
  `https://github.com/sierra-research/tau2-bench/commit/fc0055dc4e0a316c3f83133267fbd6faaa770992`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/LICENSE`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/pyproject.toml`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/uv.lock`
- τ³ task/evaluator and retrieval sources:
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/airline/tasks.json`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/telecom/tasks.json`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/telecom/split_tasks.json`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/banking_knowledge/tasks.json`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/docs/evaluation.md`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/evaluator/evaluator.py`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/data_model/tasks.py`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/domains/banking_knowledge/retrieval.py`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/banking_knowledge/prompts/classic_rag_bm25_no_grep.md`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/domains/telecom/tools.py`;
  `https://raw.githubusercontent.com/sierra-research/tau2-bench/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/user/user_simulator.py`
- Qwen3.6 model card:
  `https://huggingface.co/Qwen/Qwen3.6-35B-A3B`
- Terminal-Bench 2.1 fallback:
  `https://www.tbench.ai/news/terminal-bench-2-1`
- Current pricing sources and observations:
  `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
- AWS EC2 Spot price-history contract:
  `https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html`
- AWS ECR private-endpoint requirements and PrivateLink pricing:
  `https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html`;
  `https://aws.amazon.com/privatelink/pricing/`
- AWS Batch compute-environment terminal-state behavior:
  `https://docs.aws.amazon.com/cli/latest/reference/batch/describe-compute-environments.html`
- AWS Batch timeout best-effort behavior:
  `https://docs.aws.amazon.com/batch/latest/userguide/job_timeouts.html`
- AWS Budgets delay/advisory behavior:
  `https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html`
- Azure Batch NVMe/start-task contracts:
  `https://learn.microsoft.com/en-us/azure/batch/batch-nvme-temporary`;
  `https://learn.microsoft.com/en-us/python/api/azure-batch/azure.batch.models.starttask`
- Azure Batch Spot, capacity, and VM-size contracts:
  `https://learn.microsoft.com/en-us/azure/batch/batch-spot-vms`;
  `https://learn.microsoft.com/en-us/azure/batch/batch-capacity-planning`;
  `https://learn.microsoft.com/en-us/azure/batch/batch-pool-vm-sizes`
- Azure NCads A100 v4 availability notice:
  `https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nca100v4-series`
- Azure Container Registry SKU/retention limits:
  `https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus`;
  `https://learn.microsoft.com/en-us/azure/container-registry/container-registry-retention-policy`
