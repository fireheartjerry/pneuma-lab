# VPS Handoff — Pneuma Lab NeurIPS 2026 Research Program

**Prepared:** 2026-07-28
**Repository:** `C:\pneuma-lab` / `https://github.com/fireheartjerry/pneuma-lab.git`
**Working branch:** `codex/neurips-2026-empirical`
**Handoff revision:** `763aa02` (`docs(neurips): harden execution design`)
**Submission target:** NeurIPS 2026 workshop, 2026-08-29 Anywhere on Earth
**Operating model:** the VPS agent may work continuously and autonomously, but must preserve the scientific and spending gates below.

## The mission

> **Full autonomy, full budget: turn our placebo-rooted verification research into the most novel, rigorous NeurIPS submission we can build by 2026-08-29. The root idea stays; everything else is ours to elevate.**

This is not a cloud-compute exercise with a paper taped onto it.

> **This is an all-out transformation of the research program—an attempt to push every dimension of Pneuma toward the frontier simultaneously. Nothing is automatically sacred except the placebo-rooted causal insight; theory, experiments, statistics, architectures, benchmarks, systems, artifacts, writing, figures, and even the framing of the problem itself should be repeatedly rebuilt until each component feels startlingly stronger than what came before. Pursue ideas with real intellectual danger. Design experiments that make skeptical reviewers stop and reconsider what “verification” even means. Build evidence so rigorous that the most exciting claims survive contact with the most hostile interpretation. Make every result legible, every artifact auditable, every figure unforgettable, and every engineering decision worthy of the science it supports. We are not optimizing for a merely competent workshop submission—we are trying to create research with unmistakable frontier energy: technically formidable, conceptually original, empirically undeniable, aesthetically exceptional, and coherent enough to feel like the beginning of an entirely new research direction. Extreme aura is the surface effect; extreme scientific substance is the mechanism.**

The one non-negotiable intellectual core is the placebo question:

> When an agent improves after it receives a verifier message, did the **content** of verification help—or did any message, pause, reset, or extra continuation simply give it another chance?

The target paper is currently titled:

> **The Resampling Null: Did Verification Help, or Did the Agent Just Get Another Try?**

Thirty-second description: this is a placebo-controlled trial for AI-agent verification. We hold an agent's prefix fixed and compare genuinely task-relevant verifier feedback with a token/shape-matched but task-irrelevant sham message, plus no-message resampled continuations. A real-feedback advantage over sham identifies content-specific causal value; a real-feedback advantage over ordinary retries identifies benefit beyond merely being allowed to continue. The retry controls quantify how unstable an apparent “improvement” would have been anyway.

## Read this first: authority and source order

The old root-level [`VPS_HANDOFF.md`](VPS_HANDOFF.md) is a useful historical migration handoff for the earlier G-1 gauge study. **It is not the execution authority for this program and must not be overwritten.**

Read the following completely, in this order, before modifying research code, protocols, claims, or infrastructure:

1. [`AGENTS.md`](AGENTS.md) — repository boundaries, current-status doctrine, commands, and non-negotiable gates.
2. [`docs/project-status.json`](docs/project-status.json) — canonical machine-readable current state; run its checker rather than trusting old prose.
3. [`docs/research/neurips-2026-workshop/31-cloud-execution-brief.md`](docs/research/neurips-2026-workshop/31-cloud-execution-brief.md) — the original current mandate: preserve the causal root, elevate everything else. Its historical branch/compute facts are not newer than this handoff, the logs, or `project-status.json`.
4. [`docs/superpowers/plans/2026-07-28-resampling-null-core.md`](docs/superpowers/plans/2026-07-28-resampling-null-core.md) — the living implementation plan and task boundary.
5. [`docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md`](docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md) — the scientific/technical contract now being hardened.
6. [`docs/research/neurips-2026-workshop/15-decision-log.md`](docs/research/neurips-2026-workshop/15-decision-log.md) — append-only decision history.
7. [`docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`](docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md) — append-only spend and reservation evidence. The verified spendable balance is presently **$0.00** and actual spend is **$0.00**.
8. [`docs/superpowers/specs/2026-07-22-neurips-execution-discovery-design.md`](docs/superpowers/specs/2026-07-22-neurips-execution-discovery-design.md) — older, useful for its external-credit and governance history only; do not let it overwrite the resampling-null thesis.

## Exact state at handoff

