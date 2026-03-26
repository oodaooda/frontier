"""Anthropic (Claude) model runner."""

import base64
import time
from pathlib import Path

import anthropic

from frontier.runners.base import BaseRunner, ModelResponse


class AnthropicRunner(BaseRunner):
    """Runner for Anthropic Claude models with vision."""

    def __init__(self, model_id: str = "claude-opus-4-6", max_tokens: int = 4096):
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    @property
    def model_id(self) -> str:
        return self._model_id

    async def query(self, image_paths: list[str], prompt: str, task_id: str) -> ModelResponse:
        """Send images + prompt to Claude, return structured response."""
        content = []

        for img_path in image_paths:
            path = Path(img_path)
            with open(path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            media_type = "image/png" if path.suffix == ".png" else "image/jpeg"
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })

        content.append({"type": "text", "text": prompt})

        start = time.monotonic()
        response = self._client.messages.create(
            model=self._model_id,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        latency_ms = (time.monotonic() - start) * 1000

        answer_text = ""
        for block in response.content:
            if block.type == "text":
                answer_text += block.text

        return ModelResponse(
            model_id=self._model_id,
            task_id=task_id,
            answer=answer_text,
            raw_response={
                "id": response.id,
                "content": [{"type": b.type, "text": getattr(b, "text", "")} for b in response.content],
                "stop_reason": response.stop_reason,
            },
            latency_ms=latency_ms,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
