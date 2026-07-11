"""Dependency-free local Ollama client + voiced skin + judge factory.

Talks to a LOCAL Ollama HTTP server via stdlib urllib only (no SDK, no new
dependency). Network access is behind the injectable ``generate`` seam so tests
never contact a real server. Nothing here is canonical: generated prose is
optional, non-deterministic elaboration over the deterministic voice.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable


class OllamaError(RuntimeError):
    """Base class for local-Ollama failures."""


class OllamaUnavailable(OllamaError):
    """Backend unreachable: connection refused / host down / model not found."""


class OllamaGenerationError(OllamaError):
    """Reachable but generation failed: HTTP error, timeout, malformed response."""


def ollama_generate(
    prompt: str,
    *,
    model: str,
    host: str,
    timeout: float = 60.0,
    temperature: float = 0.7,
    options: dict | None = None,
) -> str:
    """POST to the local Ollama /api/generate and return the response text."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, **(options or {})},
    }
    req = urllib.request.Request(
        host.rstrip("/") + "/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise OllamaUnavailable(f"model or endpoint not found: {model}") from exc
        raise OllamaGenerationError(f"ollama HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OllamaUnavailable(f"ollama unreachable at {host}: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise OllamaGenerationError(f"ollama request failed: {exc}") from exc
    except ValueError as exc:
        raise OllamaGenerationError(f"ollama returned malformed JSON: {exc}") from exc
    text = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise OllamaGenerationError("ollama response missing 'response' text")
    return text.strip()


_VOICE_SYSTEM = (
    "Rephrase these grounded thoughts into one vivid, first-person passage. "
    "First-person is an interface convention, not an ontological claim. Use ONLY "
    "the facts, numbers, and names given. Add no number, faculty, or claim not "
    "present. Never claim to feel, to be aware/conscious/sentient, to suffer, or "
    "to be a moral patient. Keep every architecture-only caveat. Reply with the "
    "passage only."
)


class OllamaVoiceSkin:
    """VoiceSkin backed by a local Ollama model (optional, non-canonical)."""

    def __init__(
        self,
        *,
        model: str,
        host: str,
        timeout: float = 60.0,
        temperature: float = 0.7,
        generate: Callable[..., str] = ollama_generate,
    ):
        self._model = model
        self._host = host
        self._timeout = timeout
        self._temperature = temperature
        self._generate = generate

    @property
    def model(self) -> str:
        return self._model

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        body = "\n".join("- " + r["text_deterministic"] for r in rendered)
        prompt = f"{_VOICE_SYSTEM}\n\n{body}"
        return self._generate(
            prompt,
            model=self._model,
            host=self._host,
            timeout=self._timeout,
            temperature=self._temperature,
        ).strip()


def make_ollama_judge(
    *,
    model: str,
    host: str,
    timeout: float = 60.0,
    generate: Callable[..., str] = ollama_generate,
) -> Callable[[str], str]:
    """Return a judge(prompt)->str backed by a local Ollama model (temperature 0)."""

    def judge(prompt: str) -> str:
        return generate(
            prompt, model=model, host=host, timeout=timeout, temperature=0.0
        )

    return judge


__all__ = [
    "OllamaError",
    "OllamaUnavailable",
    "OllamaGenerationError",
    "ollama_generate",
    "OllamaVoiceSkin",
    "make_ollama_judge",
]
