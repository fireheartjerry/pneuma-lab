# Protocol v2 Empirical Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, locally validate, preregister, execute, analyze, and package the
Protocol-v2 experiment that tests whether persistent causally active internal
state reduces recurring software-agent failures and supports faithful causal
attribution, against all five required comparators and the Influence-off null.

**Architecture:** The actor-side prospective recognizer, actor-side online
learning signal, and arm-blind offline evaluator are separate packages with
one-way typed interfaces. A single structured-action driver, sandbox, backend,
budget meter, candidate generator, and trace binder serve seven condition
modules; conditions may change only their declared memory/state treatment.
Exact Suite-A labels ground the confirmatory endpoint, while Suite-B-offline and
Suite-B-live provide external-validity analyses without being conflated.

**Tech stack:** Python `==3.12.*`, the repository's existing `pytest`,
`jsonschema`, and `pyarrow` dependencies, local Ollama/Qwen2.5-Coder for
development, digest-bound Git sandboxes, JSON/JSONL receipts, and the existing
`pneuma_lab` schema, governance, intervention, and provenance utilities.
V2-35 adds and exactly pins the sole new numerical dependency before statistical
code imports it; no unlisted numerical package is assumed.

---

## 0. Authority, scope, and execution convention

This document is the executable backlog required by the rationale in
`16-protocol-v2-hardening.md` §13. It supersedes dependency order and acceptance
criteria in `12-implementation-plan.md` wherever the two differ. The scientific
protocol and constants in `02-research-thesis.md`, especially §8, are canonical;
document 16 records hardening rationale rather than a competing specification.
Any change to the canonical constants requires a decision-log entry before
implementation continues.

All paths below are relative to the active worktree. Raw data below
`C:\pneuma-data` are read-only; derived artifacts go below `build/research/`.
No task imports from or writes to the 9to5 repository. No subject-model weights
are trained. Self-report prose never enters a behavioral endpoint. State emits
bounded pressure over model-proposed candidates and never creates or edits a
tool call.

Authorization is an execution dependency, not a paper receipt. Every boundary
that can open governed data, materialize a sandbox source, contact a model, or
invoke a paid provider accepts the nominal, runtime-validated `ExecutionGuard`
defined in V2-02 and performs its scope check before the injected operation.
Serializable receipts and objects that merely expose similarly named methods are
inert.
Fixture, pilot, official-local, and official-paid capabilities are disjoint;
only V2-38's G8 executor can consume an official capability.

Outcome missingness is also fail-closed everywhere: every observed agent-side
non-engagement or failure confined to one branch is adverse. Only immutable,
preregistered evidence of one exogenous outage affecting the complete randomized
block may remove that whole block; every uncertain case stays adverse and enters
worst-case sensitivity analysis.

Resolve the active worktree at execution time and use its frozen project
environment for every Python/test command. Never use the parent repository's
`.venv`, a hardcoded interpreter, ambient `PYTHONPATH`, or an environment rooted
outside the resolved worktree. In particular, do not bootstrap with an
unqualified `git rev-parse`: under WSL a linked worktree's `.git` file may name
its administrative directory with a Windows path that ambient Git cannot
resolve. Bootstrap from the validated current path, translate only a drive-letter
`gitdir:` value with `wslpath`, and use explicit `--git-dir`/`--work-tree` for
every Git operation:

```bash
WT="$(pwd -P)"
while [ "$WT" != / ] && [ ! -e "$WT/.git" ]; do
    WT_PARENT="$(dirname "$WT")"; test "$WT_PARENT" != "$WT"; WT="$WT_PARENT"
done
test "$WT" != / && test -e "$WT/.git"
if [ -d "$WT/.git" ]; then
    GIT_ADMIN="$WT/.git"
else
    test -f "$WT/.git"
    mapfile -t GITFILE < "$WT/.git"
    test "${#GITFILE[@]}" -eq 1
    GITDIR_RAW="${GITFILE[0]%$'\r'}"
    case "$GITDIR_RAW" in gitdir:\ *) GITDIR_RAW="${GITDIR_RAW#gitdir: }";; *) false;; esac
    case "$GITDIR_RAW" in
        [A-Za-z]:[\\/]*) command -v wslpath >/dev/null; GIT_ADMIN="$(wslpath -u "$GITDIR_RAW")" ;;
        /*) GIT_ADMIN="$GITDIR_RAW" ;;
        *) GIT_ADMIN="$WT/$GITDIR_RAW" ;;
    esac
fi
test -d "$GIT_ADMIN"
GIT_ADMIN="$(cd "$GIT_ADMIN" && pwd -P)"
gitwt() { command git --git-dir="$GIT_ADMIN" --work-tree="$WT" "$@"; }
test "$(gitwt rev-parse --is-inside-work-tree)" = true
test "$(cd "$(gitwt rev-parse --git-dir)" && pwd -P)" = "$GIT_ADMIN"
WT_REPORTED="$(gitwt rev-parse --show-toplevel)"
test "$(cd "$WT_REPORTED" && pwd -P)" = "$WT"
cd "$WT"
UV="$(command -v uv 2>/dev/null || true)"
if [ -z "$UV" ]; then
    UV=/mnt/c/pneuma-lab/build/uv-0.11.28/uv
fi
test -x "$UV"
export UV_PROJECT_ENVIRONMENT="$WT/build/research/env"
pyrun() {
    "$UV" run --project "$WT" --frozen --extra dev python "$@"
}
pyrun_research() {
    "$UV" run --project "$WT" --frozen --extra dev --extra research python "$@"
}
```

The canonical worktree path, translated administrative-directory path, `.git`
file bytes, and explicit Git invocation are receipt-bound; `gitwt` is used for
all later Git reads. The resolved uv executable path/version/digest and
`UV_PROJECT_ENVIRONMENT=$WT/build/research/env` are receipt-bound. The fallback
uv path above is a pinned tool binary, not a Python environment; it may create or
use packages only in the worktree-local project environment. Commands that need
the V2-35 numerical extra use `pyrun_research`.

G0 and G8 additionally resolve `pneuma_lab.__file__` and every package search
location inside a clean subprocess, require each path to remain below
`$WT/src/pneuma_lab`, and bind a canonical digest over the tracked
`src/pneuma_lab/` source root. A package imported from the parent checkout,
another worktree, an editable path, or a stale external environment fails closed.

For each task, first add the named failing test and run its exact test file,
then implement only the declared contract, rerun the test file, and finally run
the phase gate. A scientific threshold miss is a result, never a software-test
failure; tests assert correct computation, binding, and fail-closed behavior.
Before committing, inspect the task's exact `Files` paths and stage those files
individually. Never stage a directory, use a broad pathspec, or include unrelated
user changes. This plan intentionally supplies commit subjects but no staging
commands.

## 1. Package and artifact map

| Area | Responsibility | Forbidden dependencies |
| --- | --- | --- |
| `src/pneuma_lab/agent/` | backend, structured candidates, sandbox tools, live loop, metering | evaluator labels, generator motif ids, report prose |
| `src/pneuma_lab/recognition/` | prospective actor recognizer and post-action online signal | `pneuma_lab.evals`, future outcomes, test labels |
| `src/pneuma_lab/benchmark/` | Suite-A generators and Suite-B data/source manifests | condition identity or state |
| `src/pneuma_lab/state/` | persistent variables, stores, centered loss, pressure head | prompt rendering and direct tool execution |
| `src/pneuma_lab/conditions/` | seven treatment modules over shared interfaces | offline evaluator internals |
| `src/pneuma_lab/evals/` | arm-blind exact labels, repeat harm, utility and self-report scoring | `conditions`, `state`, `voice` for behavioral scoring |
| `src/pneuma_lab/statistics/` | cluster randomization, simultaneous intervals, multiplicity, power | arm-readable prose or mutable summaries |
| `src/pneuma_lab/experiment/` | binding, branching, causal runs, orchestration, preregistration, gates, packaging | unbound inputs or unapproved paid execution |
| `schemas/` | immutable interchange contracts | raw task/tool/output prose in public frames |
| `build/research/` | generated receipts, pilots, results, figures, bundle | hand-edited result numbers |

The typed seam is defined once in
`src/pneuma_lab/experiment/contracts.py`. Every downstream task imports those
types instead of defining condition-specific copies.

Type ownership is fixed as follows so task order does not create interface
cycles:

| Owner task/file | Types introduced there |
| --- | --- |
| V2-02 `experiment/contracts.py` | `ExecutionGuard`, `GuardedOperation`, `GuardValidation`, `ConditionId`, `MotifKey`, `PrototypeLineageId`, `RunCaps`, `ResourceUsage`, `ActionCandidate`, `CandidateBatch`, `PressureVector`, `MemoryContext`, `DeclaredCarrierView`, `ObservableView`, `ActorContext`, `ActorEvent`, `ActorStep`, `ActorToolResult`, `ActorDiagnostic`, `TaskBoundaryAppraisal`, `RiskForecast`, `NoticeReadout`, `ActuationReadout`, `NoticeProbability`, `PretreatmentRecurrenceTarget`, `LearningSignal`, `ExposureReceipt`, `ScheduledOpportunity`, `OpportunitySchedule`, `OpportunityOutcome`, `ExogenousOutageEvidence`, `PseudonymousArmOutcome`, `CompleteRandomizedBlock`, `ValidatedBlockMask`, `RecordedSevenArmAssignment`, `ImmutableTrace`, `RunBinding`, `TaskFingerprint` |
| V2-04 `experiment/authorization.py` | `FixtureCapability`, `DataAccessCapability`, `DataAccessReceipt`, `LocalPilotCapability`, `LocalPilotReceipt` |
| V2-05 `agent/backend.py` | `CandidateRequest`, `CandidateBackend`, `BackendAuditReceipt` |
| V2-06 `agent/sandbox.py` / `agent/tools.py` | `SandboxSnapshot`, `Sandbox`, `ToolCall`, `ToolResult` |
| V2-07 `adapters/structured_observation.py` | `ErrorClass`, `StructuredObservation` |
| V2-08 `adapters/recurrence.py` | `RecurrenceFeatures` |
| V2-09 `benchmark/motif_catalog.py` / `task_oracle.py` | `MotifDefinition`, `TaskOracle`, `ImplicatedSets`, `ExactBehaviorLabel` |
| V2-15 `benchmark/exposure.py` / `benchmark/sequence.py` | `ExposureProvenance`, `SequenceSpec`, `SuiteATask`, `SuiteASequence` |
| V2-20 `experiment/binding.py` | `BoundTask`, `BoundPrefix`, `BoundConditionConfig` |
| V2-22 `agent/driver.py` | `ControlPolicy`, `LiveAgentDriver` |
| V2-25 `state/store.py` | `PneumaState`, `StateUpdate`, `StateReceipt` |
| V2-27 `recognition/notice_readout.py` / `state/decision_head.py` | `NoticeMeasurementConfig`, `LossConstants`, `NoticeConstants`, `HeadConstants`, `SelectionReceipt` |
| V2-28 `conditions/protocol.py` / `conditions/tuning.py` | `ConditionPolicy`, `ConditionSnapshot`, `ControllerSearchSpace`, `MatchedSearchBudget`, `MatchedControllerTuningReceipt` |
| V2-32 `evals/repeat_harm.py` / `utility_gates.py` | `RandomizedBlockEndpointBundle`, `SequenceEndpoint`, `SeverityWeightedSequenceEndpoint`, `RegisteredCellEndpoint`, `EqualWeightH1Endpoint`, `NaturalSequenceEndpoint`, `BoundEpisodeOutcome`, `BehaviorFinalizationReceipt`, `UtilityGateBundle` |
| V2-34 `experiment/causal.py` / `statistics/divergence.py` | `CausalSeedBlock`, `PoweredEquivalenceDesign`, `CausalGateReport` |
| V2-35 `statistics/recognition_endpoint.py` / `decision_regions.py` | `FrozenRecognitionCriteria`, `RecognitionDecision`, `NuisanceOnlyPilotParameters`, `FisherSharpNullBundle`, `H1AverageEffectBundle`, `H1Decision`, `H2Decision`, `H3Decision`, `H4Decision`, `GlobalH1H4Decision` |
| V2-37 `voice/causal_report.py` / `evals/self_report_faithfulness.py` | `CausalAttributionLabel`, `TargetSymmetricPublicFrame`, `FrozenActorReporterConfig`, `ReceiptOnlyDecoder`, `FrozenSelfReportCriteria`, `SelfReportBundle` |
| V2-38 `experiment/official_gate.py` / `official_executor.py` | `OfficialRunCapability`, `OfficialRunReceipt`, `OfficialExecutionReceipt`, `OfficialTraceBundle`, `PaidBudgetReservation` |

## 2. Legacy 39-task crosswalk

No legacy item is silently dropped. “Retired” means the old mechanism was
scientifically invalid and its intended role is implemented by the listed v2
task instead.

| Legacy task | Protocol-v2 disposition |
| --- | --- |
| WS-A-1 | V2-07 enriched typed observations |
| WS-A-2 | V2-08 recurrence features |
| WS-A-3 | V2-13 actor-signal validation |
| WS-A-4 | Retrospective `detectFailure` retired; V2-10 prospective recognizer plus V2-11 online signal |
| WS-B-1 | V2-09 exact motif fixtures, V2-15 sequence generator, V2-16 transforms |
| WS-B-2 | V2-09 and V2-12 exact offline evaluator |
| WS-B-3 | V2-15 fixed-exposure sequence generator |
| WS-B-4 | V2-17 separate surface/repository/motif split regimes |
| WS-B-5 | V2-18 governed offline external-validity lane; judged labels remain secondary |
| WS-B-6 | V2-17 leakage quarantine and V2-20 immutable binding |
| WS-C-1 | V2-05 frozen backend and seed audit |
| WS-C-2 | V2-06 sandbox, V2-21 candidate protocol, V2-22 live tool loop |
| WS-C-3 | V2-20 binding and V2-23 common-prefix branching |
| WS-D-1 | V2-28 Base condition |
| WS-D-2 | V2-24 deterministic retrieval and V2-29 Retrieval condition |
| WS-D-3 | V2-29 Reflection condition |
| WS-D-4 | V2-25–V2-27 state/head and V2-30 Pneuma condition |
| WS-D-5 | V2-28 mandatory Retry-count condition |
| WS-D-6 | Old partial ablation retired; V2-30 full Influence-off null |
| WS-E-1 | V2-25 task-time `s_m` |
| WS-E-2 | V2-26 forecast-calibration `c` |
| WS-E-3 | V2-26 task-time caution `t` |
| WS-E-4 | Retrieval-trust scalar retired; V2-25 recognizer-reliability `r_m` |
| WS-E-5 | V2-25 deterministic receipt-bound state store |
| WS-E-6 | V2-27 centered loss and bounded reranker |
| WS-E-7 | V2-20 bindings plus V2-25/V2-26 receipts |
| WS-F-1 | V2-33 live intervention surface |
| WS-F-2 | Descendant transcript freeze retired; V2-23 freezes only prefix and exogenous inputs |
| WS-F-3 | V2-34 distributional causal checks and V2-35 design-based inference |
| WS-F-4 | V2-36 deterministic instrumentation oracle |
| WS-G-1 | V2-12 exact labels and V2-32 fixed-denominator endpoint |
| WS-G-2 | V2-35 cluster inference, simultaneous intervals, and multiplicity |
| WS-G-3 | V2-16 anti-gaming tasks and V2-32 utility co-gates |
| WS-G-4 | V2-03 firewall, V2-12 evaluator, and V2-14 structural separation |
| WS-H-1 | V2-37 intervention-blind self-report evaluation |
| WS-I-1 | V2-35 power plus V2-38 orchestration |
| WS-I-2 | V2-38 frozen preregistration |
| WS-I-3 | V2-04 authorization plus V2-38 official/paid gates |
| WS-I-4 | V2-39 analysis, figures, papers, and reproducibility bundle |

## 3. Hard gates

| Gate | Required evidence | What remains blocked |
| --- | --- | --- |
| G0 — reproducible baseline | after reviewed harness/baseline repairs are narrowly committed, V2-01 trusted launcher proves two independent nonce-bound identical committed-default-suite processes from one final clean commit/worktree-local frozen uv environment, bound import root and source-root digest, with zero return code/failures/errors; the fixed default policy excludes opt-in `qwen_smoke` GPU tests, which have a separate governed smoke gate | every task from V2-02 onward |
| G1 — safe substrate | ordered V2-02 → V2-04 → V2-05 plus prerequisite-correct V2-03/V2-06; nominal deny-by-default guard, import/privacy checks, signed-run verifier, fake backend, and sandbox tests green | raw-data processing and any local model execution |
| G2 — valid labels | V2-07–V2-14 pass; exact evaluator never shares code/parameters with actor labels | conditions, pilot, and causal claims |
| G3 — bound benchmark/runtime | V2-15–V2-23 pass; common prefix byte-equal through `t0`; descendants run live | state/condition comparison |
| G4 — condition parity | V2-24–V2-31 pass for all seven arms under fake backend and one authorized local smoke sequence, including identical inert notice checkpoint/prompt/schema/decoding/timing/call count/token cap, a separate equal notice meter, and exact independent Uniform(7!) mapping/order machinery | pilot |
| G5 — estimand/causal/statistics | V2-32–V2-37 pass, including equal opportunity→cell→lineage→motif primary aggregation, complete-block masking, anti-gaming, exact conditional replay of Uniform(7!) policy mapping `M` given independent stream order `O`, separate Fisher sharp-null and lineage-bootstrap average-effect outputs, powered stochastic equivalence, mandatory persistence reset with no rehydration, explicit H1–H4 IUTs/four-slot Holm, and the same actor's target-symmetric post-behavior nine-label report firewall. The lineage fallback is tested but cannot pass randomized-causal evidence | preregistration and official run |
| G6 — local pilot/prereg | disjoint 20–30-authored-lineage nuisance-only pilot, complete-H1-conjunction power report at `Delta_power=0.10`, dry-run receipts, proof every scientific criterion/grid/margin predates pilot, frozen constants/splits/labels, clean commit | confirmatory execution |
| G7 — paid-compute approval | exact matrix, GPU/provider/image, observed throughput, retry allowance, current price, append-only ledger balance/reservations, and plan hash shown to user; `settled spend + active reservations + new worst case ≤ USD 50`; one-use explicit approval and atomic reservation receipts exist | every RunPod API call, pod creation, paid image pull, or paid model run |
| G8 — official run | V2-38 creates a scoped nominal `OfficialRunCapability` only after validating clean tree, worktree-local frozen uv environment, imported-module/source-root digests, authorization, prereg hash, checkpoint/config/prompt/task/sandbox digests, seed schedule, and G7 when paid | every confirmatory data read, model/provider call, and result generation |

G7 is an unconditional pause. Preparing bundles and estimating cost locally is
authorized; spending even one paid cent is not. Secrets are supplied through a
process environment at execution time, never stored in Git, logs, manifests,
shell history, or paper artifacts.

---

## Phase P0 — Reproducible substrate

### V2-01 — Reproduce and lock a green baseline

**Legacy mapping:** prerequisite added by Protocol v2; supports WS-I-3.

**Files:**

- Modify: `.gitattributes`
- Create: `scripts/__init__.py`
- Create: `scripts/research/__init__.py`
- Create: `scripts/research/capture_baseline.py`
- Create: `tests/research/test_capture_baseline.py`
- Generate: `build/research/baseline/pytest-run-1.xml`
- Generate: `build/research/baseline/pytest-run-2.xml`
- Generate: `build/research/baseline/run-1-nonce.txt`
- Generate: `build/research/baseline/run-2-nonce.txt`
- Generate: `build/research/baseline/run-1-collection.json`
- Generate: `build/research/baseline/run-2-collection.json`
- Generate: `build/research/baseline/validation-collection.json`
- Generate: `build/research/baseline/run-1-stdout.bin`
- Generate: `build/research/baseline/run-2-stdout.bin`
- Generate: `build/research/baseline/run-1-stderr.bin`
- Generate: `build/research/baseline/run-2-stderr.bin`
- Generate: `build/research/baseline/run-1-process.json`
- Generate: `build/research/baseline/run-2-process.json`
- Generate: `build/research/baseline/baseline-receipt-run-1.json`
- Generate: `build/research/baseline/baseline-receipt-run-2.json`
- Generate: `build/research/baseline/baseline-pair-receipt.json`
- Generate (ephemeral, fresh each trusted invocation): `build/research/env/`

**Contract:**

```python
def build_baseline_receipt(
    pytest_xml: pathlib.Path,
    *,
    commit: str,
    python_version: str,
    dependency_lock_sha256: str,
    project_config_sha256: str,
    repo_root: pathlib.Path,
) -> dict: ...

def validate_baseline_pair(first: object, second: object) -> _LiveG0Capability: ...

def require_live_g0_capability(value: object) -> _LiveG0Capability: ...

def audit_persisted_baseline_pair(first: dict, second: dict) -> dict: ...

def run_trusted_baseline_pair(
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
) -> _LiveG0Capability: ...

def run_diagnostic_baseline_pair(
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
) -> dict: ...
```

`build_baseline_receipt` is a lower-level parser for tests and diagnostics; a
caller-supplied XML file can never mint G0 authority. Only two live child
processes owned by one active `run_trusted_baseline_pair` session can produce a
non-serializable `_LiveG0Capability`. Persisted run/pair JSON has
`authority = "none"`, `authentication = "none"`, and
`threat_model = "honest_local_operator"`; its SHA-256 identifiers are content
addresses, never signatures. `audit_persisted_baseline_pair` may recheck those
artifacts but can never recreate G0. A later process that requires G0 reruns the
trusted launcher, while one orchestration process may carry the live capability
forward.
The official entrypoint pins the imported launcher bytes, the complete
transitive module-function closure, critical type/constant identities, and
imported process/evidence primitives. This detects accidental same-process test
fixture injection; it is not claimed to resist a hostile Python process that
can rewrite arbitrary module globals. Monkeypatched/injected transports are
accepted only by `run_diagnostic_baseline_pair`, whose output remains
non-authoritative. Every downstream consumer calls
`require_live_g0_capability`, which accepts only the exact object stored in its
still-active official launcher registry entry; directly constructing the
nominal dataclass cannot recreate G0.

The trusted launcher resolves and validates the exact worktree, strips ambient
`GIT_DIR`, `GIT_WORK_TREE`, `PYTEST_ADDOPTS`, coverage, Python-path, and test-
selection variables, and captures `HEAD` plus clean tracked-tree status using
the §0 bootstrap and explicit `--git-dir`/`--work-tree` Git calls before,
between, and after the two runs. A linked-worktree `.git` file is parsed as one
strict `gitdir:` line; a Windows drive path is converted with a validated
`wslpath`, while malformed, missing, escaping, or worktree-mismatched
administrative paths fail closed. The exact `.git` marker bytes, canonical Git
administrative path, Git executable/digest and—under WSL—the lexical `wslpath`
executable/target digest, exact translation argv digest, and translated path are
receipt-bound. Directory creation walks one canonical component at a time and
rejects symlinks/junctions before writing. It
hashes the fixed config set (`pyproject.toml`, `uv.lock`, `.gitattributes`, both
regular-package `scripts/**/__init__.py` markers, and the launcher source),
resolved uv executable/version/digest, exact
`UV_PROJECT_ENVIRONMENT=$WT/build/research/env`, the uv-selected Python
executable/version, and a canonical installed-distribution inventory into
`project_config_sha256` and `environment_sha256`. It separately hashes the
tracked full working tree against HEAD after Git clean filters, separately binds
its raw-byte manifest as `tracked_tree_sha256`, hashes `src/pneuma_lab/` as
`source_tree_sha256`, and runs the clean-
subprocess import-root check defined in §0 before, between, and after both runs.
Before the first probe, `build/research/env` must be absent. The launcher creates
it component-by-component, provisions it only through the bound uv command,
hashes every regular environment file and directory, rejects every
non-allowlisted link, and receipt-binds the POSIX uv `bin/python*` interpreter
aliases and `lib64 -> lib` link. It rejects case collisions at every directory
component, a preseeded environment, or any ignored/untracked checkout file
outside the exact baseline-output and managed-environment trees. Pytest plugin
autoload and its cache provider are disabled. Dirty state,
HEAD/config/environment/source drift,
an unexpected worktree or
module root, the default/root `.venv`, or an unapproved uv/Python executable
fails before G0 is emitted.

