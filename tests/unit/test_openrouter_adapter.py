"""Unit tests for OpenRouterAdapter retry behavior (transient 429 handling)."""

from __future__ import annotations

from unittest import mock

import pytest

from ports.llm_provider.openrouter_adapter import OpenRouterAdapter


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = body.get("error", {}).get("message", "") if status_code != 200 else "ok"

    def json(self):
        return self._body


def _ok_response() -> _FakeResponse:
    return _FakeResponse(200, {"choices": [{"message": {"content": "synthesized answer"}}]})


def _ratelimited_response() -> _FakeResponse:
    return _FakeResponse(
        429,
        {
            "error": {
                "message": "mistralai/mistral-large-2512 is temporarily rate-limited upstream. Please retry shortly.",
                "metadata": {"limit_source": "upstream_provider_shared_pool"},
            }
        },
    )


@pytest.fixture
def adapter() -> OpenRouterAdapter:
    return OpenRouterAdapter(api_key="sk-or-v1-test")


def test_transient_429_retries_then_succeeds(adapter):
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None):
        calls["n"] += 1
        if calls["n"] < 3:
            return _ratelimited_response()
        return _ok_response()

    with mock.patch("time.sleep"), mock.patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post = fake_post
        out = adapter.generate_chat([{"role": "user", "content": "hi"}])

    assert out == "synthesized answer"
    assert calls["n"] == 3  # 2 failures + 1 success


def test_permanent_429_raises_clean_runtime_error(adapter):
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None):
        calls["n"] += 1
        return _ratelimited_response()

    with mock.patch("time.sleep"), mock.patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post = fake_post
        with pytest.raises(RuntimeError, match="OpenRouter API error \\(HTTP 429\\)"):
            adapter.generate_chat([{"role": "user", "content": "hi"}])

    assert calls["n"] == adapter.max_retries