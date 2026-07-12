"""
Claude API client for the CAE chatbot.
Provides streaming responses grounded in the project's analysis context.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List

import structlog
from anthropic import AsyncAnthropic

from app.config import settings

logger = structlog.get_logger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are CAE Assistant, an expert in Computer-Aided Engineering (CAE) analysis.
You help engineers understand:
- FEA results (stress, displacement, modal frequencies, fatigue life)
- CFD results (velocity, pressure, heat transfer)
- Boundary condition setup and best practices
- Material selection for structural and thermal applications
- CalculiX and OpenFOAM solver settings
- Mesh quality and convergence criteria

IMPORTANT RULES:
1. Ground your answers in the actual analysis data provided in the context below.
2. Use SI units by default (MPa, mm, N, K) but clarify when using others.
3. Always flag when results suggest safety concerns and recommend licensed engineer review.
4. When referencing results, cite specific numbers from the context.
5. Be concise and technically precise. Avoid generic answers when specific data is available.
6. You are a decision-support tool — not a replacement for a qualified engineer's judgment.

Current project context:
{context_json}
"""


async def stream_chat_response(
    user_message: str,
    context: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Claude API for the given user message + project context.
    """
    client = _get_client()

    # Build message history
    history: List[Dict] = context.get("history", [])
    messages = []
    for h in history[:-1]:  # exclude the current user message (already in history)
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    system = SYSTEM_PROMPT.format(context_json=json.dumps(context, indent=2, default=str))

    try:
        async with client.messages.stream(
            model=settings.claude_model,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.error("Claude API error", error=str(e))
        yield f"\n\n[Error communicating with Claude API: {e}]"
