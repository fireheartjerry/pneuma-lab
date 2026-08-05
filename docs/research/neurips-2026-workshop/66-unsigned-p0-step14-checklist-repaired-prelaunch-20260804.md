# Unsigned P0 / Step-14 repaired pre-launch checklist — 2026-08-04

**Disposition:** implementation and bounded production-surface admission are
complete; this checklist is unsigned, non-authorizing, and not a scientific
receipt. The official P0/Step-4B action remains `launch_blocked`.

## Complete in this implementation slice

- [x] Repair source is bound to `c352c9e0e4459c80cddfbf84cce94d0b4c79aaa4`.
- [x] Controller, model-server, and benchmark-worker production images were
  rebuilt with immutable digests, SBOMs, and BuildKit provenance.
- [x] The real production role surface passed one bounded,
  non-scientific AWS E2E with restart reconciliation, observation-error
  preservation, role evidence, and explicit teardown.
- [x] Fresh absence checks show no action compute, network, role, or profile
  resources remain. Retained ECR images and evidence are intentional.
- [x] The repaired candidate input lock, analysis graph, provider binding,
  image set, surface, and run-spec candidate are schema-validated and
  digest-bound.
- [x] Candidate state is explicitly `pre_launch_candidate` and
  `authorizing: false`; it has no power report, tier, or official authority.

## Still blocked by scientific/authority prerequisites

- [ ] Conduct and validate the live eligible-roster Sigstore/drand/Node
  ceremony. The current candidate is `ceremony_status: not_performed` with no
  eligible-confirmation reference.
- [ ] Run the registered C120 and C160 power/type-I validations only after the
  live ceremony, combine their receipts, and apply the registered
  largest-feasible rule. No tier may be selected by hard-code or feasibility
  prose.
- [ ] Seal packet, assignment, task-block, detectability, leakage, blinding,
  frozen-analysis, account/quota, spend, and reproducibility receipts.
- [ ] Mint the separately signed official authorization bound to the final
  repaired code, image, input, analysis, power, and selected-tier digests.
- [ ] Pass the hostile Step-14 launch review with the fresh receipt index.
- [ ] Launch the official P0/Step-4B action only after the above authority
  exists. The official study is still unrun.

## Canonical repaired candidate digests

- input lock: `7bb584da29f1fb55e5f46133a985bd3c249f154643dad5a3469ae737aee497e7`
- analysis graph: `aa4310584d605928e2edcba0828381c97f4aab0e51f115569073b9e22f4a44e4`
- image set: `2497d0e5a30b012c6b9d3ce0e025094a511626d5d5ed58de99078d5603f5c226`
- production surface: `0b401d505368505be161ead2fd54d8016bc7fd12aeabe3b4be3e8f8e93114f35`
- run-spec candidate: `028c39c4e44cf66438df528b64ba73209e49205266e156dfcfbe506b60aa5760`
- input package: `d81e4dcfc9ec3ae37f78d3398b8df88f64918a8f4f883460f1ebfd86c8d1a7a4`

The full evidence index is
`docs/research/neurips-2026-workshop/evidence/official-study-input-package-20260804-repair/`.
