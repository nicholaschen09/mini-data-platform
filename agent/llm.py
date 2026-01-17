"""LLM provider abstraction for easy swapping between providers."""

import os
import sys
from abc import ABC, abstractmethod
from .constants import MAX_LLM_TOKENS


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Generate a completion given system and user prompts."""
        pass


class GroqProvider(LLMProvider):
    """Groq LLM provider (default, free tier available)."""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY not set.", file=sys.stderr)
            print("Get a free key at: https://console.groq.com/keys", file=sys.stderr)
            sys.exit(1)
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=MAX_LLM_TOKENS
        )
        return response.choices[0].message.content.strip()


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
            print("Get a key at: https://platform.openai.com/api-keys", file=sys.stderr)
            sys.exit(1)
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=MAX_LLM_TOKENS
        )
        return response.choices[0].message.content.strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
            print("Get a key at: https://console.anthropic.com/settings/keys", file=sys.stderr)
            sys.exit(1)
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def complete(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_LLM_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return response.content[0].text.strip()


PROVIDERS = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider based on LLM_PROVIDER env var."""
    provider_name = os.environ.get("LLM_PROVIDER", "groq").lower()
    
    if provider_name not in PROVIDERS:
        print(f"Error: Unknown LLM_PROVIDER '{provider_name}'", file=sys.stderr)
        print(f"Supported: {', '.join(PROVIDERS.keys())}", file=sys.stderr)
        sys.exit(1)
    
    return PROVIDERS[provider_name]()
