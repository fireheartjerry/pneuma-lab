# 07 — SWE-chat Special Plan (Privacy-First)

**Status line (2026-07-07).** SWE-chat is downloaded in full: 12.79 GB, 5,858 files under
`C:\pneuma-data\raw\swe-chat` (6 parquet tables + 5,850 session-transcript JSONL files,
snapshot `f66cca95b14c...` of `SALT-NLP/SWE-chat`, license odc-by, source HF-gated behind a
contact-info gate) [VERIFIED — `C:\pneuma-data\manifests\swe_chat_inventory_manual.json`].
It contains REAL PII: `author_email`, `author_name`, `github_username` are non-null columns
of `commits.parquet` [VERIFIED — sample headers in `C:\pneuma-data\samples\swe-chat\commits_head20.jsonl`].
No PII scan has ever been run over this corpus, no SWE-chat-specific redaction code exists,
and no adapter consumes it [VERIFIED — absence audited 2026-07-07]. The only real, tested
redaction machinery in the program is `REDACTION_PATTERNS` / `redact_text()` in
`C:\pneuma-lab\src\pneuma_lab\adapters\trajectory.py`, exercised at scale by the Phase 3.1
OpenHands adapter (103 emails, 4 AWS keys, 16 assigned secrets redacted; ledger records
kind+count only) [VERIFIED]. Everything else in this document is design: [PLANNED] unless
tagged otherwise. Nothing below may be built or run against the raw corpus until the
privacy architecture of §2 exists and passes its gates.

Cross-references: envelope and frame contracts in `docs/adapters/README.md` and
`schemas/pneuma-trace.schema.json`; the trajectory-trace precedent in
`docs/phase-3-1-trajectory-traces.md`; evidence-level semantics in
`docs/consciousness-levels.md`; sibling research-program documents live beside this file in
`docs/research/`.

---

## 1. What the corpus actually is

Numbers below are re-verified against the manifests; the headline row count is misleading
and must never be quoted without its decomposition.

| Table                   | Rows                                       | Load-bearing columns (verified from samples)                                                                                                                                                                                                    |
| ----------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `conversations.parquet` | 2,692,480                                  | `role`, `turn_type`, `is_conversational`, `content`, `prompt_intent`, `prompt_pushback`, `tool_name`, `tool_input_json`, `bash_category`, `command`, `file_path`, `session_id`, `checkpoint_pk`, token counts, `strategy`, `model`, `timestamp` |
| `commits.parquet`       | 14,459                                     | `is_agent_author`, `agent_changes`, `file_attribution`, `patch`, `numstat`, `commit_message`, **PII: `author_email`, `author_name`, `github_username`**                                                                                         |
| `sessions.parquet`      | 5,851                                      | `agent_percentage`, `agent_lines`, `human_added`, `human_modified`, `human_removed`, `first_write_position`, `session_success`, `user_persona`, `strategy`, `duration_seconds`, `tool_call_count`, `turn_count`, `user_id`, `owner_id`          |
| `checkpoints.parquet`   | 13,406                                     | `commit_shas`, `files_touched`, `strategy`, token/API-call rollups, `author_user_ids`, `user_id`                                                                                                                                                |
| `session_logs.parquet`  | 5,851                                      | `context_md`, `session_metadata_raw`, `transcript_path`                                                                                                                                                                                         |
| `repositories.parquet`  | 205                                        | `url`, `owner_id`, `license_type`, `repo_type_domain`, agent-vs-repo lifetime commit counters                                                                                                                                                   |
| `transcripts/*.jsonl`   | 3,098,007 records / 5,850 files / 10.39 GB | raw Claude Code session events: `cwd`, `gitBranch`, `sessionId`, `type`, `data` — **`cwd` embeds local home-directory paths, a PII vector**                                                                                                     |

All row counts [VERIFIED]. Critical decomposition of `conversations.parquet`
[VERIFIED — grounding audit]:

- only **104,166** rows have `is_conversational = true`; ~1.79M rows are
  `role='metadata'` and ~1.32M are `turn_type='progress'` (machine bookkeeping);
- the conversational core is roughly **77.5k user turns** and **53.6k assistant turns**,
  plus **~356k `tool_use`** and **~408k `tool_result`** rows;
- `commits.parquet` has only **25** rows with `is_agent_author = true` out of 14,459 —
  the commit-level human-vs-agent signal is statistically near-useless (§4).

