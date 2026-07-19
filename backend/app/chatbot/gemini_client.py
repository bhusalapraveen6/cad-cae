"""
Gemini API client for the CAE chatbot.
Provides streaming responses grounded in the project's analysis context.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List

import structlog
import httpx

from app.config import settings

logger = structlog.get_logger(__name__)


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
    user_api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Google Gemini API for the given user message + project context.
    """
    api_key = user_api_key or settings.gemini_api_key
    if not api_key:
        yield "\n\n[Error: No Gemini API key configured. Provide an API key in Settings.]"
        return

    contents = []
    
    # Add history
    history: List[Dict] = context.get("history", [])
    for h in history[:-1]:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["content"]}]})
        
    # Add current user message
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    # System instruction prompt
    system_text = SYSTEM_PROMPT.format(context_json=json.dumps(context, indent=2, default=str))
    
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_text}]
        },
        "generationConfig": {
            "maxOutputTokens": 1024,
            "temperature": 0.2
        }
    }

    model = settings.gemini_model or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}"

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=60.0) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error("Gemini API error status", status=response.status_code, response=err_body.decode())
                    yield f"\n\n[Error communicating with Gemini API: HTTP {response.status_code}]"
                    return

                buffer = ""
                async for text in response.aiter_text():
                    buffer += text
                    while True:
                        idx = buffer.find('{"candidates"')
                        if idx == -1:
                            break
                        
                        bracket_count = 0
                        end_idx = -1
                        for i in range(idx, len(buffer)):
                            if buffer[i] == '{':
                                bracket_count += 1
                            elif buffer[i] == '}':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_idx = i
                                    break
                        if end_idx != -1:
                            obj_str = buffer[idx:end_idx + 1]
                            buffer = buffer[end_idx + 1:]
                            try:
                                obj = json.loads(obj_str)
                                text_chunk = obj["candidates"][0]["content"]["parts"][0]["text"]
                                if text_chunk:
                                    yield text_chunk
                            except Exception:
                                pass
                        else:
                            break

    except Exception as e:
        logger.error("Gemini API stream error", error=str(e))
        yield f"\n\n[Error communicating with Gemini API: {e}]"