### Git and repository state

- Branch: `codex/neurips-2026-empirical`
- Remote tracking branch: `origin/codex/neurips-2026-empirical`
- Pushed head: `763aa02`
- `git status --short` was clean when this document was created.
- The branch was pushed at the user's explicit request. Do not rewrite history, reset, or discard unrelated user work.
- Use `apply_patch` for textual edits. Preserve the repository's four-space Python indentation rule.

### What has actually been implemented

The project is beyond a research memo but is not yet an empirical result. Two foundational implementation tasks are complete and reviewed; the remaining execution is intentionally gated.

| Area | Exact completed state | Evidence |
|---|---|---|
| Resampling-null core records and invariants | Implemented and accepted. | Commits `2050dec`, `5c46043`, `1a991fe`, `82d813b`; focused tests passed; Ruff and mypy checks were clean. |
| Artifact contracts and lineage closure | Implemented and accepted. | Commits `5e57bfe`, `8a075fd`, `12cb141`, `6c830ae`, `16fa07d`; 149 artifact tests passed during implementation. |
| Independent regression check of the new work | Passed. | `python -m pytest tests/resampling_null tests/test_schema_loads.py -q` reported **427 passed** (about 28 seconds); Ruff clean; mypy with `--ignore-missing-imports` clean; project status checker passed. |
| Current scientific-plan hardening | Documented but not yet represented by all planned code. | Commit `763aa02`, including the core plan, resampling-null design, and execution brief. |
| Paid execution / cloud provisioning | Not performed. | Ledger actual spend $0; credits are discussed but not verified as spendable. |
| Foundation training or model promotion | Not performed and not authorized. | Repository governance deliberately leaves authorization pending. |

The full historical suite is **not** a clean green gate: it has five known non-passes caused by absent ignored historical research artifacts. Those failures predate this work and must be reported as environmental/historical missing-artifact failures, never silently hidden and never used to claim the full suite is green.

### The implemented research substrate

The package already contains the stable substrate for data contracts, deterministic replay, internal control/treated/null harnesses, offline advisory estimators, guarded training conversion, and the foundation toolchain. Its relevant live areas include:

- `src/pneuma_lab/schemas/` — schema loading and stable frame contracts.
- `src/pneuma_lab/replay/` — deterministic replay and causal trace bridge.
- `src/pneuma_lab/interventions/` — internal control/treated/null harness.
- `src/pneuma_lab/evals/` — internal-harness evidence scoring, capped at four.
- `src/pneuma_lab/resampling_null/` and `tests/resampling_null/` — the new resampling-null record/artifact foundation.
- `src/pneuma_lab/foundation/` — tooling only; local 2B-to-4B machinery is not trained or promoted.

No component establishes phenomenal consciousness, imports the legacy scorer, or turns Pneuma into an operational 9to5 nervous system. Those are explicit non-claims and non-goals.

## The current scientific contract — precise enough to preserve

The experimental unit is a fixed agent-prefix/eligible-task instance. Before the randomized slot, freeze the common prefix and evaluate a four-slot intervention family:

| Slot | Payload | What it is meant to identify |
|---|---|---|
| `REAL` | Correct task-specific verifier feedback | The intended verification intervention. |
| `SHAM` | Token- and structure-matched feedback drawn from a different lineage and semantically irrelevant to the task | Whether feedback **content**, not message form, caused improvement. |
| `NONE` | No verifier payload, independently continued from the frozen prefix | Ordinary continuation/retry baseline. |
| `RESAMPLE` | Another independent no-payload continuation from the same prefix | Retry instability and a placebo-free resampling null. |

The three scientific comparisons must remain distinct:

1. `REAL − SHAM`: content-specific verification effect.
2. `REAL − mean(NONE, RESAMPLE)`: benefit beyond ordinary continuation opportunity.
3. paired discordance between `NONE` and `RESAMPLE` (including `q0` and `r95`): how often a retry alone changes the apparent outcome.

Do not collapse these into “feedback helps.” The entire contribution is that ordinary agent evaluation often cannot distinguish message semantics from another sample of a stochastic process.

The intended external subjects are SWE-bench-Live MultiLang and an objective `τ³` subset. Current roster status is deliberately conservative:

