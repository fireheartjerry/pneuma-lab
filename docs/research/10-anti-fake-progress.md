# 10 — Anti-Fake-Progress Rules

Status (2026-07-07): the harness already implements a real anti-fake core — hard Level-4 cap
(`src/pneuma_lab/evals/evidence.py`, `min(level, 4)`), conjunctive L4 gate, null-condition paired
replay (`src/pneuma_lab/interventions/runner.py`), honest-refusal fixtures
(`fixtures/interventions/failing_hypothesis.jsonl`, `restore_null.jsonl`), receipts-based scoring
with hash-derived confabulation risk, the anti-fake-cognition consistency gate
(`src/pneuma_lab/adapters/envelope.py::consistency_errors`), drift-failing golden-fixture CLIs, and
byte-determinism checks replayed twice per fixture — all [VERIFIED], 234/234 tests passing.
Everything past that core — external audit, contamination scans, PII scans over pneuma-data,
doc-drift CI, learned-estimator defenses — is [PLANNED] and specified below as build items. The
single largest current honesty risk is structural, not technical: all Level-4 evidence concerns
ReferencePsyche, a toy co-designed with its own fixtures. (Update 2026-07-07: the intervention
harness, Phase 3.1, the replay bridge, HollowPsyche, and the E-0 experiment are now committed —
`cf014b7`, `d9df2f5` — so the former uncommitted-tree gap is closed; G-12's `--official`
provenance mode remains a build item.)

This document enumerates every way this program could fool itself, and for each failure mode gives
(a) the concrete guardrail and (b) the executable test — either its current location or where it
MUST live. Missing guardrails are numbered G-01…G-12 with acceptance tests. The promotion protocol
at the end is binding on every sibling document in `docs/research/`.

---

## 0. Threat model

The adversary is us. Not a malicious agent — an optimistic research team with three repos
(`C:\pneuma-lab`, `C:\9to5`, `C:\pneuma-data`), an ambitious vocabulary (AGI, RSI, machine
consciousness), and every ordinary incentive to see progress. Each failure mode below is a channel
through which effort can convert into the _appearance_ of capability without the capability.
Standing rule: **architecture is not evidence; only receipts + interventions + nulls are.**

Summary table (G = guarded now, P = partially guarded, U = unguarded / build item):

| #   | Failure mode                                       | Status | Build item |
| --- | -------------------------------------------------- | ------ | ---------- |
| 1   | Fake consciousness / roleplay scored as evidence   | G      | —          |
| 2   | Circular validation of the reference psyche        | P      | G-01       |
| 3   | AGI branding without capability                    | P      | G-02       |
| 4   | RSI theater (loop runs, nothing improves)          | U      | G-03       |
| 5   | Proxy overclaiming                                 | P      | G-04       |
| 6   | Train/eval leakage                                 | U      | G-05       |
| 7   | Benchmark contamination (SWE-bench in pretraining) | U      | G-05       |
| 8   | Test overfitting / golden-fixture gaming           | P      | G-06       |
| 9   | Self-report confabulation                          | G      | —          |
| 10  | Cherry-picked demos                                | P      | G-07       |
| 11  | Evaluator contamination (LLM judge shares priors)  | U      | G-08       |
| 12  | Learned estimator gaming its own gate              | U      | G-09       |
| 13  | Private-trace overfitting                          | U      | G-05/G-09  |
| 14  | Accidental PII exposure                            | P      | G-10       |
| 15  | Goodharting the Level-5 evals                      | U      | G-09/G-11  |
| 16  | Determinism theater (quantized-float hashing)      | P      | G-11       |
| 17  | Uncommitted-code audit gap                         | U      | G-12       |
| 18  | Doc drift rewriting history                        | U      | G-07       |
| 19  | Metric-definition drift between cycles             | U      | G-07       |
| 20  | Integration mirage (claiming pipelines that gap)   | P      | G-02       |
| 21  | Simulation results passing as real-world evidence  | P      | G-04       |

