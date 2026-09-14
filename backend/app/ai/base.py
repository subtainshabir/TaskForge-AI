from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Base interface all AI providers must implement.

    Concrete providers (OpenAI, Anthropic, local models, etc.) and
    feature-specific services (task understanding, decomposition,
    embeddings, RAG, planning, agent tool-calling) are added in
    later phases under app/ai/.
    """

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError