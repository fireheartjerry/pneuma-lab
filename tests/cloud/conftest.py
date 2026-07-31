"""Cloud tests are strictly local; any client/network fixture is a test bug."""

import socket

import pytest


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("cloud tests must not access network")

    monkeypatch.setattr(socket, "create_connection", blocked)
