"""OpenAI provider."""

from typing import List, Dict, Any, Optional
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for model."""
        model_id_lower = model_id.lower()
        if "gpt-4o" in model_id_lower:
            return 128000
        elif "gpt-4-turbo" in model_id_lower:
            return 128000
        elif "gpt-3.5" in model_id_lower:
            return 16385
        elif "o1" in model_id_lower:
            return 200000
        return 8192

    def _get_input_cost(self, model_id: str) -> float:
        """Get input cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "gpt-4o-mini" in model_id_lower:
            return 0.00015
        elif "gpt-4o" in model_id_lower:
            return 0.0025
        elif "gpt-4-turbo" in model_id_lower:
            return 0.01
        elif "gpt-3.5" in model_id_lower:
            return 0.0005
        elif "o1" in model_id_lower:
            return 0.015
        return 0.01

    def _get_output_cost(self, model_id: str) -> float:
        """Get output cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "gpt-4o-mini" in model_id_lower:
            return 0.0006
        elif "gpt-4o" in model_id_lower:
            return 0.01
        elif "gpt-4-turbo" in model_id_lower:
            return 0.03
        elif "gpt-3.5" in model_id_lower:
            return 0.0015
        elif "o1" in model_id_lower:
            return 0.06
        return 0.03

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from explicit mapping based on actual model capabilities."""
        # Explicit tier mapping based on OpenAI's model documentation
        tier_mapping = {
            # SLM models (fast, efficient, for simple tasks)
            "gpt-4o-mini": ModelTier.SLM,
            "gpt-3.5-turbo": ModelTier.SLM,
            "gpt-3.5-turbo-16k": ModelTier.SLM,
            "gpt-3.5-turbo-instruct": ModelTier.SLM,
            # Medium models (balanced, for most tasks)
            "gpt-4o": ModelTier.MEDIUM,
            "gpt-4-turbo": ModelTier.MEDIUM,
            "gpt-4-turbo-preview": ModelTier.MEDIUM,
            "gpt-4-turbo-2024-04-09": ModelTier.MEDIUM,
            "o1-mini": ModelTier.MEDIUM,
            # Frontier models (most capable, for complex tasks)
            "gpt-4": ModelTier.FRONTIER,
            "gpt-4-32k": ModelTier.FRONTIER,
            "gpt-4-turbo-2024-04-09": ModelTier.FRONTIER,
            "o1-preview": ModelTier.FRONTIER,
            "o1": ModelTier.FRONTIER,
        }

        return tier_mapping.get(model_id, ModelTier.MEDIUM)

    def _get_capabilities(self, model_id: str) -> List[str]:
        """Get model capabilities."""
        capabilities = ["chat", "code", "analysis"]
        if "gpt-4" in model_id.lower() or "o1" in model_id.lower():
            capabilities.append("vision")
        return capabilities

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                provider="OpenAI",
                tier=ModelTier.SLM,
                context_window=128000,
                input_cost_per_1k=0.00015,
                output_cost_per_1k=0.0006,
                description="Fast and efficient model for most tasks",
                capabilities=["chat", "code", "analysis"],
            ),
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                provider="OpenAI",
                tier=ModelTier.MEDIUM,
                context_window=128000,
                input_cost_per_1k=0.0025,
                output_cost_per_1k=0.01,
                description="Most capable model for complex tasks",
                capabilities=["chat", "code", "analysis", "vision"],
            ),
        ]