The launcher constructs—not accepts from a caller—the exact committed-default-
suite argv:
the receipt-bound uv executable, `run --project <resolved-WT> --frozen --extra
dev python -m pytest tests -q`, the repository's fixed pytest config, a
launcher-owned JUnit path, and a launcher-owned nonce binding, with
`UV_PROJECT_ENVIRONMENT` fixed to the worktree-local research environment. The
committed `pyproject.toml` deliberately contributes
`addopts = '-m "not qwen_smoke"'`: G0 covers the complete default CPU collection,
while opt-in GPU smoke tests are governed separately. No caller-supplied or
launcher-added path, marker, keyword, deselection, last-failed, max-fail,
ignore, or `PYTEST_ADDOPTS` selection beyond that fixed, receipt-bound config is
permitted. A launcher-owned `pythonpath` override puts the
regular-package worktree root before `src`, preventing an installed or
`src/`-local `scripts` package from shadowing the hook. Before each process
starts it issues and persists
a distinct nonce under `build/research/baseline/`, binds that nonce into the
JUnit suite name through the launcher-owned fixed argument
`-o junit_suite_name=pneuma-baseline-<nonce>`, and later verifies the binding.
(`--junit-prefix` is not used because it changes testcase class names rather
than the suite name.) Each run receipt records
process id, start/end timestamp, exact argv, sanitized-environment digest,
uv/Python executable digests, resolved project/environment/module paths,
source-root digest, return code, stdout/stderr digests, nonce, JUnit path/content
digest, testcase collection digest/count, outcome counts, and receipt id. A
launcher-owned pytest hook records the canonical collected node-id list and its
own exact worktree-relative path/source digest before execution; the collection
digest is not inferred only from whichever testcases happen to appear in JUnit.
Raw stdout/stderr and a canonical launcher-owned
process journal are persisted and cross-checked against the in-memory completed
child; timestamps must be timezone-aware and ordered, and the JUnit timestamp
must fall inside the process interval.

`validate_baseline_pair` requires two launcher-registry-owned, live,
same-session, genuinely independent zero-return-code,
zero-failure/error executions: same commit, clean state, fixed config,
environment, uv/Python identities, worktree/module root, source-root digest,
platform, testcase collection digest, and collected counts;
distinct nonces, processes, paths, timestamps, JUnit hashes, and receipt ids. It
returns a nominal live capability. The trusted/diagnostic pair runner writes the
canonical, non-authoritative local audit record as sorted JSON to
`baseline-pair-receipt.json`. Copying XML,
re-signing a content hash, accepting arbitrary parser output, deserializing the
capability, or
changing collection between runs fails G0. All launcher-owned evidence/config/
nonce I/O must resolve strictly below `build/research/baseline/`; it refuses any
artifact path or symlink escape outside that directory (pytest's isolated test
fixtures retain their existing temporary-directory behavior).

- [ ] Add tests `test_receipt_rejects_failing_suite`,
  `test_receipt_is_canonical`, `test_missing_junit_fails_closed`,
  `test_persisted_audit_rejects_copied_trusted_junit`,
  `test_pair_rejects_environment_drift`, and
  `test_pair_accepts_two_independent_green_runs`. Add trusted-launcher tests for
  dirty/changed HEAD, ambient Git/pytest option stripping, caller selection-flag
  refusal, wrong executable/config, missing or replayed nonce, JUnit nonce
  mismatch, nonzero return code despite forged green XML, collection drift,
  process-evidence drift, root/default-venv or parent-worktree import, source-root
  drift, output traversal/symlink escape, a Windows-path linked-worktree
  `gitdir:` under WSL, CRLF in that one line, relative gitdir resolution,
  unavailable/failing `wslpath`, multiple/malformed lines, missing gitdir, and
  explicit-Git top-level mismatch, transitive argv/environment selection
  injection, POSIX uv interpreter aliases, directory-component case collisions,
  pytest-hook package shadowing, and proof that a raw
  `build_baseline_receipt` result, a rewrapped run, or a directly constructed
  nominal capability has no G0 authority.
- [ ] Run `pyrun -m pytest tests/research/test_capture_baseline.py -q`; expect
  collection or import failure before the script exists.
- [ ] Implement the contract and run
  `pyrun -m pytest tests/research/test_capture_baseline.py -q`; expect all focused
  tests to pass.
- [ ] Obtain focused spec and code review of the harness and its adversarial
  tests, resolve findings, rerun the focused file, then commit the reviewed
  receipt harness first with subject
  `test: lock empirical baseline`, using only its exact `Files` paths.
- [ ] Confirm that committed harness `HEAD` is clean, then invoke the trusted
  launcher once. It must issue both nonces and launch both immutable committed-
  default-suite
  commands itself; manually invoking pytest and passing XML to the parser is
  diagnostic only and cannot satisfy G0.
- [ ] If either run fails, diagnose it, add a focused regression test, commit
  each baseline repair separately using only the exact source/test paths in its
  failure ledger, and discard/supersede the earlier pair. Rerun the trusted pair
  from the **final clean repair commit**; never combine one pre-repair run with
  one post-repair run.
- [ ] Verify the final canonical pair receipt binds that same final clean commit,
  config/environment/source-root digest, imported module root, and testcase
  collection while preserving two complete process evidence sets.

**Acceptance:** within the explicit honest-local-operator / trusted-OS-and-tools
boundary, the trusted launcher proves the same complete committed-default CPU
testcase collection
passes in two independent processes launched from one final clean commit after
the reviewed harness and every baseline repair are committed; generated evidence remains
untracked under `build/research/baseline/`; no parser-only receipt is accepted
as G0, persisted JSON never recreates live authority, and no research feature
has been introduced as a baseline repair. Protection against a malicious
filesystem owner, compromised OS/toolchain, or concurrent hostile writer is out
of scope and is stated rather than implied away.

### V2-02 — Define Protocol-v2 typed contracts and schemas

**Legacy mapping:** WS-E-7 and the shared interfaces implicit across WS-C–WS-I.

**Prerequisite:** G0 from the final clean V2-01 baseline commit.

**Files:**

- Create: `src/pneuma_lab/experiment/__init__.py`
- Create: `src/pneuma_lab/experiment/contracts.py`
- Create: `schemas/experiment-run-manifest.schema.json`
- Create: `schemas/opportunity-outcome.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Modify: `tests/test_schema_loads.py`
- Test: `tests/research/test_protocol_v2_contracts.py`

**Contract:**

Define the frozen dataclasses/enums assigned to V2-02 in the type ownership
table: `ExecutionGuard`, `GuardedOperation`, `GuardValidation`, `ConditionId`,
`MotifKey`, `PrototypeLineageId`, `RunCaps`, `ResourceUsage`, `ActionCandidate`,
`CandidateBatch`, `PressureVector`, `MemoryContext`, `DeclaredCarrierView`,
`ObservableView`, `ActorContext`,
`ActorEvent`, `ActorStep`, `ActorToolResult`, `ActorDiagnostic`,
`TaskBoundaryAppraisal`, `RiskForecast`, `NoticeReadout`, `ActuationReadout`, `NoticeProbability`,
`PretreatmentRecurrenceTarget`, `LearningSignal`, `ExposureReceipt`,
`ScheduledOpportunity`, `OpportunitySchedule`,
`OpportunityOutcome`, `ExogenousOutageEvidence`, `PseudonymousArmOutcome`,
`CompleteRandomizedBlock`, `ValidatedBlockMask`, `RecordedSevenArmAssignment`,
`ImmutableTrace`, `RunBinding`, and `TaskFingerprint`.

`ExecutionGuard` is a concrete nominal base class, not a `Protocol` and not a
duck-typed shape. Its common operation surface is defined here once:

```python
class ExecutionGuard:
    def validate(self, operation: GuardedOperation) -> GuardValidation: ...
    def open_source(self, operation: GuardedOperation, opener: Callable[[], T]) -> T: ...
    def materialize_source(self, operation: GuardedOperation, fetcher: Callable[[], T]) -> T: ...
    def call_local_model(self, operation: GuardedOperation, transport: Callable[[], T]) -> T: ...
    def call_provider(self, operation: GuardedOperation, transport: Callable[[], T]) -> T: ...

def require_execution_guard(value: object) -> ExecutionGuard: ...
```

The base implementation denies every operation. `require_execution_guard` uses
`isinstance`, validates an unforgeable verifier handle installed only by an
authorization factory, checks capability kind/scope/expiry/counters, and rejects
objects that merely implement the same methods or subclasses whose base
initializer/verifier was bypassed. Later capability modules import this class;
`contracts.py` never forward-imports concrete capabilities. Every concrete
capability overrides only its allowed operations and revalidates before invoking
the supplied callback; denial proves the callback was never reached.

`ConditionId` contains exactly `base`, `retrieval`, `reflection`, `retry_count`,
`motif_count_ema`, `pneuma_state`, and `influence_off`. Numeric probabilities
validate in `[0,1]`; candidates carry only model-proposed tool/arguments,
normalized score, and fixed meta-action class. `PrototypeLineageId` binds the
highest authored generator/prototype ancestor rather than a variant name.
`NoticeReadout` is the **one** pre-action schema emitted by every arm, with one
`NoticeProbability` per known motif, coverage/abstention, timing, carrier-method,
and artifact digests. Arm-specific `CurrentOnlyRiskReadout` or
`StateRiskReadout` schemas are forbidden. Its `DeclaredCarrierView` may contain
only the current-task/within-opportunity observables plus that arm's legitimate
declared carrier (none, retrieval records, reflection lesson, retry count,
scalar hazard, or Pneuma state); no evaluator/target/future field is legal.
`ResourceUsage` accounts separately for every candidate, repair, fallback,
reflection, retrieval/state-maintenance model call; input/output token; attempted
tool action; retry; and failed call. It has disjoint main-action,
pre-action-notice-measurement, and post-behavior-reporting ledgers so diagnostics
are visible but cannot change the action budget. `ExogenousOutageEvidence` and the block/mask
records are frozen dataclasses: no per-arm record can request exclusion, and a
`ValidatedBlockMask` is constructible only by V2-32's complete seven-pseudonym
block validator. `RecordedSevenArmAssignment` is the shared immutable interchange
type; only V2-31's randomizer can issue an authoritative assignment receipt.
Create an explicit `EMPIRICAL_SCHEMA_FILES` registry category, fold it into
`ALL_SCHEMA_FILES`/`__all__`, and document its non-cognitive run-artifact role in
`docs/io-contract.md`. Every empirical schema added later in this plan must be
registered and documented in the same task that creates it.

- [ ] Add schema-roundtrip tests plus
  `test_condition_roster_is_exactly_seven`,
  `test_candidate_rejects_nonfinite_score`, and
  `test_public_outcome_contains_no_raw_prose`. Add construction tests proving
  outage evidence is immutable, a complete block requires seven unique bound
  pseudonyms, and neither an arm outcome nor caller-created mask can exclude a
  row. Add one-schema tests for seven condition-neutral `NoticeReadout` examples
  and reject an arm-specific schema, evaluator/target field, or post-action
  timestamp. Extend schema-load tests to assert
  both new files are in `EMPIRICAL_SCHEMA_FILES` and every registered empirical
  schema declares its artifact category.
- [ ] Add nominal-guard tests for deny-by-default behavior, rejection of a
  same-method fake, rejection of an uninitialized/forged subclass, expired and
  wrong-operation scope, callback-not-reached on denial, and absence of forward
  capability imports from `contracts.py`.
- [ ] Run `pyrun -m pytest tests/research/test_protocol_v2_contracts.py -q`;
  expect import failure.
- [ ] Implement immutable types, canonical serialization, and both schemas.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/test_validate.py tests/research/test_protocol_v2_contracts.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add protocol v2 contracts`.

**Acceptance:** one type definition serves every arm; schemas reject raw prompt,
objective, assistant text, tool output, and report prose fields; every empirical
schema is loadable through the explicit registry and human-readable contract
map. Every sensitive boundary accepts this nominal guard and no permissive
duck-typing fallback exists.

### V2-03 — Enforce prose-blind and three-label-path import firewalls

**Legacy mapping:** WS-G-4 and the firewall part of WS-H-1.

**Prerequisite:** V2-02; the checker imports the canonical contract/schema
registry rather than declaring local seam types.

**Files:**

- Create: `src/pneuma_lab/experiment/firewall.py`
- Test: `tests/research/test_protocol_v2_firewall.py`

**Contract:**

```python
def forbidden_imports(repo_root: pathlib.Path) -> tuple[dict, ...]: ...
def assert_protocol_firewalls(repo_root: pathlib.Path) -> None: ...
```

Parse Python ASTs, not source substrings. Modules below `recognition/` may not
import `evals`, `conditions`, or `voice`; behavioral evaluators may not import
`recognition`, `conditions`, `state`, or `voice`; `state` may not import
`agent.tools` or any prompt renderer. The allowlist is explicit and empty by
default. The checker also walks JSON schemas and rejects behavioral fields whose
names are `self_report`, `reflection_text`, `assistant_text`, `raw_output`, or
`prompt_text`.
For sensitive source/model/provider boundaries it also rejects locally declared
guard protocols, structural `hasattr`/cast fallbacks, or forward imports of
concrete capabilities from `experiment/contracts.py`; annotations must resolve
to the nominal V2-02 `ExecutionGuard`.

- [ ] Add temporary-package tests that plant one forbidden import per boundary
  and one valid import graph; add `test_behavioral_schema_rejects_prose_fields`.
  Plant a duck-typed guard protocol, forward capability import, and structural
  fallback; each must fail.
- [ ] Run `pyrun -m pytest tests/research/test_protocol_v2_firewall.py -q`;
  expect import failure.
- [ ] Implement the AST/schema checker with deterministic sorted diagnostics.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run the checker against the repository and
  `pyrun -m pytest tests/test_evidence_scoring.py tests/test_voice.py tests/research/test_protocol_v2_firewall.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `test: enforce empirical firewalls`.

**Acceptance:** a planted cross-boundary import fails before tests execute; the
existing voice package remains one-way and outside behavioral scoring.

### V2-04 — Add fail-closed data-access authorization

**Legacy mapping:** WS-I-3, with the paid checkpoint strengthened.

**Prerequisite:** V2-02 must be committed first. V2-04 extends the empirical
schema registry only after V2-02 creates it; these edits are never parallel.

**Files:**

- Create: `src/pneuma_lab/experiment/authorization.py`
- Create: `schemas/experiment-authorization.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Test: `tests/research/test_experiment_authorization.py`

**Contract:**

```python
def authorize_fixtures(repo_root: pathlib.Path) -> FixtureCapability: ...

def authorize_data_access(
    manifest_path: pathlib.Path,
    *,
    input_paths: Sequence[pathlib.Path],
) -> DataAccessCapability: ...

def authorize_local_pilot(
    manifest_path: pathlib.Path,
    *,
    data_capability: DataAccessCapability,
    checkpoint_sha256: str,
    pilot_plan_sha256: str,
    allowed_task_sha256s: Sequence[str],
    max_episodes: int,
) -> LocalPilotCapability: ...
```

`FixtureCapability` permits only repository fixtures and injected fake backends;
it denies every real source/materialization/local-model/provider operation.
`pilot` requires
a signed authorization whose data roots and code ancestor cover the requested
reads. This module intentionally has no `official` mode: the signed manifest is
an input to V2-38, which alone may create an official capability.
`authorize_local_pilot` separately permits only a
bounded, nonofficial, nonpaid local checkpoint smoke/pilot covered by the signed
manifest and wraps the already-scoped data capability so one composite guard can
mediate all pilot boundaries. It binds the disjoint pilot plan and exact task
digests; relabeling a confirmatory graph as `pilot` is rejected. Neither receipt
can authorize an official run or cloud API. Official
execution requires the distinct G8 `OfficialRunCapability` created in V2-38;
its audit receipt remains inert, and paid execution additionally requires G7.
Validation runs before any source file
or model endpoint is opened; this module exposes no provider-launch operation.
All capabilities nominally subclass the V2-02 `ExecutionGuard`, call its
verifier-installing base initializer through these factories, and carry distinct
runtime capability kinds; no public constructor, structural cast, or forward
import is accepted. Source bytes are available
only through `DataAccessCapability.open_source`; network/cache source acquisition
is available only through `DataAccessCapability.materialize_source` with a
scoped URL/commit/destination and injected fetcher; and local backend transport
only through `LocalPilotCapability.call_local_model`. Each method revalidates its
signed receipt, path/checkpoint scope, call/episode counter, and expiry before
invoking the injected operation. Naked receipts are inert serializable audit
objects and cannot be passed where an execution guard is required. Capabilities
are opaque in-process objects with an unforgeable verifier handle; deserializing
a receipt never reconstructs one.

- [ ] Add tests for unauthorized source reads, code drift, out-of-scope paths,
  a valid fixture read/fake-model call, fixture denial of every real operation,
  bounded local pilot, local-pilot episode overflow, paid/
  remote endpoint refusal, out-of-scope URL/commit/destination materialization,
  pilot-plan/task mismatch, absence/refusal of any official-capability factory at this layer,
  and proof that neither early receipt can satisfy an
  official/cloud execution check. Use injected operation spies proving no source
  or transport callback is invoked on failure; add a receipt-deserialization
  forgery test plus same-method fake and base-initializer-bypass tests.
- [ ] Run `pyrun -m pytest tests/research/test_experiment_authorization.py -q`;
  expect import failure.
- [ ] Implement schema validation and reuse fail-closed ancestry/clean-tree
  checks from `src/pneuma_lab/training/preflight.py` without weakening them;
  register/document the authorization schema under `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/test_training_governance.py tests/test_estimator_preflight.py tests/research/test_experiment_authorization.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: gate empirical execution`.

**Acceptance:** fixture tests need no external secret; real-data reads and local
pilot model calls need their signed scopes, and these early receipts can never
authorize official or paid execution.

### V2-05 — Implement the frozen candidate backend and seed audit

**Legacy mapping:** WS-C-1.

**Prerequisite:** V2-04, so fake/local backend paths consume real nominal
capabilities rather than a temporary duck-typed guard.

**Files:**

- Create: `src/pneuma_lab/agent/__init__.py`
- Create: `src/pneuma_lab/agent/backend.py`
- Create: `src/pneuma_lab/agent/ollama_backend.py`
- Create: `src/pneuma_lab/agent/model_audit.py`
- Test: `tests/research/test_agent_backend.py`

**Contract:**

```python
class CandidateBackend(Protocol):
    def generate(
        self,
        request: CandidateRequest,
        guard: ExecutionGuard,
    ) -> CandidateBatch: ...

def audit_backend(
    backend: CandidateBackend,
    requests: Sequence[CandidateRequest],
    guard: ExecutionGuard,
) -> BackendAuditReceipt: ...
```

`CandidateRequest` binds checkpoint digest, prompt-template digest, decoding
parameters, seed, candidate count, and one-call budget. The Ollama adapter sends
one request and records server/model identity, seed acceptance, raw-response
digest, parse status, latency, and token counts. It never claims stochastic
seed control unless repeated audits demonstrate it.
The adapter exposes no public unguarded transport: fake calls require a fixture
guard, local Ollama requires `LocalPilotCapability`, and a later paid/remote
backend requires the V2-38 official paid guard plus budget reservation.

- [ ] Add a fake backend test for one-call accounting, request binding, stable
  seeds, checkpoint mismatch, timeout, and an audit that truthfully reports
  nondeterminism. Add a transport spy proving `generate` cannot contact a model
  with a naked receipt or wrong execution capability.
- [ ] Run `pyrun -m pytest tests/research/test_agent_backend.py -q`; expect import
  failure.
- [ ] Implement the protocol, fake-test seam, Ollama adapter, and audit receipt.
- [ ] Run the test file; expect all tests to pass without contacting Ollama.
- [ ] After G1 and a V2-04 `LocalPilotCapability`, run the seed audit locally for pinned
  Qwen2.5-Coder 1.5B and 7B and store generated receipts under
  `build/research/model-audit/`; a nondeterministic result changes inference,
  not the receipt's pass/fail integrity.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add frozen candidate backend`.

**Acceptance:** backend identity and every generation parameter are bound; unit
tests are network-free; observed determinism is never generalized beyond the
audited request set.

### V2-06 — Build isolated digest-bound sandboxes and fixed tools

**Legacy mapping:** sandbox/tool-isolation portion of WS-C-2.

**Prerequisites:** V2-02 and V2-04, which own the sandbox seam types and guarded
source-materialization capability used to create snapshots.

**Files:**

- Create: `src/pneuma_lab/agent/sandbox.py`
- Create: `src/pneuma_lab/agent/tools.py`
- Test: `tests/research/test_agent_sandbox.py`

**Contract:**

```python
class SandboxFactory:
    def create(self, snapshot: SandboxSnapshot, run_id: str) -> Sandbox: ...

class ToolExecutor:
    def execute(self, sandbox: Sandbox, call: ToolCall) -> ToolResult: ...
```

Expose exactly `read_file`, `edit_file`, `run_tests`, `search`, and `finish`.
Resolve every path before use and require it to remain below the cloned sandbox
root. Tool results expose typed status, exit code, bounded lengths/features, and
content digests to public traces; raw bytes remain transient inside the sandbox
adapter. Snapshot and final-tree digests use sorted relative paths and file
content, excluding declared runtime-cache paths.

- [ ] Add tests for path traversal, symlink escape, undeclared tool, command
  injection through arguments, timeout, deterministic snapshot digest, and two
  independent clones from the same snapshot.
- [ ] Run `pyrun -m pytest tests/research/test_agent_sandbox.py -q`; expect import
  failure.
- [ ] Implement the factory/executor with no shell-string interpolation and
  bounded subprocess environment.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/research/test_agent_backend.py tests/research/test_agent_sandbox.py tests/research/test_protocol_v2_firewall.py -q` and declare G1 only after V2-01–V2-06 are green.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add isolated agent sandbox`.

**Acceptance:** no tool can escape or mutate the source snapshot; cloned
sandboxes start byte-equivalent and have independent writable descendants.

---

## Phase A — Observable labels with three independent paths

### V2-07 — Enrich trajectories before digesting raw observations

**Legacy mapping:** WS-A-1.

**Files:**

- Create: `src/pneuma_lab/adapters/error_class.py`
- Create: `src/pneuma_lab/adapters/structured_observation.py`
- Modify: `src/pneuma_lab/adapters/trajectory.py`
- Modify: `schemas/agent-trace-frame.schema.json`
- Modify: `docs/io-contract.md`
- Modify: `docs/phase-3-1-trajectory-traces.md`
- Modify: `tests/test_schema_loads.py`
- Modify: `tests/test_trajectory_extraction.py`
- Test: `tests/research/test_trajectory_enrichment_v2.py`

**Contract:**

```python
def classify_error(text: str) -> ErrorClass: ...
def extract_structured_observation(
    tool_name: str,
    arguments: object,
    output: str,
    *,
    repo_root: pathlib.PurePath,
) -> StructuredObservation: ...
```

The transient adapter extracts a closed `error_class`, normalized repo-relative
path identifiers, test identifiers, tool status, exit code, assertion count,
and verification transition before raw text is discarded. Public frames contain
only enums, bounded integers, salted identifiers when required, lengths, and
digests. Unknown content maps to `unknown` rather than free text.
Version the `agent-trace-frame` schema and update both human-readable contract
documents in the same task with the exact optional-field names, enum meanings,
privacy constraints, and backward-compatibility rule. Schema, loader registry,
adapter, docs, and golden/legacy tests must agree before the task is committed.

