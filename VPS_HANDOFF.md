# VPS Handoff — G-1 self-report gauge study (pneuma-lab)

**Created:** 2026-07-28, migrating from Windows laptop to `vps-41e741fc` (144.217.94.114).
**Handoff branch:** `gauge/g1-self-report-msa`
**Head commit at handoff:** `51a0d4c`
**Remote path:** `/home/ubuntu/code/pneuma-lab`

---

## 1. Objective and acceptance criteria

**Objective.** Establish measurement-system analysis (MSA) as a precondition for publishing an
_elicited_ LLM metric (self-reported confidence, LLM-as-judge score, elicited eval rating),
by (a) running a pre-registered study of the confidence channel, (b) shipping the check as a
one-command tool, and (c) shipping a "gauge card" reporting standard reviewers can ask for.

**Acceptance criteria.**

1. Pre-registration committed before any model call. — **DONE** (`c42507a`, before the run).
2. Study run across wordings, response scales, temperatures, provenances, model families and
   arithmetic precisions, with a placebo arm and a five-remedy battery. — **DONE**, 13,632
   elicitations, 7 stages.
3. Every remedy falsified or supported with its own error bar. — **DONE**, interval-based
   verdicts.
4. Show the failure is not about introspection (same collapse on code the model never wrote),
   extending the result to LLM-as-judge. — **DONE**, G1-H2 confirmed.
5. One-command tool. — **DONE**, `python -m pneuma_lab.gauge {selftest,run,analyze}`.
6. Gauge-card reporting standard + JSON Schema. — **DONE**.
7. Research paper with explicit placeholders where cloud-scale experiments are required. —
   **DONE**, 8 tagged `⟦CLOUD-EXP-n⟧`.

**Important scope correction made during the work.** The original framing was "prove the
channel cannot be made into a measurement instrument by any technique". The data falsified
that. Three of six pre-registered hypotheses were falsified and the surviving claim is
different and larger; see §8. The pre-registration was deliberately **not** edited.

---

## 2. What is complete

### Code — `src/pneuma_lab/gauge/` (new package, stdlib-only)

| File                   | Purpose                                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `stats.py`             | Deterministic stdlib numerics: normal CDF/quantile, bootstrap CI, entropy, AUROC, ECE, kappa, paired t, BH-FDR                                               |
| `cube.py`              | `Response` / `ResponseCube`, byte-stable JSONL IO, facet filtering, balanced-matrix collapse                                                                 |
| `anova.py`             | Crossed two-way random-effects variance components (AIAG ANOVA gauge study)                                                                                  |
| `resolution.py`        | `%GRR`, `ndc`, `ICC`, discrimination index `D`, resolving power, effective support, saturation, selection stability, cross-condition stability, verdict rule |
| `theory.py`            | T1 attenuation ceiling, AUROC ceiling, T3 aggregation asymptote + required-k, T4 MDE                                                                         |
| `remedies.py`          | Five-remedy battery with interval-based verdicts; Platt + isotonic (PAVA)                                                                                    |
| `placebo.py`           | Placebo-dominance ratio, sham contrast, MDE context                                                                                                          |
| `items.py` / `bank.py` | 48-item reference bank, hidden-test execution in a timeout-guarded subprocess                                                                                |
| `elicit.py`            | 8 wordings, 4 scales, 3 arms, 2 provenances, threaded runner behind an injectable `chat` seam                                                                |
| `card.py`              | Gauge-card assembly, schema validation, JSON + Markdown writers                                                                                              |
| `synthetic.py`         | Gauges with known ground truth, for validating the estimator itself                                                                                          |
| `__main__.py`          | `selftest` / `run` / `analyze`; exit 2 on an uninterpretable channel so CI can gate                                                                          |

### Schema, config, fixtures

- `schemas/gauge-card.schema.json` (registered in `src/pneuma_lab/schemas/__init__.py`).
- `configs/g1.json` — the 7-stage fractional design.
- `fixtures/gauge/g1-core-sample.jsonl` — 384 **real** elicitations, committed as the
  regression fixture for T1/T2.

