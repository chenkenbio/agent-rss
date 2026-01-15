"""OpenAI LLM provider."""

import logging

from openai import OpenAI

from .base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI LLM.

        Parameters
        ----------
        api_key : str
            OpenAI API key
        model : str
            Model name to use
        """
        super().__init__(api_key)
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def _call_api(self, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
