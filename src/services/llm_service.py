"""
LLM Service - Unified interface for Anthropic Claude and Google Gemini
Supports both synchronous calls (for debate exchanges) and streaming (for SSE panels)
"""
import anthropic
from google import genai as google_genai
from google.genai import types as genai_types
from typing import Optional, Generator, Tuple, Dict


class LLMService:
    """Unified interface for Claude and Gemini APIs"""

    def __init__(self, anthropic_key: Optional[str] = None, google_key: Optional[str] = None):
        self.anthropic_key = anthropic_key
        self.google_key = google_key
        self.anthropic_client = None
        self.gemini_configured = False
        self._last_usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

        if anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)

        if google_key:
            self.gemini_client = google_genai.Client(api_key=google_key)
            self.gemini_configured = True
        else:
            self.gemini_client = None

    def call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Tuple[str, Dict[str, int]]:
        """
        Synchronous model call. Returns (response_text, token_usage_dict).
        Used by the debate orchestrator for each exchange.
        """
        if model.startswith("claude"):
            return self._call_claude(model, prompt, system_prompt, temperature, max_tokens)
        elif model.startswith("gemini"):
            return self._call_gemini(model, prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}. Must start with 'claude' or 'gemini'.")

    def stream_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Generator[str, None, None]:
        """
        Streaming model call. Yields text chunks.
        Token usage is available via get_last_usage() after the generator is exhausted.
        Used by standard analysis and final review SSE endpoints.
        """
        self._last_usage = {"input_tokens": 0, "output_tokens": 0}
        if model.startswith("claude"):
            yield from self._stream_claude(model, prompt, system_prompt, temperature, max_tokens)
        elif model.startswith("gemini"):
            yield from self._stream_gemini(model, prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}. Must start with 'claude' or 'gemini'.")

    def get_last_usage(self) -> Dict[str, int]:
        """Return token usage from the most recent streaming call."""
        return self._last_usage

    # ── Synchronous implementations ──────────────────────────────────────────

    def _call_claude(self, model, prompt, system_prompt, temperature, max_tokens):
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured. Please set your API key.")

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.anthropic_client.messages.create(**kwargs)
        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text, usage

    def _call_gemini(self, model, prompt, system_prompt, temperature, max_tokens):
        if not self.gemini_configured or not self.gemini_client:
            raise ValueError("Google API key not configured. Please set your API key.")

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt if system_prompt else None,
        )
        response = self.gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        text = response.text or ""
        usage = {"input_tokens": 0, "output_tokens": 0}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage["input_tokens"] = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            usage["output_tokens"] = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        return text, usage

    # ── Streaming implementations ─────────────────────────────────────────────

    def _stream_claude(self, model, prompt, system_prompt, temperature, max_tokens):
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured. Please set your API key.")

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        with self.anthropic_client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
            # Capture token usage after stream completes
            final_msg = stream.get_final_message()
            self._last_usage = {
                "input_tokens": final_msg.usage.input_tokens,
                "output_tokens": final_msg.usage.output_tokens,
            }

    def _stream_gemini(self, model, prompt, system_prompt, temperature, max_tokens):
        if not self.gemini_configured or not self.gemini_client:
            raise ValueError("Google API key not configured. Please set your API key.")

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt if system_prompt else None,
        )
        for chunk in self.gemini_client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
        # Gemini streaming doesn't reliably expose token counts
        self._last_usage = {"input_tokens": 0, "output_tokens": 0}


# Available models
AVAILABLE_MODELS = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-opus-4-6": "Claude Opus 4.6",
    "gemini-3-flash-preview": "Gemini 3 Flash",
    "gemini-3-pro-preview": "Gemini 3 Pro",
}
