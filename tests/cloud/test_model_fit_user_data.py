from pathlib import Path


USER_DATA = Path("infra/aws/qualification-model-fit-user-data.sh")


def test_read_only_model_fit_routes_triton_cache_to_writable_tmpfs() -> None:
    script = USER_DATA.read_text(encoding="utf-8")

    assert "--read-only --tmpfs /tmp:rw,nosuid,size=8g" in script
    assert "--env HOME=/tmp --env TRITON_CACHE_DIR=/tmp/triton" in script