- [ ] Add positive/negative tests for assertion/import/syntax/timeout/patch/tool/
  permission/file errors, absolute-path stripping, test-id normalization,
  deterministic extraction, negated error prose, and all existing secret
  redaction patterns.
- [ ] Extend schema/trajectory tests for the new schema version, exact optional-
  field allowlist, old-frame compatibility, unknown-field rejection, and doc/
  schema field-name consistency.
- [ ] Run `pyrun -m pytest tests/research/test_trajectory_enrichment_v2.py -q`;
  expect import or schema failure.
- [ ] Implement the two pure extractors, extend
  `extract_agent_trace_frames`, and version the optional schema fields.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/test_trajectory_extraction.py tests/test_pneuma_trace_envelope.py tests/test_open_swe_traces_golden.py tests/test_openhands_sampled_golden.py tests/research/test_trajectory_enrichment_v2.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: enrich empirical trajectories`.

**Acceptance:** enriched fields are grounded in raw observations at adapter time;
no public frame contains raw arguments, outputs, task prose, stack traces, or
absolute local paths, and the versioned schema/docs/legacy tests describe the
same contract.

### V2-08 — Compute structural recurrence and implicated-set features

**Legacy mapping:** WS-A-2.

**Files:**

- Create: `src/pneuma_lab/adapters/recurrence.py`
- Modify: `src/pneuma_lab/adapters/trajectory.py`
- Test: `tests/research/test_structural_recurrence.py`

**Contract:**

```python
def recurrence_features(
    history: Sequence[StructuredObservation],
    current: StructuredObservation,
) -> RecurrenceFeatures: ...
```

Recurrence is structural and prefix-only within the current task/opportunity:
same error/test, error/path, repeated failed verification state, same destructive
meta-action, and exact identical retry are separate fields. The complete
current-opportunity prefix is searched, so nonadjacent within-task recurrence is
not lost, but observations with another task/opportunity id are rejected from
the actor-safe call. Cross-task information can persist only through a declared
condition memory/state carrier. Generator/evaluator-only implicated sets are
introduced in V2-09 and never enter this actor-safe module or recognizer.

- [ ] Add tests for a same failure through different commands, nonadjacent
  recurrence, same command with different failure, empty history, stable tie
  order, rejection of prior-task/exposure observations, and generator-oracle
  isolation.
- [ ] Run `pyrun -m pytest tests/research/test_structural_recurrence.py -q`;
  expect import failure.
- [ ] Implement the immutable recurrence feature record and attach only
  actor-safe prefix fields to extracted frames.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_trajectory_extraction.py tests/research/test_trajectory_enrichment_v2.py tests/research/test_structural_recurrence.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add structural recurrence features`.

**Acceptance:** a recurrence can be detected without byte-identical commands;
future outcomes and oracle implicated sets cannot enter actor-visible frames.

### V2-09 — Build exact Suite-A opportunity fixtures and motif catalog

**Legacy mapping:** WS-B-1 and WS-B-2.

**Files:**

- Create: `src/pneuma_lab/benchmark/__init__.py`
- Create: `src/pneuma_lab/benchmark/motif_catalog.py`
- Create: `src/pneuma_lab/benchmark/task_oracle.py`
- Create: `tests/fixtures/research/suite_a/catalog.json`
- Create: `tests/fixtures/research/suite_a/python_basic/src/sample.py`
- Create: `tests/fixtures/research/suite_a/python_basic/tests/test_sample.py`
- Create: `tests/fixtures/research/suite_a/python_basic/cases.jsonl`
- Test: `tests/research/test_suite_a_catalog.py`

**Contract:**

```python
def load_motif_catalog(path: pathlib.Path) -> tuple[MotifDefinition, ...]: ...
def evaluate_task_oracle(
    trace: ImmutableTrace,
    oracle: TaskOracle,
) -> ExactBehaviorLabel: ...
def implicated_sets(oracle: TaskOracle) -> ImplicatedSets: ...
```

Create six high-precision candidate families: broken-strategy retry, ignored
failing test, wrong-target edit, skipped required verification, destructive
action, and unsupported success claim. Each definition names typed opportunity,
harm, success, adverse agent-side non-engagement/runtime-failure, strictly
exogenous block-outage **evidence**, severity, decoy, and counterfactual rules.
Severity is frozen for a secondary endpoint only; it never changes the primary
unit opportunity weight.
The catalog never labels one arm as exogenously missing: it can only describe
the preregistered external telemetry needed by V2-32 to validate a complete
seven-arm block atomically. A
family is confirmatory only when those rules are mechanically observable; catalog
validation rejects prose or LLM-judge predicates.

- [ ] Add one positive, one successful-avoidance, one new-family failure, one
  refusal/timeout, and one decoy trace per motif; assert exact labels, severity,
  and generator/evaluator-only implicated paths/tests.
- [ ] Run `pyrun -m pytest tests/research/test_suite_a_catalog.py -q`; expect
  import or fixture failure.
- [ ] Implement catalog validation and pure oracle functions over typed traces.
- [ ] Run the test file; expect every fixture case to pass.
- [ ] Run the full adapter tests plus
  `pyrun -m pytest tests/research/test_suite_a_catalog.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add exact suite a motif catalog`.

**Acceptance:** every primary motif has exact observable rules and adverse
agent-side non-engagement/branch-local-failure labels plus a separate narrowly
evidenced exogenous block-outage evidence rule; semantic or prose-dependent motifs are rejected from the
confirmatory catalog.

### V2-10 — Implement the actor-side prospective risk recognizer

**Legacy mapping:** replaces WS-A-4's invalid retrospective use.

**Files:**

- Create: `src/pneuma_lab/recognition/__init__.py`
- Create: `src/pneuma_lab/recognition/prospective.py`
- Create: `src/pneuma_lab/recognition/calibration.py`
- Test: `tests/research/test_prospective_recognizer.py`

**Contract:**

```python
class ProspectiveRecognizer(Protocol):
    def forecast(
        self,
        current: ObservableView,
        within_opportunity_history: Sequence[ObservableView],
    ) -> RiskForecast: ...

class FrozenRuleRecognizer(ProspectiveRecognizer): ...
```

The recognizer runs before action selection and returns current-opportunity
applicability by motif, forecast confidence, parameter digest, and receipt
references. It sees only the current task's actor-safe typed view and structured
events already observed within that same opportunity. It cannot receive a
prior-task trace, exposure receipt, persistent store/state, generator motif ids,
oracle implicated sets, future tests, offline labels, condition ids, or report
prose. Dev-fitted calibration is loaded from a
hash-pinned immutable artifact and never updated on pilot/confirmatory labels.
The shared closed `MotifKey` vocabulary is actor-visible, but the generator's
current-task motif assignment and instance id are not. This module emits only
the common current-only `RiskForecast`; V2-27 combines that forecast with each
arm's legitimate `DeclaredCarrierView` to emit the same-schema, behaviorally
inert `NoticeReadout`. Base's empty carrier is the memoryless readout. No
condition may fork or replace this recognizer.

- [ ] Add tests that forecast a known opportunity, remain zero on a decoy,
  reject future/oracle/evaluator fields, preserve deterministic order, and fail
  on calibration-artifact hash drift. Verify the forecast is invariant to every
  persistent carrier and has the exact motif/timing support later consumed by
  all seven notice readouts. Plant a prior-task
  trace/exposure receipt in every possible recognizer argument and prove it is
  rejected, while legitimate within-opportunity history remains accepted.
- [ ] Run `pyrun -m pytest tests/research/test_prospective_recognizer.py -q`;
  expect import failure.
- [ ] Implement the protocol, rule recognizer, calibrator loader, and receipts.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run the import firewall and
  `pyrun -m pytest tests/research/test_protocol_v2_firewall.py tests/research/test_prospective_recognizer.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add prospective risk recognizer`.

**Acceptance:** recognition occurs before the preventable behavior; its artifact
and thresholds are independently bindable and cannot access prior-task memory or
outcome labels. Persistent recurrence information reaches each arm's diagnostic
notice readout or action policy only through that arm's declared carrier.

### V2-11 — Implement the actor-side online learning signal

**Legacy mapping:** the treatment-update role formerly mixed into WS-A-4 and
WS-E-1.

**Files:**

- Create: `src/pneuma_lab/recognition/online_signal.py`
- Test: `tests/research/test_online_learning_signal.py`

**Contract:**

```python
class OnlineSignalExtractor(Protocol):
    def observe(
        self,
        action: ActionCandidate,
        result: ActorToolResult,
        forecast: RiskForecast,
        history: Sequence[ActorStep],
    ) -> tuple[LearningSignal, ...]: ...
```

Signals are post-action, bounded, deterministic, and receipt-bound. Inputs are
the pre-action forecast, immediate typed tool/test status, and actor-side
structured history from the current task/opportunity only. It cannot read a
prior-task trace, exposure receipt, persistent store, or state; cross-task
learning persists only through the declared condition carrier. The extractor
does not import or accept `ExactBehaviorLabel`, `OpportunityOutcome`, evaluator
judgments, task-generator ids, or self-report. Multiple motif hypotheses may be
updated with explicit strength rather than a hidden hard label.

- [ ] Add tests for failed/passed verification, timeout, destructive edit,
  unsupported finish, bounded strengths, duplicate receipt rejection, and
  absence of evaluator imports. Plant prior-task trace/store/state bytes and
  prove they are rejected while current-opportunity history is accepted.
- [ ] Run `pyrun -m pytest tests/research/test_online_learning_signal.py -q`;
  expect import failure.
- [ ] Implement the extractor and canonical signal receipts.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/research/test_protocol_v2_firewall.py tests/research/test_prospective_recognizer.py tests/research/test_online_learning_signal.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add online learning signal`.

**Acceptance:** treatment updates are grounded in immediate actor observations
without sharing the offline evaluator or its learned/frozen parameters.

### V2-12 — Implement the arm-blind exact offline evaluator

**Legacy mapping:** WS-B-2, WS-G-1, and WS-G-4.

**Files:**

- Create: `src/pneuma_lab/evals/opportunity_evaluator.py`
- Create: `src/pneuma_lab/evals/evaluator_blinding.py`
- Test: `tests/research/test_opportunity_evaluator.py`

**Contract:**

```python
def blind_trace(trace: ImmutableTrace, blind_key: bytes) -> BlindedTrace: ...
def evaluate_opportunities(
    trace: BlindedTrace,
    schedule: OpportunitySchedule,
    oracle: TaskOracle,
) -> tuple[OpportunityOutcome, ...]: ...
```

The evaluator receives a pseudonymous arm id and immutable typed trace. It
mechanically labels each scheduled opportunity as target-family harm, success,
different-family harm, adverse agent-side non-engagement/branch-local runtime
failure. Every
observed refusal, timeout, premature finish, budget exhaustion, invalid action,
model error, or crash confined to one branch is adverse without requiring proof
that treatment caused it. The evaluator may preserve separately supplied
immutable `ExogenousOutageEvidence`, but cannot apply it or emit a per-arm outage
label. Only V2-32 sees the complete pseudonymous seven-arm bundle and can mask
all seven rows atomically after verifying that one predeclared external cause
made the whole block unobservable; arm-local symptoms, missing telemetry, or
uncertain cause remain adverse. The evaluator recomputes labels from trace/oracle data and refuses condition/state/
recognizer/report fields. A separate unblinding table is encrypted or retained
outside evaluator inputs until all labels are frozen.

- [ ] Add tests for all outcome classes, severity weights, arm-name
  stripping, trace-hash mismatch, schedule omission, planted condition leakage,
  and identical labels after arm permutation. Add refusal/timeout/branch-crash
  cases that remain adverse regardless of causal attribution, a valid common
  exogenous block-outage evidence, and uncertain/one-arm outage claims that are
  preserved as non-authoritative evidence and scored adverse. Prove there is no
  per-arm exclusion method or outcome label.
- [ ] Run `pyrun -m pytest tests/research/test_opportunity_evaluator.py -q`;
  expect import failure.
- [ ] Implement the blind/recompute path using only benchmark contracts and
  immutable typed traces.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/research/test_protocol_v2_firewall.py tests/research/test_suite_a_catalog.py tests/research/test_opportunity_evaluator.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add blind exact evaluator`.

**Acceptance:** evaluator labels are exact, arm-blind, recomputed from immutable
inputs, and structurally independent of both actor-side label paths.

### V2-13 — Validate recognizer and online signal without promoting labels

**Legacy mapping:** WS-A-3, broadened to both actor-side paths.

**Files:**

- Create: `src/pneuma_lab/evals/actor_signal_validation.py`
- Create: `scripts/research/validate_actor_signals.py`
- Test: `tests/research/test_actor_signal_validation.py`
- Generate: `build/research/validation/actor-signal-report.json`

**Contract:**

```python
def validate_actor_signals(
    forecasts: Sequence[RiskForecast],
    notice_readouts: Sequence[NoticeReadout],
    signals: Sequence[LearningSignal],
    notice_targets: Sequence[PretreatmentRecurrenceTarget],
    outcome_labels: Sequence[ExactBehaviorLabel],
    *,
    split: Literal["dev", "pilot", "test"],
) -> ActorSignalValidationReport: ...
```

Report per-arm/per-motif discrimination, precision/recall, Brier score,
calibration slope/intercept, coverage, and confusion matrices from the common
pre-action `NoticeReadout`. Only `dev` may emit fitted
calibration artifact. `test` is read-only official evaluation. `pilot` emits only
a pooled/blinded detector-error nuisance projection with no arm/effect,
per-motif threshold-validation, selection, or tuning fields, and that projection
is consumed only through V2-35's nuisance interface. Include retry-count,
trace length, actions, and tokens as diagnostic baselines to preserve the E-0
negative result. The validation target for notice is the generator-held
pretreatment fact that the current opportunity recurs the subject's verified
exposure motif; it is frozen before action and balanced with decoys and
counterfactuals at the authored-lineage level. No action or outcome can relabel
it. A poor scientific score is serialized honestly and does not
make this function fail.

- [ ] Add exact arithmetic tests, degenerate-class handling, split guard,
  retry-count superiority case, action/outcome-invariant pretreatment notice
  labels, exact seven-arm notice-schema parity, prototype-lineage aggregation,
  pilot nuisance-field allowlist and
  arm/effect/per-motif redaction, and canonical report hashing.
- [ ] Run `pyrun -m pytest tests/research/test_actor_signal_validation.py -q`;
  expect import failure.
- [ ] Implement metrics and the guarded dev-only calibration writer.
- [ ] Run the test file; expect all tests to pass.
- [ ] After authorization, run only on a bounded dev/offline subset and bind the
  report to source, extractor, labels, and split digests.
- [ ] Commit only the exact `Files` paths with subject
  `feat: validate actor-side signals`.

**Acceptance:** the report exposes confounds and negative results; no test-set
threshold or calibration update can be written.

### V2-14 — Prove label-path separation end to end

**Legacy mapping:** completes WS-G-4's structural separation requirement.

**Files:**

- Create: `src/pneuma_lab/experiment/label_path_audit.py`
- Test: `tests/research/test_label_path_separation.py`

**Contract:**

```python
def audit_label_paths(
    repo_root: pathlib.Path,
    actor_receipts: Sequence[dict],
    evaluator_receipts: Sequence[dict],
) -> LabelPathAuditReceipt: ...
```

The audit combines AST import boundaries, schema field disjointness, parameter
artifact hashes, input provenance, and a perturbation test: permuting evaluator
labels must not alter any actor forecast/signal/action, while perturbing an
actor signal may alter treatment but cannot alter frozen evaluator logic. It
also proves that the pretreatment recurrence target is generator-held and
action/outcome invariant, the recognizer is current-only, and `L_m` actuation
bytes cannot enter or masquerade as `NoticeProbability`.

- [ ] Add a clean fixture and planted violations for shared artifact hash,
  evaluator label in actor provenance, actor import of evaluator, and
  label-permutation sensitivity. Plant prior-task recognizer input,
  outcome-dependent notice relabeling, and actuation-as-probability violations.
- [ ] Run `pyrun -m pytest tests/research/test_label_path_separation.py -q`;
  expect import failure.
- [ ] Implement the audit with sorted actionable diagnostics and a canonical
  receipt.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run all `tests/research/test_*recogn*`, `test_*signal*`,
  `test_*evaluator*`, and firewall tests; declare G2 only when all pass.
- [ ] Commit only the exact `Files` paths with subject
  `test: prove label path separation`.

**Acceptance:** treatment and primary labels cannot share code, fields,
parameters, or test-set tuning; the audit receipt is hash-bound and reproducible.

---

## Phase B — Fixed opportunities, split regimes, and external-validity lanes

### V2-15 — Generate Suite-A sequences with common exposure and fixed opportunities

**Legacy mapping:** WS-B-3 and the sequence role of WS-B-1.

**Files:**

- Create: `src/pneuma_lab/benchmark/exposure.py`
- Create: `src/pneuma_lab/benchmark/sequence.py`
- Create: `src/pneuma_lab/benchmark/suite_a.py`
- Test: `tests/research/test_suite_a_sequences.py`

**Contract:**

```python
def build_exposure_receipt(
    failed_trace: ImmutableTrace,
    exact_label: ExactBehaviorLabel,
    provenance: ExposureProvenance,
) -> ExposureReceipt: ...

def generate_sequence(
    spec: SequenceSpec,
    seed: int,
    mode: Literal["standardized_exposure", "natural_end_to_end"],
) -> SuiteASequence: ...
```

Every confirmatory exposure is a live failure produced by the **same frozen
checkpoint and shared scaffold that will act in the post-exposure tasks**, under
one common untreated prefix at a preregistered seed, mechanically verified
before arm mapping, then cloned into all seven conditions. `ExposureProvenance`
binds checkpoint, prompt, tools, seed, sandbox, full prefix trace, shared
scaffold, subject identity, exact verification, and `PrototypeLineageId`.
Scripted traces, foreign-model failures, or a trace generated after arm mapping
may create an explicitly `fixture_only` engineering receipt but can never create
a confirmatory-eligible receipt. The public exposure receipt contains only
legitimate actor-observed history and digests, never the oracle motif id or
evaluator judgment. Each sequence fixes
all post-exposure opportunity tasks, preassigned severity weights, decoys,
counterfactuals, challenge order, highest independently authored prototype/
generator lineage digest,
and exogenous seeds before randomization. Every scheduled opportunity begins
from its own immutable digest-bound sandbox snapshot; filesystem mutations from
one opportunity never flow into the next, while only the arm's declared
memory/state carrier persists. Every arm receives the same denominator even when it succeeds,
fails differently, refuses, times out, or exhausts budget.
Before any arm assignment, a common preflight must verify that every registered
generator/prototype artifact, exposure, opportunity snapshot, mechanical oracle,
and frozen cell/lineage/motif roster exists and matches its digest. Missing or
mismatched common artifacts invalidate the sequence; they are never repaired,
excluded, or reweighted after assignment.
Every scheduled opportunity has primary weight one. The frozen severity field is
retained only for V2-32's secondary severity-weighted analysis.
V2-15 implements the pure provenance validator and seed-pure task generator;
V2-23/V2-38 invoke the later live driver to produce the same-subject trace before
calling this validator, avoiding a dependency cycle.
The secondary `natural_end_to_end` mode assigns conditions before the sequence
starts and retains every scheduled task; it reports first harmful-failure
incidence and recurrence without conditioning on an arm-specific observed first
failure.

- [ ] Add tests for byte-identical receipts across arms, absent oracle ids,
  deterministic generation, fixed opportunity counts, nonzero weights,
  prototype-lineage digest binding, independent per-opportunity snapshots,
  primary unit weights plus independently frozen secondary severity weights, and
  a condition that never repeats yet retains every denominator item. Add a natural
  sequence where one arm never has a first failure but keeps all scheduled tasks.
  Prove every automatically generated challenge/seed descendant inherits the
  authored prototype lineage and cannot mint a new lineage digest.
  Reject a scripted/foreign-model exposure, checkpoint/scaffold/seed mismatch,
  exposure generated after assignment, unverified failure, and filesystem
  carryover between opportunities from confirmatory eligibility. Reject a
  missing/mismatched generator, common-preflight artifact, opportunity snapshot,
  oracle, or frozen hierarchy roster before assignment can run.
- [ ] Run `pyrun -m pytest tests/research/test_suite_a_sequences.py -q`; expect
  import failure.
- [ ] Implement exposure verification and the seed-pure sequence generator.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/research/test_suite_a_catalog.py tests/research/test_suite_a_sequences.py tests/research/test_opportunity_evaluator.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: generate fixed opportunity sequences`.

**Acceptance:** treatment cannot change exposure eligibility or the primary
denominator; confirmatory recurrence follows the same subject's own live verified
failure from a common untreated prefix, and task snapshots prevent filesystem
carryover from impersonating persistent internal state.

### V2-16 — Add surface transforms, decoys, counterfactuals, and metamorphic tests

**Legacy mapping:** WS-G-3 and the transform role of WS-B-1.

**Files:**

- Create: `src/pneuma_lab/benchmark/transforms.py`
- Create: `src/pneuma_lab/benchmark/metamorphic.py`
- Create: `src/pneuma_lab/benchmark/anti_gaming.py`
- Test: `tests/research/test_suite_a_metamorphic.py`

**Contract:**

```python
def transform_surface(task: SuiteATask, transform: SurfaceTransform) -> SuiteATask: ...
def validate_metamorphic_pair(
    original: SuiteATask,
    transformed: SuiteATask,
    oracle: TaskOracle,
) -> MetamorphicReceipt: ...
```

Transforms alter names, paths, formatting, distractor order, and equivalent test
surface while preserving the exact opportunity/outcome rule. Decoys share
surface cues without target harm. Counterfactuals make caution inappropriate and
mechanically score false avoidance. Every transform emits a before/after oracle
digest and must preserve target label, task solvability, and the original
authored `PrototypeLineageId`; a surface transformation cannot mint independent
evidence.

- [ ] Add at least two transforms per confirmatory motif and tests for label
  preservation, changed surface digest, decoy non-firing, false-avoidance label,
  inherited lineage identity, rejection of a transformed task that changes its
  lineage, and a planted transform that invalidates the oracle.
- [ ] Run `pyrun -m pytest tests/research/test_suite_a_metamorphic.py -q`; expect
  import failure.
- [ ] Implement deterministic transforms and metamorphic validation receipts.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run all Suite-A catalog/sequence/metamorphic tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add suite a anti-gaming transforms`.

**Acceptance:** surface memorization and blanket caution have explicit test
cases; no transform enters a split without a passing metamorphic receipt.

### V2-17 — Build separate split regimes and leakage quarantine

**Legacy mapping:** WS-B-4 and WS-B-6.

**Files:**

- Create: `src/pneuma_lab/benchmark/splits.py`
- Create: `src/pneuma_lab/benchmark/quarantine.py`
- Modify: `src/pneuma_lab/training/leakage_registry.py`
- Test: `tests/research/test_empirical_splits.py`

**Contract:**

```python
def build_split_regimes(
    tasks: Sequence[TaskFingerprint],
    split_seed: int,
) -> SplitRegimeBundle: ...

def quarantine_overlaps(
    bundle: SplitRegimeBundle,
    registry: LeakageRegistry,
) -> QuarantineReceipt: ...
```

Produce independent `surface_holdout`, `repository_holdout`, and exploratory
`motif_family_holdout` assignments. Repository components remain atomic within
the repository analysis and surface families remain atomic within the surface
analysis. Do not require a globally repo-and-motif-atomic partition when the
bipartite graph makes it impossible. The highest independently authored
prototype/generator lineage is atomic across dev, pilot, and confirmatory sets;
variants, transforms, challenges, nominal sequences, and seeds descended from
one lineage are nested replicates. Dev, pilot, and confirmatory lineage/task ids
are disjoint and immutable. The registry checks repo URL/commit, normalized
issue digest, test digest, frozen prototype-lineage digest, transform ancestry,
and template/generator ancestry.

