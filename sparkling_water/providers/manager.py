"""Provider manager for managing multiple AI providers."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path
import json

from .base import BaseProvider, ModelInfo, ModelTier
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .openrouter import OpenRouterProvider
from .kilocode import KilocodeProvider
from .opencode import OpencodeProvider
from .nvidia import NVIDIAProvider


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    name: str
    api_key: Optional[str] = None
    enabled: bool = True
    primary_model: Optional[str] = None
    secondary_model: Optional[str] = None


@dataclass
class ModelSelection:
    """Model selection configuration."""

    primary_provider: str
    primary_model: str
    secondary_provider: Optional[str] = None
    secondary_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_provider": self.primary_provider,
            "primary_model": self.primary_model,
            "secondary_provider": self.secondary_provider,
            "secondary_model": self.secondary_model,
        }


class ProviderManager:
    """Manager for multiple AI providers."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or Path.home() / ".sparkling_water_providers.json"
        self.providers: Dict[str, BaseProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.model_selection: Optional[ModelSelection] = None
        self._lock = asyncio.Lock()

        # Initialize providers
        self._initialize_providers()

        # Load configuration
        self._load_config()

    def _initialize_providers(self):
        """Initialize all available providers."""
        provider_classes = {
            "Claude": ClaudeProvider,
            "OpenAI": OpenAIProvider,
            "Gemini": GeminiProvider,
            "OpenRouter": OpenRouterProvider,
            "Kilocode": KilocodeProvider,
            "Opencode": OpencodeProvider,
            "NVIDIA": NVIDIAProvider,
        }

        for name, provider_class in provider_classes.items():
            self.providers[name] = provider_class(api_key=None)

    def _load_config(self):
        """Load configuration from file."""
        config_path = Path(self.config_file)
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)

                # Load provider configs
                for provider_name, provider_config in config.get("providers", {}).items():
                    self.provider_configs[provider_name] = ProviderConfig(
                        name=provider_name,
                        api_key=provider_config.get("api_key"),
                        enabled=provider_config.get("enabled", True),
                        primary_model=provider_config.get("primary_model"),
                        secondary_model=provider_config.get("secondary_model"),
                    )

                    # Update provider with API key
                    if provider_config.get("api_key"):
                        provider_class = type(self.providers[provider_name])
                        self.providers[provider_name] = provider_class(
                            api_key=provider_config["api_key"]
                        )

                # Load model selection
                model_selection = config.get("model_selection")
                if model_selection:
                    self.model_selection = ModelSelection(
                        primary_provider=model_selection.get("primary_provider"),
                        primary_model=model_selection.get("primary_model"),
                        secondary_provider=model_selection.get("secondary_provider"),
                        secondary_model=model_selection.get("secondary_model"),
                    )
            except Exception as e:
                print(f"Error loading config: {e}")

    def _save_config(self):
        """Save configuration to file."""
        config = {
            "providers": {},
            "model_selection": None,
        }

        # Save provider configs
        for name, provider_config in self.provider_configs.items():
            config["providers"][name] = {
                "api_key": provider_config.api_key,
                "enabled": provider_config.enabled,
                "primary_model": provider_config.primary_model,
                "secondary_model": provider_config.secondary_model,
            }

        # Save model selection
        if self.model_selection:
            config["model_selection"] = self.model_selection.to_dict()

        # Write to file
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def set_provider_api_key(self, provider_name: str, api_key: str):
        """Set API key for a provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Update provider config
        if provider_name not in self.provider_configs:
            self.provider_configs[provider_name] = ProviderConfig(name=provider_name)

        self.provider_configs[provider_name].api_key = api_key

        # Reinitialize provider with API key
        provider_class = type(self.providers[provider_name])
        self.providers[provider_name] = provider_class(api_key=api_key)

        # Save config
        self._save_config()

    def enable_provider(self, provider_name: str):
        """Enable a provider."""
        if provider_name not in self.provider_configs:
            self.provider_configs[provider_name] = ProviderConfig(name=provider_name)

        self.provider_configs[provider_name].enabled = True
        self._save_config()

    def disable_provider(self, provider_name: str):
        """Disable a provider."""
        if provider_name not in self.provider_configs:
            self.provider_configs[provider_name] = ProviderConfig(name=provider_name)

        self.provider_configs[provider_name].enabled = False
        self._save_config()

    def set_model_selection(
        self,
        primary_provider: str,
        primary_model: str,
        secondary_provider: Optional[str] = None,
        secondary_model: Optional[str] = None,
    ):
        """Set model selection."""
        self.model_selection = ModelSelection(
            primary_provider=primary_provider,
            primary_model=primary_model,
            secondary_provider=secondary_provider,
            secondary_model=secondary_model,
        )
        self._save_config()

    async def get_all_models(self, force_refresh: bool = False) -> Dict[str, List[ModelInfo]]:
        """Get all models from all enabled providers."""
        all_models = {}

        for provider_name, provider in self.providers.items():
            # Check if provider is enabled
            if provider_name in self.provider_configs:
                if not self.provider_configs[provider_name].enabled:
                    continue

            try:
                models = await provider.get_models(force_refresh=force_refresh)
                all_models[provider_name] = models
            except Exception as e:
                print(f"Error fetching models from {provider_name}: {e}")
                all_models[provider_name] = []

        return all_models

    async def get_models_by_provider(
        self, provider_name: str, force_refresh: bool = False
    ) -> List[ModelInfo]:
        """Get models from a specific provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        return await self.providers[provider_name].get_models(force_refresh=force_refresh)

    async def get_models_by_tier(self, tier: ModelTier) -> Dict[str, List[ModelInfo]]:
        """Get models by tier from all providers."""
        all_models = await self.get_all_models()
        models_by_tier = {}

        for provider_name, models in all_models.items():
            tier_models = [m for m in models if m.tier == tier]
            if tier_models:
                models_by_tier[provider_name] = tier_models

        return models_by_tier

    def get_primary_provider(self) -> Optional[BaseProvider]:
        """Get the primary provider."""
        if not self.model_selection:
            return None

        return self.providers.get(self.model_selection.primary_provider)

    def get_secondary_provider(self) -> Optional[BaseProvider]:
        """Get the secondary provider."""
        if not self.model_selection or not self.model_selection.secondary_provider:
            return None

        return self.providers.get(self.model_selection.secondary_provider)

    def get_primary_model(self) -> Optional[str]:
        """Get the primary model ID."""
        if not self.model_selection:
            return None

        return self.model_selection.primary_model

    def get_secondary_model(self) -> Optional[str]:
        """Get the secondary model ID."""
        if not self.model_selection:
            return None

        return self.model_selection.secondary_model

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        use_secondary: bool = False,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Get chat completion using selected model."""
        provider = self.get_secondary_provider() if use_secondary else self.get_primary_provider()
        model = self.get_secondary_model() if use_secondary else self.get_primary_model()

        if not provider or not model:
            raise RuntimeError("No provider or model selected. Please set model selection first.")

        return await provider.chat_completion(
            model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kwargs
        )

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self.providers.keys())

    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled providers."""
        enabled = []

        for provider_name in self.providers:
            if provider_name in self.provider_configs:
                if self.provider_configs[provider_name].enabled:
                    enabled.append(provider_name)
            else:
                # Default to enabled
                enabled.append(provider_name)

        return enabled

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers."""
        status = {}

        for provider_name, provider in self.providers.items():
            config = self.provider_configs.get(provider_name)

            status[provider_name] = {
                "enabled": config.enabled if config else True,
                "has_api_key": bool(config.api_key if config else False),
                "primary_model": config.primary_model if config else None,
                "secondary_model": config.secondary_model if config else None,
                "is_primary": self.model_selection.primary_provider == provider_name
                if self.model_selection
                else False,
                "is_secondary": self.model_selection.secondary_provider == provider_name
                if self.model_selection
                else False,
            }

        return status

    async def get_recommended_models(self) -> Dict[str, Dict[str, Optional[ModelInfo]]]:
        """Get recommended models from all providers."""
        recommendations = {}

        for provider_name, provider in self.providers.items():
            try:
                recommended = provider.get_recommended_models()
                recommendations[provider_name] = recommended
            except Exception as e:
                recommendations[provider_name] = {
                    "slm": None,
                    "medium": None,
                    "frontier": None,
                }

        return recommendations
