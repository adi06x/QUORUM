from __future__ import annotations

import json
import re
from typing import Any

import httpx


JSON_BLOCK_PATTERN = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class JsonLlmClient:
    def __init__(self, *, api_key: str | None, base_url: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        fallback: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        if not self.enabled:
            return fallback

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Return only valid JSON with double-quoted keys and no markdown.\n"
                    + json.dumps(user_payload, ensure_ascii=True, indent=2)
                ),
            },
        ]

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_seconds, connect=20.0)) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "temperature": temperature,
                        "messages": messages,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                return self._parse_json(content)
        except Exception:
            return fallback

    def _parse_json(self, content: str) -> dict[str, Any]:
        block_match = JSON_BLOCK_PATTERN.search(content)
        candidate = block_match.group(1) if block_match else content.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = min(
                [index for index in (candidate.find("{"), candidate.find("[")) if index != -1],
                default=-1,
            )
            end = max(candidate.rfind("}"), candidate.rfind("]"))
            if start == -1 or end == -1:
                raise
            return json.loads(candidate[start : end + 1])