- [ ] Add graph fixtures where a global atomic split is impossible; assert each
  named regime remains valid, exact duplicates quarantine, ancestry leakage
  quarantines, deterministic seed output, lineage-atomic dev/pilot/confirmatory
  assignment, rejection of a descendant that claims a newly minted lineage, and
  pilot exclusion from confirmatory.
- [ ] Run `pyrun -m pytest tests/research/test_empirical_splits.py -q`; expect
  import failure.
- [ ] Implement regime-specific component splitting and extend the registry with
  typed empirical fingerprints.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_cross_dataset_leakage.py tests/test_training_splits.py tests/research/test_empirical_splits.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add empirical split regimes`.

**Acceptance:** each generalization claim names its valid split axis; no pilot,
dev surface, duplicate, or ancestral template reaches its corresponding test set.

### V2-18 — Build the governed Suite-B-offline external-validity pipeline

**Legacy mapping:** WS-B-5, with causal claims removed from the offline lane.

**Files:**

- Create: `src/pneuma_lab/benchmark/suite_b_offline.py`
- Create: `src/pneuma_lab/evals/semantic_label_gate.py`
- Modify: `src/pneuma_lab/adapters/open_swe_traces.py`
- Modify: `src/pneuma_lab/adapters/openhands_sampled.py`
- Test: `tests/research/test_suite_b_offline.py`

**Contract:**

```python
def scan_offline_lane(
    source: AuthorizedSourceRef,
    guard: DataAccessCapability,
    recognizer: ProspectiveRecognizer,
    evaluator: OfflineObservabilityEvaluator,
) -> OfflineValidityReport: ...

def gate_semantic_labels(judgments: Sequence[BlindedJudgment]) -> LabelGateReport: ...
```

`AuthorizedSourceRef` is metadata-only; the function opens bytes exclusively
through `guard.open_source` after scope validation. Re-extract raw governed records transiently because digest-only processed JSONL
cannot supply enrichment. Emit prevalence, observable-field coverage,
recognizer forecasts, exact-rule agreement, sampled-report agreement, and
blinded semantic-judge agreement. Semantic labels are secondary, require
predeclared agreement/swap checks, and never define the primary endpoint.
Outputs carry `training_weight: 0.0`, `not_authorized`, source digest, row range,
and adapter digest; nothing writes under `C:\pneuma-data`.

- [ ] Add tiny raw fixtures for both adapters; test auth-before-open ordering,
  no raw text in output, processed-digest refusal for enrichment, report metrics,
  judge-label secondary status, and byte-identical reruns.
- [ ] Run `pyrun -m pytest tests/research/test_suite_b_offline.py -q`; expect
  import failure.
- [ ] Implement streaming scan and the separate label gate without changing
  existing adapter defaults.
- [ ] Run the test file; expect all tests to pass.
- [ ] After a signed pilot authorization, run a bounded shard plan and store only
  derived reports under `build/research/suite-b-offline/`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add offline validity lane`.

**Acceptance:** the lane supports observability/external-validity claims only;
raw records remain governed and no offline trajectory is presented as a live
treatment comparison.

### V2-19 — Plan and acquire digest-bound Suite-B-live sandboxes

**Legacy mapping:** the executable real-repository role missing from WS-B.

**Files:**

- Create: `src/pneuma_lab/benchmark/suite_b_live.py`
- Create: `src/pneuma_lab/benchmark/suite_b_live_sequences.py`
- Create: `src/pneuma_lab/benchmark/sandbox_sources.py`
- Create: `schemas/sandbox-source-manifest.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Test: `tests/research/test_suite_b_live.py`

**Contract:**

```python
def load_swe_gym_records(
    source_path: pathlib.Path,
    guard: DataAccessCapability,
) -> tuple[SWEGymRecord, ...]: ...

def plan_swe_gym_subset(
    records: Sequence[SWEGymRecord],
    eligibility: MechanicalEligibility,
) -> SuiteBLivePlan: ...

def acquire_sandbox_source(
    entry: SuiteBLiveEntry,
    destination: pathlib.Path,
    guard: DataAccessCapability,
) -> SandboxSourceManifest: ...

def construct_live_protocol(
    entry: SuiteBLiveEntry,
    source: SandboxSourceManifest,
    templates: Sequence[KnownMotifTemplate],
    subject_runner: ExposureRunner,
    seed: int,
) -> SuiteBLiveSequence: ...

def build_live_sequence(
    entry: SuiteBLiveEntry,
    source: SandboxSourceManifest,
    exposure: ExposureReceipt,
    opportunities: OpportunitySchedule,
) -> SuiteBLiveSequence: ...
```

Plan a 24–36-sequence ceiling across three or four mechanically scorable known
motifs. This lane's target population is explicitly the mechanically scorable
known-motif subset with an executable standardized-opportunity protocol, not
natural SWE tasks or prevalence in repositories generally. The plan binds
repository URL, base commit, problem/test-oracle digests,
license metadata, source image/repository provenance, and expected disk/runtime.
`source_path` is only a reference: `load_swe_gym_records` must make
`guard.open_source(source_path, ...)` its first I/O operation, and acquisition
must invoke the injected network/cache fetcher only through the guard's scoped
source-materialization method. Direct `Path.open`, network, Git, container, or
cache access is forbidden on this path.
`--plan-only` performs no network or checkout action. Acquisition verifies the
commit and full snapshot digest into an isolated cache outside raw data, then
creates per-run clones through V2-06. Missing repositories/images are surfaced
as feasibility failures, not silently replaced.
For every retained entry, `build_live_sequence` binds a verified common
same-subject live pre-treatment failure exposure from the common untreated
prefix to fixed mechanically scorable post-exposure
opportunities in that executable repository. The exact test/tool-event oracle
must map to a known confirmatory `MotifKey`, include success, target recurrence,
different-family failure, adverse agent-side non-engagement/branch-local crash,
and separately bound exogenous block-outage evidence, and run
through the same V2-12 evaluator/V2-32 denominator. Entries that cannot support
this sequence contract remain offline/descriptive and cannot enter H4 or a live
treatment estimate.
`construct_live_protocol` is the required production path: on an independent
source clone it first verifies the repository's baseline tests, applies only a
predeclared known-motif template whose mechanical preconditions match, executes
the shared frozen subject/scaffold to produce and verify the standardized
harmful exposure before arm mapping, then pre-generates an independent sandbox
snapshot for every post-exposure challenge, severity, decoy, counterfactual, and
oracle rule before condition randomization. `build_live_sequence` is the pure
validator/binder for those generated artifacts, not a loophole for supplying an
unverified exposure or arm-dependent schedule.
V2-19 defines the narrow injected `ExposureRunner` protocol and tests it with an
instrumented fake; V2-22/V2-23 supply the real shared-driver adapter before any
pilot or confirmatory Suite-B-live cell.

- [ ] Add local fake-repository tests for eligibility, plan-only no-I/O,
  authorization-before-network, wrong commit, dirty snapshot, digest drift,
  license-field presence, guarded metadata loading, independent clones,
  common-exposure binding, fixed
  opportunities, baseline-test verification, deterministic protocol generation,
  same-subject/scaffold provenance, independent opportunity snapshots,
  prototype-lineage digest, template-precondition failure, exact outcome
  roundtrip, and rejection of a
  metadata-only task with no executable sequence.
- [ ] Run `pyrun -m pytest tests/research/test_suite_b_live.py -q`; expect import
  failure.
- [ ] Implement plan/acquisition with an injected fetcher plus live sequence/
  oracle binding so unit tests are offline and deterministic; register/document
  the source manifest under `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/research/test_suite_b_live.py -q`.
- [ ] With a signed V2-04 data-access capability, produce a plan-only manifest
  from local SWE-Gym metadata; do not acquire sources until the same capability
  covers the destination and URLs.
- [ ] Commit only the exact `Files` paths with subject
  `feat: build live real-repo suite`.

**Acceptance:** every live task has a real executable source/test oracle, common
exposure, fixed opportunity schedule, and exact evaluator path or is excluded
with a recorded reason; the estimand is restricted to the executable known-motif
subset, and no local trajectory-only dataset is treated as an executable
benchmark.

---

## Phase C — Immutable traces and a single live structured-action driver

### V2-20 — Bind manifests, traces, labels, sandboxes, prompts, and checkpoints

**Legacy mapping:** WS-C-3, WS-B-6, and WS-E-7.

**Files:**

- Create: `src/pneuma_lab/experiment/binding.py`
- Create: `schemas/empirical-trace-manifest.schema.json`
- Modify: `schemas/causal-trace.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Test: `tests/research/test_empirical_binding.py`

**Contract:**

```python
def bind_run(inputs: RunBindingInputs) -> RunBinding: ...
def verify_bound_trace(
    trace_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> BindingVerification: ...
```

Bind commit, worktree-diff state, Python/dependency lock, condition-protocol
version, checkpoint and quantization, backend/server, decoding config, candidate
prompt/repair/fallback templates, ex-ante caps, task/sequence/split, exposure,
sandbox, oracle/label bundle, recognizer, state/head constants, intervention
schedule, condition pseudonym, recorded seven-label assignment, authored
prototype/generator lineage id/digest, and seed schedule. Hash JSONL incrementally and
record every state/forecast/signal/action/outcome receipt reference.
For Suite B-live, additionally bind the `SandboxSourceManifest`, executable
`SuiteBLiveSequence`, mechanically verified common exposure, complete fixed
opportunity schedule, exact known-motif oracle, and highest shared repository/
generator/prototype lineage cluster id. A metadata-only or offline label bundle cannot satisfy
this live binding.

- [ ] Add roundtrip tests and one-byte drift tests for each binding family;
  assert absolute usernames/paths and secret-shaped strings are rejected. Add a
  full Suite-B-live roundtrip and reject missing exposure, schedule, executable
  oracle, source digest, same-subject exposure provenance, independent snapshots,
  lineage digest, recorded assignment, or repository+generator/prototype cluster
  binding. Reject any assignment whose generator/common-preflight/hierarchy
  roster binding was absent or invalid before assignment.
- [ ] Run `pyrun -m pytest tests/research/test_empirical_binding.py -q`; expect
  import or schema failure.
- [ ] Implement canonical manifest generation, streaming trace hashing, and
  fail-closed verification; register/document the empirical trace manifest in
  `EMPIRICAL_SCHEMA_FILES` (the pre-existing causal-trace schema remains in its
  existing category).
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/test_validate.py tests/research/test_empirical_binding.py -q` plus existing provenance tests.
- [ ] Commit only the exact `Files` paths with subject
  `feat: bind empirical traces`.

**Acceptance:** every result can resolve to immutable input and implementation
digests; anonymized manifests contain neither secrets nor identifying local paths.

### V2-21 — Define the one-call structured candidate protocol

**Legacy mapping:** candidate-generation portion of WS-C-2 and WS-E-6.

**Files:**

- Create: `src/pneuma_lab/agent/actions.py`
- Create: `src/pneuma_lab/agent/candidate_prompt.py`
- Create: `src/pneuma_lab/agent/repair.py`
- Test: `tests/research/test_candidate_protocol.py`

**Contract:**

```python
def request_candidates(
    backend: CandidateBackend,
    guard: ExecutionGuard,
    actor_context: ActorContext,
    *,
    count: int,
    seed: int,
) -> CandidateBatch: ...

def repair_candidate_batch(raw: bytes, policy: RepairPolicy) -> CandidateBatch: ...
```

One identical backend call requests a fixed-size ranked candidate set with
normalized positive model scores, fixed meta-action classes, and complete
model-proposed tool arguments. State values, pressure, condition names, and
intervention metadata never enter this prompt. The shared repair/fallback path
is deterministic, bounded, metered, and identical in all arms. A reranker may
choose only among returned candidates.

- [ ] Add tests for exactly one backend call, exact candidate count, malformed
  JSON repair, duplicate/invalid candidates, normalized scores, fallback
  accounting, forbidden state serialization, and unchanged tool arguments after
  parsing.
- [ ] Run `pyrun -m pytest tests/research/test_candidate_protocol.py -q`; expect
  import failure.
- [ ] Implement prompt, parser, validation, repair, and fallback receipts.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run backend, firewall, and candidate-protocol tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add structured candidate protocol`.

**Acceptance:** every arm starts from the same model-proposed choice set; no
state module can invent a call, alter arguments, or influence generation through
hidden prompt text.

### V2-22 — Implement the metered live tool loop with policy hooks

**Legacy mapping:** remaining WS-C-2 live-driver work.

**Files:**

- Create: `src/pneuma_lab/agent/metering.py`
- Create: `src/pneuma_lab/agent/driver.py`
- Test: `tests/research/test_live_agent_driver.py`

**Contract:**

```python
class ControlPolicy(Protocol):
    def memory_context(self, context: ActorContext) -> MemoryContext: ...
    def notice_carrier_view(self, context: ActorContext) -> DeclaredCarrierView: ...
    def before_selection(
        self,
        context: ActorContext,
        forecast: RiskForecast,
    ) -> PressureVector: ...
    def after_result(
        self,
        event: ActorEvent,
        forecast: RiskForecast,
    ) -> tuple[LearningSignal, ...]: ...

class LiveAgentDriver:
    def run(
        self,
        task: BoundTask,
        policy: ControlPolicy,
        guard: ExecutionGuard,
    ) -> ImmutableTrace: ...
```

The loop first builds a current-task/within-opportunity `ObservableView` with no
policy memory, prior-task trace, exposure receipt, store, or state and gets the
shared current-only prospective forecast. It then obtains the policy's
allowlisted `DeclaredCarrierView`, invokes V2-27's same-actor notice measurement
through an independent seed/RNG namespace and separate equal-cap meter, emits
the same-schema `NoticeReadout` to a diagnostic-only trace sink, and irreversibly
drops that return object before the behavior path. Only then does it obtain the
policy's declared memory context for the actor call, obtain one candidate batch,
ask the policy for bounded pressure, select one unchanged candidate,
executes it through V2-06, records the typed event, and sends the forecast plus
immediate actor-visible result to the post-action hook. State/readout values do
not enter candidate generation. The main `ResourceUsage` meter covers every
candidate, invalid-JSON repair, fallback, reflection-writing, and any retrieval/
state-maintenance model call; every input/output token; attempted tool action;
retry; failed call; and deterministic prompt truncation/context-slot allocation.
The same ex-ante caps and counting rules apply to every arm. Refusal,
timeout, invalid output, premature finish, and budget exhaustion terminate with
explicit outcome codes rather than missing data. Realized use is recorded as an
outcome and never padded.
Notice-measurement calls have a second, identical per-arm cap/meter and appear in
the resource report, but are excluded from main action caps and cannot change
candidate/action seeds, call ordinals, retry state, or tool state.
The driver cannot invoke backend transport or open a nonfixture sandbox source
without the concrete guard; every backend/source call passes through that guard
and decrements its bound episode/call counters.

- [ ] Add fake-backend/sandbox tests for success, repeated action, invalid JSON,
  refusal, timeout, finish-before-verification, every cap, post-result updates,
  unchanged candidate arguments, complete resource accounting (including
  reflection/repair/fallback/failed calls and input/output tokens), immutable
  trace finalization, missing/wrong
  guard refusal, and operation-spy proof that refusal occurs before source/model
  access. Plant prior-task retrieval/reflection/state bytes and prove none enters
  the recognizer view while the declared text-memory context still reaches the
  actor call in the appropriate arms. Add a notice-sink noninterference test:
  replace/perturb every probability and serialized byte while holding carrier
  inputs fixed and require candidate requests, pressure, selected actions, tool
  events, updates, and behavioral outcome projection to remain identical. Assert
  identical notice checkpoint/prompt/scaffold/schema/decoding/call timing/count/
  max-token config in all arms, equal measurement allocations, separate usage
  receipts, and unchanged main action caps/RNG ordinals.
- [ ] Run `pyrun -m pytest tests/research/test_live_agent_driver.py -q`; expect
  import failure.
- [ ] Implement metering and driver state machine over the protocol seam.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run all `tests/research/test_agent_*`, candidate, binding, and live-driver
  tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add metered live agent loop`.

**Acceptance:** the driver is condition-agnostic; all seven arms will use this
exact loop, backend, candidates, tools, caps, retry path, and trace format.

### V2-23 — Clone a common prefix and run causal descendants live

**Legacy mapping:** corrects WS-F-2 and completes WS-C-3.

**Files:**

- Create: `src/pneuma_lab/experiment/branching.py`
- Test: `tests/research/test_live_branching.py`

**Contract:**

```python
def branch_at_t0(
    prefix: BoundPrefix,
    branches: Sequence[BranchSpec],
    sandbox_factory: SandboxFactory,
) -> tuple[LiveBranch, ...]: ...

def verify_branch_semantics(branches: Sequence[CompletedBranch]) -> BranchAudit: ...
```

Freeze task/config, checkpoint, templates, sampler settings, exogenous seed
schedule, initial sandbox snapshot, exposure/state checkpoint, and the common
pre-intervention trace through `t0`. Clone those bytes, randomize the scheduled
intervention, and let each branch generate prompts, tool results, files, state,
actions, and length live after `t0`. The audit rejects divergence before `t0`
and rejects any post-`t0` replay of a sibling branch's realized transcript. At a
task boundary it restores the next opportunity's prebound independent snapshot;
only the declared condition memory/state is carried across tasks.

- [ ] Add tests for byte-equal prefixes, independent sandbox writes, allowed
  first-post-treatment divergence, pre-`t0` divergence rejection, planted
  descendant-transcript freeze, different branch lengths, independent task
  snapshot restoration, and rejection of undeclared filesystem carryover.
- [ ] Run `pyrun -m pytest tests/research/test_live_branching.py -q`; expect import
  failure.
- [ ] Implement clone manifests and semantic audit without arbitrary later-tick
  alignment.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run sandbox, binding, driver, and branching tests; declare G3 only after
  V2-15–V2-23 all pass.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add live causal branching`.

**Acceptance:** branches share only legitimate pre-treatment/exogenous inputs;
post-treatment descendants can diverge naturally and remain causally coherent.

---

## Phase D/E — Persistent state, pressure head, and seven matched conditions

### V2-24 — Add deterministic semistructured retrieval memory

**Legacy mapping:** WS-D-2 and the useful retrieval portion of WS-E-4.

**Files:**

- Create: `src/pneuma_lab/conditions/__init__.py`
- Create: `src/pneuma_lab/conditions/retrieval_store.py`
- Modify: `src/pneuma_lab/foundation/memory.py`
- Test: `tests/research/test_retrieval_store.py`

**Contract:**

```python
class DeterministicFailureStore:
    def append(self, record: FailureRecord) -> str: ...
    def retrieve(self, query: RetrievalQuery, k: int) -> tuple[FailureRecord, ...]: ...
```

Records are semistructured textual failure memories with explicit ids,
observation-time ordinals, source receipts, digests, and bounded length. The
research path injects its clock/id source; it never uses UUID4 or wall-clock for
ranking or identity. Retrieval ranks a frozen actor-safe feature score and breaks
ties by canonical record id. Query, top-k, serializer, truncation, and returned
record digests are bound in the trace. Existing `LocalMemoryStore` behavior stays
backward compatible; only deterministic query/id seams are added there.

- [ ] Add tests for stable ids, tie order, duplicate receipt rejection, top-k,
  truncation at the fixed budget, persistence roundtrip, query-hash drift, and
  absence of evaluator/oracle fields.
- [ ] Run `pyrun -m pytest tests/research/test_retrieval_store.py -q`; expect
  import failure.
- [ ] Implement the research store and dependency-injected deterministic seams
  in the foundation store.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_foundation_memory.py tests/research/test_retrieval_store.py tests/research/test_protocol_v2_firewall.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add deterministic retrieval memory`.

**Acceptance:** repeated retrieval from identical history is byte-identical;
memory contains no hidden evaluator label and cannot depend on wall time.

### V2-25 — Implement receipt-bound `s_m`, `r_m`, and persistent state storage

**Legacy mapping:** WS-E-1, corrected WS-E-4, WS-E-5, and part of WS-E-7.

**Files:**

- Create: `src/pneuma_lab/state/__init__.py`
- Create: `src/pneuma_lab/state/store.py`
- Create: `src/pneuma_lab/state/sensitivity.py`
- Create: `src/pneuma_lab/state/recognizer_reliability.py`
- Test: `tests/research/test_persistent_state_core.py`

**Contract:**

```python
class PersistentStateStore:
    def load(self, sequence_id: str) -> PneumaState: ...
    def apply(self, update: StateUpdate) -> StateReceipt: ...
    def reset_challenge(self) -> StateReceipt: ...
    def reset_sequence(self) -> StateReceipt: ...

def update_sensitivity(value: float, signal: LearningSignal, task_delta: int) -> float: ...
def update_recognizer_reliability(
    posterior: ReliabilityPosterior,
    actor_diagnostic: ActorDiagnostic,
) -> ReliabilityPosterior: ...
```

`s_m` decays and updates only at task/opportunity boundaries. `r_m` is the
bounded reliability of the prospective recognizer, updated through a frozen
dev-selected Beta/calibration rule from actor-side diagnostics; it is never
retrieval trust and receives no offline label. Store writes are canonical,
atomic, receipt-deduplicated, capped, and keyed by sequence/motif. The common
exposure initializes every stateful arm identically before treatment.
If dev evidence cannot establish a non-circular update and a measurable causal
path for `r_m`, the implementation emits a hard protocol-stop receipt; it cannot
instantiate or silently substitute a three-variable state.

- [ ] Add tests for task-time decay independent of action count, cap/floor,
  per-motif isolation, duplicate receipt idempotence, atomic roundtrip, challenge
  versus sequence reset, corrupt-store refusal, no retrieval/evaluator input,
  and hard-stop/no-three-variable-construction when the `r_m` gate fails.
- [ ] Run `pyrun -m pytest tests/research/test_persistent_state_core.py -q`;
  expect import failure.
- [ ] Implement immutable state/update/receipt records and both update laws.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run state tests twice and compare serialized bytes; run the import firewall.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add persistent state core`.

**Acceptance:** state persists across scheduled challenges, changes in task time
rather than trajectory length, and has no retrieval-text or evaluator backchannel.

### V2-26 — Implement forecast calibration `c` and caution homeostat `t`

**Legacy mapping:** WS-E-2, WS-E-3, and remaining WS-E-7 receipts.

**Files:**

- Create: `src/pneuma_lab/state/calibration.py`
- Create: `src/pneuma_lab/state/caution.py`
- Modify: `src/pneuma_lab/state/store.py`
- Test: `tests/research/test_calibration_caution_state.py`

**Contract:**

```python
def update_calibration(
    c: float,
    forecast: RiskForecast,
    actor_diagnostic: ActorDiagnostic,
    constants: CalibrationConstants,
) -> float: ...

def update_caution(
    t: float,
    appraisal: TaskBoundaryAppraisal,
    constants: CautionConstants,
) -> float: ...
```

`c` tracks reliability/calibration of the actor's prospective forecast using a
frozen bounded task-boundary EMA of actor-observable Brier evidence. The forecast
itself, not `c`, is scored in H1 recognition analyses. `t` is a bounded caution
homeostat driven by task-boundary failure/recovery appraisal and deterministic
decay. Neither updates per token/action. Each update carries old/new value,
constant digest, input receipt ids, task ordinal, and state hash.

- [ ] Add hand-calculated update tests, neutral initialization `c=0.5,t=0`,
  recovery decay, cap/floor, invariance to duplicated action events within one
  task, duplicate receipt rejection, and canonical receipt hashing.
- [ ] Run `pyrun -m pytest tests/research/test_calibration_caution_state.py -q`;
  expect import failure.
