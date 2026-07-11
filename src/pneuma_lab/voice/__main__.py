"""CLI: python -m pneuma_lab.voice <fixture> [--out DIR] [--subject reference|baseline]"""

from __future__ import annotations

import argparse
from pathlib import Path

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import load_jsonl

from . import config as _config
from . import ollama as _ollama
from . import voiced
from .stream import voice_run, voice_run_paired
from .transcript import write_transcript


def _factory(name: str):
    if name == "baseline":
        from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

        return BaselinePsycheSubject
    return ReferencePsyche


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pneuma_lab.voice")
    parser.add_argument("fixture", help="input-frame JSONL timeline")
    parser.add_argument(
        "--out", default=None, help="output dir (default build/voice/<run>)"
    )
    parser.add_argument(
        "--subject", choices=("reference", "baseline"), default="reference"
    )
    parser.add_argument(
        "--paired",
        action="store_true",
        help="run a paired replay and narrate the tested counterfactual",
    )
    parser.add_argument(
        "--skin",
        choices=("none", "reference", "llm"),
        default="none",
        help="voiced skin over the deterministic stream",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        help="voice model override (else env/config/llama3.1)",
    )
    parser.add_argument("--judge-model", default=None, help="judge model override")
    parser.add_argument("--ollama-host", default=None, help="Ollama host URL override")
    parser.add_argument(
        "--no-entailment",
        action="store_true",
        help="skip the local-LLM entailment judge for --skin llm",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="also write a self-contained HTML mind monitor (monitor.html)",
    )
    args = parser.parse_args(argv)

    skin = None
    judge = None
    if args.skin == "reference":
        skin = voiced.ReferenceVoiceSkin()
    elif args.skin == "llm":
        host = _config.resolve_ollama_host(args.ollama_host)
        skin = _ollama.OllamaVoiceSkin(
            model=_config.resolve_voice_model(args.ollama_model), host=host
        )
        if not args.no_entailment:
            judge = _ollama.make_ollama_judge(
                model=_config.resolve_judge_model(args.judge_model), host=host
            )

    factory = _factory(args.subject)
    if args.paired:
        stream = voice_run_paired(
            load_jsonl(args.fixture), subject_factory=factory, skin=skin, judge=judge
        )
    else:
        stream = voice_run(
            load_jsonl(args.fixture), subject_factory=factory, skin=skin, judge=judge
        )
    out_dir = Path(args.out) if args.out else Path("build/voice") / stream["run_id"]
    write_transcript(stream, out_dir)
    if args.monitor:
        from .monitor import write_monitor

        write_monitor(stream, out_dir / "monitor.html")
    print(
        f"wrote {out_dir}/stream.md (level {stream['evidence_level']}, {len(stream['atoms'])} atoms)"
        + (" + monitor.html" if args.monitor else "")
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