---

## 1. Fake consciousness / roleplay scored as evidence

Failure: prose that _describes_ interiority ("I feel tension rising") gets counted as evidence of
interiority. LLM outputs are trained to produce exactly this prose.

Guardrail [VERIFIED]: `ConsciousnessEvidenceScorer` never promotes on self-report. Confabulation
risk is computed from hash cross-checks between grounded self-reports and the underlying causal
trace — not from prose content — and L4 requires `confab_risk <= 0.2` conjunctively with
intervention passes, null holds, and causal-trace completeness
(`src/pneuma_lab/evals/evidence.py`, gate at the `l4 = (...)` conjunction). The v0.2 envelope
additionally rejects undeclared cognition-bearing frames: `agent_trace`/`memory` frames are
permitted only when a real recorded trajectory exists and counts reconcile
(`src/pneuma_lab/adapters/envelope.py::consistency_errors`).

Executable tests [VERIFIED]:

    python -m pytest tests/test_level4_scoring.py tests/test_evidence_scoring.py -q
    python -m pytest tests/test_openhands_sampled_adapter.py -q   # consistency-gate assertions

`tests/test_level4_scoring.py::test_hard_refusal_when_no_interventions` proves a fully "evidenced"
architecture with eloquent reports still scores ≤ 3 without interventions.

## 2. Circular validation of the reference psyche

Failure: ReferencePsyche (1078-line hand-coded Level-3 mind) passes fixtures co-designed with it,
and the result is quietly read as evidence about minds in general. This is the program's central
epistemic caveat [VERIFIED]: the harness validates the METHODOLOGY (pre-registration, nulls,
receipts, refusal), not any mind.

Guardrail (existing, partial): every published phrase must read "Level 4 of a hand-coded reference
implementation inside its own harness." `tests/test_canonical_demo.py::test_readme_names_the_level5_blockers`
and `::test_docs_page_explains_the_ceiling` already enforce that the README and
`docs/consciousness-levels.md` state the ceiling [VERIFIED].

**G-01 (BUILT 2026-07-07, commit `cf014b7`): adversarial non-mind baseline.**
`src/pneuma_lab/psyche/hollow.py` (`HollowPsyche`, alias `NullPsyche`) emits schema-valid,
causally hollow frames. Result: scores **level 0** with confabulation risk 0.0 — grounding is
cheap, causation is not; the ladder discriminates (ReferencePsyche 3 > Hollow 0 on the same
fixture). Tests: `tests/test_hollow_baseline.py` (6, incl.
`test_hollow_psyche_never_exceeds_level2` and per-family failure assertions). Remaining
sub-item: wire Hollow into the canonical demo summary as a standing negative control [PLANNED].

## 3. AGI branding without capability

Failure: "AGI-grade SWE autonomy" language attaches to systems whose measured capability is a
7B-local-planner pipeline with a deterministic verifier (9to5) [VERIFIED as engineering utility,
not AGI]. The 9to5 RSI substrate is dormant (adapters table = 0 rows, lessons = 2,
conviction.db = 0 rows) [VERIFIED], and there is ZERO Pneuma↔9to5 integration [VERIFIED].

Guardrail: the evidence-grading vocabulary of the grounding regime — every capability claim in
`docs/` carries [VERIFIED]/[PARTIAL]/[PLANNED]/[UNSUPPORTED]. Currently enforced only by review
discipline [PARTIAL].

**G-02 (MISSING): claims linter.** A script that scans `docs/research/*.md` for capability verbs
("achieves", "demonstrates", "is capable of", "AGI", "RSI", "conscious") and fails if the sentence
lacks an evidence tag or cites no artifact path. Must live: `scripts/lint_claims.py` +
`tests/test_claims_lint.py`. Acceptance: seeded fixture doc with an untagged "achieves AGI"
sentence fails the lint; every current research doc passes. The same linter enforces the
integration-mirage rule (mode 20): any sentence describing a pipeline must name the code path, and
the known gaps — no adapter-output→`ReplayHarness` code path, no 9to5→Pneuma exporter [VERIFIED
absent] — are whitelisted only as explicitly-negated statements.

