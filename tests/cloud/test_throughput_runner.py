from __future__ import annotations

import ast
from pathlib import Path


RUNNER = Path("scripts/research/step5b_throughput_runner.py")


def test_runner_freezes_registered_measurement_shape() -> None:
    module = ast.parse(RUNNER.read_text(encoding="utf-8"))
    constants = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"SAMPLES", "TOKENS", "WARMUPS"}
    }
    assert constants == {"SAMPLES": 10, "TOKENS": 128, "WARMUPS": 1}


def test_runner_forces_exact_tokens_and_retains_raw_samples() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "min_tokens=TOKENS" in source
    assert "ignore_eos=True" in source
    assert '"output_tokens_per_second": [' in source
    assert '"samples": observations' in source