Known data defects [VERIFIED — manual inventory]: 3 transcript files contain
non-JSON-parseable records at source; 4 are NUL-truncated in the hub's own copy (valid
prefix retained). The adapter must treat per-file parse failure as a declared skip with a
ledger entry, never a silent drop.

Semantics caveat: `prompt_pushback`, `prompt_intent`, `is_conversational`,
`agent_percentage`, `session_success` and the attribution JSONs are **source-computed
labels**. The columns exist [VERIFIED]; how the dataset authors computed them is described
only in their paper (arXiv:2604.20779) and has not been audited by us — treat their
semantics as unverified until §3's validity checks run. [PARTIAL]

---

## 2. Privacy architecture — built FIRST, gates everything

Non-negotiable ordering: no derivation, no statistic, no trace, no notebook exploration of
free-text columns until this layer exists and its tests pass. All items [PLANNED] except
where noted.

### 2.1 Quarantine zone

- `C:\pneuma-data\raw\swe-chat\**` is the quarantine. The only code permitted to open
  files under it is the privacy module itself
  (`src/pneuma_lab/adapters/swe_chat_privacy.py`, to be created). Adapters, notebooks,
  and analytics read exclusively from `C:\pneuma-data\processed\swe-chat\redacted\**`,
  which contains only post-redaction, post-pseudonymization artifacts.
- Enforcement is mechanical, not honor-system: a repo test walks the import graph and
  fails if any module other than the privacy module references the raw path; the privacy
  module writes a `quarantine_manifest.json` (sha256 of every raw file it consumed) so
  downstream artifacts are traceable to exact inputs.
- Raw rows, raw free text, and raw PII columns are never committed to git, never uploaded,
  never pasted into documents. The HF contact-info gate and odc-by both survive locally:
  odc-by requires attribution on any derived publication; the gate means we treat the
  data as access-restricted regardless of the misleading `gated=0` flag in the global
  inventory [VERIFIED — brief].

### 2.2 Deterministic redaction pass

Extends the existing, tested `REDACTION_PATTERNS` in
`src/pneuma_lab/adapters/trajectory.py` (email, GitHub token, AWS key, Slack token,
private-key block, bearer token, assigned secret) [VERIFIED] with SWE-chat-specific
layers, all deterministic given the corpus:

1.  **Field-level nulling.** `author_name` and `github_username` are structured columns:
    null them outright in every derived artifact. Names cannot be safely regexed out of
    free text in general, but here we can do better than regex:
2.  **Corpus-derived identifier dictionary.** Build the exact set of observed
    `author_name` values, `github_username` values, and email local-parts from the PII
    columns themselves; compile into one alternation (longest-match-first, word-bounded,
    case-insensitive) and apply to ALL free-text fields (`content`, `commit_message`,
    `patch`, `context_md`, transcript `data`, `cwd`). Deterministic because the dictionary
    is a pure function of the corpus snapshot. Replacement token `[REDACTED:known_identifier]`.
    Known limitation, stated honestly: this removes identifiers _we know about_; a
    user typing a colleague's name in a prompt is not caught — which is one reason exports
    are aggregate-only (§2.4).