## 4. RSI theater (loop runs, nothing improves)

Failure: a self-improvement loop executes (training jobs scheduled, prompts mutated, journals
written) and cycle counts get reported as progress while no measured capability moves. 9to5 is the
live example: LoRA/DPO trainer has never produced an adapter, `selfmod.py` is a revert-or-keep
gate that modifies nothing itself, `step_journal` = 0 rows [VERIFIED]. Reporting that substrate as
"RSI" would be theater.

Guardrail: none automated today [UNSUPPORTED as a guarded property].

**G-03 (MISSING): improvement-delta gate.** Rule: an RSI cycle may only be counted if a
pre-registered, held-out metric improved between cycle N and N+1 with the same eval battery and
pinned dependencies, and the artifact diff (adapter weights, prompt variant, config) is committed
and hash-logged. Must live: `src/pneuma_lab/evals/improvement_gate.py` +
`tests/test_improvement_gate.py`; the ledger at `build/rsi_ledger.jsonl`. Acceptance:
`test_cycle_without_delta_scores_zero` (loop ran, metric flat ⇒ counted improvement = 0) and
`test_delta_requires_preregistered_metric` (post-hoc metric choice rejected). Until this exists,
the standing sentence is: "9to5's RSI substrate is dormant; zero self-improvement cycles have
occurred" [VERIFIED].

## 5. Proxy overclaiming

Failure: operator pushback read as suffering; tension scalars read as affect; scar counts read as
trauma; `prompt_pushback` columns in swe-chat read as agent preference. Honesty rule 3 of the
grounding regime: proxies are proxies.

Guardrail [PARTIAL]: `docs/consciousness-levels.md` and the evidence scorer's family notes keep
proxy status explicit; the scorer's family status caps a merely-exercised family at 0.6
(`evidence.py`, "A merely-exercised family caps at 0.6").

**G-04 (MISSING): proxy registry.** A machine-readable table mapping every proxy signal to (a) the
construct it does NOT establish and (b) the intervention that would upgrade it. Must live:
`docs/research/proxy-registry.md` + `tests/test_proxy_registry.py` asserting every output-frame
field referenced in research docs appears in the registry. Acceptance: registry covers all 9
indicator families and all `human_nature/` affect signals; the claims linter (G-02) cross-checks
that no doc asserts the right-hand construct from the left-hand proxy. The same registry carries
mode 21: results produced under 9to5 simulation mode (seeded chaos) must be labeled
`evidence_class: simulated` and can never satisfy an autonomy-evidence criterion — enforced by an
assertion that any summary row sourced from simulation mode is excluded from autonomy claims.

## 6. Train/eval leakage

Failure: any learned component (future estimator, future fine-tune) trains on rows that later
appear in its eval split — trivial to do accidentally with pneuma-data's overlapping corpora
(SWE-Gym task pool overlaps OpenHands trajectories by construction; 100% task join in Phase 3.1
[VERIFIED]).

Guardrail: none — no learned components exist yet [VERIFIED absent], so the risk is prospective
but must be gated _before_ the first training run, not after.

**G-05 (MISSING): split manifest + overlap scanner.** Deterministic split assignment by
instance-ID hash, committed as `pneuma-data` manifests; a scanner that computes exact-ID and
near-duplicate (minhash over problem statements) overlap between any declared train and eval sets
and fails CI on nonzero exact overlap. Must live: `scripts/check_split_overlap.py` +
`tests/test_split_overlap.py`. Acceptance: seeded fixture with one leaked instance fails; the
scanner runs over swe-gym/OpenHands joins and publishes the overlap matrix into the run summary.
Private-trace overfitting (mode 13) uses the same machinery: 9to5's `state/experience.db` (3,534
runs [VERIFIED]) is declared a train-only source; any eval task whose repo+issue matches an
experience.db row is excluded, tested by `test_experience_db_rows_excluded_from_eval`.

