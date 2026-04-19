"""OpenRouter provider."""

from typing import List, Dict, Any, Optional
import aiohttp
from .base import OpenAICompatibleProvider, ModelInfo, ModelTier


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from explicit mapping."""
        # Default to MEDIUM for OpenRouter models since they vary widely
        # Users can override this by selecting specific models
        return ModelTier.MEDIUM

    async def fetch_models(self) -> List[ModelInfo]:
        """Fetch available OpenRouter models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://openrouter.ai/api/v1/models") as response:
                    if response.status != 200:
                        return self._get_default_models()

                    data = await response.json()
                    models = []

                    for model in data.get("data", []):
                        model_id = model.get("id")
                        pricing = model.get("pricing", {})
                        # OpenRouter pricing is per token, we need per 1k
                        input_cost = float(pricing.get("prompt", 0)) * 1000
                        output_cost = float(pricing.get("completion", 0)) * 1000
                        context_window = model.get("context_length", 128000)

                        models.append(
                            ModelInfo(
                                id=model_id,
                                name=model.get("name") or model_id,
                                provider="OpenRouter",
                                tier=self._get_model_tier(model_id),
                                context_window=context_window,
                                input_cost_per_1k=input_cost,
                                output_cost_per_1k=output_cost,
                                description=model.get("description"),
                                capabilities=["chat", "code", "analysis"],
                            )
                        )

                    if not models:
                        return self._get_default_models()
                    return models
        except Exception:
            return self._get_default_models()

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="openai/gpt-4o-mini",
                name="GPT-4o Mini",
                provider="OpenRouter",
                tier=ModelTier.SLM,
                context_window=128000,
                input_cost_per_1k=0.00015,
                output_cost_per_1k=0.0006,
                description="Fast and efficient model",
                capabilities=["chat", "code", "analysis"],
            ),
            ModelInfo(
                id="anthropic/claude-3.5-sonnet",
                name="Claude 3.5 Sonnet",
                provider="OpenRouter",
                tier=ModelTier.FRONTIER,
                context_window=200000,
                input_cost_per_1k=0.003,
                output_cost_per_1k=0.015,
                description="Most capable model",
                capabilities=["chat", "code", "analysis", "reasoning"],
            ),
        ]
