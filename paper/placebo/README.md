# PLACEBO paper materials

Everything in this directory, plus `paper/placebo_protocol.tex`, is new on the
`codex/placebo-paper-review` branch. `paper/main.tex`, `paper/placebo.tex`, and
`paper/neurips_2026.sty` are **not modified** by this branch, and a test asserts
it.

| path | what it is |
| --- | --- |
| `../placebo_protocol.tex` | the pre-results, double-blind manuscript |
| `refs-placebo.bib` | new references only; `../refs.bib` is shared and untouched |
| `citation-queue.json` | citation verification state; one entry is unresolved and blocks |
| `claims.json` | declared claims and the receipt that would support each |
| `generated/` | emitted tables, figure data, claim matrix, artifact appendix — never hand-edited |

## Commands

```sh
# every manuscript check; exits 1 while blocked
python -m pneuma_lab.placebo_paper preflight

# regenerate the scaffold (or the filled assets, with --package)
python -m pneuma_lab.placebo_paper render --out paper/placebo/generated

# admit a sealed Task 10 package, or see exactly why it was refused
python -m pneuma_lab.placebo_paper admit --package <dir>
```

## State

The preflight **blocks**, and should. No arm has been run, no evidence package
exists, and the closest-prior-art citation is unresolved. See
`docs/research/placebo-paper/00-result-to-paper-pipeline.md` for the current
failure list and what discharges each item.

No PDF has been built: this environment has no LaTeX toolchain, so page count,
font embedding, PDF metadata, and text-layer anonymity are `pending`, not
passing.
