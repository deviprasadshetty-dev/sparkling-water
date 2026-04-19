"""Gemini (Google) provider."""

from typing import List, Dict, Any, Optional
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class GeminiProvider(OpenAICompatibleProvider):
    """Gemini (Google) provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key, 
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    @property
    def provider_name(self) -> str:
        return "Gemini"

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for model."""
        model_id_lower = model_id.lower()
        if "1.5-pro" in model_id_lower:
            return 2800000
        if "1.5-flash" in model_id_lower:
            return 1000000
        if "2.0-flash" in model_id_lower:
            return 1000000
        return 128000

    def _get_input_cost(self, model_id: str) -> float:
        """Get input cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "1.5-pro" in model_id_lower:
            return 0.00125
        if "flash" in model_id_lower:
            return 0.000075
        return 0.0005

    def _get_output_cost(self, model_id: str) -> float:
        """Get output cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "1.5-pro" in model_id_lower:
            return 0.005
        if "flash" in model_id_lower:
            return 0.0003
        return 0.0015

    def _get_capabilities(self, model_id: str) -> List[str]:
        capabilities = ["chat", "code", "analysis", "vision"]
        if "pro" in model_id.lower() or "2.0" in model_id.lower():
            capabilities.append("reasoning")
        return capabilities

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="gemini-2.0-flash-exp",
                name="Gemini 2.0 Flash Experimental",
                provider="Gemini",
                tier=ModelTier.FRONTIER,
                context_window=1000000,
                input_cost_per_1k=0.000075,
                output_cost_per_1k=0.0003,
                description="Most capable model for complex tasks",
                capabilities=["chat", "code", "analysis", "reasoning", "vision"],
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                provider="Gemini",
                tier=ModelTier.SLM,
                context_window=1000000,
                input_cost_per_1k=0.000075,
                output_cost_per_1k=0.0003,
                description="Fast and efficient model for quick tasks",
                capabilities=["chat", "code", "analysis", "vision"],
            ),
        ]
