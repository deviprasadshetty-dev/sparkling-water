"""Claude (Anthropic) provider."""

from typing import List, Dict, Any, Optional
import aiohttp
from .base import BaseProvider, ModelInfo, ModelTier


class ClaudeProvider(BaseProvider):
    """Claude (Anthropic) provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)

    @property
    def provider_name(self) -> str:
        return "Claude"

    @property
    def base_url(self) -> str:
        return "https://api.anthropic.com/v1"

    async def fetch_models(self) -> List[ModelInfo]:
        """Fetch available Claude models."""
        if not self.api_key:
            return self._get_default_models()

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/models", headers=headers) as response:
                    if response.status != 200:
                        return self._get_default_models()
                    
                    data = await response.json()
                    models = []

                    for model in data.get("data", []):
                        model_id = model.get("id")
                        tier = self._classify_model_tier(model_id)
                        
                        models.append(
                            ModelInfo(
                                id=model_id,
                                name=model.get("display_name") or model_id,
                                provider="Claude",
                                tier=tier,
                                context_window=200000, # Claude default
                                input_cost_per_1k=self._get_input_cost(model_id),
                                output_cost_per_1k=self._get_output_cost(model_id),
                                description=f"Claude model: {model.get('display_name') or model_id}",
                                capabilities=self._get_capabilities(model_id),
                            )
                        )
                    
                    if not models:
                        return self._get_default_models()
                    return models
        except Exception:
            return self._get_default_models()

    def _classify_model_tier(self, model_id: str) -> ModelTier:
        """Classify model tier based on ID."""
        model_id_lower = model_id.lower()
        if "opus" in model_id_lower:
            return ModelTier.FRONTIER
        if "sonnet" in model_id_lower:
            if "3-5" in model_id_lower:
                return ModelTier.FRONTIER
            return ModelTier.MEDIUM
        if "haiku" in model_id_lower:
            return ModelTier.SLM
        return ModelTier.MEDIUM

    def _get_input_cost(self, model_id: str) -> float:
        """Get input cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "claude-3-5-sonnet" in model_id_lower:
            return 0.003
        if "claude-3-5-haiku" in model_id_lower:
            return 0.0008
        if "claude-3-opus" in model_id_lower:
            return 0.015
        if "claude-3-sonnet" in model_id_lower:
            return 0.003
        if "claude-3-haiku" in model_id_lower:
            return 0.00025
        return 0.003

    def _get_output_cost(self, model_id: str) -> float:
        """Get output cost per 1K tokens."""
        model_id_lower = model_id.lower()
        if "claude-3-5-sonnet" in model_id_lower:
            return 0.015
        if "claude-3-5-haiku" in model_id_lower:
            return 0.004
        if "claude-3-opus" in model_id_lower:
            return 0.075
        if "claude-3-sonnet" in model_id_lower:
            return 0.015
        if "claude-3-haiku" in model_id_lower:
            return 0.00125
        return 0.015

    def _get_capabilities(self, model_id: str) -> List[str]:
        """Get model capabilities."""
        capabilities = ["chat", "code", "analysis"]
        if "opus" in model_id.lower() or "sonnet" in model_id.lower():
            capabilities.append("reasoning")
        return capabilities

    def _get_default_models(self) -> List[ModelInfo]:
        """Get default models if API call fails."""
        return [
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider="Claude",
                tier=ModelTier.FRONTIER,
                context_window=200000,
                input_cost_per_1k=0.003,
                output_cost_per_1k=0.015,
                description="Most capable model for complex tasks",
                capabilities=["chat", "code", "analysis", "reasoning"],
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                name="Claude 3.5 Haiku",
                provider="Claude",
                tier=ModelTier.SLM,
                context_window=200000,
                input_cost_per_1k=0.0008,
                output_cost_per_1k=0.004,
                description="Fast and efficient model for quick tasks",
                capabilities=["chat", "code", "analysis"],
            ),
        ]

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Get chat completion from Claude using aiohttp."""
        if not self.api_key:
            raise RuntimeError("Claude API key not provided.")

        system_message = None
        claude_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append(msg)

        payload = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_message:
            payload["system"] = system_message

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/messages", headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Claude API error ({response.status}): {text}")
                
                data = await response.json()
                return data["content"][0]["text"]
