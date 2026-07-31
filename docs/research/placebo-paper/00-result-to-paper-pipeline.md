# The PLACEBO result-to-paper pipeline

**Status:** implementation complete; no evidence package exists
**Scope:** paper-facing only. Authorizes nothing; produces no scientific result.

Implementation: `src/pneuma_lab/placebo_paper/`.
Manuscript: `paper/placebo_protocol.tex` (new; `main.tex`, `placebo.tex`, and
`neurips_2026.sty` are untouched).
Fixtures: `fixtures/placebo_paper/`. Tests: `tests/placebo_paper/`.

The pipeline exists because of one failure mode: a number that reached a paper
without a producing artifact. Every check below is a mechanical answer to a way
that has happened or could happen here.

---

## 1. The one admissible source of numbers

`package.admit()` accepts exactly one object: a directory containing a
`package.json` describing a **verified, sealed Task 10 evidence package**
produced under an authority that licenses a scientific result of record.

Admission requires all of:

| requirement | field |
| --- | --- |
| package kind is `resampling_task10_sealed` | `package_kind` |
| lineage is `canonical_confirmation` | `lineage` |
| the package is sealed | `sealed` |
| the artifact root completed recursive verification | `artifact_root.verified` |
| the artifact root digest is a 64-hex value | `artifact_root.digest` |
| the unblind ceremony completed | `unblind.ceremony_completed` |
| authority is `confirmation_execution_authorized` | `authority` |
| all nine required receipts are present | `receipts` |
| the verdict is in the preregistered taxonomy | `verdict` |

### Refusals, by name

| lineage | refused because |
| --- | --- |
| `step_4a` | the bounded implementation-verification lineage. Its power final and sealed schedule prove plumbing, not efficacy. Its numbers are real numbers about a synthetic exercise, which makes them the most dangerous numbers in the repository: they look exactly like results. |
| `step_4b` | a separately authorized experiment, not the confirmation lineage |
| `p0_incomplete` | the preserved canonical P0 screen and its ten shards are an explicitly experiment-only incomplete non-result |
| `synthetic_fixture` | validates code and runtime only |
| `pilot` | pilot efficacy is labelled and excluded by the design |

Additional refusals: an unsealed package, an unverified artifact root, a
package with no completed unblind ceremony (numbers read before the permit was
consumed are numbers the analyst was not allowed to see), a missing receipt, a
verdict outside the taxonomy, and a directory with no `package.json`.

### No manual numbers

`SealedPackage.number(key)` raises `PackageRejected` for any key the package
did not emit. There is no default, no fallback, and no override. The renderer
calls only this method, so a value that reaches a table came from the analysis
or the cell is unfilled.

---

## 2. Generated assets

`python -m pneuma_lab.placebo_paper render --out paper/placebo/generated`

| asset | content |
| --- | --- |
| `table-primary.tex` | co-primary estimands and required decompositions |
| `table-resolution.tex` | $q_0$, $r_{95}$, $\Delta_{\text{null}}$, $\delta^\star$ |
| `table-environments.tex` | per-environment estimates |
| `table-claim-evidence.tex` | claim–evidence matrix from `paper/placebo/claims.json` |
| `appendix-artifacts.tex` | artifact appendix from the receipt index |
| `figure-data.json` | the machine-readable source for every figure |

Before a package exists, each asset is an **unfilled scaffold with the final
shape**: the same rows, the same captions, the same labels, and `\result{pending}`
in every value position. A test asserts the scaffold and the filled table have
identical row counts, so a missing estimand appears as an empty cell rather
than a silently absent row.

Figures are drawn from `figure-data.json` and never from ad-hoc values, so any
figure can be regenerated and diffed against the paper.

---

## 3. Manuscript checks

`python -m pneuma_lab.placebo_paper preflight [--package DIR] [--json OUT]`

These run against LaTeX **source**, so they work with no TeX distribution
installed. Checks that genuinely need a rendered document report `pending`,
never `pass`.

| check | fails on |
| --- | --- |
| `placeholders` | any surviving `\result{}`, `\TODO{}`, or `\draftnotice` outside comments |
| `anonymity` | identifying strings anywhere in the source, **comments included** — a stripped comment is not guaranteed absent from a submitted archive |
| `page_budget` | a source estimate above the 9-page body budget; otherwise `pending`, because the authoritative count needs a PDF |
| `bibliography` | a cited-but-undefined key, or any citation-queue entry not in state `verified` |
| `number_provenance` | a measured-looking decimal in prose introduced by "we find/observe/measure/report" |
| `novelty_discipline` | phrasings claiming placebo control itself is novel ("the first placebo-controlled", "we are the first to", …) |
| `evidence_package` | no package, or a refused one |
| `pdf_*` | always `pending` without a built PDF |

Exit codes: `0` clean, `1` blocked, `2` package refused.

**A pre-results draft is expected to fail.** The failure list is the submission
checklist, and it shrinks as the work completes rather than being asserted
complete in advance. Current state, `2026-07-31`:

```
FAIL  placeholders        8 result slots, 1 TODO, draft notice enabled
FAIL  bibliography        citation queue entry 'try_again_dont_look_back_2026' unresolved
FAIL  evidence_package    no sealed evidence package supplied
pend  page_budget         ~8.2 pages estimated from source (budget 4-9)
pend  pdf_*               no LaTeX toolchain in this environment
ok    anonymity, number_provenance, novelty_discipline
```

---

## 4. The unresolved citation

`paper/placebo/citation-queue.json` holds one blocking entry:
`try_again_dont_look_back_2026`. The July 2026 paper "Try Again, Don't Look
Back" was named as closest prior art for the retry-versus-feedback contrast.
Two targeted searches on 2026-07-31 returned no matching record, and no local
receipt references it.

It is recorded `unresolved` rather than cited from memory. Fabricating a
bibliographic record for the paper the work is most directly compared against
would be the single worst citation error available, and the preflight blocks
until a primary source is supplied. The manuscript carries a matching `\TODO`
where the delta paragraph belongs.

Three adjacent 2026 papers were resolved against the arXiv export API and are
cited: `arl_pivotal_retry_2026` (prefix-anchored retry as a method),
`reflect_error_attribution_2026` (resampling from a bare prefix as a retry
baseline), and `unreliable_feedback_2026` (harm from unreliable tool feedback).

---

## 5. Build

`latexmk`, `pdflatex`, and `pdftotext` are **not installed** in this
environment, so `paper/placebo_protocol.tex` has not been compiled and no PDF
check has been run. The manuscript's LaTeX has been checked structurally by the
source-level preflight only. Building it requires a TeX distribution:

```sh
cd paper && latexmk -pdf -halt-on-error -interaction=nonstopmode placebo_protocol.tex
./preflight.sh placebo_protocol    # PDF-level checks, once a PDF exists
```

Until that runs, page count, font embedding, PDF metadata, and text-layer
anonymity are `pending` and must not be described as passing.
