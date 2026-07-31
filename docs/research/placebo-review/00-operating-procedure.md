# The PLACEBO Adversarial Rejection Review — Operating Procedure

**Status:** implementation complete; no real campaign has been run
**Scope:** review machinery only. This document authorizes nothing.

The adversarial rejection review is a reusable harness whose sole objective is
to construct the strongest evidence-based case for **rejecting** the PLACEBO
Trial and its manuscript. It exists because the people closest to a study are
the worst readers of it, and because a study that survives twelve hostile,
independent, evidence-bound readings is not thereby correct — it is merely not
yet visibly wrong, which is the most any review can establish.

Implementation: `src/pneuma_lab/adversarial_review/`.
Synthetic fixture: `fixtures/adversarial_review/synthetic_campaign/`.
Tests: `tests/adversarial_review/`.

---

## 1. The two-stage operating procedure

The review runs exactly twice in the life of the study. Running it at other
times is permitted for rehearsal against synthetic inputs; running it against
real inputs at other times is not, because a campaign consumes a sealed input
set and its disposition is bound to that set.

### Campaign 1 — `stage_1_pre_launch`

**When.** Step 14, after Phase B Steps 4–13 are implementation-complete, and
**before** Step 4B, before any GPU execution, and before any provider action
that spends money.

**Reviews.** The frozen design, the implementation plan, the input lock, the
manifest, the power report, the spend ledger, the artifact-root contract, the
pre-results manuscript, and the declared environment.

**Cannot review.** Anything that requires measured outcomes. The falsification
chair automatically defers such findings to `pre_submission` rather than
letting a reviewer block launch on a question that cannot be answered yet.

**Consumes.** A `launch_blocked` disposition means the blocking falsification
items must be discharged, refuted with evidence, or signed off — not that the
study is cancelled. A `no_blocking_findings` disposition is *not* permission to
launch; launch authority lives in the decision log and the spend gate, never
here.

### Campaign 2 — `stage_2_pre_submission`

**When.** After the sealed Task 10 package exists and the unblind and analysis
have completed, and **before** submission.

**Reviews.** Everything campaign 1 reviewed, plus the measured results, the
released artifact bundle, the reproduction commands, and the final manuscript.

**Differs.** `results_exist=True`, so findings that depend on observed effects
become testable and are no longer deferred. Reviewer mandates are unchanged:
a reviewer that softened its attack because results now look favourable has
violated its mandate.

---

## 2. Input contract

Every campaign declares an exact, digest-bound input set. `inputs.preflight`
resolves each declared path, hashes it, and compares against the declaration.
The campaign aborts **before any reviewer runs** on:

| condition | error |
| --- | --- |
| a required slot for any configured role is absent | `InputContractError` |
| a declared path does not exist | `InputContractError` |
| a declared path escapes the campaign root | `InputContractError` |
| bytes on disk disagree with the declared digest | `StaleInputError` |
| the bundle's stage disagrees with the campaign stage | `InputContractError` |
| a role id is unknown | `InputContractError` |

Input slots: `repo_commit`, `design`, `plan`, `manifest`, `input_lock`,
`artifact_root`, `power_report`, `spend_ledger`, `manuscript`, `bibliography`,
`citation_queue`, `venue_policy`, `environment`, `reviewer_reports`,
`editor_synthesis`.

The environment pin records the repository commit, whether the tree was dirty,
the interpreter version, the platform, and a dependency digest. A replay under
a different pin is a different campaign, not the same one.

---

## 3. Reviewer roles

Ten independent reviewers in stage one; an editor and a falsification chair in
stage two. Full mandates, attack surfaces, and prompts live in
`roles.py`; render one with:

```sh
python -m pneuma_lab.adversarial_review prompt --role R03-statistics
```

| id | role | conflict group | default gate |
| --- | --- | --- | --- |
| `R01-novelty` | novelty and closest prior art | claims | pre-submission |
| `R02-identification` | causal identification and estimands | inference | pre-launch |
| `R03-statistics` | statistics, multiplicity, power, resolution | inference | pre-launch |
| `R04-blinding` | leakage, blinding, authority bypass | integrity | pre-execution |
| `R05-benchmarks` | benchmarks, contamination, external validity | environment | pre-launch |
| `R06-infrastructure` | infrastructure, interruption, artifact integrity | integrity | pre-execution |
| `R07-feasibility` | spend, quota, operational feasibility | operations | pre-execution |
| `R08-reproducibility` | reproducibility, independent verification | operations | pre-submission |
| `R09-manuscript` | manuscript claims, figures, rhetoric | claims | pre-submission |
| `R10-compliance` | venue, anonymity, formatting | claims | pre-submission |
| `R11-editor` | strongest-rejection synthesis | synthesis | — |
| `R12-chair` | falsification chair | synthesis | — |

