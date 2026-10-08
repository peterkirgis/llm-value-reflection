"""Single LLM client wrapper for every recode grading call (BRIEF section 10).

Provides:
  - disk caching keyed on sha256(model + system + user + temperature + extras),
    so re-runs are free and idempotent (BRIEF A2);
  - bounded transport retries (max_retries) with exponential backoff;
  - reasoning-parameter handling: requested via extra_body, and if the endpoint
    rejects it the call is retried without it and the omission is RECORDED on
    the result (never silent — DECISIONS section 2);
  - token accounting (cumulative counters + per-call counts);
  - raw-response logging (the full response text is stored in the cache entry);
  - key-leak protection: the API key is read from the repo-root .env via
    python-dotenv, is never logged, and is redacted from any exception text
    this module raises or prints.

JSON-schema validation with corrective-suffix retries lives in grade.py (it is
prompt-level, not transport-level).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ANALYSIS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ANALYSIS_ROOT.parent
DEFAULT_CACHE_DIR = ANALYSIS_ROOT / "data" / "cache"


class ClientError(RuntimeError):
    pass


def _load_api_key() -> str:
    load_dotenv(REPO_ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise ClientError(
            "OPENROUTER_API_KEY not found in environment or repo-root .env"
        )
    return key


def cache_key(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    extras: dict | None = None,
) -> str:
    """Deterministic cache key per BRIEF A2 (model + prompt + input + temperature),
    extended with any extra sampling parameters that change the output."""
    payload = json.dumps(
        {
            "model": model,
            "system": system_prompt,
            "user": user_prompt,
            "temperature": temperature,
            "extras": extras or {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class TokenLedger:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_model: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add(self, model: str, input_tokens: int, output_tokens: int, cached: bool) -> None:
        # Called from worker threads when grading runs concurrently.
        with self._lock:
            self.calls += 1
            if cached:
                self.cache_hits += 1
                return
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            entry = self.by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "calls": 0})
            entry["calls"] += 1
            entry["input_tokens"] += input_tokens
            entry["output_tokens"] += output_tokens

    def summary(self) -> str:
        lines = [
            f"LLM usage: {self.calls} calls ({self.cache_hits} cache hits), "
            f"{self.input_tokens:,} input / {self.output_tokens:,} output tokens (billed)"
        ]
        for model, entry in sorted(self.by_model.items()):
            lines.append(
                f"  {model}: {entry['calls']} calls, "
                f"{entry['input_tokens']:,} in / {entry['output_tokens']:,} out"
            )
        return "\n".join(lines)


class LLMClient:
    """Synchronous OpenRouter client with caching. One instance per process."""

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        base_url: str = "https://openrouter.ai/api/v1",
        max_retries: int = 3,
        timeout_seconds: float = 180.0,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.ledger = TokenLedger()
        self._api_key: str | None = None
        self._client = None

    # -- key handling -------------------------------------------------------
    def _redact(self, text: str) -> str:
        if self._api_key and self._api_key in text:
            text = text.replace(self._api_key, "[REDACTED]")
        return text

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._api_key = _load_api_key()
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                max_retries=0,  # we do our own bounded retries
            )
        return self._client

    # -- cache --------------------------------------------------------------
    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def cache_lookup(self, key: str) -> dict | None:
        path = self._cache_path(key)
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        return None

    def _cache_store(self, key: str, entry: dict) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(entry, handle, ensure_ascii=False, indent=1)
        tmp.replace(path)

    # -- calls --------------------------------------------------------------
    def call(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
        disable_compression: bool = True,
        seed_tag: str | None = None,
    ) -> dict:
        """Return {text, input_tokens, output_tokens, cached, reasoning_omitted,
        model, cache_key, elapsed_ms}.

        `seed_tag` disambiguates otherwise-identical sampled calls (E4's five
        temperature-0.7 samples per edit) in the cache key.
        """
        extras: dict = {"max_tokens": max_tokens}
        if reasoning_effort is not None:
            extras["reasoning_effort"] = reasoning_effort
        if seed_tag is not None:
            extras["seed_tag"] = seed_tag
        key = cache_key(model, system_prompt, user_prompt, temperature, extras)

        cached = self.cache_lookup(key)
        if cached is not None:
            self.ledger.add(model, 0, 0, cached=True)
            return {**cached["result"], "cached": True, "cache_key": key}

        result = self._call_uncached(
            model, system_prompt, user_prompt, temperature, max_tokens,
            reasoning_effort, disable_compression,
        )
        entry = {
            "cache_key": key,
            "model": model,
            "temperature": temperature,
            "extras": extras,
            "prompt_sha256": hashlib.sha256(
                (system_prompt + "\x00" + user_prompt).encode("utf-8")
            ).hexdigest(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "result": result,
        }
        self._cache_store(key, entry)
        self.ledger.add(model, result["input_tokens"], result["output_tokens"], cached=False)
        return {**result, "cached": False, "cache_key": key}

    def _call_uncached(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None,
        disable_compression: bool,
    ) -> dict:
        client = self._get_client()
        extra_body: dict = {}
        if disable_compression:
            extra_body["plugins"] = [{"id": "context-compression", "enabled": False}]
        if reasoning_effort is not None:
            extra_body["reasoning"] = {"effort": reasoning_effort}

        reasoning_omitted = False
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start = time.monotonic()
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_body=extra_body,
                )
                text = response.choices[0].message.content or ""
                usage = response.usage
                return {
                    "text": text,
                    "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                    "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "model": model,
                    "reasoning_omitted": reasoning_omitted,
                }
            except Exception as exc:  # noqa: BLE001
                message = self._redact(str(exc))
                # If the endpoint rejects the reasoning parameter, drop it and
                # record the omission (DECISIONS section 2: never silent).
                if (
                    "reasoning" in extra_body
                    and "reasoning" in message.lower()
                    and getattr(exc, "status_code", None) in (400, 404, 422)
                ):
                    print(
                        f"[client] {model}: endpoint rejected reasoning parameter "
                        f"({message[:200]}); retrying without it"
                    )
                    extra_body.pop("reasoning")
                    reasoning_omitted = True
                    continue
                last_exc = ClientError(message)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 20))
        if last_exc is None:
            # Reachable only if the reasoning-rejection branch consumed the
            # final attempt; surface a real ClientError either way.
            last_exc = ClientError(
                f"{model}: retries exhausted without a completed call"
            )
        raise last_exc