## 7. Benchmark contamination (SWE-bench in pretraining)

Failure: SWE-bench (22,962 rows local [VERIFIED]) and its variants are in the pretraining sets of
every frontier and most open models, including the qwen2.5-coder:7b planner and any Claude/Gemini
component of 9to5. Resolution rates on these tasks partially measure memorization.

Guardrail: none [UNSUPPORTED as a guarded property].

**G-05 extension (MISSING): contamination protocol.** (a) Report all SWE-bench-family results with
a standing contamination disclaimer; (b) maintain a post-cutoff slice — tasks whose fix commits
postdate the model's training cutoff (swe-mera and swe-evo in `C:\pneuma-data` are candidate
rolling sources [PARTIAL — present, unassessed]) — and report paired contaminated/post-cutoff
numbers; (c) canary-string probe: query the model for verbatim gold patches on a sample; nonzero
verbatim reproduction flags the slice. Must live: `scripts/contamination_probe.py` +
`tests/test_contamination_probe.py`. Acceptance: probe emits per-dataset contamination flags into
the same summary artifact the scorer reads; no headline number may be published without its
post-cutoff pair.

## 8. Test overfitting / golden-fixture gaming

Failure: golden fixtures get regenerated to match broken output ("update the fixture until green"),
converting the drift detector into a rubber stamp.

Guardrail [VERIFIED]: both adapters ship a drift-failing CLI —

    python -m pneuma_lab.adapters.openhands_sampled --emit-fixture
    python -m pneuma_lab.adapters.swe_gym_lite --emit-fixture

— which exits nonzero on any byte difference and requires an explicit `--update-fixture` opt-in
(`openhands_sampled.py`; `swe_gym_lite.py`). Tests:
`tests/test_openhands_sampled_golden.py::test_golden_byte_match`, `::test_emit_fixture_detects_drift`,
and the swe-gym twins in `tests/test_swe_gym_lite_golden.py`.

**G-06 (MISSING): fixture-update audit trail.** `--update-fixture` currently leaves no record of
_why_ the golden changed. Rule: every fixture regeneration must be an isolated commit whose message
cites the schema/adapter change, and a checker fails if a golden fixture and adapter source changed
in different commits with no cross-reference. Must live: `scripts/check_fixture_provenance.py`
(git-log based) + `tests/test_fixture_provenance.py`. Acceptance: a synthetic history with a
fixture-only change and no rationale fails. This is blocked on G-12 (the code must be committed for
git-based provenance to mean anything).

## 9. Self-report confabulation

Failure: the psyche's grounded self-reports narrate causes that the causal trace does not contain.

Guardrail [VERIFIED]: confabulation risk is computed from hash cross-checks between report-cited
state and the recurrent state-hash chain, not from prose; L4 requires grounded reports to _track
the perturbation_ (report content must change under intervention and match the treated trace), and
`roleplay_confabulation_risk` is emitted on every evidence frame (`evidence.py`). Honest-refusal is
fixture-tested: `tests/test_canonical_demo.py::test_failing_hypothesis_reports_level3` and
`::test_restore_null_reports_level3` prove that a failing pre-registered hypothesis and a
restore-only null both score 3, not 4.

Executable test [VERIFIED]:

    python -m pytest tests/test_canonical_demo.py tests/test_level4_scoring.py -q

## 10. Cherry-picked demos

Failure: the published story is built from the best fixture, the best run, or the best of N seeds.

Guardrail [PARTIAL]: the canonical demo (`python -m pneuma_lab.demo`) is all-fixtures-or-fail — it
replays _every_ file in `fixtures/interventions/` plus the passive timeline, consolidates into
`build/canonical/summary.json`, and exits nonzero on any determinism regression;
`tests/test_canonical_demo.py::test_summary_partitions_the_three_buckets` pins the L3/L4/refusal
partition [VERIFIED]. Nothing yet prevents _narrative_ cherry-picking in docs.

