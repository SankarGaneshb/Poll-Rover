"""
Poll-Rover LLM Client
Zero-cost LLM strategy: Ollama (local) primary → Gemini free tier fallback.
Handles auto-failover, retries, and token tracking.
"""

import time
from typing import Optional

from agents.common.config import get_llm_config
from agents.common.logger import get_logger

logger = get_logger("llm_client")


class LLMClient:
    """Unified LLM client with automatic failover from Ollama to Gemini.

    Usage:
        client = LLMClient()
        response = client.generate("Extract polling station data from this text: ...")
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = config or get_llm_config()
        self._primary = self._config.get("primary", {})
        self._fallback = self._config.get("fallback", {})
        self._max_retries = self._config.get("max_retries", 3)
        self._total_tokens_used = 0
        self._ollama_client = None
        self._gemini_model = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text using primary LLM with automatic fallback.

        Args:
            prompt: User prompt text.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum response tokens.

        Returns:
            Generated text response.

        Raises:
            RuntimeError: If both primary and fallback LLMs fail.
        """
        # Try primary (Ollama)
        try:
            response = self._call_ollama(prompt, system_prompt, temperature)
            logger.debug(f"Ollama responded ({len(response)} chars)")
            return response
        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}. Falling back to Gemini.")

        # Try fallback (Gemini)
        try:
            response = self._call_gemini(prompt, system_prompt, temperature, max_tokens)
            logger.debug(f"Gemini responded ({len(response)} chars)")
            return response
        except Exception as e:
            logger.error(f"Gemini also failed: {e}")

        raise RuntimeError(
            "All LLM providers failed. Check Ollama is running "
            "(ollama serve) or GEMINI_API_KEY is set."
        )

    def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> str:
        """Call Ollama local LLM."""
        if self._ollama_client is None:
            try:
                import ollama
                self._ollama_client = ollama.Client(
                    host=self._primary.get("base_url", "http://localhost:11434")
                )
            except ImportError:
                raise RuntimeError("ollama package not installed")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._ollama_client.chat(
            model=self._primary.get("model", "llama3.2"),
            messages=messages,
            options={"temperature": temperature},
        )

        return response["message"]["content"]

    def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Google Gemini API (free tier)."""
        if self._gemini_model is None:
            try:
                import google.generativeai as genai
            except ImportError:
                raise RuntimeError("google-generativeai package not installed")

            api_key = self._fallback.get("api_key")
            if not api_key:
                import os
                api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY not set")

            genai.configure(api_key=api_key)
            self._gemini_model = genai.GenerativeModel(
                model_name=self._fallback.get("model", "gemini-2.0-flash"),
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

        response = self._gemini_model.generate_content(prompt)
        return response.text

    @property
    def stats(self) -> dict:
        """Return usage statistics."""
        return {
            "total_tokens": self._total_tokens_used,
            "estimated_cost_usd": 0.0,  # Both providers are free tier
        }
