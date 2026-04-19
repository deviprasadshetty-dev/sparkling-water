"""Opencode provider."""

from typing import List, Dict, Any, Optional
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class OpencodeProvider(OpenAICompatibleProvider):
    """Opencode provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, base_url="https://api.opencode.ai/v1")

    @property
    def provider_name(self) -> str:
        return "Opencode"

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from explicit mapping."""
        # Explicit tier mapping based on Opencode's model documentation
        tier_mapping = {
            "opencode-mini": ModelTier.SLM,
            "opencode-standard": ModelTier.MEDIUM,
            "opencode-pro": ModelTier.FRONTIER,
        }

        return tier_mapping.get(model_id, ModelTier.MEDIUM)

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="opencode-standard",
                name="Opencode Standard",
                provider="Opencode",
                tier=ModelTier.MEDIUM,
                context_window=65536,
                input_cost_per_1k=0.0005,
                output_cost_per_1k=0.0005,
                description="Balanced model for code tasks",
                capabilities=["chat", "code", "analysis", "reasoning"],
            ),
        ]
