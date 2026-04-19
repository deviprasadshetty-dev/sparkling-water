"""Base provider interface for AI models."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    """Model tier classification."""

    SLM = "slm"  # Small Language Model (1B-4B)
    MEDIUM = "medium"  # Medium model (7B-30B)
    FRONTIER = "frontier"  # Large frontier model (100B+)


@dataclass
class ModelInfo:
    """Information about a model."""

    id: str
    name: str
    provider: str
    tier: ModelTier
    context_window: int
    input_cost_per_1k: float
    output_cost_per_1k: float
    description: Optional[str] = None
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class BaseProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._models_cache: Optional[List[ModelInfo]] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL for the provider."""
        pass

    @abstractmethod
    async def fetch_models(self) -> List[ModelInfo]:
        """Fetch available models from the provider."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Get chat completion from the model."""
        pass

    async def get_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """Get available models (with caching)."""
        if self._models_cache is None or force_refresh:
            self._models_cache = await self.fetch_models()
        return self._models_cache

    def get_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        """Get model info by ID."""
        if self._models_cache:
            for model in self._models_cache:
                if model.id == model_id:
                    return model
        return None

    def get_models_by_tier(self, tier: ModelTier) -> List[ModelInfo]:
        """Get models by tier."""
        if self._models_cache:
            return [m for m in self._models_cache if m.tier == tier]
        return []

    def get_recommended_models(self) -> Dict[str, ModelInfo]:
        """Get recommended models for different use cases."""
        models = {
            "slm": None,
            "medium": None,
            "frontier": None,
        }

        if self._models_cache:
            slm_models = self.get_models_by_tier(ModelTier.SLM)
            medium_models = self.get_models_by_tier(ModelTier.MEDIUM)
            frontier_models = self.get_models_by_tier(ModelTier.FRONTIER)

            if slm_models:
                models["slm"] = slm_models[0]
            if medium_models:
                models["medium"] = medium_models[0]
            if frontier_models:
                models["frontier"] = frontier_models[0]

        return models


class OpenAICompatibleProvider(BaseProvider):
    """Base class for providers that use OpenAI-compatible API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key)
        self._custom_base_url = base_url
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url) if api_key else None

    @property
    def base_url(self) -> str:
        return self._custom_base_url or "https://api.openai.com/v1"

    async def fetch_models(self) -> List[ModelInfo]:
        """Fetch available models using OpenAI API."""
        if not self.client:
            return self._get_default_models()

        try:
            models_response = await self.client.models.list()
            models = []

            for model in models_response.data:
                # Get tier from provider-specific mapping
                tier = self._get_model_tier(model.id)
                models.append(
                    ModelInfo(
                        id=model.id,
                        name=getattr(model, "name", model.id) or model.id,
                        provider=self.provider_name,
                        tier=tier,
                        context_window=self._get_context_window(model.id),
                        input_cost_per_1k=self._get_input_cost(model.id),
                        output_cost_per_1k=self._get_output_cost(model.id),
                        description=getattr(model, "description", f"{self.provider_name} model"),
                        capabilities=self._get_capabilities(model.id),
                    )
                )

            return models if models else self._get_default_models()
        except Exception:
            return self._get_default_models()

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Get chat completion from OpenAI-compatible API."""
        if not self.client:
            raise RuntimeError(f"{self.provider_name} client not initialized.")

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens or 4096,
            temperature=temperature,
            **kwargs,
        )

        return response.choices[0].message.content

    def _get_model_tier(self, model_id: str) -> ModelTier:
        """Get model tier from provider-specific mapping. Override in subclasses."""
        # Default to MEDIUM if not overridden
        return ModelTier.MEDIUM

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for model. Override in subclasses."""
        return 128000

    def _get_input_cost(self, model_id: str) -> float:
        """Get input cost per 1K tokens. Override in subclasses."""
        return 0.001

    def _get_output_cost(self, model_id: str) -> float:
        """Get output cost per 1K tokens. Override in subclasses."""
        return 0.002

    def _get_capabilities(self, model_id: str) -> List[str]:
        """Get model capabilities. Override in subclasses."""
        return ["chat", "code", "analysis"]

    @abstractmethod
    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails. Must be implemented by subclasses."""
        pass