**G-07 (MISSING): summary-of-record rule + doc-drift CI.** All numbers in `docs/` and
`docs/research/` must be mechanically derivable from a committed `build/canonical/summary.json`
(or a pneuma-data inventory artifact); a checker extracts numeric claims from docs and diffs them
against the artifacts. Must live: `scripts/check_doc_numbers.py` + `tests/test_doc_numbers.py`.
Acceptance: the known live discrepancies fail on first run — the "8,521,307 verified rows" claim
(mixes JSONL line counts with parsed records; honest total ≈ 5.99M records [VERIFIED]), 9to5's
`TESTING.md` naming 9 golden fixtures of which 0 exist [VERIFIED], and `CAPABILITIES.md` drift in
both directions [VERIFIED]. This same checker is the guardrail for mode 18 (doc drift rewriting
history: docs edited to match new results without a changelog — the checker requires numeric
changes in docs to co-occur with the artifact change) and mode 19 (metric-definition drift: every
reported metric must cite a definition anchor, e.g. `rows(parsed-records)` vs `rows(jsonl-lines)`,
and the anchor string is diffed between cycles so a silent redefinition fails CI).

## 11. Evaluator contamination (LLM judge shares priors/provider with agent)

Failure: a future LLM judge scoring "does this trace exhibit self-modeling?" shares training data,
provider, or system-prompt priors with the agent that produced the trace — inflating agreement.
9to5 already mixes providers (Ollama planner, Claude executor, Gemini adversary) [VERIFIED], but
Pneuma's scorer is deliberately non-LLM today [VERIFIED].

Guardrail (standing rule): the evidence scorer must remain receipts-based; no LLM judge may emit
or influence `evidence_level`. If an LLM is ever used for auxiliary annotation, it is data, not
gate.

**G-08 (MISSING): judge-independence contract.** If any LLM-assisted annotation enters the
pipeline: (a) judge provider must differ from agent provider; (b) judge sees observable frames
only (digests, not prose reports); (c) judge outputs are calibrated against a human-labeled or
rule-labeled anchor set, with agreement reported; (d) a swap test — replacing the judge with a
different-provider judge — must move conclusions by less than the pre-registered tolerance. Must
live: `docs/research/judge-contract.md` + `tests/test_judge_independence.py` (asserts the gate code
path imports no LLM client; today this passes trivially and pins the invariant). Acceptance: the
import-graph assertion is in CI before any judge code lands.

## 12. Learned estimator gaming its own gate

Failure: a learned consciousness-/quality-estimator is trained on traces, then used as the
promotion gate for systems optimized against it — the optimizer finds the estimator's decision
boundary, not the construct. No learned estimators exist today [VERIFIED absent].

**G-09 (MISSING): frozen-gate + holdout-battery rule.** (a) Any learned estimator used in a gate is
frozen and hash-pinned per evaluation cycle; the system under test never receives gradient or
score feedback from the frozen gate during optimization; (b) promotion additionally requires a
non-learned battery (the intervention harness) to agree — the learned estimator can veto but never
solely promote; (c) an adversarial-probe suite searches for trivial inputs that max the estimator
(random frames, replayed high-scoring traces with shuffled content) and fails if found. Must live:
`src/pneuma_lab/evals/gate_freeze.py` + `tests/test_gate_freeze.py`,
`tests/test_estimator_adversarial_probes.py`. Acceptance: shuffled-content probe scores below the
promotion threshold; gate hash recorded in every evidence frame. Modes 13 and 15 route here: an
estimator trained on private traces must exclude those traces' tasks from its gating scope
(G-05 machinery), and any Level-5 eval battery (the five named internal suites are docs-only today
[VERIFIED]) becomes Goodhart bait the day it is implemented — see G-11.

## 13. Private-trace overfitting

