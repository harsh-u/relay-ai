import json

import httpx
import pytest

from backend.app.domain.llm.message import LLMMessage
from backend.app.infrastructure.llm.openai_compatible import OpenAICompatibleLLMProvider


def _provider(handler) -> OpenAICompatibleLLMProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    return OpenAICompatibleLLMProvider(
        base_url="https://llm.example.com/v1",
        api_key="test-key",
        model="test-model",
        client=client,
    )


async def test_generate_returns_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://llm.example.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"

        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello! How can I help you?"}}],
            },
        )

    provider = _provider(handler)

    result = await provider.generate([LLMMessage(role="user", content="Hello")])

    assert result == "Hello! How can I help you?"


async def test_generate_sends_model_and_messages() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    provider = _provider(handler)

    await provider.generate(
        [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hi"),
        ]
    )

    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
    ]


async def test_generate_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = _provider(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await provider.generate([LLMMessage(role="user", content="Hello")])


async def test_stream_yields_content_deltas() -> None:
    chunks = [
        'data: {"choices": [{"delta": {"content": "Hel"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": "lo"}}]}\n\n',
        "data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="".join(chunks))

    provider = _provider(handler)

    received = [chunk async for chunk in provider.stream([LLMMessage(role="user", content="Hi")])]

    assert received == ["Hel", "lo"]