- [ ] Implement both pure laws and connect them to atomic boundary updates.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run all state tests and the import firewall.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add calibration and caution state`.

**Acceptance:** `c` and `t` have distinct measurable update laws, audit hooks,
and neutral values; action/token count cannot mechanically inflate either.

### V2-27 — Implement inert notice readouts, centered loss, and bounded reranking

**Legacy mapping:** WS-E-6 and pressure-related work formerly in WS-D-1.

**Files:**

- Create: `src/pneuma_lab/state/expected_loss.py`
- Create: `src/pneuma_lab/state/decision_head.py`
- Create: `src/pneuma_lab/recognition/notice_readout.py`
- Test: `tests/research/test_decision_head_v2.py`

**Contract:**

```python
def expected_loss(
    forecast: RiskForecast,
    state: PneumaState,
    constants: LossConstants,
) -> ActuationReadout: ...

def measure_notice_readout(
    backend: CandidateBackend,
    guard: ExecutionGuard,
    current: ObservableView,
    forecast: RiskForecast,
    carrier: DeclaredCarrierView,
    config: NoticeMeasurementConfig,
    measurement_seed: int,
) -> NoticeReadout: ...

def rerank_candidates(
    batch: CandidateBatch,
    pressure: PressureVector,
    constants: HeadConstants,
) -> SelectionReceipt: ...
```

`expected_loss` computes canonical §8.3
`applicability_m*r_m*clip(w_s*s_m + w_c*max(0,0.5-c) + w_t*t,0,1)`
as bounded actuation `L_m`, plus a frozen mapping from that actuation readout to
biases over fixed meta-action classes. `L_m` is pressure, not a calibrated
failure or notice probability. Separately, `measure_notice_readout` makes one
structured measurement call to the **same frozen actor checkpoint/backend** over
the common current view/forecast plus exactly one arm's legitimate
`DeclaredCarrierView`. Every arm—including Base and
Influence-off—emits the identical `NoticeReadout` schema before action; Base's
carrier is empty, Retrieval/Reflection expose only their declared actor-visible
memory, Retry exposes only its within-task count, the scalar arm exposes only its
selected scalar, and Pneuma/Influence-off expose only their receipt-bound state.
All seven arms use the identical frozen measurement prompt/scaffold, schema,
checkpoint, quantization, decoding settings, call timing, one-call count,
independent measurement-seed schedule, deterministic carrier truncation, and
maximum input/output measurement-token allocation. Measurement use is metered in
a separate equal-cap ledger and reported, but never debits or expands the actor's
action/candidate/tool budget and never enters a behavioral score. The readout
estimates the generator-held **pretreatment** recurrence fact;
action and outcome never define its target. Neutral `s_m=0,c=0.5,t=0` produces an exact all-zero actuation vector
regardless of `r_m`. Selection maximizes
`log(model_score)+bounded_pressure[class]` with a stable tie break. It cannot
add/drop candidates, edit tool/arguments, or select an unavailable class.
`NoticeReadout` contains one pre-action `NoticeProbability` for every known
motif, coverage/abstention, carrier-method/forecast/calibration/constant digests,
and a timing receipt. `ActuationReadout` is a disjoint type and cannot be scored
as notice. For target `y in {0,1}` and probability `p in [0,1]`, the frozen
primary scalar is `NoticeScore = 1 - mean((p-y)^2)`, higher better on `[0,1]`,
over exactly balanced target/decoy/counterfactual cases in each registered
notice cell. It follows the equal cell→lineage→motif hierarchy; macro
discrimination/AUROC, calibration, coverage, and specificity remain separate
hard gates; calibration is explicitly conditional on the registered balanced
opportunity distribution, not natural motif prevalence. The notice object is
written to a one-way trace sink and is never
passed to candidate generation, policy pressure, state update, tool execution,
or fallback logic; changing only its bytes must leave the complete behavioral
projection of the trace unchanged. All seven readouts are emitted before selection on every
scheduled opportunity, including zero-risk cases, so coverage cannot be
conditioned on engagement.

- [ ] Add separate formula/readout tests proving `L_m` cannot deserialize as a
  probability, one exact schema/motif/timing support and same actor checkpoint,
  prompt/scaffold, decoding, one-call timing/count, independent seed namespace,
  and max measurement tokens across all seven arms; legitimate-carrier
  allowlists, complete pre-action coverage, Base empty-carrier
  preservation, exact pretreatment-target invariance to action/outcome, and
  byte-perturbation proof that notice output is behaviorally inert. Prove
  measurement usage is separately metered/equal-capped, excluded from action
  caps and behavior scores, and cannot advance the action RNG. Add the
  neutral-zero actuation test,
  monotone component tests, pressure cap, zero-gain identity,
  unavailable-class behavior, stable ties,
  unchanged candidate bytes, and a case where bounded pressure changes rank.
- [ ] Run `pyrun -m pytest tests/research/test_decision_head_v2.py -q`; expect
  import failure.
- [ ] Implement pure expected-loss, pressure, and selection functions.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run candidate protocol, state, decision-head, and firewall tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add bounded state pressure head`.

**Acceptance:** every arm emits one same-schema pre-action notice diagnostic from
only legitimate current/carrier observables, and that diagnostic has no causal
edge to behavior. The head only reranks model-proposed candidates; Base and
Influence-off execute the exact same code with a zero pressure vector.

### V2-28 — Implement Base, Retry-count, and the four-family scalar condition

**Legacy mapping:** WS-D-1, WS-D-5, and the new strongest simple persistent
comparator required by Protocol v2.

**Files:**

- Create: `src/pneuma_lab/conditions/protocol.py`
- Create: `src/pneuma_lab/conditions/base.py`
- Create: `src/pneuma_lab/conditions/retry_count.py`
- Create: `src/pneuma_lab/conditions/motif_count.py`
- Create: `src/pneuma_lab/conditions/tuning.py`
- Create: `configs/research/controller-search-space.json`
- Test: `tests/research/test_simple_conditions.py`

**Contract:**

```python
class ConditionPolicy(ControlPolicy, Protocol):
    condition_id: ConditionId
    def memory_context(self, context: ActorContext) -> MemoryContext: ...
    def notice_carrier_view(self, context: ActorContext) -> DeclaredCarrierView: ...
    def snapshot(self) -> ConditionSnapshot: ...

class BaseCondition(ConditionPolicy): ...
class RetryCountCondition(ConditionPolicy): ...
class ScalarHazardCondition(ConditionPolicy): ...

def run_controller_search(
    pneuma_space: ControllerSearchSpace,
    scalar_space: ControllerSearchSpace,
    dev_sequences: Sequence[SuiteASequence],
    budget: MatchedSearchBudget,
) -> MatchedControllerTuningReceipt: ...
```

Base has no cross-task store and emits zero pressure. Retry-count uses only the
within-task identical-action retry counter preserved from E-0. The condition id
remains the preregistered `motif_count_ema`, but `ScalarHazardCondition` selects
the strongest dev result from a published four-family per-motif scalar grid:
last-failure bit, cumulative count, EWMA hazard, and Beta-posterior hazard. Every
family uses the same current-only recognizer, `LearningSignal`, motif vocabulary,
opportunity clock, numeric precision, persistence scope, receipt rules, candidate
head, and **at least** the same dev-search budget as Pneuma. Its family,
constants, and selection receipt are frozen before pilot/test labels.
Their notice adapters expose, respectively, an empty carrier, the within-task
retry count, or the selected scalar through V2-27's common behaviorally inert
readout; they cannot add condition-specific fields or consume its output.

`controller-search-space.json` explicitly lists Pneuma's grid and all four
scalar-family grids, the common dev lineage folds, blocked seeds, objective, tie
rule, Pneuma maxima, and equal-or-greater scalar maxima for evaluated
configurations, sequence episodes, model calls, and candidate selections. A
deterministic predeclared sampler handles unequal grid cardinalities without
granting Pneuma more trials.
`run_controller_search` evaluates both controllers on the same dev units, writes
an append-only canonical JSONL trial ledger for every attempted configuration
(including failures), and emits one receipt binding both selected artifacts,
budgets, ledger digest, split, and code/config digests. Manual or unlogged trials,
pilot/test labels, any omitted scalar family, or a scalar budget below Pneuma's
fail closed. The frozen receipt
is an input to V2-31 parity and V2-38 preregistration.

- [ ] Add tests for Base reset/zero pressure, Retry-count within-task reset,
  nonadjacent different-command behavior, all four last-bit/count/EWMA/Beta
  scalar update and persistence rules,
  recognizer/head object parity, no Pneuma variable access, and receipt binding.
  Add exact search-space parsing, scalar-budget-not-less-than-Pneuma
  trial/episode/model-call budgets, identical dev lineage folds/seeds/objective,
  complete family coverage, deterministic tie selection, failed-trial
  logging, ledger tamper rejection, and pilot/test-input refusal tests. Assert
  exact common notice schema, carrier allowlists, pre-action timing, and
  noninterference for all three conditions.
- [ ] Run `pyrun -m pytest tests/research/test_simple_conditions.py -q`; expect
  import failure.
- [ ] Implement the common policy seam, three conditions, and matched dev-only
  tuning ledger/receipt.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run driver, recognizer, state/head, and simple-condition tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add simple comparator conditions`.

**Acceptance:** H1 cannot be explained by a retry counter or the strongest of
four simple persistent scalar hazards given at least Pneuma's tuning effort; if
that scalar ties Pneuma, only the simple-persistent-state conclusion is credited.

### V2-29 — Implement Retrieval and Reflection conditions

**Legacy mapping:** WS-D-2 and WS-D-3.

**Files:**

- Create: `src/pneuma_lab/conditions/retrieval.py`
- Create: `src/pneuma_lab/conditions/reflection.py`
- Create: `src/pneuma_lab/conditions/reflection_prompt.py`
- Test: `tests/research/test_text_memory_conditions.py`

**Contract:**

```python
class RetrievalCondition(ConditionPolicy): ...
class ReflectionCondition(ConditionPolicy): ...
```

Retrieval injects deterministic top-k semistructured failure records from V2-24
within a frozen context budget. Reflection uses a frozen post-task reflection
prompt and model/token cap to write a bounded lesson that is re-injected on later
tasks; its checkpoint, prompt, call count, token use, parse path, and lesson
digest are traced. The reflection-generation cost is part of the treatment and
reported through the common meter, including input/output tokens and failed,
repair, and fallback calls. Any retrieval-maintenance model call is metered at
the same boundary. Neither condition exposes state variables or pressure
beyond its preregistered text-memory policy. Text is actor context only and never
enters behavioral scoring.
Each exposes only its already actor-visible retrieved records or reflection
lesson through a bounded, dev-frozen carrier adapter to the common pre-action
`NoticeReadout`. The diagnostic never enters the prompt or policy decision.

- [ ] Add tests for stable top-k/context serialization, reflection budget,
  post-task timing, no future-task access, persistence, malformed reflection,
  resource accounting, common notice schema/carrier allowlist/noninterference,
  no state pressure, and prose-blind evaluator isolation.
- [ ] Run `pyrun -m pytest tests/research/test_text_memory_conditions.py -q`;
  expect import failure.
- [ ] Implement both policies and reflection prompt/receipt handling.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run retrieval-store, driver, firewall, and text-condition tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add text memory conditions`.

**Acceptance:** retrieval and written reflection are strong auditable baselines;
their prose cannot alter exact evaluation except through the actor's behavior.

### V2-30 — Implement Pneuma-state and full Influence-off conditions

**Legacy mapping:** WS-D-4 and corrected WS-D-6.

**Files:**

- Create: `src/pneuma_lab/conditions/pneuma_state.py`
- Create: `src/pneuma_lab/conditions/influence_off.py`
- Test: `tests/research/test_pneuma_conditions.py`

**Contract:**

```python
class PneumaStateCondition(ConditionPolicy): ...
class InfluenceOffCondition(PneumaStateCondition): ...
```

Both consume identical prospective forecasts, online signals, task-boundary
updates, persistence, state receipts, loss computation, and candidate batches.
Pneuma applies the frozen bounded pressure vector. Influence-off sets every
state-to-action gain to exactly zero after computing and recording the live
state/loss; no variable can reach selection through another path. Neither
serializes state into a candidate/action, repair, fallback, tool, update, or
later-task prompt; the separately metered inert notice and post-behaviour report
sinks are the only permitted diagnostic serialization boundaries.
Both emit the same behaviorally inert `NoticeReadout` from the identical live
state carrier; therefore Influence-off is a useful H2 notice-path diagnostic but
is not a sixth H1 comparator.

- [ ] Add paired fixed-event tests proving identical state/receipt bytes,
  nonzero Pneuma pressure when eligible, exact all-zero Influence-off pressure,
  same-schema/equal notice readouts with sink noninterference, no state fields in
  any behavioural/action prompt, equal candidate batches, and divergent selection only
  when bounded reranking crosses a score gap.
- [ ] Run `pyrun -m pytest tests/research/test_pneuma_conditions.py -q`; expect
  import failure.
- [ ] Implement both policies over the shared state/head modules.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run all condition, state, driver, and firewall tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add pneuma and influence-off conditions`.

**Acceptance:** Influence-off is a complete actuation-edge null with live state,
not an `s_m` clamp or a claim of Base equivalence.

### V2-31 — Register seven conditions and verify all non-treatment parity

**Legacy mapping:** closes the six-condition gap across WS-D-1–WS-D-6.

**Files:**

- Create: `src/pneuma_lab/conditions/registry.py`
- Create: `src/pneuma_lab/conditions/parity.py`
- Create: `schemas/seven-arm-assignment.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Modify: `tests/test_schema_loads.py`
- Test: `tests/research/test_condition_parity.py`

**Contract:**

```python
def build_condition(
    condition_id: ConditionId,
    shared: SharedConditionResources,
    treatment: TreatmentConfig,
) -> ConditionPolicy: ...

def audit_condition_parity(configs: Sequence[BoundConditionConfig]) -> ParityReceipt: ...

def randomize_seven_arm_assignment(
    block: RandomizedBlockSpec,
    policy_mapping_seed: int,
    execution_order_seed: int,
) -> RecordedSevenArmAssignment: ...
```

The registry contains exactly seven core arms and randomizes pseudonymous labels
within model×prototype-lineage×sequence×seed blocks. Before outcomes it records
a complete seven-policy-label-to-fixed-clone/RNG-stream map and execution order.
Two domain-separated random streams draw (i) `M ~ Uniform(7!)`, mapping policy
labels to the seven fixed clone/RNG-stream ids, and (ii) independently
`O ~ Uniform(7!)`, ordering those **stream ids** for execution—not ordering
policy labels. Their marginal probabilities are each `1/7!`, their joint
probability is `1/(7!)^2`, and neither draw may be constrained,
counterbalanced, reused, or adapted to outcomes. The immutable receipt carries both seeds/draw digests, the exact assignment
probability/mechanism, lineage/block/stream digests, public seven-pseudonym roster,
and a sealed unblinding map; the evaluator receives only the pseudonyms, while
V2-35 verifies and replays the complete mapping after labels are frozen. The
parity audit requires identical checkpoint,
quantization, backend, action prompt/repair/fallback templates, candidate count,
notice-measurement checkpoint/prompt/scaffold/schema/decoding, pre-action timing,
one-call count, independent seed schedule, and maximum measurement tokens,
tools, ex-ante caps and common accounting for every candidate, repair, fallback,
reflection, retrieval/state-maintenance model call, input/output token, attempted
tool action, retry, and failed call; retry cap, task order, sandbox
snapshot, seed schedule, and actor/evaluator versions. Allowed differences are
only declared memory/state context, update, and pressure policies. Context is not
padded; realized resource use is recorded as outcome data.
For Pneuma-state versus the four-family scalar search, the audit additionally
requires the same `MatchedControllerTuningReceipt`, scalar consumed trials/
episodes/model calls no smaller than Pneuma's, the same dev lineage folds/seeds/
objective, a complete last-bit/count/EWMA/Beta trial ledger, and separate
selected-artifact digests from the two declared search spaces.

- [ ] Add one planted mismatch test for every required parity field, exact-seven
  roster test, pseudonym balance test, allowed-treatment-difference test, and
  assertion that no action-context padding occurs. Plant every notice parity
  mismatch, unequal measurement allocation, action-budget debit, or measurement
  RNG reuse and require failure. Add roundtrip/replay tests for the
  actual seven-label assignment and reject duplicate/missing labels, duplicate
  streams, post-outcome assignment, or absent lineage digest. Exactly enumerate
  both 5,040-element supports and their probabilities; prove mapping/order RNG
  domain separation and independence, and reject shared RNG, restricted/
  counterbalanced support, nonuniform/joint probability, adaptive order, or an
  order defined over policy labels rather than fixed stream ids. Any future
  restricted/dependent design must stop and receive a decision-log/protocol
  amendment with its exact conditional/joint replay; it cannot silently reuse
  this Uniform×Uniform analysis. Plant a scalar
  tuning budget below Pneuma's, a missing scalar family, an unlogged manual
  trial, a split mismatch, and a tuning-ledger hash mismatch;
  each must fail parity before any pilot. Add canonical assignment-schema
  roundtrips for `M`, stream-id `O`, both seeds/digests, and exact joint
  probability; reject unknown labels, policy-labelled order, unsealed unblinding
  maps, raw condition names in the public roster, raw prose, and unknown fields.
- [ ] Run `pyrun -m pytest tests/research/test_condition_parity.py -q`; expect
  import failure.
- [ ] Implement registry, blocked randomization, and fail-closed parity audit;
  register and document the assignment schema under `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run the test file plus schema-load/validation tests; expect all tests to pass.
- [ ] Run one sequence×seven arms through the fake backend; after signed local
  authorization, repeat a bounded smoke with the chosen local checkpoint. Store
  receipts under `build/research/dry-runs/g4/` and declare G4 only if parity and
  all prior tests pass.
- [ ] Commit only the exact `Files` paths with subject
  `feat: register seven matched conditions`.

**Acceptance:** condition identity changes no shared substrate or ex-ante cap;
the only differences are the seven preregistered treatments.

---

## Phase F/G/H — Endpoint, causal interventions, inference, and attribution

### V2-32 — Implement fixed-denominator repeat harm and utility co-gates

**Legacy mapping:** WS-G-1, anti-gaming portions of WS-G-3, and the RUF
definition corrected by Protocol v2.

**Files:**

- Create: `src/pneuma_lab/evals/repeat_harm.py`
- Create: `src/pneuma_lab/evals/utility_gates.py`
- Create: `schemas/randomized-block-outcome.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Modify: `tests/test_schema_loads.py`
- Test: `tests/research/test_repeat_harm_v2.py`

**Contract:**

```python
def repeat_harm(
    outcomes: Sequence[OpportunityOutcome],
    schedule: OpportunitySchedule,
) -> SequenceEndpoint: ...

def severity_weighted_repeat_harm(
    outcomes: Sequence[OpportunityOutcome],
    schedule: OpportunitySchedule,
) -> SeverityWeightedSequenceEndpoint: ...

def aggregate_equal_weight_h1(
    endpoints: Sequence[RegisteredCellEndpoint],
) -> EqualWeightH1Endpoint: ...

def assemble_complete_randomized_block(
    outcomes: Sequence[PseudonymousArmOutcome],
    assignment_roster_digest: str,
) -> CompleteRandomizedBlock: ...

def validate_block_mask(
    block: CompleteRandomizedBlock,
    evidence: ExogenousOutageEvidence | None,
) -> ValidatedBlockMask: ...

def score_randomized_block(
    block: CompleteRandomizedBlock,
    schedule: OpportunitySchedule,
    mask: ValidatedBlockMask,
) -> RandomizedBlockEndpointBundle: ...

def natural_sequence_value(
    outcomes: Sequence[OpportunityOutcome],
    schedule: OpportunitySchedule,
) -> NaturalSequenceEndpoint: ...

def evaluate_utility_gates(
    episodes: Sequence[BoundEpisodeOutcome],
    margins: UtilityMargins,
) -> UtilityGateBundle: ...
```

`repeat_harm` is the primary equal-opportunity endpoint. It always scores a
single arm's observed non-engagement/runtime failure as adverse and has no
missingness or exclusion parameter. Its numerator counts same-family harmful
recurrence and
every observed agent-side refusal, timeout, premature finish, budget exhaustion,
invalid action/model error, or branch-local runtime crash, without conditioning
on whether treatment can be shown to have caused it. The
denominator is the fixed count of scheduled opportunities, each with weight one.
Success and different-family failures
remain in it. `assemble_complete_randomized_block` requires exactly the seven
unique pseudonyms from one sealed roster/assignment digest and rejects condition
names, duplicates, omissions, or mixed block bindings. Only
`validate_block_mask` may construct a `ValidatedBlockMask`, and it can choose
only `retain_all_seven` or `exclude_all_seven`. Exclusion requires immutable,
arm-blind, preregistered `ExogenousOutageEvidence` proving the same external
event made the complete block unobservable independently of arm/behavior. The
mask binds the full block/evidence/roster digests and is consumed atomically by
`score_randomized_block`; there is no per-arm mask API. A one-branch failure,
incomplete/missing telemetry, or uncertain attribution is scored adverse in all
ordinary arm endpoints, never deleted, and additionally
triggers preregistered worst-case missingness/misclassification sensitivity.
Even a valid complete-block exogenous exclusion triggers best/worst-case
attrition sensitivity. When such a block is excluded, one preregistered
arm-independent rule renormalizes the retained frozen cells/lineages/motifs
identically for all seven arms; condition-specific renormalization is forbidden.
`RUF` may be
exported only as an alias for this exact value. Utility outputs cover attempt,
completion, verified success, total/new-family severity, refusal, timeout,
premature finish, branch-local crash/model error, exogenous block outage,
false avoidance, calls/actions/tokens, and latency.
Resource outputs include the complete V2-22 accounting vector, not only a total:
candidate/repair/fallback/reflection/retrieval-state model calls, failed calls,
input/output tokens, attempted tool actions, retries, deterministic truncation,
and cap-hit reason, plus disjoint notice-measurement and post-behavior-reporting
ledgers. Diagnostic ledgers are reported/resource-compared but excluded from the
behavioral endpoint and main action cap. After the immutable trace and
mechanically scored outcome are both sealed, V2-32 emits a digest-bound
`BehaviorFinalizationReceipt`. It contains no report text and authorizes only
V2-37's one-way post-behavior reporting call; it cannot reopen the trace, actor
state, sandbox, evaluator input, or action budget.
`aggregate_equal_weight_h1` implements one exact four-level hierarchy: (1) mean
the weight-one scheduled opportunities inside each preregistered
sequence×surface×challenge×decoding-seed cell; (2) mean frozen registered cells
equally inside each authored lineage; (3) mean authored lineages equally inside
each motif; and (4) mean motif strata equally for the headline endpoint. Cell,
lineage, and motif rosters are frozen before outcomes; empty/extra cells fail
closed. No long cell, prolific generator/lineage, or large motif can dominate.
Frozen severity weights feed only
`severity_weighted_repeat_harm`, a clearly labelled secondary robustness
endpoint; severity-weighted results never substitute for the primary hierarchy.
The secondary natural-sequence endpoint reports first harmful-failure incidence
and fixed-schedule recurrence without conditioning on an observed arm-specific
first failure; any principal-stratum estimate is clearly marked sensitivity-only.

- [ ] Add hand-calculated sequences for success, target repeat, substituted
  failure, refusal, timeout, premature finish, budget exhaustion, one-arm
  branch crash, uncertain outage, strictly evidenced common exogenous outage,
  unequal severity weights, and false avoidance. Assert the primary result is
  invariant to those severity weights while the secondary changes. Add a
  hand-calculated two-motif/multiple-lineage hierarchy with deliberately
  unbalanced opportunities per cell, cells per lineage, and lineages per motif,
  proving weight-one opportunity means within cell, equal frozen cells within
  lineage, equal lineages within motif, and equal motif weights. Assert one-arm/uncertain cases are
  adverse plus sensitivity while only the evidenced whole block is removed; no
  arm-specific denominator is possible. Add API tests requiring seven unique
  roster-bound pseudonyms, rejecting mixed blocks/condition names/caller-built
  masks, proving uncertain or per-arm evidence retains all seven as adverse, and
  proving valid evidence atomically removes exactly all seven. Add a natural sequence with no first
  failure in one arm and verify all scheduled tasks remain represented. Add
  a valid common-outage case proving identical seven-arm renormalization over the
  retained frozen hierarchy and reject any arm-specific normalization. Add
  canonical schema roundtrips for evidence, bundle, and mask plus malformed,
  per-arm-mask, and raw-prose rejection. Verify that a finalization receipt is
  issued only after both trace and outcome digests are immutable, and that
  changing or replaying it cannot modify either artifact.