Covered by G-05 (split manifests over `state/experience.db` and OpenHands joins) and G-09
(estimator scope exclusion). Standing rule: anything the system trained on, remembered
(experience.db retrieval lanes are wired into planning in 9to5 [VERIFIED]), or was fixture-tuned
against is inadmissible as capability evidence for that same task family.

## 14. Accidental PII exposure

Failure: real names/emails/keys leak into frames, fixtures, or published artifacts. The exposure is
concrete: swe-chat carries non-null `author_email`, `author_name`, `github_username`; the source is
HF-gated (contact-info gate) while the local inventory says "gated=0", which is misleading; NO PII
scan has ever been run over pneuma-data [VERIFIED].

Guardrail [VERIFIED, scope-limited]: Phase 3.1 deterministic redaction —
`src/pneuma_lab/adapters/trajectory.py::redact_text` with machine-checkable `REDACTION_PATTERNS`,
`[REDACTED:<kind>]` substitution, and a ledger that never contains the matched text; 103 emails,
4 AWS keys, 16 assigned secrets redacted from Phase 3.1 task texts. But this covers only text that
flows through the two shipped adapters.

**G-10 (MISSING): corpus-wide PII scan + egress gate.** (a) Run the redaction patterns (plus
name/username detectors) over all of `C:\pneuma-data` and commit a counts-only report; (b) fix the
inventory to state "local copy of a gated source; odc-by; contains contributor PII"; (c) an egress
gate: no file leaves `build/` for publication without passing the PII scanner. Must live:
`scripts/scan_pii.py` + `tests/test_pii_scan.py` (+ `tests/test_egress_gate.py`). Acceptance:
scanner fails loudly on a seeded fixture containing a fake AWS key; swe-chat report exists;
publication tooling refuses unscanned artifacts.

## 15. Goodharting the Level-5 evals

Failure: once the five internal eval suites exist (docs-only today [VERIFIED]; nearest real
analogue is 9to5's `human_nature/` eval tests — phenomenology-honesty, operator-sovereignty,
affect-to-action monotonicity, scar generalization, habit compression [VERIFIED]), development
optimizes against the suite until scores decouple from the constructs.

**G-11 (MISSING): eval-rotation + pre-registration regime.** (a) Every Level-5-relevant criterion
is pre-registered (hypothesis, metric, threshold, null) before the system that will be scored is
built — extending the pattern the intervention harness already uses [VERIFIED for L4]; (b) a
held-back suite variant (parameter-perturbed fixtures, fresh task instances) is generated per
evaluation cycle and never enters the development loop; (c) score divergence between the public and
held-back variants above a pre-registered tolerance voids the cycle. Must live:
`src/pneuma_lab/evals/preregistration.py` + `tests/test_preregistration.py`; registry at
`docs/research/preregistered-hypotheses.md`. Acceptance: attempting to score a hypothesis whose
registration postdates the run's first artifact fails the gate.

## 16. Determinism theater

Failure: "byte-deterministic" claims backed by hashes of quantized state can hide real drift.
Concretely: `src/pneuma_lab/psyche/hashing.py` rounds floats to `_FLOAT_PRECISION = 6` before
hashing [VERIFIED], so state drift below 1e-6 per tick is invisible to the hash chain and could
accumulate across long runs while every hash still matches; similarly
`src/pneuma_lab/interventions/report.py` rounds deltas at 6 decimals with `_EPS = 1e-6`.

Guardrail [PARTIAL]: the demo and golden tests compare _serialized output bytes_, not just hashes
(`tests/test_canonical_demo.py::test_repeated_demo_runs_are_byte_identical`,
`::test_every_fixture_is_byte_deterministic`; `tests/test_determinism.py`) [VERIFIED] — but the
serialized floats are themselves rounded, so the same blind spot applies below the quantum.

