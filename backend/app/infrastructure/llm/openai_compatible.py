import json
from collections.abc import AsyncIterator

import httpx

from backend.app.domain.llm.message import LLMMessage


class OpenAICompatibleLLMProvider:
    """LLMProvider adapter for any OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _payload(self, messages: list[LLMMessage], *, stream: bool) -> dict:
        return {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }

    async def generate(self, messages: list[LLMMessage]) -> str:
        response = await self._client.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(messages, stream=False),
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(messages, stream=True),
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                payload = line.removeprefix("data: ").strip()

                if payload == "[DONE]":
                    return

                delta = json.loads(payload)["choices"][0]["delta"].get("content")

                if delta:
                    yield delta
