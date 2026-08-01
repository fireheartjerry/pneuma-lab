from __future__ import annotations

from pathlib import Path


SCRIPT = Path("infra/aws/qualification-throughput-user-data.sh")


def test_throughput_action_is_bounded_and_isolated() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "--on-active=100m" in source
    assert source.count("run_rung ") == 2
    assert "run_rung l40s-tp1-32768 32768" in source
    assert "run_rung l40s-tp1-65536 65536" in source
    for fragment in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges"):
        assert fragment in source


def test_throughput_action_verifies_inputs_and_publishes_failures() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count("sha256sum --check") == 2
    assert 'echo "$rc" > "$ROOT/results/${name}.rc"' in source
    assert '"$ROOT"/results/* "$ROOT/receipt.json"' in source