**G-11 extension (MISSING): sub-quantum drift probe.** A long-horizon replay (≥ 10^4 ticks) that
accumulates the _unrounded_ state vector in parallel and asserts the max absolute divergence
between two runs is exactly 0.0 at full float64 precision (pure dict arithmetic, no parallel
nondeterminism — this should hold exactly and is worth pinning). Must live:
`tests/test_full_precision_determinism.py`. Acceptance: any nonzero full-precision divergence
fails, and the rounding quantum (1e-6) is documented in every determinism claim as its resolution
limit.

## 17. Uncommitted-code audit gap

Failure: results are published from working-tree code no auditor can check out. Current state:
HEAD = b3102c6 contains only the Phase-3 adapter; the entire intervention harness, demo, and Phase
3.1 adapter are uncommitted [VERIFIED]. Every [VERIFIED] tag above that touches those modules is
verified against the working tree, not against auditable history.

**G-12 (MISSING, highest priority): commit-or-it-didn't-happen rule.** No evidence-level claim,
fixture hash, or summary artifact may be cited in any research doc unless produced from a clean
checkout of a pushed commit, with the commit hash embedded in `build/canonical/summary.json`. Must
live: `src/pneuma_lab/demo.py` extension (embed `git rev-parse HEAD` + dirty-tree flag; refuse
`--official` mode on a dirty tree) + `tests/test_summary_provenance.py`. Acceptance: `--official`
run on a dirty tree exits nonzero; summary without a commit hash is rejected by the claims linter
(G-02). First action under this rule: commit the Phase-2/3.1 working tree.

## 18–19. Doc drift and metric-definition drift

Covered by G-07. Live instances to fix on first enforcement: TESTING.md 0/9 fixtures (9to5),
CAPABILITIES.md two-way drift, dead `monitoring/`/`scheduling/` dirs with orphan `.pyc` (9to5),
row-count definition mix in pneuma-data messaging [VERIFIED all].

## 20. Integration mirage

Failure: describing the three-repo system as a pipeline. Reality: no code path connects adapter
output (PneumaTraces) to `ReplayHarness`; no 9to5→Pneuma exporter exists; 9to5 contains zero
Pneuma vocabulary; the dossier's `pneuma_frame_map`/`training_targets` entries are aspirational
notes no code consumes (except the two shipped adapters) [VERIFIED]. Guardrail: G-02 claims linter
plus the standing sentence pattern "X and Y are not connected; the connection is [PLANNED]."

## 21. Simulation-mode results as autonomy evidence

Failure: 9to5's simulation mode with seeded chaos [VERIFIED] produces clean-looking runs that get
cited as field autonomy. Guardrail: evidence-class labeling under G-04; simulated runs are
methodology evidence only.

---

## Promotion protocol (binding)

1.  **Claim source of record.** An evidence-level claim exists only as a row in a committed
    `build/canonical/summary.json` produced by `python -m pneuma_lab.demo` from a clean pushed
    commit (G-12). Prose never upgrades a level; it can only quote the artifact, with the mandatory
    phrasing for the current ceiling: "Level 4 of a hand-coded reference implementation inside its
    own harness."

2.  **Two-key rule.** Promotion of any claim (a level, a capability tag upgrade to [VERIFIED], a
    headline benchmark number) requires two independent keys:
    - **Key 1 — automated gate [VERIFIED]:** the conjunctive scorer in
      `src/pneuma_lab/evals/evidence.py` (interventions pass + null holds + causal trace complete +
      grounded reports track perturbation + confab risk ≤ 0.2), hard-capped at `min(level, 4)`,
      plus every guardrail test in this document that exists at the time.
    - **Key 2 — external auditor [PLANNED, no path exists today]:** a party outside the authoring
      team re-runs the demo from the committed artifacts on independent hardware and byte-compares
      `summary.json`. Until the external-audit path is built (runbook + pinned environment +
      auditor checklist, to live at `docs/research/audit-runbook.md`), no claim may be tagged
      stronger than "internally audited" — which is exactly the `audit_status` string the scorer
      already emits [VERIFIED].
      Neither key may be held by the same process: the psyche under test never writes evidence frames
      (verifier invariance), and no future learned estimator may solely hold Key 1 (G-09).