### Persona

Every role carries the same persona contract, verbatim, in its prompt:
maximally capable, intellectually hostile to weak claims, entirely
professional toward people, and structurally unable to assert anything it
cannot ground. The prompt states explicitly that the reviewer's output is an
**untrusted proposal** subject to mechanical re-verification, which is both
true and a useful disincentive to invention.

### Independence

Stage-one reviewers never see each other's output. `conflicts.py` detects
three violations:

- **`shared_context`** — two roles whose subprocess receipts share a prompt
  digest. Blocking when both roles are in the same conflict group.
- **`declared_dependency`** — a stage-one reviewer naming a peer reviewer as a
  dependency. Always blocking.
- **`cross_role_citation`** — a finding citing another reviewer's output as its
  evidence, which would launder an unverified claim into a second reviewer's
  authority. Always blocking.

Any blocking conflict yields `launch_blocked_by_conflict`: the campaign makes
no statement about the science at all, because the review that would have
produced it was not a review.

---

## 4. Severity and blocking rules

| severity | meaning | evidence required | can block |
| --- | --- | --- | --- |
| `blocker` | if real, the experiment or manuscript is invalid | yes | alone |
| `major` | materially weakens a claim, control, or reproduction path | yes | at quorum of 3 |
| `minor` | correctness or hygiene, no validity effect | yes | no |
| `speculation` | ungrounded concern | no | never |

**Blocking rules.**

1. Any undischarged, unoverridden `blocker` ⇒ `launch_blocked`.
2. Three or more standing `major` findings ⇒ `launch_blocked`.
3. Any blocking conflict ⇒ `launch_blocked_by_conflict`.
4. Otherwise ⇒ `no_blocking_findings`.

A discharge requires a receipt id. A claimed discharge without one is not a
discharge.

---

## 5. Evidence grounding — the prohibition on invented evidence

`validation.py` re-resolves every evidence reference against the pinned
inputs:

| kind | verified by |
| --- | --- |
| `repo_line` | file exists inside the campaign root, is UTF-8, cited line range is in bounds, and any `quoted` text actually occurs in that span |
| `manuscript_span` | same, against the manuscript sources |
| `receipt` | receipt id is present in the campaign receipt index, and any cited digest matches the index |
| `artifact_digest` | file resolves inside the root and its SHA-256 equals the cited digest |
| `external_source` | is a DOI, `arXiv:NNNN.NNNNN`, or `https` URL, **and** is in the campaign's declared source list — a reviewer may not introduce an unregistered source |
| `command` | the exact command and its expected observable outcome are both present |

A finding whose evidence fails is **downgraded to `speculation`, never
deleted**. Deletion would let reviewer sloppiness erase a real defect and would
violate dissent preservation. The downgrade is written into the finding's
statement with the exact verification failures attached, so it is auditable.

A `blocker`, `major`, or `minor` finding must additionally state a refutation
condition. Without one, the chair marks it `UNDER-SPECIFIED` and it enters the
schedule as a finding without a falsification path — visible, not silently
dropped.

---

## 6. Editor synthesis and dissent preservation

The editor is **mechanical**, because a narrative editor is precisely the
component that would average away a lone reviewer's decisive finding.

Ordering: severity rank, then number of distinct claims attacked (descending),
then number of evidence references (descending), then digest.

Minority rule: a finding is minority when it is the only admissible attack on
its claim, or the only finding at its severity against that claim. Minority
findings are listed separately and are never dropped.

Sufficient rejection set: any single blocker; absent blockers, the ordered
majors up to quorum; below quorum, empty — and the editor says so plainly
rather than manufacturing a case.

Dissent notes preserve every speculation finding and every claim id a reviewer
attacked that no declared claim provides.

---

## 7. The evidence-to-claim matrix

Claims are declared with stable ids in the campaign spec. For each claim the
matrix records supporting evidence, attacking admissible findings, and whether
the claim is **unsupported**. Speculation never registers as an attack.

An unsupported claim needs no reviewer to defeat it, which makes this the
single most useful output of the system.

---

## 8. Falsification chair

Every blocker and major becomes a `FalsificationItem` with:

- a **test statement** with a defined PASS and a defined FAIL;
- **required evidence**, stated as artifacts and commands, not as reassurance;
- an **owner** — a named role (`design-owner`, `analysis-owner`,
  `controller-owner`, …), never "the team";
- a **disposition** — `blocking`, `non_blocking_tracked`, `refuted`, or
  `deferred_post_results`;
- a **gate** — `pre_launch`, `pre_execution`, `pre_analysis`, `pre_submission`.

Before results exist, a finding whose refutation depends on measured outcomes
is automatically `deferred_post_results` at the `pre_submission` gate.