### Scripts

- `scripts/gauge_g1_analysis.py` — runs the pre-registered analysis order, writes cards +
  `summary.json`.
- `scripts/gauge_g1_verify_claims.py` — recomputes all **64** figures quoted in the write-ups
  from the raw cubes; exits non-zero on drift.
- `scripts/gauge_extract_fixture.py` — extracts the committable real-data fixture.

### Docs

- `docs/research/experiments/g1-gauge-preregistration.md` — locked, **never edited after the run**.
- `docs/research/experiments/g1-gauge-results.md` — full results, all sections complete.
- `docs/research/gauge-paper/paper.md` — the working paper, with 8 cloud-experiment placeholders.
- `docs/gauge-card-standard.md` — the reporting standard.
- `docs/superpowers/plans/2026-07-28-self-report-gauge-study.md` — implementation plan.
- `README.md`, `docs/project-status.json`, `src/pneuma_lab/status.py` — subsystem registered as
  `pneuma_gauge_msa`; negative result registered as `g1_self_report_gauge`.

### Tests — 6 new files, all passing

`tests/test_gauge_{core,remedies,items,elicit,card,real_data}.py`.

---

## 3. Branch, commit, working tree

- Branch: `gauge/g1-self-report-msa`, cut from `codex/foundation-training-launch-prep` at `0e8f728`.
- Head: `51a0d4c`.
- Working tree: **clean**. No modified or untracked tracked-path files at handoff.
- 21 commits on the branch, all with descriptive messages.

### Untracked-but-essential data (NOT in git — `build/` is gitignored)

`build/gauge/g1/` — **6.3 MB, the irreplaceable experimental data.** ~75 minutes of local GPU
elicitation. Transferred over SSH separately (see §5). Contents:

| File                            | Rows   | What                                          |
| ------------------------------- | ------ | --------------------------------------------- |
| `cube-core.jsonl`               | 3,072  | 8 wordings x 8 replicates, the primary stage  |
| `cube-scales.jsonl`             | 2,304  | 4 response scales                             |
| `cube-temperature0.jsonl`       | 1,536  | T=0 arm                                       |
| `cube-placebo.jsonl`            | 2,304  | base / sham / treated                         |
| `cube-provenance_self.jsonl`    | 768    | model rates its own code                      |
| `cube-provenance_foreign.jsonl` | 768    | matched foreign arm                           |
| `cube-families.jsonl`           | 2,880  | 5 further models                              |
| `cube.jsonl`                    | 13,632 | merged                                        |
| `self_truth.json`               | 24     | execution labels for model-authored solutions |
| `summary.json`                  | —      | analysis output                               |
| `cards/`                        | 9      | per-cell gauge cards                          |

**This data cannot be regenerated on the VPS** (see §6). Losing it means losing the study.

---

## 4. Commands already run, and their results

| Command                                                                    | Result                                                    |
| -------------------------------------------------------------------------- | --------------------------------------------------------- |
| `python -m pneuma_lab.gauge selftest`                                      | 4/4 synthetic gauges recovered their known verdict        |
| `python -m pneuma_lab.gauge run --config configs/g1.json`                  | exit 0; 13,632 elicitations, 7 stages, ~75 min            |
| `python scripts/gauge_g1_analysis.py --draws 1000`                         | full pre-registered analysis; determinism re-check `True` |
| `python scripts/gauge_g1_verify_claims.py`                                 | **64/64 claims verified**, exit 0                         |
| `python -m pneuma_lab.status --check`                                      | PASS: schema-valid and checkout-coherent                  |
| `python -m pytest tests/ -q`                                               | **2,149 passed, 26 failed, 13 skipped, 1 deselected**     |
| `python -m pytest tests/test_gauge_*.py -q`                                | all gauge tests pass                                      |
| `python -m pneuma_lab.gauge analyze --cube build/gauge/g1/cube-core.jsonl` | exit 0, schema-valid card written                         |

### About the 26 failures — pre-existing, Windows-only, NOT caused by this work

