"""Google Gemini LLM provider."""

import logging

from google import genai

from .base import BaseLLM

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini LLM.

        Parameters
        ----------
        api_key : str
            Google API key
        model : str
            Model name to use
        """
        super().__init__(api_key)
        self.model_name = model
        self.client = genai.Client(api_key=api_key)

    def _call_api(self, prompt: str) -> str:
        """Call Gemini API."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
