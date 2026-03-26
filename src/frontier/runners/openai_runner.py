"""OpenAI (GPT) model runner."""

import base64
import time
from pathlib import Path

import openai

from frontier.runners.base import BaseRunner, ModelResponse


class OpenAIRunner(BaseRunner):
    """Runner for OpenAI GPT models with vision."""

    def __init__(self, model_id: str = "gpt-4o", max_tokens: int = 4096):
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._client = openai.OpenAI()

    @property
    def model_id(self) -> str:
        return self._model_id

    async def query(self, image_paths: list[str], prompt: str, task_id: str) -> ModelResponse:
        """Send images + prompt to GPT, return structured response."""
        content = []

        for img_path in image_paths:
            path = Path(img_path)
            with open(path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            media_type = "image/png" if path.suffix == ".png" else "image/jpeg"
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}",
                    "detail": "high",
                },
            })

        content.append({"type": "text", "text": prompt})

        start = time.monotonic()
        response = self._client.chat.completions.create(
            model=self._model_id,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        latency_ms = (time.monotonic() - start) * 1000

        answer_text = response.choices[0].message.content or ""

        return ModelResponse(
            model_id=self._model_id,
            task_id=task_id,
            answer=answer_text,
            raw_response={
                "id": response.id,
                "choices": [{"message": {"content": c.message.content}} for c in response.choices],
                "model": response.model,
            },
            latency_ms=latency_ms,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
