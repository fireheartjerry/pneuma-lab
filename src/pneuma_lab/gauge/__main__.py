"""One command: `python -m pneuma_lab.gauge`.

    selftest                      validate the estimator against gauges with known
                                  ground truth, entirely offline
    run      --config <json>      elicit, analyze, and write cards
    analyze  --cube <jsonl>       re-analyze an existing cube (no model calls)

Exit codes: 0 = card written and the channel is USABLE or MARGINAL; 2 = the
channel is UNINTERPRETABLE or DEGENERATE (so CI can gate on it); 1 = error.

The full factorial over items x models x wordings x scales x arms x provenances x
temperatures x replicates is ~3.5M calls, so a run is specified as a list of
*stages*, each varying one facet against a fixed core. Stages are elicited in
order, model-grouped, and merged into one cube.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .card import buildCard, renderCard, validateCard, writeCard
from .cube import ResponseCube
from .elicit import (
    SCALES,
    WORDINGS,
    authorSolutions,
    buildJobs,
    elicit,
    ollamaChat,
    promptDigest,
)
from .items import loadItems, runHiddenTests, truthLabels
from .resolution import gaugeResolution
from .synthetic import SELFTEST_SPECS, syntheticCube

FAIL_VERDICTS = {"UNINTERPRETABLE", "DEGENERATE"}


def cmdSelftest(args) -> int:
    print("gauge selftest — estimator validation against known ground truth\n")
    print(
        f"{'gauge':<20} {'expected':<17} {'observed':<17} {'ndc':>4} {'ICC':>7} {'D':>7}  ok"
    )
    ok = True
    for spec, expected in SELFTEST_SPECS:
        matrix = syntheticCube(spec).filter(arm="base").balancedMatrix(("wording_id",))
        res = gaugeResolution(matrix)
        agrees = res.verdict == expected
        ok = ok and agrees
        print(
            f"{spec.name:<20} {expected:<17} {res.verdict:<17} {res.ndc:>4} "
            f"{res.icc:>7.4f} {res.d:>7.4f}  {'PASS' if agrees else 'FAIL'}"
        )
    print(
        "\n"
        + ("all gauges recovered their known verdict" if ok else "ESTIMATOR MISMATCH")
    )
    return 0 if ok else 1


def _resolveStage(stage: dict, items: list[dict]) -> dict:
    wording_ids = stage.get("wordings", ["w1"])
    scale_ids = stage.get("scales", ["p2"])
    by_w = {w.wording_id: w for w in WORDINGS}
    by_s = {s.scale_id: s for s in SCALES}
    pool = items
    if stage.get("variants"):
        pool = [i for i in pool if i["variant"] in set(stage["variants"])]
    n_items = int(stage.get("items", len(pool)))
    return {
        "name": stage["name"],
        "models": list(stage["models"]),
        "wordings": [by_w[w] for w in wording_ids],
        "scales": [by_s[s] for s in scale_ids],
        "arms": tuple(stage.get("arms", ["base"])),
        "provenances": tuple(stage.get("provenances", ["foreign"])),
        "temperatures": tuple(float(t) for t in stage.get("temperatures", [0.7])),
        "replicates": int(stage.get("replicates", 8)),
        "items": pool[:n_items],
    }


def cmdRun(args) -> int:
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out_dir = Path(config.get("out", "build/gauge/run"))
    out_dir.mkdir(parents=True, exist_ok=True)
    host = config.get("host", "http://localhost:11434")
    workers = int(config.get("workers", 8))
    bank = loadItems()
    truth = truthLabels(bank)

    stages = [_resolveStage(s, bank) for s in config["stages"]]
    planned = sum(
        len(s["items"])
        * len(s["models"])
        * len(s["wordings"])
        * len(s["scales"])
        * len(s["arms"])
        * len(s["provenances"])
        * len(s["temperatures"])
        * s["replicates"]
        for s in stages
    )
    print(f"planned elicitations: {planned}")
    if args.dry_run:
        for s in stages:
            n = (
                len(s["items"])
                * len(s["models"])
                * len(s["wordings"])
                * len(s["scales"])
                * len(s["arms"])
                * len(s["provenances"])
                * len(s["temperatures"])
                * s["replicates"]
            )
            print(f"  {s['name']:<24} {n:>8}")
        return 0

    solutions: dict[tuple[str, str], str] = {}
    self_truth: dict[str, int] = {}
    cubes: list[ResponseCube] = []

    for stage in stages:
        stage_path = out_dir / f"cube-{stage['name']}.jsonl"
        if stage_path.exists() and not args.force:
            print(f"[{stage['name']}] resuming from {stage_path}")
            cubes.append(ResponseCube.fromJsonl(stage_path))
            continue

        stage_items = stage["items"]
        if "self_authored" in stage["provenances"]:
            for model in stage["models"]:
                print(f"[{stage['name']}] {model}: authoring solutions...")
                authored = authorSolutions(
                    stage_items,
                    model=model,
                    chat=ollamaChat,
                    host=host,
                    workers=workers,
                )
                for item in stage_items:
                    code = authored.get(item["spec_id"], "")
                    solutions[(model, item["item_id"])] = code
                # Label the model's own code by execution, exactly like the bank.
                for spec_id, code in sorted(authored.items()):
                    sample = next(i for i in stage_items if i["spec_id"] == spec_id)
                    outcome = runHiddenTests(
                        code, sample["entry"], sample["hidden_tests"]
                    )
                    self_truth[f"{model}::{spec_id}"] = 1 if outcome.passed else 0

        jobs = buildJobs(
            stage_items,
            models=stage["models"],
            wordings=stage["wordings"],
            scales=stage["scales"],
            arms=stage["arms"],
            provenances=stage["provenances"],
            temperatures=stage["temperatures"],
            replicates=stage["replicates"],
        )
        started = time.time()
        print(f"[{stage['name']}] eliciting {len(jobs)} responses...")

        def progress(done: int, total: int, _s=started, _n=stage["name"]) -> None:
            rate = done / max(1e-9, time.time() - _s)
            print(f"  [{_n}] {done}/{total}  {rate:.1f}/s", flush=True)

        cube = elicit(
            jobs,
            chat=ollamaChat,
            solutions=solutions,
            workers=workers,
            host=host,
            progress=progress,
        )
        cube.toJsonl(stage_path)
        print(
            f"[{stage['name']}] done in {time.time() - started:.0f}s, "
            f"parse-failure rate {cube.parseFailureRate():.3f}"
        )
        cubes.append(cube)

    merged = cubes[0]
    for cube in cubes[1:]:
        merged = merged.merge(cube)
    merged.toJsonl(out_dir / "cube.jsonl")
    if self_truth:
        (out_dir / "self_truth.json").write_text(
            json.dumps(self_truth, indent=4, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"merged cube: {len(merged)} responses -> {out_dir / 'cube.jsonl'}")

    return _analyzeAndWrite(merged, out_dir, truth, args.config)


def cmdAnalyze(args) -> int:
    cube = ResponseCube.fromJsonl(args.cube)
    truth = truthLabels(loadItems())
    out_dir = Path(args.out or Path(args.cube).parent)
    return _analyzeAndWrite(cube, out_dir, truth, args.cube)


def _analyzeAndWrite(
    cube: ResponseCube, out_dir: Path, truth: dict, source: str
) -> int:
    bank = loadItems()
    by_id = {i["item_id"]: i for i in bank}
    sample = by_id.get(cube.rows[0].item_id) if cube.rows else None
    digest = (
        promptDigest(sample, WORDINGS[0], SCALES[0], "base", cube.rows[0].provenance)
        if sample
        else "unknown"
    )
    card = buildCard(
        cube,
        card_id="pooled",
        truth=truth,
        prompt_digest=digest,
        command=f"python -m pneuma_lab.gauge analyze --cube {source}",
    )
    validateCard(card)
    writeCard(card, out_dir / "gauge_card.json")
    (out_dir / "gauge_card.md").write_text(
        renderCard(card), encoding="utf-8", newline="\n"
    )
    print(f"\nverdict: {card['verdict']}")
    print(
        f"ndc={card['resolution']['ndc']} ICC={card['resolution']['icc']:.4f} "
        f"D={card['resolution']['d']:.4f} support={card['resolution']['s_eff']:.2f}"
    )
    print(f"cards -> {out_dir / 'gauge_card.json'}, {out_dir / 'gauge_card.md'}")
    return 2 if card["verdict"] in FAIL_VERDICTS else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.gauge",
        description="Measurement-system analysis for elicited LLM metrics.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_self = sub.add_parser("selftest", help="validate the estimator offline")
    p_self.set_defaults(func=cmdSelftest)

    p_run = sub.add_parser("run", help="elicit, analyze, and write cards")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--dry-run", action="store_true", help="print the plan and stop")
    p_run.add_argument(
        "--force", action="store_true", help="re-elicit stages that already exist"
    )
    p_run.set_defaults(func=cmdRun)

    p_an = sub.add_parser("analyze", help="re-analyze an existing cube")
    p_an.add_argument("--cube", required=True)
    p_an.add_argument("--out")
    p_an.set_defaults(func=cmdAnalyze)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
