"""LLM provider implementations for paper screening."""

from .base import BaseLLM
from .claude import ClaudeLLM
from .openai import OpenAILLM
from .gemini import GeminiLLM


def get_llm(provider: str, api_key: str) -> BaseLLM:
    """
    Get LLM instance by provider name.

    Parameters
    ----------
    provider : str
        Provider name: 'claude', 'openai', or 'gemini'
    api_key : str
        API key for the provider

    Returns
    -------
    BaseLLM
        LLM instance
    """
    providers = {
        "claude": ClaudeLLM,
        "openai": OpenAILLM,
        "gemini": GeminiLLM,
    }
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Choose from: {list(providers.keys())}")
    return providers[provider](api_key)


__all__ = ["BaseLLM", "ClaudeLLM", "OpenAILLM", "GeminiLLM", "get_llm"]
