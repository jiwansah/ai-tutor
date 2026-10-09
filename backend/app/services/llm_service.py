from typing import AsyncIterator
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
import re

def _strip_json_wrappers(text: str) -> str:
    """Remove markdown fences and surrounding prose from an LLM JSON response."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```\s*$", "", t)
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        t = t[first:last + 1]
    return t.strip()

_client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL or "https://api.openai.com/v1",
    api_key=settings.LLM_API_KEY or "ollama",
    timeout=180.0,
)


def _is_ollama() -> bool:
    return "11434" in (settings.LLM_BASE_URL or "")


# ---------------------------------------------------------------
# Legacy single-turn API
# ---------------------------------------------------------------

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=8))
async def complete(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return await complete_chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )


# ---------------------------------------------------------------
# Multi-turn chat API
# ---------------------------------------------------------------

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=8))
async def complete_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    kwargs = dict(
        model=model or settings.LLM_MODEL_MEDIUM,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if json_mode:
        # Both OpenAI and Ollama (OpenAI-compatible endpoint) accept this.
        kwargs["response_format"] = {"type": "json_object"}

    r = await _client.chat.completions.create(**kwargs)
    content = r.choices[0].message.content or ""
    if json_mode:
        content = _strip_json_wrappers(content)
    return content


# ---------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------

async def stream(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> AsyncIterator[str]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    async for tok in stream_chat(
        messages, model=model, temperature=temperature, max_tokens=max_tokens,
    ):
        yield tok


async def stream_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> AsyncIterator[str]:
    stream_resp = await _client.chat.completions.create(
        model=model or settings.LLM_MODEL_MEDIUM,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream_resp:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        if content:
            yield content