- SWE C120/C160 are **NO_GO** until base-commit and lineage qualification are auditable.
- `τ³` C120 is feasible only after qualification.
- `τ³` C160 is conditional.
- Qwen3.6-35B-A3B-FP8 is the primary external candidate; BF16 is a separately labeled replication; Qwen3.5-9B is a local simulator, not an external-result substitute.

The earlier G-1 gauge work is valuable provenance and may become a supporting/bridge result, but it is not permission to replace the resampling-null causal contribution with a self-report study.

## Known technical work in progress — preserve these exact facts

The plan has ten tasks. Tasks 1 and 2 are complete. Tasks 3–10 are not complete merely because the documents describe them.

| Task | State at handoff |
|---|---|
| 1. Core records and invariants | Complete. |
| 2. Schemas and canonical IO | Complete. |
| 3. Power-gated schedule and four-slot assignment seals | Designed/hardened; implementation remains. |
| 4. Token-exact REAL/SHAM packet construction | Planned; implementation remains. |
| 5. Snapshot-paired synthetic controller | Planned; implementation remains. |
| 6. Pre-outcome analysis freeze, blinded projection, gated unblinding | Planned; implementation remains. |
| 7. Registered sharp tests, average-effect bounds, verdicts | Designed/hardened; implementation remains. |
| 8. Frozen-grid P0 power/type-I simulator | Designed/hardened; implementation remains. |
| 9. CLI and deterministic synthetic P0 | Planned; implementation remains. |
| 10. Full verification and plan receipt | Planned; implementation remains. |

The following details are intentionally recorded because losing any of them would quietly downgrade the paper's credibility:

### Assignment, roster, and chronology authority

- Separate nominal capabilities: `AssignmentSecretStore`, assignment/unblind handles, commitment and derivation verification. Do not revive the stale `AssignmentKeyProvider` wording/API from older prose.
- The pre-beacon ceremony must bind **all three** independent commitments before the beacon: `roster_local_nonce`, schedule seed, and assignment master key. Binding only a roster nonce leaves post-anchor grinding room for schedule/key selection.
- Use the terminology `roster_local_nonce_commitment_sha256` and `roster-local-nonce` unless a carefully reviewed alternative retains exactly the same binding semantics.
- Preserve the exact roster HMAC ranking, collision fallback, quota consumption, and two-pass `τ³` stratum-normalization/family matching rules in the current design. They are part of the auditable sampling protocol, not an implementation suggestion.
- The preferred public entropy anchor is drand **default mainnet**, not Quicknet: chain hash `8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce`, scheme `pedersen-bls-chained`, group hash `176f93498eac9ca337150b46d21dd58673ea4e3581185f869672e59fa4cb390a`, genesis `1595431050`, period 30 seconds. Round 1 known-answer randomness is `101297f1ca7dc44ef6088d94ad5fb7ba03455dc33d53ddb412bbc4564ed986ec`.
- The pinned verifier route is official `drand-client` 1.4.2, package tar SHA-256 `81de34afba38520b461152bf032cfb5139bb6ced205bf9f50bc8216fdc394eef`, integrity `sha512-jeNJmrVplfgIA/GVndxxJ5mo8y63BS2pEdNhk1siU4pQ+z/BnxsqRnxjH9ag1ip887s12SEgo0MTZPbQNz27NA==`, source commit `ef8c9260294f8699b5e8c27a6b764f8f0d768bea`; extracted bundled CJS SHA-256 `45cb65d533cc7e8527e9bba92df875c066511c3d6286adc7fcb293f0d03c7566`.
- Anchor the precommit with a cryptographically verified Sigstore/cosign bundle that includes an RFC3161 TSA timestamp. Rekor `integratedTime` is mutable and is **never** sufficient chronology by itself. Require bundle v0.3, exactly one RFC3161 timestamp, exactly one Rekor inclusion proof, and use verified TSA `genTime` for chronology.
- The precommitted future drand target must be at least 24 hours after verified TSA time; targetting roughly 48 hours ahead (`+5760` rounds) is preferred. There is no replacement round or nonce after anchoring.
- Cosign v3.1.2 Windows x64 SHA-256 was recorded as `fe4d621d7ae5e900ee62089837c00f996ae9acb82027d573d1d157b6ee875cb2`; its companion Sigstore JSON SHA-256 as `e8d7ea5dd91902b0c23e68a08136d9c43b3573a4974fdbdc89ba5a6890a4ab8b`. Verify actual commands against the installed version before ceremony; do not execute a remembered command as authority.