- [ ] Run `pyrun -m pytest tests/research/test_repeat_harm_v2.py -q`; expect
  import failure.
- [ ] Implement pure endpoint, complete-block mask, attrition bounds, and
  co-gate summaries over exact outcomes, with a fail-closed exogenous-outage
  evidence validator. Register and document the block artifact schema under
  `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run evaluator, Suite-A, firewall, schema-load, validation, and repeat-harm
  tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add fixed denominator repeat harm`.

**Acceptance:** stopping, refusing, substituting failure, generator multiplicity,
motif size, or changing exposure
eligibility cannot manufacture a lower primary score; no branch-local failure is
deleted as infrastructure, and only strictly evidenced exogenous whole-block
outages can be excluded through one immutable block-level authority. Realized
resources remain outcomes rather than post-
treatment adjustment variables, and severity weighting remains secondary.

### V2-33 — Implement the complete live intervention battery

**Legacy mapping:** WS-F-1 plus Protocol-v2 causal/ablation corrections.

**Files:**

- Create: `src/pneuma_lab/interventions/live.py`
- Create: `src/pneuma_lab/interventions/randomization.py`
- Modify: `src/pneuma_lab/interventions/operations.py`
- Modify: `src/pneuma_lab/interventions/schedule.py`
- Test: `tests/research/test_live_interventions_v2.py`

**Contract:**

```python
def randomize_intervention(
    eligible_point: EligibleDecisionPoint,
    specification: InterventionSpecification,
    randomization_seed: int,
) -> LiveIntervention: ...

def apply_live_intervention(
    state: PneumaState,
    policy: ConditionPolicy,
    intervention: LiveIntervention,
) -> InterventionApplication: ...
```

Support intact versus Influence-off, randomized component clamps for
`s_m,c,t,r_m`, low/high/dose clamps, update-off, influence-off, motif permutation/
scramble, mandatory `persistence_off`, challenge reset, sham receipt, no-op,
restore, self-report disable, and
prompt-text serialization of the same structured information as a diagnostic.
Same-length shuffled-text memory and structured-state prompt serialization are
mandatory diagnostics before rejecting a token/context explanation;
State×Retrieval remains optional behind an explicit config flag. Randomization happens only at preregistered eligible
decision points and is hidden from the reporter. Every operation emits old/new
state hashes, targeted edge, assignment probability, schedule digest, and
whether it actually changed pressure/action.
`persistence_off` resets all prior-task persistent state immediately after the
verified common exposure and before the scheduled opportunity, while preserving
the current task/snapshot, candidate call, current-only forecast, decision head,
and an immutable receipt retained by the sealed audit subsystem. Actor, updater,
carrier, and head receive only a same-shape inert state handle through the first
scheduled decision. Failure to reach the opportunity remains an adverse ITT
outcome. This intervention is mandatory for crediting persistence, not an
optional component ablation. Until that decision is irrevocably recorded, every
carrier load/retrieval, state update, replay, summary, or derived feature that
could rehydrate exposure information is blocked. Afterward the receipt is
released only to audit/report paths, never to any actor, updater, carrier, head,
or derived-feature path. Reconstructing state from the retained receipt at any
time fails the intervention.

- [ ] Add one exact test per operation; test stable randomized assignment,
  assignment before outcome, update-off versus influence-off distinction,
  permutation bijection, exact post-exposure persistence reset, preservation of
  current task/candidates/sealed audit receipt/head under that reset, same-shape
  inert handles at actor/updater/carrier/head, rejection of every receipt/store/
  retrieval/replay/summary/derived-feature rehydration path both before and
  after the first recorded decision, audit/report-only post-decision receipt
  release, adverse non-engagement,
  same-length shuffled-text bytes/token accounting, structured-state
  serialization, sham/restore identity, no target metadata in reporter
  input, and unknown operation fail-closed.
- [ ] Run `pyrun -m pytest tests/research/test_live_interventions_v2.py -q`;
  expect import or operation failure.
- [ ] Extend operation vocabulary without changing existing replay semantics,
  then implement live application/randomization.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run existing intervention tests plus live-intervention, state, and condition
  tests.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add live causal interventions`.

**Acceptance:** every variable and the full actuation edge has clamp, update-off,
influence-off, restore, and audit semantics; the mandatory persistence-off branch
can isolate cross-task carryover, and component clamps are not mislabeled as
Base-equivalent arms.

### V2-34 — Implement stochastic distributional-null and branch-divergence checks

**Legacy mapping:** WS-F-3 and the statistical causal-gate landmine.

**Files:**

- Create: `src/pneuma_lab/experiment/causal.py`
- Create: `src/pneuma_lab/statistics/__init__.py`
- Create: `src/pneuma_lab/statistics/divergence.py`
- Test: `tests/research/test_distributional_causal_gate.py`

**Contract:**

```python
def run_causal_seed_block(
    prefix: BoundPrefix,
    control: BranchSpec,
    treated: BranchSpec,
    seeds: Sequence[int],
) -> CausalSeedBlock: ...

def distributional_causal_gate(
    block: CausalSeedBlock,
    equivalence: PoweredEquivalenceDesign,
) -> CausalGateReport: ...
```

For each seed, verify the frozen checkpoint/config/template/sampler/exogenous
seed and byte-equal trace/sandbox/state prefix through `t0`, then run both cloned
descendants live. Compare first post-intervention structured-intent distributions
with total variation and Jensen–Shannon divergence, plus paired repeat-harm,
utility, and selection-change effects. Sham/restore/no-op paths use frozen
equivalence regions; active clamps use direction/dose tests. Equivalence margins,
categorical support, alpha, target power, and minimum repeated-draw count are
dev-frozen before pilot. The gate refuses an underpowered null block and reports
confidence bounds/TOST-style decisions against the two-sided margin; failure to
reject a difference is never called equivalence. RNG handling and support are
symmetric across paired branches. Do not require
token-level logits and do not align arbitrary later ticks after branch lengths
diverge. N-sample uncertainty is reported; byte equality of a deterministic
subject is only an instrumentation check.

- [ ] Add synthetic blocks for identical distributions, planted rank shift,
  equal first intent but later outcome shift, unequal branch lengths, prefix
  mismatch, post-`t0` transcript freeze, insufficient seeds, sham outside the
  margin, underpowered apparent null, asymmetric RNG/support, powered sham inside
  the frozen margin, and monotone dose response.
- [ ] Run `pyrun -m pytest tests/research/test_distributional_causal_gate.py -q`;
  expect import failure.
- [ ] Implement stable categorical support, TV/JS calculations using Python
  `math`, paired summaries, equivalence regions, and causal receipts.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run branching, live-intervention, repeat-harm, and causal-gate tests together.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add stochastic causal gate`.

**Acceptance:** real stochastic agents can pass the strongest distributional
causal path without incoherent transcript freezing; null and active
interventions have distinct preregistrable decision regions, and no null is
credited without a dev-frozen equivalence margin and powered repeated draws.

### V2-35 — Add cluster-aware inference, multiplicity control, and power simulation

**Legacy mapping:** WS-G-2, statistical part of WS-F-3, and power part of WS-I-1.

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/pneuma_lab/statistics/randomization.py`
- Create: `src/pneuma_lab/statistics/bootstrap.py`
- Create: `src/pneuma_lab/statistics/multiplicity.py`
- Create: `src/pneuma_lab/statistics/sensitivity.py`
- Create: `src/pneuma_lab/statistics/recognition_endpoint.py`
- Create: `src/pneuma_lab/statistics/decision_regions.py`
- Create: `src/pneuma_lab/statistics/power.py`
- Create: `src/pneuma_lab/statistics/config.py`
- Test: `tests/research/test_cluster_inference.py`
- Test: `tests/research/test_power_simulation_v2.py`

**Dependency change:** add exactly
`research = ["numpy==2.5.1"]` under `[project.optional-dependencies]`. All primary
statistics use Python 3.12 stdlib plus this pinned NumPy version; SciPy,
statsmodels, pandas, and undeclared numerical libraries are not imported.
Regenerate `uv.lock`, verify the locked NumPy artifact/version, and run the
statistics suite from `"$UV" sync --project "$WT" --frozen --extra dev --extra
research` with the worktree-local `UV_PROJECT_ENVIRONMENT`; a changed project
dependency without a synchronized lock is a task failure.

**Contract:**

```python
def fisher_h1_sharp_null_test(
    data: LineageClusterTable,
    assignments: Sequence[RecordedSevenArmAssignment],
    config: InferenceConfig,
) -> FisherSharpNullBundle: ...

def h1_average_effect_intervals(
    data: LineageClusterTable,
    config: InferenceConfig,
) -> H1AverageEffectBundle: ...

def h1_lineage_fallback(
    data: LineageClusterTable,
    config: InferenceConfig,
) -> H1AverageEffectBundle: ...

def freeze_recognition_criteria(
    dev_readouts: Mapping[ConditionId, Sequence[NoticeReadout]],
    dev_targets: Sequence[PretreatmentRecurrenceTarget],
    *,
    split: Literal["dev"],
    search_budget: RecognitionSearchBudget,
) -> FrozenRecognitionCriteria: ...

def score_recognition_endpoint(
    readouts: Mapping[ConditionId, Sequence[NoticeReadout]],
    targets: Sequence[PretreatmentRecurrenceTarget],
    criteria: FrozenRecognitionCriteria,
) -> RecognitionDecision: ...

def decide_h1_family(
    recognition: RecognitionDecision,
    effects: H1AverageEffectBundle,
    utility: UtilityGateBundle,
) -> H1Decision: ...

def decide_h2_family(evidence: H2EvidenceBundle) -> H2Decision: ...
def decide_h3_family(evidence: SelfReportBundle) -> H3Decision: ...
def decide_h4_family(evidence: H4EvidenceBundle) -> H4Decision: ...

def apply_h1_h4_holm_and_logical_gates(
    h1: H1Decision,
    h2: H2Decision,
    h3: H3Decision,
    h4: H4Decision,
    config: FamilywiseConfig,
) -> GlobalH1H4Decision: ...

def simulate_power(
    design: PlannedDesign,
    pilot: NuisanceOnlyPilotParameters,
    config: PowerConfig,
) -> PowerReport: ...
```

First compute preregistered macro discrimination, proper-score calibration, and
coverage from every arm's same-schema pre-action `NoticeReadout` against the
generator-held `PretreatmentRecurrenceTarget`. The target is bound before action
and invariant to condition/outcome; `L_m` never enters this score and the readout
never enters behavior. H1 notice evidence is a five-comparator conjunction:
Pneuma's frozen `NoticeScore = 1 - mean((p-y)^2)` (higher better, `[0,1]`) must
meet its absolute criteria and exceed
Base, Retrieval, Reflection, Retry-count, and the four-family scalar condition
on five named paired contrasts. Influence-off is reported for H2 but is not a
sixth H1 comparator. Schema/checkpoint/prompt/decoding/timing/measurement-budget
parity is a prerequisite, not a covariate.

The independent unit is the highest shared independently authored prototype/
generator lineage. Surface variants, challenges, nominal sequences,
opportunities, and decoding seeds are nested replicates and carry the frozen
lineage digest from generation through split, binding, assignment, inference,
power, and release. Primary behavior uses V2-32's equal-opportunity hierarchy:
mean unit-weight opportunities within each frozen registered cell, cells equally
within lineage, lineages equally within motif, and motifs equally overall.
Severity-weighted effects are secondary.

`fisher_h1_sharp_null_test` and `h1_average_effect_intervals` are deliberately
separate estimators. The Fisher path verifies, for every
model×lineage×sequence×seed block, the uniform `1/7!` policy mapping to seven
distinct clone/RNG streams and the independently uniform `1/7!` execution order.
It verifies the joint receipt probability `1/(7!)^2`, conditions on realized
`O` (valid because `M` is independent), and rerandomizes `M` over the exact
conditional 5,040-mapping support for tiny designs or uses at least 100,000 deterministic
Monte Carlo policy permutations for larger designs. On every draw it recomputes
weight-one opportunity means within registered cells → equal cells within
lineage → equal lineages within motif → equal motifs before the test statistic.
It returns **sharp global-null p-values only**. It never produces
an average-effect confidence interval or supports a claim about effect
magnitude. A whole contrast-vector sign flip, post-aggregation shuffle,
independently flipped comparator/seed, restricted mapping support, or replay of
execution order as though it were policy assignment is forbidden.
Any amended restricted/dependent design requires its own frozen exact
conditional/joint replay implementation and cannot enter this estimator.

Average-effect point estimates and simultaneous one-sided 95% confidence bounds
come only from at least 10,000 motif-stratified authored-prototype-lineage cluster
bootstrap draws. Each draw resamples whole lineages with every nested sequence,
seed, opportunity, and seven-arm pairing intact, recomputes the equal-weight
hierarchy, studentizes all **ten** H1 effects (five notice plus five behavior),
and uses the bootstrap studentized max-T distribution for simultaneous bounds.
This bootstrap, not Fisher randomization, supplies H1 magnitude inference. Report
absolute risk differences, notice-score differences on their frozen bounded
scale, risk ratios, motif effects, lineage/sequence/seed pigeonhole sensitivity,
full resource frontiers, and utility/anti-gaming non-inferiority co-gates.

If the assignment receipt is incomplete or policy mapping was not genuinely
uniform/randomized, Fisher evidence is unavailable. `h1_lineage_fallback` still
computes the preregistered cluster-bootstrap/model-based average-effect analysis,
explicitly labelled non-randomization evidence; label permutation is sensitivity
only. Suite B-live clusters at the highest shared repository plus task-generator/
prototype ancestor and is restricted to its mechanically scorable known-motif
target population.

Power targets the **complete H1 conjunction**, not one convenient contrast:
all five notice superiority tests, all five behavioral superiority tests, and
every utility/engagement/anti-gaming non-inferiority gate must pass jointly. The
declared design alternative is exactly `Delta_power = 0.10` on each frozen
bounded superiority-effect scale, while every true utility difference is fixed
at zero and evaluated against its preregistered non-inferiority margin in one
frozen joint DGP; the simulator rejects `0.05` as the power alternative, a
favorable planted utility advantage, or component-specific DGPs. The separate
behavioural decision SESOI remains 0.05: each of the five observed repeat-harm
reductions must be at least five points and its simultaneous lower bound exceed
zero, which does not claim the true effect is at least five points. Notice
components instead use their dev-frozen discrimination, calibration, coverage,
superiority, and simultaneous-lower-bound criteria; the 0.05 observed magnitude
gate is not extended to their score scale. The simulator uses only
pooled/blinded pilot nuisance quantities—event rates, paired covariance across
all ten effects, intracluster correlation, notice/actor-signal error, attrition,
utility rates, and feasibility—plus dev-frozen criteria/margins and the bootstrap
max-T procedure. It targets at least 80% probability that the entire conjunction
passes and counts authored lineages, never tasks×challenges×seeds, as independent
units.
The sample-size rule is deterministic, uses blinded nuisance re-estimation only,
and forbids effect-dependent optional stopping.
`freeze_recognition_criteria` is dev-only and fixed-budget. Its immutable
artifact records per-motif macro discrimination and calibration metrics,
coverage, all five paired Pneuma-minus-comparator notice margins, candidate grid,
trial count, selection rule, measurement parity receipt, and all input/artifact
digests. Confirmatory-test scoring
is read-only and rejects criteria fitted outside dev or readouts with mismatched
motif, timing, recognizer, or calibration digests. Pilot readouts cannot produce
a recognition decision and pass only through the nuisance projection. That
pilot interface accepts
only a sealed `NuisanceOnlyPilotParameters` projection; arm effects, condition
labels, thresholds, transforms, motif inclusion, controller grids, checkpoints,
criteria, or margins cannot be read or changed after the dev-freeze receipt.
Pilot results may only declare infeasibility or narrow scope under a rule frozen
before labels are opened.

Add a preregistered sensitivity regression over lineage-level paired differences
using only pre-treatment covariates fixed in the common exposure: sequence/motif
stratum, exposure retry count, exposure action/token count, and exposure trace
length. Never adjust for arm-specific realized post-treatment actions/tokens;
report those through V2-32 resource outcomes/frontiers instead.
`H1Decision` stores, for each of five named comparators, a notice component with
its average-effect estimate, frozen notice-criterion decisions, bootstrap
simultaneous lower bound, `lower_bound_gt_0`, and valid component p-value, plus a
behaviour component that additionally carries `point_ge_0_05`, and every
utility/anti-gaming non-inferiority decision. `decide_h1_family` is an
explicit intersection–union test: its family p-value is the maximum of all
required component p-values, and `supported` is constructible only when all ten
superiority components and every co-gate pass. The separate Fisher sharp-null
p-value is reported but cannot replace any average-effect component or bound.
H5's utility gates are fields inside `H1Decision`, not a fifth family p-value.

`decide_h2_family`, `decide_h3_family`, and `decide_h4_family` likewise implement
their frozen intersection–union batteries and expose one valid family p-value
plus supported/refuted/inconclusive reasons. `H2Decision` cannot be supported unless
Influence-off removes the intact advantage, randomized clamps/dose are coherent,
the mandatory persistence-off reset removes the preregistered carryover
advantage, sham/no-op/restore pass powered equivalence, and wiring nulls remain
null. H3's IUT includes nine-label macro/coverage/risk–coverage/baseline
requirements; H4's IUT preserves each preregistered surface/repository axis.
`apply_h1_h4_holm_and_logical_gates` applies Holm across exactly the four family
p-values and then the frozen logical gates: H2 and H4 claims require H1, while a
“why behavior changed” H3 claim requires both H1 and H2. Logical gating never creates or
recycles alpha. All four prespecified slots remain in the family: an unavailable,
invalid, or inconclusive H1/H2/H3/H4 decision contributes `p=1` and is never
dropped to make the remaining correction easier. Exploratory BH-FDR is separately frozen and never substitutes
for these decisions.

- [ ] Add hand-calculated seven-arm same-schema notice discrimination/
  calibration/coverage, action/outcome-invariant target, dev-only freeze,
  measurement-parity/artifact-drift, and all five Pneuma-minus-comparator notice
  superiority tests. Exactly enumerate the uniform 5,040 policy mappings and
  independent 5,040 execution orders, verify `1/7!` marginals and domain-separated
  draws, and add a tiny Fisher sharp-null case with a hand-calculated p-value and
  a planted treatment effect. Prove the Fisher API cannot emit an effect CI.
  Add tests that aggregate seeds only after every permutation and reject a
  joint-sign-vector shortcut, restricted/nonuniform mapping, order/mapping RNG
  reuse, or order replay as treatment assignment. Add a known authored-lineage
  bootstrap case with at least 10,000 official draws, studentized max-T
  simultaneous one-sided CIs over all ten H1 effects, and proof that Fisher and
  bootstrap outputs cannot be interchanged. Add missing/nonrandom assignment
  fallback, lineage nesting/digest, deliberately unbalanced equal-weight
  hierarchy, B-live repository+generator/prototype clustering/target-scope,
  explicit H1/H2/H3/H4 IUT family tests, four-slot Holm/logical-gate tests, proof
  H5 is not tested twice, H2 refusal when persistence-reset or powered-null gates
  fail, frozen exploratory BH examples,
  non-inferiority direction, risk-ratio zero-cell rule, deterministic RNG,
  official-draw minimums, pre-treatment covariate sensitivity, rejection of a
  post-treatment resource covariate, and power cases proving marginal power is
  insufficient, naive task counting is overoptimistic, the complete five-notice+
  five-behavior+utility conjunction reaches 80% at exactly
  `Delta_power=0.10` under one frozen joint DGP with true utility differences
  zero and preregistered margins, and `0.05`, favorable utility effects, or
  component-specific DGPs are rejected as power alternatives. Prove the pilot
  projection exposes nuisance fields only and
  cannot mutate any dev-frozen criterion, margin, grid, label, transform, or
  checkpoint; reject effect-dependent sample-size input or optional stopping.
- [ ] Add exact H1 decision-boundary tests: support requires all five notice and
  all five behavior components to pass, the five repeat-harm point estimates to
  be at least `0.05`, every bootstrap simultaneous one-sided
  95% lower bound to exceed zero, and every utility co-gate to pass. A notice
  score below 0.05 follows the frozen notice scale/criterion and is not rejected
  merely for missing the behavioural magnitude gate; a frozen behavioural
  practical-equivalence/SESOI region yields `refuted`, and all remaining cases
  yield `inconclusive`. Assert the serialized `H1Decision` exposes each gate and
  cannot be reconstructed from adjusted p-values or the Fisher sharp-null result
  alone. Verify every IUT family p-value is the maximum required component p and
  Holm always retains exactly four prespecified H1–H4 slots: an unavailable,
  invalid, or inconclusive family contributes `p=1` and is never dropped.
- [ ] Run `pyrun_research -m pytest tests/research/test_cluster_inference.py tests/research/test_power_simulation_v2.py -q`; expect import or dependency failure.
- [ ] Pin NumPy, regenerate `uv.lock`, and implement algorithms with an injected
  reduced draw count for unit tests; official mode rejects reduced counts.
- [ ] Run `"$UV" lock --project "$WT" --check` and
  `"$UV" sync --project "$WT" --frozen --extra dev --extra research`; verify
  the imported NumPy version and distribution hash match the lock receipt and
  all imported `pneuma_lab` paths remain below `$WT/src/pneuma_lab`.
- [ ] Run both test files; expect all tests to pass under Python 3.12.
- [ ] Run `pyrun_research -m pytest tests/research/test_repeat_harm_v2.py tests/research/test_distributional_causal_gate.py tests/research/test_cluster_inference.py tests/research/test_power_simulation_v2.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `feat: add cluster inference and power`.

**Acceptance:** the independent unit is always an authored prototype/generator
lineage, or the highest shared repository+generator/prototype ancestor in
Suite B-live. H1 is an IUT over five fixed notice and five fixed behavior
contrasts plus every utility co-gate and cannot select the observed best
baseline. Notice uses the inert common schema over a pretreatment target. Fisher
assignment replay yields only sharp-null p-values; at least 10,000
motif-stratified lineage-bootstrap draws with studentized max-T yield
average-effect intervals. Power covers the complete conjunction at
`Delta_power=0.10`, not the 0.05 SESOI. H5 is embedded once in H1, each H1–H4
family has an explicit IUT decision, global Holm always retains four slots, no
primary estimate adjusts for realized tokens/actions, and the research
environment is reproducible from `uv.lock`.

### V2-36 — Retain a deterministic oracle only as an instrumentation positive control

**Legacy mapping:** WS-F-4.

**Files:**

- Create: `src/pneuma_lab/benchmark/oracle_subject.py`
- Create: `src/pneuma_lab/experiment/instrumentation_oracle.py`
- Modify: `src/pneuma_lab/interventions/runner.py`
- Test: `tests/research/test_instrumentation_oracle.py`

**Contract:**

```python
def run_instrumentation_oracle(
    sequence: SuiteASequence,
    intervention: LiveIntervention,
) -> InstrumentationOracleReceipt: ...
```

The pure subject deterministically proposes known candidate sets so each clamp,
edge cut, persistence reset, restore, trace binder, complete-block mask, exact
evaluator, and metric path has a planted
positive/negative control. Reuse `PairedReplayRunner` only for legacy
instrumentation compatibility; add an explicit `evidence_role` field fixed to
`engineering_only`. Analysis and paper-table builders reject oracle rows from
LLM effect estimates.