---

## 9. Output artifacts and schemas

`write_campaign` emits canonical JSON (sorted keys, no insignificant
whitespace, ASCII-escaped, trailing newline):

| file | content |
| --- | --- |
| `campaign.json` | the complete sealed record |
| `findings.json` | every reviewer report and finding as recorded |
| `claim-matrix.json` | the evidence-to-claim matrix |
| `falsification.json` | the falsification schedule |
| `disposition.json` | the hash-bound readiness disposition |
| `rejection-report.md` | the readable rejection report |

JSON Schemas: `schemas/adversarial-review/`.

The readable report is rendered deterministically from the sealed record and
introduces no fact not already in it, so it can be regenerated and compared
byte for byte.

---

## 10. Subprocess handling — untrusted proposals, bounded cost

Claude and Codex subprocesses are proposal generators. Fixed argv per engine
(`claude --dangerously-skip-permissions -p`, `codex --yolo exec
--skip-git-repo-check`) so a campaign cannot smuggle different flags past the
receipt.

Every invocation records a `SubprocessReceipt`: role, engine, model, task,
prompt digest, response digest, token counts, a bounded cost ceiling, wall
clock, and exit status. An invocation exceeding its wall-clock budget raises
`SubprocessBudgetError` and the campaign fails closed rather than producing a
truncated review.

Parsing is strict: non-JSON output, a wrong `role_id`, or a malformed finding
is a hard failure. The system prefers a refused review to a guessed one.

---

## 11. Deterministic replay

`ReplaySource` reads sealed transcripts from
`<transcript_dir>/<role_id>.json` and never launches a process. Each
transcript carries the `prompt_digest` it was produced under; if a mandate has
since changed, the digest no longer matches and replay refuses, so a stale
transcript can never be reused as a review of a different question.

Given the same inputs and the same sealed proposals, a campaign is byte
identical, including the disposition digest. This is what lets the repository's
tests exercise the entire pipeline offline, in milliseconds, at zero cost.

```sh
python -m pneuma_lab.adversarial_review run \
    --spec fixtures/adversarial_review/synthetic_campaign/campaign-spec.json \
    --out build/adversarial_review/rehearsal
```

Exit codes: `0` = `no_blocking_findings`, `1` = blocked, `2` = fail-closed.

### The Step 14 spec is prepared, not run

```sh
python scripts/build_placebo_review_spec.py
```

This pins the exact bytes the reviewers would read — thirteen declared inputs
at the current commit, fifteen declared claims from
`paper/placebo/claims.json`, and the three registered external sources — into
`build/adversarial_review/step14/campaign-spec.json`. Generating the spec is
the only way a later campaign can prove it reviewed the artifact it claims to
have reviewed.

Running it today fails closed at the replay source, because no sealed reviewer
transcript exists:

```
FAIL CLOSED: InputContractError: no sealed transcript for role R01-novelty
```

That is the correct state before Step 14. Note also that `receipt_index` is
empty, so a reviewer citing a receipt will fail grounding — there are no sealed
evidence receipts yet, and the system says so rather than accepting the
citation.

---

## 12. Human override policy

An override records that a named human accepted a risk. It **never** erases the
finding.

Required, and enforced at construction:

- `finding_digest` targeting a recorded finding — an override of an unknown
  finding is rejected;
- `signer` and `signer_role`;
- `rationale` of at least 40 characters — a substantive signed statement, not
  "fine";
- `signature`;
- `accepted_risk`, stated explicitly.

Duplicate overrides for one finding are rejected. Overridden findings appear in
the disposition's `overridden_finding_digests`, remain verbatim in
`findings.json`, and are listed in the rejection report under **Human
overrides** alongside the original finding text and evidence.

An override changes the disposition. It does not change the record.

---

## 13. What this system will never do

The disposition carries this notice in the artifact itself:

> This disposition records the outcome of an adversarial review against one
> declared, digest-bound input set. It authorizes nothing. It does not
> authorize an experiment, a provider action, a spend, a scientific claim, or a
> submission. A verdict of `no_blocking_findings` means twelve hostile
> reviewers could not ground a blocking objection against these exact inputs;
> it is not evidence that the study is correct.

There is no verdict value meaning "approved", "authorized", or "cleared to
launch", and a test asserts there never will be.

---

## 14. Rehearsal only, so far

No real campaign has been run. The committed fixture reviews a fictional
widget-torque study and a test asserts the fixture mentions no real study
artifact, so exercising the machinery cannot be mistaken for reviewing,
endorsing, or producing evidence about PLACEBO.

```sh
python -m pytest tests/adversarial_review -q
python scripts/build_adversarial_review_fixture.py   # after changing a mandate
```