### Storage, runtime, and artifact authority

- A storage receipt must be provisional until replaced by a verified provider receipt **before** the scientific commitment; after that it becomes immutable evidence.
- A live lease must be bound to the serialized attestation: lease ID, generation, expiry, renewals, and freshness at the end of the held interval. Prose alone is not evidence of continuously held storage.
- Match backend sessions across the intervention slots; record CAS references and publish the ledger last. Keep keyed/unkeyed verification and grammar constraints separate.
- Ambient local Python is only a known-answer-test environment. The observed bundled local runtime was Python 3.12.13 / NumPy 2.3.5 with interpreter SHA-256 `3C6A206B7D93CCA823934A83732220DCFFD413FD1036D9FB82EEBB64599CF7F3`; it is not a portable scientific runtime receipt.
- The intended reproducible authority includes exact lock/container/runtime receipt and KATs. Reject ambient Python 3.11/NumPy 2.4 and the current uv 2.5 from being presented as authoritative execution.
- The planned wheel pin includes `cryptography==49.0.0`; recorded Windows cp311 abi3 wheel SHA-256 is `e5dfc1e64de5677cec922ffa8da89c546d0415bf6efdf081842e5d44c84e1f0e`.

### P0 simulation and inference authority

- Use a phase/method-neutral outcome stream named `power-outcome-philox-v2`; keys derive only from the U64 root, tier, per-tier **outcome population digest**, and per-cell rational DGP-law digest.
- The outcome population digest contains selected rows/groups only, such that C120 remains stable under a C160 extension. Never let a calendar, cost estimate, or caller-provided prefix choose a scientific tier.
- The inference stream is manifest-owned `inference-philox-v1`; remove free seeds from Task 7 APIs and CLI.
- Fix canonical cell IDs, family ordering, 16 bit patterns, NumPy 2.3.5 calls, and task-level—not aggregate-count—expansion. The multiplier must act over the canonical task-level data.
- Production and approximation-validation are separate outcome domains. Gaussian and fallback audits must reuse exactly the raw production outcomes; no splicing audit observations into the 20,000-count authority.
- The selected tier is the highest supported tier passing deterministic tests. Type-I/power authority must scan a fixed global namespace, not caller-selected refs or prefixes.
- Joint Clopper–Pearson coverage needs the stored rational tails: alternative lower `0.025/(K*729)` and null upper `0.025/(K*2187)`, with `K` the number of supported tiers (one or two).
- The paired Gaussian audit selects, per tier, five lowest alternative passes plus five highest cells for each null family (20 per tier); both methods run on the same 2K paired outcomes and classify via CP discordance. A fallback full grid uses the same raw production outcomes.
- Raw timing evidence is operational evidence. Claim determinism only for logical outcomes/counts/decisions—not byte-identical whole artifacts. Fix the clock, timing topology, retry delta, and no-op rejection contract.
- The tiny n=12/24 machinery fixture is non-decisive and non-P0. Keep it distinct from full synthetic C120/C160 P0 fixtures. Do not retain the mathematically invalid assertion that C160 power cannot be lower than C120.

## Hard gates the VPS agent must obey

The user has given broad autonomy and a stated maximum credit pool, but project governance remains stricter where it needs to be. Autonomy means work relentlessly inside the mission; it does not mean inventing evidence, bypassing authorization, or treating pending credits as cash.

1. **No paid or resource-reserving action** until credits are verified and the exact action passes the per-action gate in the current design. “Pending”, “promised”, or dashboard-looking credit is not spendable authorization.
2. **No foundation training, model promotion, or external model download/service** without a positive hash-bound authorization. Qwen3.5-397B is compatibility reference only: never download or serve it.
3. **No 9to5 integration or modification.** Pneuma remains standalone and consumes exported/reference material only.
4. **No real empirical outcome before the pre-outcome protocol is frozen, the selection/assignment seals are valid, and P0 authority is complete.** A fast result produced before those gates is not a result.
5. **No arbitrary retries, parameter fishing, silent roster swaps, or result-dependent stop rules.** Record every decision and every eligible/no-go outcome.
6. **No claim of consciousness, causal verification benefit, generality, or external validity beyond what the finalized experiment identifies.** The contribution can be powerful while remaining precisely scoped.