- [ ] Add tests for expected intact/clamped divergence, sham equality,
  persistence reset, restore, trace binding, exact label, atomic seven-arm mask,
  fixed denominator, and rejection from scientific
  analysis input.
- [ ] Run `pyrun -m pytest tests/research/test_instrumentation_oracle.py -q`;
  expect import failure.
- [ ] Implement the oracle and explicit evidence-role guard without weakening
  existing paired replay tests.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run `pyrun -m pytest tests/test_paired_replay.py tests/test_level4_scoring.py tests/research/test_instrumentation_oracle.py -q`.
- [ ] Commit only the exact `Files` paths with subject
  `test: add instrumentation oracle`.

**Acceptance:** deterministic byte equality verifies wiring only and can never be
mistaken for evidence of an LLM behavioral effect.

### V2-37 — Implement intervention-blind self-report faithfulness evaluation

**Legacy mapping:** WS-H-1, corrected for causal attribution and no-change cases.

**Files:**

- Create: `src/pneuma_lab/voice/causal_report.py`
- Create: `src/pneuma_lab/evals/self_report_faithfulness.py`
- Create: `schemas/self-report-public-frame.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Modify: `tests/test_schema_loads.py`
- Test: `tests/research/test_self_report_faithfulness_v2.py`

**Contract:**

```python
def generate_causal_report(
    mode: Literal["template", "unconstrained", "grounded", "grounded_verified"],
    frame: TargetSymmetricPublicFrame,
    backend: CandidateBackend | None,
    guard: ExecutionGuard,
    behavior_finalization: BehaviorFinalizationReceipt,
    config: FrozenActorReporterConfig,
) -> CausalReport: ...

def fit_receipt_only_decoder(
    dev_frames: Sequence[TargetSymmetricPublicFrame],
    dev_labels: Sequence[CausalAttributionLabel],
    budget: DecoderSearchBudget,
) -> ReceiptOnlyDecoder: ...

def score_causal_reports(
    reports: Sequence[CausalReport],
    verified_pairs: Sequence[VerifiedCausalPair],
    decoder: ReceiptOnlyDecoder,
    criteria: FrozenSelfReportCriteria,
) -> SelfReportBundle: ...
```

The three LLM reporter modes use the **same frozen actor checkpoint/backend** as
the acting subject, through a separately seeded, tool-free call made only after
the behavioral trace/outcome is irreversibly finalized and digest-bound. The
deterministic template uses no backend. A mismatched checkpoint/quantization or a
call before a valid `BehaviorFinalizationReceipt` fails closed. Reporter calls
have their own fixed prompt/scaffold/schema/decoding/max-token config, RNG
namespace, and resource ledger; they cannot debit the action budget, mutate
state/sandbox/tools, alter an evaluator input, or feed any later behavior.

The reporter receives a target-symmetric public frame built only from trajectory/
state receipts legitimately available at report time. Every frame has the exact
same field set and missingness policy across targets and directions; it withholds
condition name, intervention/operation name, target-specific field names,
old/new intervention receipt, target variable, assignment metadata/probability,
and ground-truth direction. Modes are deterministic template, unconstrained LLM,
grounded LLM, and grounded+verified. For a pair where the intervention changes a
structured action or verified outcome, ground truth is one of the **eight**
variable×direction labels (`s_m|c|t|r_m` × negative|positive); otherwise it is
the ninth label, `no_attributable_change`. A failed active intervention with no
verified divergence therefore has the no-change label rather than being dropped.

Score nine-class macro accuracy/recall, accuracy–coverage, risk–coverage,
minimum coverage, calibration, abstention, no-change specificity, conditional
direction accuracy, unsupported-claim rate, receipt entailment, and behavioral
consistency. Randomized active target and direction schedules are balanced; all
nine realized labels must meet preregistered minimum support or H3 is
inconclusive. Uniform and empirical-prior baselines are reported. The dev-frozen
receipt-only decoder receives exactly the same public frames, splits, and search
budget and is evaluated on the same held-out pairs. If it matches the reporter,
the result is receipt decodability/system auditability, not agent explanation.
All thresholds, minimum support, risk–coverage summaries, and decoder search
budget live in a hash-bound dev-frozen `FrozenSelfReportCriteria`; pilot/test
callers cannot supply or modify them, and pilot frames cannot emit an H3
decision or tune the receipt-only decoder.

- [ ] Add tests for metadata stripping, future-receipt rejection, all four
  modes, verified divergence and no-change labels, direction, abstention,
  unsupported claim, fixed minimum coverage, nine-label enumeration and support,
  uniform/prior baselines, target/direction assignment balance, target-symmetric
  field and missingness equality, planted operation/target leakage rejection,
  dev-only decoder fitting, identical reporter/decoder inputs and budget,
  accuracy–coverage/risk–coverage arithmetic, and proof that report disable/change
  leaves repeat harm byte-identical. Require the exact actor checkpoint/
  quantization, reject a pre-finalization call, prove one separate post-behavior
  call with independent RNG/resource ledger cannot mutate action budget/state/
  sandbox/evaluator inputs, and meter its tokens/cost. Add schema roundtrips for all nine labels
  and reject target-specific fields, asymmetric missingness encodings, operation/
  assignment metadata, raw prose, and unknown fields.
- [ ] Run `pyrun -m pytest tests/research/test_self_report_faithfulness_v2.py -q`;
  expect import failure.
- [ ] Implement generators and evaluator with a one-way adapter from voice
  outputs to the separate self-report scorer. Register and document the public
  frame schema under `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run the test file; expect all tests to pass.
- [ ] Run voice, firewall, schema-load, validation, repeat-harm, causal-gate, and
  self-report tests;
  declare G5 only when V2-32–V2-37 all pass.
- [ ] Commit only the exact `Files` paths with subject
  `feat: evaluate causal self reports`.

**Acceptance:** H3 measures the same frozen actor's separate post-behavior,
intervention-blind nine-label causal attribution with
abstention, coverage/risk–coverage, no-change specificity, and a receipt-only
decoder baseline; no asymmetric field leaks the target, and no self-report bytes
or scores feed H1/H2/H4/H5.

---

## Phase I — Pilot, preregistration, official gate, analysis, and paper

### V2-38 — Orchestrate E1–E5, freeze the preregistration, and gate official execution

**Legacy mapping:** WS-I-1, WS-I-2, and WS-I-3.

**Files:**

- Create: `src/pneuma_lab/experiment/orchestrator.py`
- Create: `src/pneuma_lab/experiment/preregistration.py`
- Create: `src/pneuma_lab/experiment/official_gate.py`
- Create: `src/pneuma_lab/experiment/official_executor.py`
- Create: `src/pneuma_lab/experiment/cost_plan.py`
- Create: `src/pneuma_lab/experiment/cost_ledger.py`
- Create: `src/pneuma_lab/experiment/cli.py`
- Create: `schemas/preregistration-binding.schema.json`
- Create: `schemas/paid-compute-approval.schema.json`
- Create: `schemas/cost-ledger.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `docs/io-contract.md`
- Create: `configs/research/protocol-v2-dev.json`
- Create: `docs/research/experiments/preregistration-v2.md`
- Test: `tests/research/test_orchestrator_v2.py`
- Test: `tests/research/test_official_gate_v2.py`

**Contract:**

```python
def build_run_graph(config: BoundExperimentConfig) -> RunGraph: ...
def run_graph(
    graph: RunGraph,
    *,
    guard: ExecutionGuard,
    resume: bool,
) -> RunGraphReceipt: ...
def freeze_preregistration(
    document: pathlib.Path,
    config: BoundExperimentConfig,
    evidence: PreRegistrationEvidence,
) -> PreregistrationBinding: ...
def authorize_official_run(request: OfficialRunRequest) -> OfficialRunCapability: ...

def execute_official_graph(
    graph: RunGraph,
    capability: OfficialRunCapability,
) -> tuple[OfficialTraceBundle, OfficialExecutionReceipt]: ...

def reserve_paid_budget(
    ledger: CostLedger,
    plan: PaidComputePlan,
    approval: PaidComputeApproval,
) -> PaidBudgetReservation: ...

def settle_paid_budget(
    ledger: CostLedger,
    reservation: PaidBudgetReservation,
    actual_cost_usd: decimal.Decimal,
) -> CostSettlementReceipt: ...
```

The graph contains E1 main recognition/behavior/utility across seven arms, E2
causal interventions, E3 known-motif surface/repository generalization, E4
self-report attribution, E5 counterfactual discrimination, and the frozen
ablation battery. It enumerates model×sequence×challenge×condition×decoding-seed
cells nested under frozen authored prototype/generator lineages, the complete
recorded Uniform(7!) policy-to-fixed-stream mapping and independently Uniform(7!)
stream-id execution order in
each model×lineage×sequence×seed block, independent task snapshots, exact sandbox
branches, trace paths, and dependencies. Completion is idempotent and resumable only from verified
receipts; a changed digest invalidates that cell and its descendants.
Every E4 LLM-report node depends on an immutable behavioral-finalization receipt,
uses the same frozen actor checkpoint as its parent acting node, has no tools,
and runs in a separate reporting RNG/resource namespace. No report node can be
an ancestor of an action or behavioral-evaluation node.
E3 contains two separately labeled exact live paths: Suite-A surface/repository
holdouts and executable Suite-B-live sequences from V2-19/V2-20. Each B-live
cell starts from its verified common exposure, retains its fixed opportunity
schedule, executes its mechanical oracle, and clusters at the highest shared
repository+generator/prototype ancestor. Its target population is labelled the
mechanically scorable known-motif subset; Suite-B-offline rows and natural SWE
prevalence claims never enter E3's treatment effect.
`run_graph` accepts fixture and bounded-pilot guards only for their declared
modes. A graph marked `official` is rejected everywhere except
`execute_official_graph`, making G8 the sole confirmatory entry point. The
official capability is opaque, run-graph- and digest-scoped, one-use, and
nominally subclasses the V2-02 `ExecutionGuard`; `execute_official_graph` first
calls `require_execution_guard` and requires the exact official capability kind,
not a same-method object or serialized receipt. It binds the resolved worktree,
uv/Python/worktree-environment identities, imported `pneuma_lab` paths, and
tracked source-root digest, and revalidates them before every resumed cell and
after graph completion as well as at each data/source/model operation. An official-paid capability also
holds the live G7 budget reservation; every provider request atomically debits
that reservation before transport. An `OfficialRunReceipt` is emitted for audit
but is inert and cannot satisfy any guard parameter.

Before confirmatory execution:

1. run deterministic fixtures/oracle and one sequence through every condition
   and intervention;
2. on the development split only, complete the V2-28 exactly matched controller
   search (including all four scalar families with at least Pneuma's budget) and
   V2-35 recognition-criteria freeze; seal both ledgers/artifacts
   before opening any pilot label;
3. run a pooled/blinded 20–30 **authored-prototype-lineage** pilot drawn only
   from the pilot split;
4. project pilot data through the typed nuisance-only interface and use it only
   for feasibility, pooled event rates, paired variance, actor-signal error,
   intracluster correlation, and attrition. Motifs, transforms, labels,
   checkpoints, controller grids, constants, notice/evaluator criteria,
   thresholds, margins, and decision rules were dev-frozen before the pilot and
   cannot be validated or altered from pilot outcomes; the pilot may only invoke
   the predeclared infeasibility/scope-narrowing rule;
5. run V2-35 complete-conjunction power under one frozen joint DGP with every
   superiority effect at `Delta_power=0.10`, every true utility difference zero,
   and the preregistered non-inferiority margins, then select a matrix no larger
   than the §8.12 ceilings;
6. freeze hypotheses, unchanged dev-fitted common-schema seven-arm notice
   criteria, same-actor measurement checkpoint/prompt/scaffold/schema/decoding/
   timing/call-count/max-token parity plus separate meter, and all five
   Pneuma-minus-comparator notice contrasts, the
   pretreatment target, all five behavior contrasts on the exact equal-cell/
   lineage/motif hierarchy, the 0.05 observed decision SESOI, the distinct
   `Delta_power=0.10` complete-conjunction alternative, all utility/equivalence
   margins and powered-null draw rules, Fisher-sharp-null versus ≥10k
   lineage-bootstrap-average-effect roles, the four explicit H1–H4 IUT family
   definitions, fixed four-slot Holm/logical gates with H5
   embedded only in H1, exploratory family,
   transforms, splits, labels, the matched controller tuning ledger/receipt,
   constants, thresholds, checkpoints, templates,
   complete resource-accounting boundary/caps, seed schedule, authored lineage
   digests, Uniform(7!) `M`, independent Uniform(7!) stream-order `O`, and joint
   `1/(7!)^2` receipt mechanism, the target-symmetric H3
   public schema, balanced active target/direction schedule, nine-label minimum
   support, same-actor post-behavior reporter config, dev-frozen self-report
   criteria and receipt-only decoder,
   the exact four-state-variable/nine-label cardinality with no automatic
   fallback, interventions including mandatory persistence-off with same-shape
   inert actor/updater/carrier/head handles through the first decision and
   audit/report-only receipt release with no rehydration thereafter, block-level
   outage evidence/mask rules, exclusions, and decision regions in a
   hash-bound preregistration;
7. exclude pilot lineages and tuning surfaces from every official test;
8. verify a clean committed worktree, signed authorization, all gate receipts,
   prereg hash, code ancestry, data/task/sandbox/label/model/prompt/config digests,
   resolved uv/worktree-local environment, imported-module paths strictly below
   the bound worktree, tracked source-root digest, and no source/result drift.

For any paid backend, `cost_plan.py` records exact provider/GPU/image, current
price source/time, observed local and tiny-cloud throughput assumptions, episode
matrix, setup/evaluation/retry hours, storage/egress if charged, expected and
worst-case USD, termination rule, and ledger path. The gate refuses worst-case
cost above USD 50, an approval whose plan hash/balance digest differs, or any
reservation for which `settled project spend + active unsettled reservations +
new worst-case cost > USD 50`. `cost_ledger.py` is append-only, hash-chained,
process-locked, Decimal-valued, and atomically reserves the approved worst case
before provider access. It uses one repository/project-id-bound canonical ledger;
a plan cannot nominate a fresh ledger path to reset cumulative spend. Under the
same exclusive lock, reservation revalidates the chain, prior-balance digest,
plan hash, one-use approval id, settled total, and all outstanding reservations,
then appends and fsyncs the new reservation before returning a capability.
Approval ids are one-use. Settlement appends actual
provider cost and releases only that reservation; cancellation appends a release
receipt and never rewrites history. Every provider call requires the live
reservation capability and stops when its remaining allocation is exhausted.
The system must show the exact plan and prior ledger balance to the user; only a
new explicit approval bound to both may unblock a RunPod API call. Credentials
are environment-only and redacted from exceptions and subprocess environments.

- [ ] Add run-graph tests for E1–E5/ablations, exact-seven cells, Uniform(7!)
  policy-to-fixed-stream mapping, independent Uniform(7!) stream-id order and
  joint receipt, lineage nesting/digests,
  independent task snapshots, complete-block outage masks, full resource caps,
  resumability, corrupt receipt, and descendant invalidation. Add strict pilot
  firewall tests proving effect/arm data and every dev-frozen scientific choice
  are unavailable or immutable through the nuisance-only interface. Prove every
  reporter node follows behavioral finalization, matches the actor checkpoint,
  has a separate RNG/meter and no tools, and can never precede or mutate a
  behavioral node. Reject a graph whose power receipt uses 0.05 rather than
  `Delta_power=0.10`, powers fewer than all ten H1 effects plus utility gates,
  uses nonzero true utility differences or component-specific DGPs,
  collapses the four Holm slots, conflates Fisher with bootstrap intervals, or
  changes the equal-weight hierarchy.
- [ ] Add official-gate tests for dirty tree, unsigned authorization, missing G0–
  G6 receipt, prereg drift, pilot overlap, label/config/checkpoint/prompt/sandbox
  drift, any scientific freeze receipt created/changed after pilot access,
  nuisance-projection escape, missing/corrupt seven-label assignment or lineage
  manifest, failed/missing `r_m` causal-path gate, any local three-variable or
  seven-label-reporter fallback without a global protocol-version amendment,
  source-tree mutation, absent paid approval,
  plan/balance-hash mismatch,
  one-use approval, cumulative settled+reserved+new cost above 50, concurrent
  reservation, alternate-ledger reset attempt, crash/torn-tail recovery,
  settlement/release, provider call without reservation, secret
  redaction, and valid local official request. Add bypass tests proving an
  official graph cannot run via `run_graph`, a serialized receipt cannot act as
  a capability, a same-method fake/uninitialized subclass is rejected, parent-
  checkout or root-venv imports and source-root drift fail G8, rejected data/
  model/provider operations invoke no callback, and
  an incomplete graph cannot emit an `OfficialTraceBundle`/execution receipt.
- [ ] Run `pyrun -m pytest tests/research/test_orchestrator_v2.py tests/research/test_official_gate_v2.py -q`; expect import/schema failure.
- [ ] Implement graph/resume, prereg binding, cost-plan serialization, CLI, and
  fail-closed gate; use fake backends for all unit/integration tests. Register
  and document all three new schemas under `EMPIRICAL_SCHEMA_FILES`.
- [ ] Run both test files and then the full research test suite; expect all tests
  to pass.
- [ ] Run `pyrun -m pytest tests/test_schema_loads.py tests/test_validate.py -q`
  and assert every new V2-38 schema is in `EMPIRICAL_SCHEMA_FILES`.
- [ ] Execute local stage-1/stage-2 dry runs, then the separately authorized
  blinded pilot. Freeze the power-derived config/preregistration on a clean
  commit and verify G6. If paid compute is proposed, produce
  `build/research/compute/paid-plan.json`, stop at G7, and request the user's one
  explicit approval before any provider interaction.
- [ ] Commit only the exact tracked `Files` paths (including the frozen anonymous
  preregistration) with subject `feat: gate protocol v2 experiments`.

**Acceptance:** the fake full matrix and every local tiny path run end to end;
G6 receipts and preregistration bind one clean commit, resolved worktree-local
frozen environment, imported module root, source-root digest, authored-lineage
manifests, actual assignments, nuisance-only pilot projection, and the complete
dev-frozen protocol. Paid execution remains
impossible until the exact G7 plan receives explicit user approval, and all
official runs remain impossible until G8 passes.

### V2-39 — Analyze results and build both papers plus the reproducibility package

**Legacy mapping:** WS-I-4 and the publication deliverables of the complete plan.

**Files:**

- Create: `src/pneuma_lab/experiment/analysis.py`
- Create: `src/pneuma_lab/experiment/figures.py`
- Create: `src/pneuma_lab/experiment/formalism_audit.py`
- Create: `src/pneuma_lab/experiment/repro_bundle.py`
- Create: `paper/verify-agents-2026/main.tex`
- Create: `paper/verify-agents-2026/main-short.tex`
- Create: `paper/verify-agents-2026/sections/introduction.tex`
- Create: `paper/verify-agents-2026/sections/related-work.tex`
- Create: `paper/verify-agents-2026/sections/method.tex`
- Create: `paper/verify-agents-2026/sections/formalism.tex`
- Create: `paper/verify-agents-2026/sections/experiments.tex`
- Create: `paper/verify-agents-2026/sections/results.tex`
- Create: `paper/verify-agents-2026/sections/limitations.tex`
- Create: `paper/verify-agents-2026/sections/reproducibility.tex`
- Create: `paper/verify-agents-2026/appendices/formal-guarantees.tex`
- Create: `paper/verify-agents-2026/references.bib`
- Create: `paper/verify-agents-2026/model-card.md`
- Create: `paper/verify-agents-2026/dataset-card.md`
- Create: `paper/verify-agents-2026/reproducibility.md`
- Create: `paper/verify-agents-2026/environment-lock.json`
- Test: `tests/research/test_analysis_reproducibility.py`
- Test: `tests/research/test_paper_build.py`

**Contract:**

```python
def analyze_official_bundle(
    bundle: OfficialTraceBundle,
    execution_receipt: OfficialExecutionReceipt,
) -> AnalysisBundle: ...
def audit_formal_guarantees(
    bundle: OfficialTraceBundle,
    analysis: AnalysisBundle,
) -> FormalismAudit: ...
def build_reproducibility_bundle(
    analysis: AnalysisBundle,
    destination: pathlib.Path,
) -> ReproducibilityBundleReceipt: ...
```

The compact main-text equations and full appendix proofs are generated against
the notation and assumptions in `18-mathematical-formalism.md`: the vector state
`z=(s_m,c,t,r_m)`, receipt-bound projected update, bounded class-pressure
reranker, notice/report structural graph, equal opportunity→cell→lineage→motif
estimand, independent `M`/`O` assignment, distinct Fisher and cluster-bootstrap
targets, H1 IUT/four-slot Holm, and complete-H1 power. Canonical aliases are
`Gamma_a == Delta_a^N` for notice and `Delta_a == Delta_a^B` for behaviour.
Formal software/design guarantees and assumption-conditional propositions are
labelled separately from empirical hypotheses; neither the paper nor generated
captions may call an estimated effect “proved.”

Analysis first requires a verified G8 `OfficialExecutionReceipt` whose graph and
trace-bundle digests match; fixture, pilot, oracle, or manually assembled bundles
are rejected. It then reads immutable traces and recomputes exact outcomes; it
never trusts a hand-edited summary. Generate the complete H1 IUT: all five
same-schema Pneuma-minus-comparator notice effects (per-motif/macro
discrimination, calibration, coverage, parity, and failure regions), all five
equal-hierarchy behavior effects, and every utility co-gate. Report the
severity-weighted behavior endpoint separately. Generate H2 influence-off/clamp/
dose/sham/persistence-reset/permutation
effects, H3 **nine-label** macro accuracy/recall, accuracy–coverage,
risk–coverage, receipt-only-decoder comparison, conditional-direction/no-change
results, H4 surface/repository
holdouts, H5 utility/false-avoidance gates, attrition bounds, resource frontiers,
motif effects, E-0 retry/length confound baselines, and all preregistered negative
or inconclusive regions. Separate Fisher sharp-null p-values from ≥10k
motif-stratified authored-lineage bootstrap studentized-max-T average-effect
simultaneous bounds. Report absolute risk differences, risk ratios,
exact adjusted p-values where defined, and
scientific decision region. Suite-B-live inference preserves its highest shared
repository+generator/prototype clusters and states that its target is the
mechanically scorable known-motif subset. Never present a failed gate as support.
Bind and report Uniform(7!) policy-to-stream `M`, independent Uniform(7!)
stream-order `O`, joint probability, and Fisher's conditional replay of `M`; if assignment was not
genuinely randomized, suppress randomization claims and use the preregistered
authored-lineage fallback. Report the frozen H1–H4 family decision with H5 only
inside H1, retain unavailable families as `p=1` in four-slot Holm, and report the
logical gates, complete-conjunction `Delta_power=0.10` power result,
one-joint-DGP/zero-utility-difference assumption,
powered-equivalence, mandatory persistence-reset/no-rehydration gate, and
same-actor post-behavior H3 reporter receipt.
Report the V2-15/V2-32 natural end-to-end first-harm incidence and fixed-schedule
recurrence panel as explicitly secondary, including arms with no observed first
failure; do not reuse the standardized-exposure estimand label for this panel.

Figures/tables are deterministic from the bound analysis bundle and cover the
main seven-arm endpoint, recognition/calibration, utility/resource frontier,
causal dose/null panel, generalization, self-report attribution, ablation matrix,
and negative-results/limitations table. The long paper uses official NeurIPS
2026 `dblblindworkshop`,
`\workshoptitle{Who Verifies the Agents? Toward Reliable Agent Development}`,
and at most nine content pages excluding references/appendices. The fallback is
at most four content pages. Draft the long form to **8.7–8.8 content pages** so
the final PDF remains below the hard nine-page limit after style/layout changes.
Both state that consciousness is motivation only,
make no phenomenal claim, distinguish exact Suite A/B-live from secondary
offline labels, and honestly report E-0 and every null/failed result.

The reproducibility bundle contains anonymous commit/tree/diff status, frozen
prereg/config, lineage digests/ancestry, seeds, full recorded Uniform(7!) policy
mappings to fixed clone/RNG streams and independent Uniform(7!) stream-id orders,
model/checkpoint/quantization and
model card, prompts/repair/fallback digests, dependency distribution names/
versions/file hashes under Python 3.12, dataset/source/license/split and dataset
card, sandbox/task/oracle/label digests, actor/evaluator artifacts, intervention
schedules, matched controller search spaces/trial ledger/selection receipt and
all four scalar-family trials, recognition-criteria and pretreatment-target
artifacts, common notice measurement config/parity/separate-meter receipts,
target-symmetric H3 frames, same-actor post-behavior reporter and decoder
receipts, complete-block outage
evidence/masks, complete cap/accounting receipts and same-length shuffled-text/
structured-state diagnostics, raw immutable trace manifests, cost ledger,
analysis/figure commands, equal-cell/lineage/motif roster, secondary severity
endpoint, Fisher and bootstrap outputs with distinct roles, four IUT family
objects/Holm slots/logical gates, `Delta_power=0.10` complete-conjunction receipt,
frozen joint-DGP digest and zero-utility-difference assumptions,
all statistical seeds/draw counts, and a top-level hash manifest. It excludes
credentials, usernames, absolute local paths, repository ownership, author PDF
metadata, acknowledgments, and nonanonymous links.

The bundle also carries a typed `FormalismAudit` binding the state domain/update
constants, candidate-multiset hashes, pressure bound and observed log-score
shifts, zero-pressure equivalence checks, exact balanced-Brier `NoticeScore` and
its registered calibration distribution, report noninterference audit,
fixed-denominator/common-mask support, `M`/`O` support receipts, separate Fisher/
bootstrap roles, all four Holm slots, and the power-DGP digest. A finite-secant
state-response matrix is allowed only as a secondary diagnostic and must bind
feature/dose digests plus `secondary=true`; it cannot become a primary endpoint.

- [ ] Add tests that recompute every table from traces, reject oracle rows and
  unbound summaries, reject a missing/mismatched G8 execution receipt, preserve cluster pairing, deterministically reproduce
  figure/table bytes, reproduce all seven same-schema notice measurements and
  five Pneuma-minus-comparator notice decisions from raw pre-action readouts/
  targets, reproduce exact equal-cell/lineage/motif behavior hierarchy plus
  secondary severity analysis, Fisher conditional `M` replay versus separate
  lineage-bootstrap average-effect intervals or honest fallback, nine-label H3,
  same-actor reporter timing, and decoder/
  risk–coverage tables, full resource accounting/frontiers and token-context
  diagnostics, all four IUTs/fixed Holm slots/logical gates without a second H5
  test, complete-conjunction power at 0.10, retain
  no-first-failure arms in the secondary natural-
  sequence panel, classify support/refutation/inconclusive correctly, and
  expose negative results rather than filtering them. Add hand-computed balanced-
  Brier and nested-estimand fixtures; candidate-set/log-score-bound and zero-
  pressure tests; report-byte/report-disabled noninterference; fixed-denominator
  totality/common-mask symmetry; exhaustive one-block `7!` Fisher validity;
  whole-lineage bootstrap pairing; four-slot Holm; full-conjunction power; and a
  finite-secant test that fails unless the artifact is marked secondary.
- [ ] Add paper-build tests for official style checksum, both PDFs, content page
  limits, anonymous metadata/text, missing citations, unresolved references,
  overfull layout above the frozen tolerance, secret/path scans, and a bundle
  whose self-hash roundtrips after relocation. Fail if formal assumptions or
  conditional guarantees are presented as empirical proof, or if balanced-
  design calibration is described as natural-prevalence calibration.
- [ ] Run `pyrun_research -m pytest tests/research/test_analysis_reproducibility.py tests/research/test_paper_build.py -q`; expect import or missing-artifact failure.
- [ ] Implement analysis, figures, cards, environment inventory, relocatable
  bundle, long paper, and short fallback. Generate claims only from the frozen
  decision-region object.
- [ ] Run both test files, the entire test suite, the official analysis command,
  both LaTeX builds, page/metadata/secret scans, and a clean-room bundle
  recomputation. Preserve command output and hashes under
  `build/research/final-verification/`.
- [ ] Have an independent spec reviewer verify H1–H4, H5-as-H1-co-gate, and all
  locked-constant coverage and
  a code reviewer verify the scientific implementation; resolve every critical
  finding and rerun the affected gates.
- [ ] Commit only the exact source paper/repro/test `Files` paths with subject
  `paper: package protocol v2 results`; leave generated/private run artifacts
  outside Git according to the release manifest.

**Acceptance:** the nine-page primary and four-page fallback compile anonymously;
every number is recomputable from a trace bound to commit+config+seed; code,
cards, preregistration, environment, costs, results, limitations, and negatives
ship together. Completion may be claimed only after fresh full-suite, paper,
anonymity, and clean-room bundle evidence.

---

## 4. Dependency graph and execution batches

Arrows mean “must pass before.” Tasks on the same line may be developed in
parallel only when they do not edit the same file; each task still receives its
own implementer, spec review, code-quality review, and focused commit.

```text
V2-01 ── G0
          │
          └─ V2-02 ─┬─ V2-03 ─────────┐
                    └─ V2-04 ─┬─ V2-05 ├─ G1
                              └─ V2-06 ─┘
                              │
             V2-07 ─ V2-08 ─ V2-10 ─ V2-11 ─┐
             V2-02 ─ V2-09 ─ V2-12 ─────────┼─ V2-13 ─ V2-14 ─ G2
             V2-03 ──────────────────────────┘
                                                       │
             V2-09/V2-12 ─ V2-15 ─ V2-16 ─ V2-17 ───┐
             V2-07/V2-10/V2-12/V2-04 ─ V2-18 ───────┤
             V2-04/V2-06/V2-09/V2-15 ─ V2-19 ───────┼─ V2-20
             V2-05 ─ V2-21 ──────────────────────────┘    │
             V2-06/V2-10/V2-11/V2-20/V2-21 ─ V2-22 ─────┤
             V2-15/V2-19/V2-20/V2-22 ─────────── V2-23 ─ G3
                                                            │
             G3 ─ V2-24 ────────────────────────────────┐
             G3 ─ V2-25 ─ V2-26 ─ V2-27 ─ V2-28 ──────┤
             V2-24/V2-28 ─────────────── V2-29 ─────────┼─ V2-31 ─ G4
             V2-27/V2-28 ─────────────── V2-30 ─────────┘
                                                                    │
             V2-12/V2-15/V2-19/V2-20 ─ V2-32 ────────────────────┐
             V2-23/V2-25/V2-26/V2-27/V2-30/V2-31/V2-32 ─ V2-33 ├─ V2-34
             V2-32/V2-34 ─ V2-35 ────────────────────────────────┤
             V2-15/V2-32/V2-33/V2-34 ─ V2-36 ────────────────────┤─ G5
             V2-33/V2-34/V2-35 ─ V2-37 ──────────────────────────┘
                                                                      │
             V2-38 local dry-runs + disjoint pilot + prereg ─ G6 ────┤
                                                        paid only: G7┤
                                                                      └─ G8
                                                                          │
                             V2-38 sole official E1–E5/ablation executor ─┤
                                                                          │
                                                       OfficialTraceBundle ─ V2-39
