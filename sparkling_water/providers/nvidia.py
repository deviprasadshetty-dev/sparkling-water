"""NVIDIA provider."""

from typing import List, Dict, Any, Optional
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class NVIDIAProvider(OpenAICompatibleProvider):
    """NVIDIA provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")

    @property
    def provider_name(self) -> str:
        return "NVIDIA"

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from explicit mapping."""
        # Explicit tier mapping based on NVIDIA's model documentation
        tier_mapping = {
            "nvidia/llama-3.1-405b-instruct": ModelTier.FRONTIER,
            "nvidia/llama-3.1-70b-instruct": ModelTier.MEDIUM,
            "nvidia/llama-3.1-8b-instruct": ModelTier.SLM,
            "nvidia/mistral-7b-instruct": ModelTier.SLM,
            "nvidia/mixtral-8x7b-instruct": ModelTier.MEDIUM,
        }

        return tier_mapping.get(model_id, ModelTier.MEDIUM)

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="nvidia/llama-3.1-70b-instruct",
                name="Llama 3.1 70B Instruct",
                provider="NVIDIA",
                tier=ModelTier.MEDIUM,
                context_window=131072,
                input_cost_per_1k=0.00027,
                output_cost_per_1k=0.00027,
                description="Balanced model for most tasks",
                capabilities=["chat", "code", "analysis"],
            ),
        ]
