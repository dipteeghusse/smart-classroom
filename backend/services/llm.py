"""
services/llm.py — Groq LLM service.

Direct Groq SDK — no LangChain wrapper needed.
Provides: chat(), chat_json() for structured output.
"""
import json
from groq import Groq
from backend.config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Send a chat request and return the reply as plain text."""
    response = _client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


def chat_json(system: str, user: str, temperature: float = 0.3) -> list | dict:
    """
    Request JSON output from the LLM.
    The system prompt must instruct the model to return valid JSON.
    Returns a parsed Python object (list or dict).
    """
    response_text = chat(
        system=system + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no extra text.",
        user=user,
        temperature=temperature,
        max_tokens=8000,
    )

    # Strip markdown code fences if the model adds them
    clean = response_text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    return json.loads(clean)