All 26 are in `tests/test_foundation_*` and are the known Windows CRLF shard-digest set
(`shard hash does not match manifest`). Verified directly: `test_foundation_runner.py::
test_run_allocates_only_after_complete_preflight` **fails identically on the base commit
`0e8f728`** in a clean worktree, before any of this work existed.

**They are expected to PASS on Linux**, because the cause is Windows CRLF translation of shard
fixtures. Remote Claude should confirm this — it is the first cheap verification win on the VPS.

---

## 5. Services, ports, environment

- **No services, no ports, no daemons** are part of this project. Nothing to start.
- The study used a **local Ollama** HTTP server at `http://localhost:11434` for elicitation
  only. It is not a project service and is not required for any analysis, test, or the tool.
- **No secrets, no `.env`, no API keys** are used anywhere in this work. Nothing sensitive
  needs transferring.
- Environment variable names that _would_ be needed for the cloud experiments in §7 (none set
  yet, values never to be committed): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
  `GOOGLE_API_KEY` — plus `GAUGE_OLLAMA_HOST` if a local backend is ever pointed elsewhere.

### Windows → Linux translation notes

- Only path construction is `pathlib`-based; no Windows-only paths in the package.
- `items.py` spawns `sys.executable -I -S` for hidden-test execution — portable.
- JSONL writers pin `newline="\n"`, so byte-stability holds across platforms.
- The scratchpad path used during development is not referenced by any committed code.

---

## 6. Capability gap on the VPS — read this before planning

`vps-41e741fc`: 6 vCPU, 11 GB RAM, 84 GB free, Python 3.12.3, **no GPU, no Ollama, no
`nvidia-smi`**.

| Capability                                 | On VPS?                         | Consequence                                                                |
| ------------------------------------------ | ------------------------------- | -------------------------------------------------------------------------- |
| Run the gauge tool, analysis, tests        | **Yes** — stdlib-only, CPU-only | Everything reproduces from the transferred cubes                           |
| Re-run local elicitation against Ollama    | **No**                          | Do not attempt `gauge run` with the local backend; it will fail to connect |
| Cloud-API elicitation (the remaining work) | **Yes**, with keys              | The VPS is a _better_ host for this than the laptop                        |

The remaining work is cloud-experiment work, which needs API access rather than a local GPU,
so the migration removes the real bottleneck. It does mean **the transferred cubes are the only
copy of the local-model evidence** — treat `build/gauge/g1/` as precious.

---

## 7. Remaining work, in execution order

1. **Verify the port.** Run the four verification commands in §9 on Linux and confirm the 26
   Windows-only failures now pass. If any _gauge_ test fails, stop and diagnose before anything
   else.
2. **`⟦CLOUD-EXP-1⟧` frontier-model replication.** Add a cloud backend behind the existing
   injectable `chat` seam in `elicit.py` (the seam already exists — no restructuring needed).
   Run the identical G-1 design against 4–6 frontier models across ≥3 providers, ~25k
   elicitations per model. Pre-specified prediction: `ndc` rises but stays `< 5`; the
   same-question vs rephrased selection-stability gap persists at `T=0`. Falsified if any
   frontier model cards `USABLE`.
3. **`⟦CLOUD-EXP-2⟧` LLM-as-judge benchmarks.** Apply the card to pairwise-preference and
   rubric-grading judge settings with ≥8 wordings and ≥5 replicates per item.
4. **`⟦CLOUD-EXP-4⟧` logit vs elicited head-to-head.** Needs logprob-exposing endpoints. This is
   the constructive counterpart and materially strengthens the paper.
5. **`⟦CLOUD-EXP-3⟧` real repository patches** on a verified SWE benchmark, ≥500 items.
6. Remaining tags `⟦CLOUD-EXP-5..8⟧` are described in `paper.md` §10 with pre-specified
   predictions.
7. **Paper finalization** once 1 and 2 land: the paper currently states its central claim as
   established _for the channels actually measured_, with generalization explicitly pending.