3.  **Raising the cap.** The `min(level, 4)` cap may be lifted only by a commit that (a) lands the
    pre-registration regime (G-11), the hollow baseline (G-01), and the frozen-gate rule (G-09);
    (b) is co-signed by Key 2; and (c) updates
    `tests/test_level4_scoring.py::test_level_never_exceeds_4` in the same commit — a cap change
    with a stale cap test is itself a guardrail failure.

4.  **Freeze rule (standing).** Any guardrail failure — a red test named in this document, golden
    fixture drift without provenance, a determinism mismatch, a PII-scan hit, a doc-number diff, a
    dirty-tree official run — immediately freezes all evidence-level and capability claims at their
    last externally-audited value (today: none are externally audited; the freeze floor is
    therefore "internally audited, Level 4 of the reference implementation, methodology-only").
    The freeze is recorded in `docs/research/freeze-ledger.md` with the failing artifact, and is
    lifted only by the commit that fixes the failure plus a full green run of:

         python -m pytest tests/ -q
         python -m pneuma_lab.demo
         python -m pneuma_lab.adapters.openhands_sampled --emit-fixture
         python -m pneuma_lab.adapters.swe_gym_lite --emit-fixture

5.  **Asymmetry rule.** Downgrades are immediate and unilateral (any team member, no second key);
    upgrades always require both keys. Fake progress is expensive to un-publish; real progress can
    wait a cycle.

---

## Build-item index

| ID   | Guardrail                                         | Must live at                                                       | Acceptance test                                                             |
| ---- | ------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| G-01 | Hollow-psyche negative control                    | `src/pneuma_lab/psyche/hollow.py`                                  | `tests/test_hollow_baseline.py::test_hollow_psyche_never_exceeds_level2`    |
| G-02 | Capability-claims linter                          | `scripts/lint_claims.py`                                           | `tests/test_claims_lint.py`                                                 |
| G-03 | RSI improvement-delta gate + ledger               | `src/pneuma_lab/evals/improvement_gate.py`                         | `tests/test_improvement_gate.py::test_cycle_without_delta_scores_zero`      |
| G-04 | Proxy registry + evidence-class labels            | `docs/research/proxy-registry.md`                                  | `tests/test_proxy_registry.py`                                              |
| G-05 | Split manifests + overlap/contamination scan      | `scripts/check_split_overlap.py`, `scripts/contamination_probe.py` | `tests/test_split_overlap.py`, `tests/test_contamination_probe.py`          |
| G-06 | Fixture-update provenance                         | `scripts/check_fixture_provenance.py`                              | `tests/test_fixture_provenance.py`                                          |
| G-07 | Doc-number / metric-definition drift CI           | `scripts/check_doc_numbers.py`                                     | `tests/test_doc_numbers.py`                                                 |
| G-08 | LLM-judge independence contract                   | `docs/research/judge-contract.md`                                  | `tests/test_judge_independence.py`                                          |
| G-09 | Frozen-gate + estimator adversarial probes        | `src/pneuma_lab/evals/gate_freeze.py`                              | `tests/test_gate_freeze.py`, `tests/test_estimator_adversarial_probes.py`   |
| G-10 | Corpus-wide PII scan + egress gate                | `scripts/scan_pii.py`                                              | `tests/test_pii_scan.py`, `tests/test_egress_gate.py`                       |
| G-11 | Pre-registration regime + sub-quantum drift probe | `src/pneuma_lab/evals/preregistration.py`                          | `tests/test_preregistration.py`, `tests/test_full_precision_determinism.py` |
| G-12 | Commit-provenance in official summaries           | `src/pneuma_lab/demo.py` (`--official`)                            | `tests/test_summary_provenance.py`                                          |

Priority order: G-12 (audit gap is live now) → G-02/G-07 (claims and doc drift are live now) →
G-10 (PII exposure is live now) → G-01 → G-05 → the rest as their triggering capabilities land.
