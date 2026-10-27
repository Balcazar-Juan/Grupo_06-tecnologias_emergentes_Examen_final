from __future__ import annotations

import httpx

from ..config import get_settings


async def explain_verdict(agent: str, deterministic_result: dict) -> dict:
    """Gemini explica resultados ya calculados. Nunca decide ni modifica reglas."""
    settings = get_settings()
    fallback = deterministic_result.get("summary", "Validación completada.")
    if not settings.gemini_api_key:
        return {"text": fallback, "source": "RULES", "model": None}

    prompt = (
        "Eres la capa explicativa de un sistema universitario de matrícula. "
        "Redacta en español peruano una explicación breve, clara y profesional para un estudiante. "
        "No cambies el estado, no inventes datos, no agregues requisitos y no recomiendes saltarse controles. "
        "Explica únicamente los datos autorizados que siguen. "
        f"Agente: {agent}. Resultado determinista: {deterministic_result}. "
        "Responde en máximo 70 palabras y sin encabezados."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 180},
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {"text": text or fallback, "source": "GEMINI", "model": settings.gemini_model}
    except Exception as exc:  # La matrícula no debe fallar si el proveedor de IA no responde.
        return {
            "text": fallback,
            "source": "RULES_FALLBACK",
            "model": settings.gemini_model,
            "provider_error": exc.__class__.__name__,
        }
