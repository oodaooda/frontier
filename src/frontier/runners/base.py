"""Base class for model runners."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResponse:
    """Raw response from a model."""

    model_id: str
    task_id: str
    answer: str
    raw_response: dict
    latency_ms: float
    input_tokens: int
    output_tokens: int


class BaseRunner(ABC):
    """Abstract base for all model runners."""

    @abstractmethod
    async def query(self, image_paths: list[str], prompt: str, task_id: str) -> ModelResponse:
        """Send image(s) and a prompt to the model, return structured response."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier for this model (e.g., 'claude-opus-4-6')."""
        ...