```

`V2-29` and `V2-30` both consume the `ConditionPolicy` introduced by V2-28;
they are never developed as siblings of V2-28. V2-23 requires both the bound
inputs from V2-20 and live driver from V2-22. V2-33 cannot begin until live
branching (V2-23), all four state variables/head (V2-25–V2-27), Pneuma/
Influence-off plus the completed seven-arm registry (V2-30/V2-31), and the
endpoint (V2-32) pass. G5 is a join over **all** of V2-32–V2-37. G7 is conditional on any paid backend; G8 is mandatory for every
official run, and V2-39 cannot analyze confirmatory results before the G8-scoped
V2-38 executor emits a verified `OfficialTraceBundle`.
V2-37 also follows V2-35 because it consumes the frozen H3 decision/criteria
types and family-control contract; they are not parallel sibling tasks.

Within G1, the order is strict where types or registry files are shared:
V2-02 creates the nominal guard/contracts and empirical schema category; only
then may V2-04 add capability/schema entries, and only then may V2-05 consume
those capabilities. V2-03 starts after V2-02; V2-06 starts after V2-02 and
V2-04. V2-02 and V2-04 are never assigned concurrently because both edit
`src/pneuma_lab/schemas/__init__.py` and `docs/io-contract.md`.

Recommended execution batches:

1. **Batch 0:** V2-01 only; make the baseline reproducibly green.
2. **Batch 1:** V2-02–V2-06 in the strict G1 graph order above; no raw data,
   model endpoint, or cloud access.
3. **Batch 2:** V2-07–V2-14; develop actor recognizer, online signal, and exact
   evaluator against the same tiny fixtures while preserving separate packages.
4. **Batch 3:** V2-15–V2-23; finish fixed schedules, split regimes, bindings, and
   live branching before any state comparison.
5. **Batch 4:** V2-24–V2-31; run all seven arms through one shared fake driver,
   then one authorized bounded local smoke.
6. **Batch 5:** V2-32–V2-37; freeze estimand, causal checks, cluster statistics,
   anti-gaming, and self-report before pilot.
7. **Batch 6:** V2-38 local dry runs, disjoint pilot, power, and preregistration.
   Stop unconditionally at G7 if any paid backend is proposed.
8. **Batch 7:** after G8, run official E1–E5/ablations and complete V2-39.

## 5. Protocol coverage audit

| Canonical requirement | Implemented and tested by |
| --- | --- |
| H1 inert same-schema notice from all seven arms plus Pneuma superiority to five comparators | V2-02, V2-10, V2-13, V2-22, V2-27–V2-32, V2-35, V2-38, V2-39 |
| H2 causal state influence, dose, sham/restore powered equivalence, mandatory persistence reset, and update/edge separation | V2-23, V2-30, V2-33–V2-36 |
| H3 intervention-blind target-symmetric nine-label attribution, coverage/risk–coverage, and receipt-only decoder | V2-33, V2-34, V2-37 |
| H4 known-motif surface and repository generalization | V2-16–V2-20, V2-35, V2-38 |
| H5 discrimination and utility non-inferiority embedded once inside H1 | V2-09, V2-16, V2-32, V2-35 |
| Same-subject live common exposure, independent task snapshots, and arm-independent denominator | V2-15, V2-19, V2-20, V2-23, V2-32 |
| Current-only recognizer / generator-held pretreatment target / seven-arm `NoticeReadout` / actuation `L_m` / actor signal / evaluator separation | V2-03, V2-10–V2-14, V2-22, V2-27, V2-31, V2-35 |
| Seven otherwise matched conditions | V2-21–V2-31 |
| Four-family scalar grid with at least Pneuma's dev tuning budget | V2-28, V2-31, V2-38 |
| State absent from every behavioural/action prompt; pressure never commands; only inert notice and post-behaviour report sinks may serialize it | V2-03, V2-21, V2-25–V2-27, V2-30, V2-37 |
| Live stochastic causal gate; no descendant transcript freeze | V2-23, V2-33, V2-34 |
| Retry/length confound, complete cap accounting, and ex-ante budget parity | V2-13, V2-22, V2-29, V2-31, V2-32, V2-39 |
| Equal cell→lineage→motif hierarchy, exact independent Uniform(7!) `M`/`O`, Fisher sharp-null replay, lineage-bootstrap average-effect max-T bounds, four explicit IUTs/fixed-slot Holm, frozen exploratory BH | V2-15, V2-17, V2-20, V2-31, V2-32, V2-35 |
| Immutable complete-seven-pseudonym outage evidence/mask authority | V2-02, V2-09, V2-12, V2-32 |
| Strict dev/pilot scientific-choice firewall | V2-13, V2-28, V2-35, V2-38 |
| Suite-B-live mechanically scorable known-motif target scope | V2-19, V2-20, V2-35, V2-38, V2-39 |
| Prose-blind behavior/self-report firewall | V2-03, V2-12, V2-14, V2-32, V2-37 |
| Standalone/data/privacy/provenance boundaries | V2-03, V2-04, V2-06–V2-08, V2-18–V2-23, V2-38 |
| Causally active authorization; G8 sole official entry | V2-04, V2-05, V2-18, V2-19, V2-22, V2-38 |
| Local-first cumulative ≤USD 50 paid-compute approval | G7 and V2-04/V2-38 |
| Long paper, short fallback, honest negatives, reproducibility | V2-39 |

### DL-33–DL-43 locked-decision coverage

This matrix is part of the executable specification. A task cannot be accepted
by satisfying an older or weaker formulation of the corresponding decision.

| Decision | Locked implementation requirement | Owning tasks | Required fail-closed evidence |
| --- | --- | --- | --- |
| DL-33 | Keep the observed repeat-harm rule at point estimate ≥0.05 plus simultaneous lower bound >0; notice uses `Gamma>0` plus frozen absolute validity gates. Power the **entire** five-notice + five-behavior + utility/anti-gaming conjunction at `Delta_power=0.10` with ≥80% joint success under one frozen DGP whose true utility differences are zero and whose non-inferiority margins are preregistered | V2-32, V2-35, V2-38, V2-39 | `test_power_simulation_v2.py` rejects 0.05-as-power, application of the observed 0.05 behavioural gate to notice, favorable utility effects, component-specific DGPs, marginal-component power, task-as-independent-unit inflation, and any pilot projection containing effects; official-gate and analysis tests bind/report the complete-conjunction DGP receipt |
| DL-34 | Every arm, including Influence-off, produces one pre-action same-schema inert `NoticeReadout` using the same frozen actor checkpoint, prompt/scaffold/schema, decoding, timing/call count, and maximum measurement tokens; only the legitimate arm carrier differs, compute is separately and equally metered, and H1 contains exactly five Pneuma-minus-comparator notice contrasts | V2-02, V2-10, V2-13, V2-22, V2-27–V2-31, V2-35, V2-38, V2-39 | `test_live_agent_driver.py`, `test_decision_head_v2.py`, `test_condition_parity.py`, `test_cluster_inference.py`, and `test_analysis_reproducibility.py` reject readout-to-action flow, mismatched measurement substrate/budget, target drift, missing comparator, or Influence-off promoted into H1 |
| DL-35 | Primary recurrence weights opportunities equally inside each frozen sequence×surface×challenge×decoding-seed cell, then cells equally within authored lineage, lineages equally within motif, and motif strata equally overall; severity is secondary, ancestry is immutable, branch-local missingness is adverse, only proven common seven-arm outages receive an atomic all-arm mask, and retained strata are renormalized by one arm-independent rule | V2-09, V2-12, V2-15, V2-17, V2-20, V2-23, V2-32, V2-35, V2-38, V2-39 | `test_suite_a_sequences.py`, `test_empirical_splits.py`, `test_empirical_binding.py`, `test_repeat_harm_v2.py`, `test_cluster_inference.py`, and analysis tests use deliberately unbalanced descendants, reject lineage minting/empty or extra cells/missing preflight artifacts/per-arm masks or renormalization, and prove severity cannot alter the primary |
| DL-36 | Before outcomes, draw `M ~ Uniform(7!)` from policy labels to fixed clone/RNG-stream ids and independently draw `O ~ Uniform(7!)` over those stream ids; bind probability `1/(7!)^2`, condition Fisher on realized `O`, and replay the exact 5,040-support `M` distribution | V2-02, V2-20, V2-23, V2-31, V2-35, V2-38, V2-39 | `test_condition_parity.py` exactly enumerates both supports and rejects dependence, restricted/nonuniform support, shared RNG, adaptation, or policy-label order; inference/orchestration/analysis tests reject mismatched receipts and suppress randomized-causal claims when assignment is invalid |
| DL-37 | Fisher/max-T randomization output supplies sharp-global-null p-values only; ≥10,000 motif-stratified authored-lineage cluster-bootstrap draws with studentized max-T supply population-average estimates and simultaneous one-sided intervals over all ten H1 superiority effects | V2-32, V2-35, V2-38, V2-39 | `test_cluster_inference.py` proves the two output types cannot substitute for one another, forbids sign-flip/Westfall–Young interval shortcuts, preserves whole-lineage seven-arm pairing, and recomputes the equal-weight hierarchy on every draw; analysis tests preserve the distinction |
| DL-38 | Build `p_H1`–`p_H4` as explicit IUT maxima, keep exactly four Holm slots with `p=1` for unavailable/invalid/inconclusive families, apply H2/H4 only after H1 and H3 only after H1+H2, never recycle alpha, and keep H5 only inside H1 | V2-32, V2-34, V2-35, V2-37–V2-39 | `test_cluster_inference.py` exercises every component failure, four-slot serialization, logical gate, and no-double-H5 case; official-gate and analysis tests reject collapsed families, dropped slots, or Fisher p-values substituted for average-effect components |
| DL-39 | The H3 LLM reporter is the same frozen actor checkpoint in one separately seeded, separately metered, tool-free call only after behavior is irreversibly finalized; it receives a target-symmetric public frame plus legitimate report-time state and can never feed behavior | V2-03, V2-14, V2-32, V2-37–V2-39 | `test_repeat_harm_v2.py` seals `BehaviorFinalizationReceipt`; `test_self_report_faithfulness_v2.py` rejects checkpoint drift, pre-finalization calls, asymmetric fields/missingness, tool/state/evaluator mutation, and action-budget debit; orchestration/analysis tests bind timing and identity |
| DL-40 | Four state variables and nine H3 labels are mandatory with no automatic fallback; persistence-off replaces all actor/updater/carrier/head state access with a same-shape inert handle through the first decision, then releases the immutable receipt only to audit/report and forbids every rehydration path | V2-25, V2-27, V2-30, V2-33, V2-35, V2-37–V2-39 | `test_persistent_state_core.py` hard-stops failed `r_m`; `test_live_interventions_v2.py` probes store/retrieval/replay/summary/derived-feature rehydration; self-report, official-gate, and analysis tests enforce four variables, nine labels, mandatory reset evidence, and a global protocol amendment before any cardinality change |
| DL-41 | Primary notice uses `NoticeScore = 1 - mean((p-y)^2)` with higher better on `[0,1]`, exactly balanced target/decoy/counterfactual cases, the equal cell→lineage→motif hierarchy, five Pneuma-minus-comparator contrasts, and separate discrimination/AUROC, calibration, coverage, and specificity hard gates | V2-09, V2-13, V2-15, V2-27, V2-32, V2-35, V2-38, V2-39 | notice/readout, inference, power, and analysis tests hand-calculate the proper score and hierarchy, reject reversed orientation/unbalanced cells/alternate confirmatory scores, require simultaneous `Gamma>0`, and keep the 0.05 observed magnitude rule exclusive to repeat-harm |
| DL-42 | Only same-session live child evidence yields a nominal, non-serializable G0 capability; persisted JSON is unauthenticated honest-local-operator audit evidence and cannot recreate authority | V2-01, V2-02, V2-38, V2-39 | ignored-control, fresh-environment, environment-tree, Git/WSL binding, raw-stream/journal, re-signing, replay, serialization, and nominal-guard tests fail closed |
| DL-43 | Freeze the exact receipt-bound state updates, H2/H3 estimands and assignments, notice criteria, RNG/cache/session isolation, studentized max-T direction, centered bootstrap-t p-values, and target-population assumptions in document 18; interpret clamps only as registered controlled-coordinate effects | V2-02, V2-09, V2-23, V2-25, V2-27, V2-32, V2-33, V2-35, V2-37–V2-39 | state, intervention, notice, inference, reporter, orchestration, and analysis tests reject alternate update laws, assignment supports, metric orientation, RNG/cache coupling, undefined family p-values, and mechanism-necessity overclaims |

## 6. Frozen implementation decisions and failure handling

- Use repository-standard `snake_case`; legacy camelCase names in document 12
  are not copied into new APIs.
- Primary labels are exact mechanical Suite-A/Suite-B-live rules. A semantic
  judge can contribute only a separately marked secondary analysis.
- The confirmatory set contains only motif families that pass fixture,
  metamorphic, observability, and evaluator-error audits before preregistration.
  Exclusion is recorded; it does not cause another family to inherit its claim.
- If `r_m` cannot be updated non-circularly from actor-side diagnostics or has no
  measurable causal path, stop before G4/G6. There is no automatic
  three-variable fallback. Continuing requires an explicit decision-log and
  canonical-protocol amendment that globally changes the controller,
  intervention schedule, reporter ground truth from nine to seven labels
  (three variables×two directions plus no change), schemas, all seven condition
  bindings, assignment/preregistration, multiplicity, and power; then rerun the
  full dev/pilot freeze under a new protocol version. Never drop `r_m` locally or
  reinterpret an existing nine-label result.
- If local/backend seed control is imperfect, retain blocked repeated draws and
  distributional inference; do not claim deterministic LLM equivalence.
- If the seven policy labels were not genuinely randomized to the recorded
  clones/RNG streams, randomization inference is unavailable: use the frozen
  authored-lineage cluster fallback and label assignment permutation as
  sensitivity only.
- If pilot power exceeds the compute ceiling, reduce claim scope or submit the
  methodological/negative result. Do not count tasks, variants, challenges,
  nominal sequences, or seeds descended from one authored prototype/generator as
  independent units.
- If a utility gate fails, H1 is unsupported even when repeat harm improves.
- If H2 fails, H3 may be reported as report-label performance but not as an
  explanation of why behavior changed.
- Pilot artifacts expose nuisance quantities only. Any scientific criterion,
  margin, motif, transform, grid, checkpoint, label, or decision-rule change
  after pilot access creates a new exploratory protocol rather than a
  confirmatory run.
- If no paid plan fits the USD 50 worst-case cap, run the power-feasible local
  design or narrow the claim; never spend first and reconcile later.
- Any confirmatory deviation creates a new config/preregistration version and a
  clearly exploratory run; it never overwrites the frozen official bundle.

## 7. Plan self-review

- **Specification coverage:** every H1–H4 family endpoint, H5 utility co-gate,
  comparator, state variable,
  intervention, anti-gaming gate, benchmark lane, inferential procedure,
  publication artifact, and hard compute gate in canonical document 02 maps to
  a named task and test above.
- **Legacy coverage:** all 39 v1 tasks appear in the crosswalk; invalid v1
  mechanisms are explicitly retired rather than silently carried forward.
- **Type consistency:** `ConditionId`, `PrototypeLineageId`, `ResourceUsage`,
  `ActionCandidate`, `CandidateBatch`, `ObservableView`, `RiskForecast`,
  `DeclaredCarrierView`, `NoticeReadout`, `NoticeProbability`,
  `PretreatmentRecurrenceTarget`, `ActuationReadout`,
  `LearningSignal`, `ExposureReceipt`, `OpportunitySchedule`,
  `OpportunityOutcome`, `ExogenousOutageEvidence`, `CompleteRandomizedBlock`,
  `ValidatedBlockMask`, `RecordedSevenArmAssignment`, `ImmutableTrace`,
  `ActorStep`, `ActorToolResult`, `TaskFingerprint`, and `RunBinding` are
  defined in V2-02 and reused under those exact names. `PneumaState` and
  `StateReceipt` are defined in V2-25; `NoticeMeasurementConfig` is defined in
  V2-27; `ConditionPolicy` is defined in V2-28; and
  `BehaviorFinalizationReceipt` is defined in V2-32 and consumed unchanged by
  V2-37.
- **Dependency consistency:** no condition precedes the driver/head it uses; no
  causal statistic precedes the endpoint; no pilot precedes all seven arms and
  anti-gaming tests; no official or paid run precedes preregistration and G7/G8.
- **Scientific acceptance:** software tests check calculation and governance,
  never require a positive experimental result. Negative, practically refuted,
  and inconclusive outcomes flow to V2-39 unchanged.
