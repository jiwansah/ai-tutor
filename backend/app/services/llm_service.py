from typing import AsyncIterator
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.config import settings

logger = structlog.get_logger()
_openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
_anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def complete(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    model = model or settings.LLM_MODEL_MEDIUM
    if _openai is None:
        raise RuntimeError("OPENAI_API_KEY not configured")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = await _openai.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


async def stream(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> AsyncIterator[str]:
    model = model or settings.LLM_MODEL_MEDIUM
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    stream_resp = await _openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream_resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta