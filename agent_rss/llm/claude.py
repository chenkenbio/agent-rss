"""Claude (Anthropic) LLM provider."""

import logging

from anthropic import Anthropic

from .base import BaseLLM

logger = logging.getLogger(__name__)


class ClaudeLLM(BaseLLM):
    """Claude LLM provider using Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude LLM.

        Parameters
        ----------
        api_key : str
            Anthropic API key
        model : str
            Model name to use
        """
        super().__init__(api_key)
        self.model = model
        self.client = Anthropic(api_key=api_key)

    def _call_api(self, prompt: str) -> str:
        """Call Claude API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
