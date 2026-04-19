"""AI providers for Sparkling Water."""

from .base import BaseProvider, ModelInfo, ModelTier
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .openrouter import OpenRouterProvider
from .kilocode import KilocodeProvider
from .opencode import OpencodeProvider
from .nvidia import NVIDIAProvider
from .manager import ProviderManager, ProviderConfig, ModelSelection

__all__ = [
    "BaseProvider",
    "ModelInfo",
    "ModelTier",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "KilocodeProvider",
    "OpencodeProvider",
    "NVIDIAProvider",
    "ProviderManager",
    "ProviderConfig",
    "ModelSelection",
]