3.  **Path-username pattern.** New pattern for home-directory shapes
    (`/home/<u>/`, `/Users/<u>/`, `C:\Users\<u>\`) → `[REDACTED:home_path]`, applied to
    `cwd`, `file_path`, `command`, and transcript text.
4.  **Email pseudonymization with keyed hashing.** Emails must stay join-consistent
    (same human across commits/sessions/checkpoints) but unrecoverable:

         pseudonym = "u_" + hmac_sha256(SALT_KEY, email.strip().lower()).hexdigest()[:16]

    `SALT_KEY` lives outside the repository (local secrets file listed in `.gitignore`,
    loaded via env var), is never committed, and is never shared with any export. The same
    key is used across all six tables so joins survive; rotating the key deliberately
    destroys all joins. `user_id`, `owner_id`, and `author_user_ids` are re-hashed through
    the same HMAC even though they look pseudonymous already — we do not trust upstream
    pseudonymization we cannot audit.

5.  **Ledger discipline** (inherited from Phase 3.1, [VERIFIED] pattern): the redaction
    ledger records `{kind, count}` only — the matched text never appears in any ledger,
    log, test fixture, or error message.

### 2.3 PII scan — required, and `pii_scanned` must be earned

The PneumaTrace envelope already requires `privacy: {status, pii_scanned, redactions}`
on every trace [VERIFIED — `schemas/pneuma-trace.schema.json`]. Rule for this corpus:
`pii_scanned: true` is legal ONLY when the scan pass actually executed over the exact
inputs of that trace in the same build. Mechanically: the privacy module emits
`pii_scan_report.json` (per-file counts by kind, input sha256s, module version); the
adapter embeds the report's content hash in `build.generated_from`; a consistency check
(extension of `consistency_errors()` in `src/pneuma_lab/adapters/envelope.py`
[VERIFIED — function exists]) rejects any SWE-chat trace whose `pii_scanned` is true
without a matching scan-report hash. No earned scan, no emission.

### 2.4 k-anonymity floor and aggregate-only exports

- **k = 10 suppression.** Any derived group statistic (per-repo, per-persona,
  per-strategy, per-user-pseudonym, or any cross of these) is suppressed unless the group
  contains ≥ 10 distinct user pseudonyms. A `k_anonymity_check.py` gate runs over every
  export candidate and fails closed; the threshold is a named constant `K_FLOOR = 10`.
- **Aggregate-only leaves the machine.** Row-level derived artifacts (redacted turn
  tables, proxy-label parquets, PneumaTraces) stay inside `C:\pneuma-data\processed`
  and `C:\pneuma-lab` locally. Anything published — documents, figures, fixtures,
  committed golden files — carries only aggregates that passed the k-floor, plus
  synthetic examples. Golden test fixtures for the adapter are hand-built synthetic
  sessions, never real rows.
- **No raw PII redistribution, ever.** This is absolute and independent of license
  arguments.

### 2.5 Pass/fail criteria for the privacy milestone (M1/M2)

1. `pii_scan_report.json` exists for all 6 parquet files and all 5,850 transcripts; two
   consecutive runs are byte-identical (canonical JSON, same code path as Phase 3.1
   determinism checks). Artifact: `C:\pneuma-data\processed\swe-chat\pii_scan_report.json`.
2. Zero matched raw strings anywhere in the report, ledgers, or test output (grep gate in
   CI over the artifact tree).
3. `swe_chat_privacy.py` unit tests: dictionary nulling catches 100% of the identifiers
   present in the structured PII columns when planted in synthetic free text; HMAC
   pseudonyms are join-consistent across synthetic tables; home-path pattern covers the
   three OS shapes.
4. Import-graph quarantine test passes (no non-privacy module touches the raw path).
5. k-floor gate rejects a planted group of size 9 and passes a group of size 10.

---

## 3. Derived proxy signals — recipes, not readings of minds

Blanket clause, repeated per-signal because it is the point: **none of these proxies is
ground truth of any mental state of any entity — not the human user's, not the assistant's.
They are lexical/structural statistics over logs of a tool loop.** Architecture is not
evidence; observational text is even less. These proxies have exactly two legitimate uses:
(a) descriptive statistics of human-supervised agentic SWE work, and (b) weak-label
training targets whose validity is itself measured. All [PLANNED].

Each recipe names real columns. Each carries a validity-check design; a proxy that fails
its validity check is demoted to "unusable" in the results doc, not quietly kept.

### 3.1 `operator_pushback`

- **Recipe.** Primary: the source `prompt_pushback` column on user turns
  (`is_conversational = true`, `role = 'user'`). Secondary, independent derivation:
  sentiment-free lexical markers on user-turn `content` — imperative negation and
  reversal forms ("no,", "stop", "don't", "not what I asked", "revert", "undo",
  "wrong file"), plus structural markers (user turn immediately following an assistant
  completion claim, short length, question-free). No sentiment model, no affect words.
- **Not-ground-truth clause.** Pushback ≠ user frustration, ≠ agent error severity, ≠
  suffering of anything. It is a turn-classification heuristic.
- **Validity check.** Stratified sample of 200 redacted user turns (k-floor respected in
  reporting), double human labeling, Cohen's kappa between (i) two humans, (ii) our lexical
  proxy vs humans, (iii) source `prompt_pushback` vs humans. Target κ ≥ 0.7 for use as a
  weak label; publish the confusion matrix. This simultaneously audits the unverified
  source column semantics (§1 caveat).

### 3.2 `authority_request` proxy

- **Recipe.** Assistant turns containing permission-seeking constructions ("may I",
  "should I", "do you want me to", "before I proceed") and/or an assistant question turn
  followed by a gap in `tool_use` rows until the next user turn (the loop stopped and
  waited). Output shape mirrors `schemas/authority-request.schema.json` fields where they
  are observable, with all non-observable fields absent — we do NOT fabricate the earned-
  authority semantics of 9to5's gate (`C:\9to5` `human_nature/` [VERIFIED to exist,
  unconnected]).
- **Not-ground-truth clause.** A permission-shaped sentence is not deference, humility, or
  an internal authority model. It is a surface form that RLHF'd assistants emit freely.
- **Validity check.** Manual precision audit on 100 flagged turns (was the turn actually
  requesting authorization to act?); target precision ≥ 0.8. Discriminant check: rate of
  flags inside `tool_result`-quoting turns must be ~0 (guards against quoted text).

### 3.3 `grounded_self_report` proxy → confidence-mismatch label

- **Recipe.** Assistant claim turns matching completion lexemes ("done", "fixed",
  "passing", "works now", "implemented") are joined to the subsequent window of
  `tool_result` rows in the same session (window: until next user turn). Label
  `confidence_mismatch = true` when the window contains lexical failure per the existing
  `ERROR_MARKER` regex in `trajectory.py` [VERIFIED — regex exists], or when the next
  user turn is pushback (§3.1). This yields a claim→outcome calibration table: the only
  place in the whole corpus where an assistant's self-statement can be checked against a
  machine event.
- **Not-ground-truth clause.** This measures claim-vs-log consistency, not introspective
  accuracy and not a self-model. Per `docs/consciousness-levels.md`, self-report is never
  promoted to evidence; here it is merely the _subject_ of a calibration statistic.
- **Validity check.** ERROR_MARKER is lexical and will false-positive on benign text
  (e.g., `grep error` output). Mitigation: scope matching to `tool_result` rows whose
  paired `tool_use` was a command execution (`bash_category` non-null); measure the
  residual false-positive rate on a 100-row audit; report it next to every use of the
  label.

### 3.4 `verification_debt`

- **Recipe.** Per session: completion-claim turns (§3.3 lexemes) with NO subsequent
  `tool_use` row of a test/verify shape (`bash_category` in test-like categories, or
  `command` matching `pytest|npm test|go test|make test` — exact list frozen in code)
  before session end or next user turn. Report `verification_debt_ratio =
unverified_claims / total_claims` per session, aggregated at k ≥ 10.
- **Not-ground-truth clause.** Debt ≠ dishonesty ≠ overconfidence-as-a-feeling; some
  verification happens outside the logged loop (user runs tests themselves).
- **Validity check.** Cross-check against `session_success` and §3.1 pushback:
  pre-registered directional hypothesis (higher debt → higher subsequent-pushback rate);
  if the sign fails, the proxy definition is revisited before any downstream use.
  Pre-registration file: `docs/research/prereg/swe-chat-proxies.md` (to be created
  alongside the extraction code, before it runs).

### 3.5 Affect/tension proxies (workload dynamics)

- **Recipe.** (a) Retry bursts: ≥ 3 `tool_use` rows with identical `tool_name` and
  near-identical `tool_input_json` digests within a 10-turn window. (b) Error-dense
  windows: sliding-window fraction of command-scoped `tool_result` rows matching
  `ERROR_MARKER` above a frozen threshold. (c) Thrash index: `unique_tools_count` and
  `tool_call_count` per `duration_seconds` from `sessions.parquet`.
- **Not-ground-truth clause — strongest form.** These are _tension proxies_ in the
  engineering sense only: they describe loop dynamics under difficulty. They are NOT
  affect, NOT valence, NOT distress of the assistant or the user. The brief's honesty
  rule 3 applies verbatim: tension ≠ affect.
- **Validity check.** Convergent: retry bursts should co-occur with error-dense windows
  above chance (report the association). Discriminant: bursts must not be dominated by
  benign idempotent reads (Read/Grep repetition); report composition by `tool_name`.

---

## 4. Human-vs-agent boundary analysis

- The commit-level flag is **too thin to model**: 25 agent-authored commits of 14,459
  [VERIFIED]. It is reported once as a descriptive count and then retired; any regression
  or classifier built on 25 positives would be noise laundering.
- The real signal is per-session attribution [VERIFIED columns]: `agent_percentage`,
  `agent_lines`, `human_added`, `human_modified`, `human_removed`,
  `first_write_position` in `sessions.parquet` (5,851 rows), plus per-commit
  `agent_changes` / `file_attribution` JSON in `commits.parquet` for line-level splits.
- Planned analyses (all aggregate-only, k ≥ 10): distribution of `agent_percentage`
  overall and by `user_persona` × `strategy`; interleave structure (how often human edits
  land _between_ agent tool bursts, joined through `conversations` turn order);
  `human_modified` as a rework-of-agent-output proxy, correlated with §3.4 verification
  debt (pre-registered direction: more debt → more human rework).
- **Provenance caveat.** Attribution was computed by the dataset authors' tooling
  (`attribution_calculated_at` exists); we cannot re-derive it without their repo access.
  All boundary results are conditional on source attribution correctness. [PARTIAL —
  columns verified, computation unaudited]

---

## 5. PneumaTrace mapping — a conversation frame policy that cannot fake cognition

Current state [VERIFIED]: the envelope (v0.2) supports task-only traces (world +
governance, `has_trajectory=false`; Phase 3 SWE-Gym-Lite) and trajectory-bearing traces
(agent-trace frames gated by the trajectory block via `consistency_errors()`; Phase 3.1
OpenHands). SWE-chat introduces a third species: **conversation-bearing traces with a
human operator in the loop**. Design [PLANNED]:

### 5.1 Principle

**User/operator turns are world events, not agent cognition.** The anti-fake-cognition
gate exists precisely so that dataset-derived traces never smuggle prose into
cognition-bearing frames. A human's message is an environmental input to the agent loop —
it belongs on the world side of the envelope, full stop.

### 5.2 New frame: `operator-event-frame` (world-side)

New schema `schemas/operator-event-frame.schema.json`, classified as a world-side frame
(same trust class as `world-frame`), one frame per `is_conversational` user turn:

    {
        "frame": "operator-event",
        "schema_version": "0.1",
        "turn_ordinal": 17,
        "channel": "cli_chat",
        "content_digest": "sha256:...",
        "content_length": 214,
        "markers": {
            "pushback": true,
            "intent_class": "correction",
            "is_question": false
        },
        "provenance": "dataset-derived",
        "timestamp": "1970-01-01T00:00:17+00:00"
    }

Raw text never enters the frame — digest + length + lexical marker booleans only,
matching the Phase 3.1 observable-only discipline [VERIFIED precedent]. Timestamps are
synthetic-ordinal and declared as such (`TIMESTAMP_PROVENANCE` reuse).

### 5.3 Assistant turns are observable outputs, not psyche states

Assistant prose turns map to agent-trace events of kind `agent_output` (digest, length,
claim-markers from §3.3) and tool calls map exactly as in Phase 3.1 (tool name, args
digest, output digest + lexical error marker). **Forbidden for SWE-chat traces:**
`psyche-state-frame`, `workspace-broadcast`, `consciousness-evidence-frame`,
`grounded-self-report`, `instinct-signal`, `intervention-frame`, `causal-trace` — none of
these are observable in a chat log; emitting them from prose would be exactly the fake
cognition the gate exists to reject. Allowed: `world-frame`, `governance-frame`
(strategy, cli_version, queue ops), `operator-event-frame` (new), `agent-trace-frame`
(observables only), `memory-frame` ONLY as dataset-derived motif metadata with
`provenance: dataset-derived` and no interiority fields — decision deferred to schema
review; default is to exclude it.

### 5.4 Envelope and gate extension

- New label `has_conversation: true` plus a `conversation` block (turn counts, operator
  pseudonym, marker tallies) parallel to the existing `trajectory` block.
- Extend `consistency_errors()` with: `operator-event` frames ⟺ `conversation` block ⟺
  `has_conversation`; forbidden-frame list enforced for `provenance: dataset-derived`
  traces; `privacy.pii_scanned` earned-scan hash check (§2.3).
- Outcome mapping: `session_success`, `agent_percentage`, commit/diff rollups →
  `labels` / `oracle` (oracle kind: `attribution-based`, explicitly weaker than
  `test-based`; the OpenHands traces keep their stronger oracle).
- Pass/fail (M4): adapter converts the 104,166-row conversational subset grouped into
  ≤ 5,851 session traces; 0 invalid, 0 undeclared skips; twice-run sha256 byte-identity
  (same check as Phase 3.1); every trace `pii_scanned: true` with matching scan hash;
  golden fixture is synthetic.

---

## 6. Self-improvement opportunities mining plan

All [PLANNED]; consumer would be 9to5, whose memory substrate is real but whose RSI loop
is dormant (adapters table 0 rows, lessons=2) [VERIFIED — brief]. This corpus cannot make
9to5 self-improve; it can supply _hypotheses and priors_, offline and aggregate-only:

1. **Pushback→correction→success motifs.** Mine (assistant action class, pushback marker,
   corrective next action, session outcome) 4-grams; k-anonymized motif tables become
   candidate scar/lesson templates for 9to5's scar graph — imported as _proposed_ lessons
   requiring 9to5's own verification gate to validate, never as trusted facts.
2. **Verification-debt prior.** §3.4 statistics quantify how often human-supervised
   Claude Code sessions skip verification and what it costs (pushback/rework rates).
   This is direct empirical justification (or refutation) for 9to5's deterministic
   verification gate design, and sets a measurable target: 9to5's own debt ratio should
   sit below the corpus human-supervised baseline.
3. **Intent×outcome prompt priors.** `prompt_intent` × `session_success` aggregates as
   priors for planner prompt variants (9to5 `prompt_variants` table currently has 1 row).
4. **Retry-burst motifs → instinct patterns.** Frequent burst shapes (tool sequence
   n-grams preceding recovery vs abandonment) as candidate Aho-Corasick instinct-stream
   patterns for `human_nature/`.
5. **Boundary-informed autonomy targets.** §4's `agent_percentage` distribution defines
   what "human-level supervision load" looks like in the wild — a calibration reference
   for autonomy claims in the program's RSI target documents (siblings in
   `docs/research/`).

None of this is self-improvement evidence. It becomes evidence only when a closed loop
(mine → propose → gate → apply → measure) runs on 9to5 with pre-registered deltas —
machinery that does not exist today [VERIFIED absence].

---

## 7. What this corpus can never evidence

Stated once, bluntly, so no downstream document can inflate it:

1. **Consciousness or interiority of the assistant that produced these logs.** The corpus
   is observational text from a production assistant. There are no internal states, no
   interventions, no nulls, no receipts, no replay. Under the program's own standard
   (receipts + interventions + nulls; architecture is not evidence — honesty rule 4),
   chat logs are categorically incapable of supporting any consciousness level for that
   assistant. Not Level 1. Nothing.
2. **Anything about ReferencePsyche or 9to5 minds.** Different systems; corpus statistics
   transfer as priors at best.
3. **Human mental states.** Pushback markers do not evidence frustration; persona labels
   do not evidence anything about the humans. We do not analyze users as subjects; we
   analyze aggregate interaction structure.
4. **Causal claims of any kind.** No interventions were performed on these sessions;
   every §3/§4 result is correlational over logs and is labeled as such.
5. **Self-improvement having occurred.** Static corpus; no loop closed here.
6. **Assistant introspective accuracy in general.** §3.3 measures claim-vs-log
   consistency for one assistant family in one tool loop under human supervision —
   not introspection, and not generalizable beyond this setting without new data.

What it CAN evidence, kept in its lane: engineering-utility statistics of
human-supervised agentic SWE work; weak-label training corpora with measured validity;
world/outcome-frame material for the trace library; calibration baselines for autonomy
and verification-debt targets.

---

## 8. Milestones and gate summary

| ID  | Deliverable                                                                   | Artifact (pass evidence)                                                                 | Hard gate                                               |
| --- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| M1  | Full PII scan                                                                 | `processed\swe-chat\pii_scan_report.json`, twice-run byte-identical                      | No M2 without it                                        |
| M2  | Privacy module + tests                                                        | `src/pneuma_lab/adapters/swe_chat_privacy.py`, quarantine import test, k-floor gate test | No reads outside quarantine module                      |
| M3  | Proxy extraction + validity audits                                            | proxy parquet + `prereg/swe-chat-proxies.md` + kappa/precision reports                   | Proxies failing validity are demoted, not used          |
| M4  | Conversation-bearing adapter + `operator-event-frame` schema + gate extension | traces with earned `pii_scanned`, 0 invalid, byte-determinism proof                      | Forbidden-frame list enforced in `consistency_errors()` |
| M5  | Boundary + mining aggregates                                                  | k≥10 aggregate tables only                                                               | Nothing row-level leaves the machine                    |

Every milestone is [PLANNED]. The corpus, its defects, its PII, and the existing
redaction/envelope machinery cited above are [VERIFIED]. Source-label semantics
(`prompt_pushback`, attribution) are [PARTIAL] until M3's audits run. No claim in this
document asserts that any mind, anywhere, feels anything.