Steps 2–6 are each independently valuable; 2 (`CLOUD-EXP-1`) and 3 (`CLOUD-EXP-2`) are the two
that must land before the central claim can be stated for the field rather than for local
open-weight models.

---

## 8. Findings, decisions, and known risks

### Headline findings (all verified by `gauge_g1_verify_claims.py`)

- Single-shot channel: `ndc = 1`, ICC 0.512, `%GRR` 69.9 → `UNINTERPRETABLE`, while
  fully-averaged AUROC is 0.906 against a reliability-implied ceiling of 0.926.
- **Determinism is not reliability.** At `T=0` repeatability variance is _exactly_ 0 and the
  channel still fails: re-asked queue overlap 0.956 vs **rephrased 0.646**.
- The residual is the `item x wording` **interaction** (24.8% of variance) not the main effect
  (4.2%) — rewording _reorders_ items, which is what a ranking pipeline cannot absorb.
- **Calibration is provably powerless** (T2): Platt changed `D` by exactly `0.00e+00` while
  cutting ECE by 0.3106.
- **Not introspection**: self-authored `D` 0.562 vs foreign `D` 0.567 → transfers to LLM-as-judge.
- **Not placebo-driven**: sham contrast +0.0044 (p=0.72, Π=0.000); treated −0.0876 (p=2.2e-10).
  The channel _ignores irrelevant content and obeys irrelevant form_.
- **Model choice spans three resolution categories** (`ndc` 0→3) while F16 vs Q4 differ by
  0.006. This is the result that makes the standard necessary.

### Pre-registration outcomes

| Hypothesis | Status                                                       |
| ---------- | ------------------------------------------------------------ |
| G1-H1      | partially falsified (`ndc=1` held, `D=0.684 > 0.65` did not) |
| G1-H2      | **confirmed**                                                |
| G1-H3      | **confirmed**                                                |
| G1-H4      | falsified (`T=0` reaches `ndc=2`)                            |
| G1-H5      | partially falsified (wording-averaging reaches ICC 0.900)    |
| G1-H6      | falsified (Π = 0.000, not placebo-dominated)                 |

### Decisions worth preserving

- The pre-registration is **never edited**; deviations are listed in the results doc §10.
- Remedy verdicts are decided by the **interval**, not the point estimate — a CI straddling the
  floor is `INDETERMINATE`, because the point rule would resolve ambiguity in our own favour.
- Non-integral answers on integer scales are rejected as scale non-compliance — conservative
  _against_ the thesis.
- `%GRR` is an SD ratio; variance tables are variance shares. These were conflated once and
  corrected; the audit script now guards it.

### Risks

- `build/gauge/g1/` is the only copy of the local-model evidence and is gitignored. **Back it up
  on the VPS before doing anything else.**
- The bootstrap CIs on ICC are wide (e.g. core ICC 0.512 with CI [0.284, 0.667]) — 47 items is a
  small design for variance-component intervals. `CLOUD-EXP-3` addresses this.
- Eight hand-authored wordings are not a sample from the wording population; `CLOUD-EXP-7`
  addresses this and the paper states the caveat.

---

## 9. First action for remote Claude

Do **not** start cloud experiments yet. First prove the port:

```bash
cd ~/code/pneuma-lab
source /home/ubuntu/.agentsrc
git status && git log --oneline -3

# 1. estimator self-validation, fully offline
python -m pneuma_lab.gauge selftest

# 2. the data survived the transfer, and every quoted number still recomputes
python scripts/gauge_g1_verify_claims.py          # expect: 64/64 claims verified, exit 0

# 3. the repo's own coherence gate
python -m pneuma_lab.status --check               # expect: PASS

# 4. tests — gauge first, then the full suite
python -m pytest tests/test_gauge_core.py tests/test_gauge_remedies.py \
    tests/test_gauge_items.py tests/test_gauge_elicit.py \
    tests/test_gauge_card.py tests/test_gauge_real_data.py -q
python -m pytest tests/ -q                        # the 26 Windows CRLF failures should now PASS
```

Report the four results before proceeding. Then continue at §7 step 2.
