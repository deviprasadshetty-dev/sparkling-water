"""Kilocode provider."""

from typing import List, Dict, Any, Optional
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class KilocodeProvider(OpenAICompatibleProvider):
    """Kilocode provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, base_url="https://api.kilocode.ai/v1")

    @property
    def provider_name(self) -> str:
        return "Kilocode"

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from explicit mapping."""
        # Explicit tier mapping based on Kilocode's model documentation
        tier_mapping = {
            "kilocode-1b": ModelTier.SLM,
            "kilocode-7b": ModelTier.MEDIUM,
            "kilocode-34b": ModelTier.FRONTIER,
        }

        return tier_mapping.get(model_id, ModelTier.MEDIUM)

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="kilocode-7b",
                name="Kilocode 7B",
                provider="Kilocode",
                tier=ModelTier.MEDIUM,
                context_window=32768,
                input_cost_per_1k=0.0005,
                output_cost_per_1k=0.0005,
                description="Balanced model for most tasks",
                capabilities=["chat", "code", "analysis"],
            ),
        ]
