from app.ai.base import AIProvider
from app.core.config import get_settings


class NoopProvider(AIProvider):
    """Placeholder provider used until a real provider is configured."""

    def is_configured(self) -> bool:
        return False

    def complete(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("No AI provider is configured yet.")


def get_ai_provider() -> AIProvider:
    settings = get_settings()

    if settings.ai_provider == "none":
        return NoopProvider()

    # Real providers (OpenAI, Anthropic, etc.) are registered here
    # in a later phase.
    raise ValueError(f"Unknown AI provider: {settings.ai_provider}")