If a cloud action becomes eligible, the existing planning assumptions are not to be silently “fixed” in code: Azure H100 is `Standard_NC40ads_H100_v5` (not an ND H100 SKU); ACR Basic has no Private Link/service endpoints/network/IP rules; Blob configuration is `StorageV2` + `Standard_LRS` + HNS false + Hot; Azure Batch Spot remains `targetLowPriorityNodes`; Anthropic identifiers are `claude-haiku-4-5-20251001` and `claude-sonnet-5`. Re-verify all live pricing, SKU availability, API terms, and policy before a real action, then log the exact action and expected/actual cost.

## Operating protocol for the VPS

Start with a fresh clone or a clean pull; do not assume this workstation's path, Node/Python toolchain, cached data, credentials, or old VPS identity exists. Record the VPS host/runtime facts in a run receipt before treating it as a reproducibility environment.

```powershell
git fetch origin
git switch codex/neurips-2026-empirical
git pull --ff-only origin codex/neurips-2026-empirical
git status --short
git log --oneline -8
python -m pneuma_lab.status --check
python -m pytest tests/resampling_null tests/test_schema_loads.py -q
git diff --check
```

Then independently compare the checked-out code and documents against this handoff. If anything conflicts, stop treating the conflict as trivia: `project-status.json`, the append-only logs, and the latest reviewed contract beat this snapshot. Document the reconciliation.

For every meaningful local action:

- Keep a concise run receipt: revision, inputs, exact commands, environment digest, outputs, test result, and whether it touched scientific authority.
- Append scientific or architectural decisions to `15-decision-log.md`; append every cloud/credit check, estimate, reservation, and actual charge to `32-cloud-spend-ledger.md`, including $0 actions where they materially affect readiness.
- Recompute/reconcile document hashes when a logged artifact changes. Never invent a provider, timestamp, storage, or execution receipt.
- Keep commits small, reviewable, and push regularly to the working branch. Do not commit secrets, private datasets, credentials, caches, or generated large artifacts.

## Future mandate — intentionally high level

The next agent should use uninterrupted time to make the whole research program formidable, not mechanically execute a stale checklist. Maintain the causal root above, then improve every layer that makes a NeurIPS workshop paper memorable and hard to dismiss:

- Turn the protocol into an adversarially robust causal study with clear estimands, credible counterfactuals, precommitted selection, and falsification paths.
- Build a research artifact that a skeptical reviewer can replay, inspect, and use to locate every decision and every byte of evidence.
- Create empirical evidence with strong baselines, diagnostics, robustness checks, negative controls, and honest uncertainty—not only one headline number.
- Make the paper exceptionally clear: a sharp motivating failure case, an intuitive causal diagram, compact results, well-designed figures, and claims that land exactly where the evidence supports them.
- Treat the spending budget as leverage only after it is real and authorized. Compute should buy decisive evidence or eliminate a major uncertainty, never merely make the project look busy.
- Continually look for the more general insight: verification itself may be confounded by continuation opportunity. If the evidence supports a stronger, cleaner framing or a better experimental apparatus, elevate it—while preserving the registered causal distinction and audit trail.

This is the correct latitude: radical quality and originality in the future, no laundering of future choices into a precommitted past.

## Completion standard

The program is finished only when it has one of two equally respectable outcomes:

1. A reproducible, blinded-then-unblinded empirical result that survives the registered placebo/resampling tests and supports a precisely bounded causal claim; or
2. A fully documented no-go/null result that explains why the causal effect cannot yet be established, with the same artifact quality and without pretending a GPU budget is evidence.

In either case, the deliverable should include the paper source/PDF, complete supplement, artifact/run receipts, reproducibility instructions, exact decision and spend history, tests, and the workshop submission package. “We provisioned cloud GPUs” is not progress. A reviewer being unable to tell whether the agent merely got another try is exactly the problem this project exists to solve.

## Handoff checklist

- [ ] Read all authority documents listed above.
- [ ] Verify branch/head/status and run the status checker plus focused regression suite.
- [ ] Record VPS environment and any divergence from the known local KAT environment.
- [ ] Confirm the ledger still says $0 actual/verified spendable unless independently evidenced otherwise.
- [ ] Reconcile unfinished contract hardening with the current design before implementing an authority-bearing task.
- [ ] Preserve the placebo/resampling causal distinction through every experiment and figure.
- [ ] Work continuously, log honestly, push reviewable commits, and make this paper impossible to confuse with “we sent the agent feedback and it did better.”
