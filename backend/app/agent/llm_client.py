import json
from langchain_groq import ChatGroq

from app.config import settings

_fast_llm = None
_reasoning_llm = None


def fast_llm() -> ChatGroq:
    """gemma2-9b-it — router/intent classification + structured extraction. Low latency."""
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_fast_model,
            temperature=0,
        )
    return _fast_llm


def reasoning_llm() -> ChatGroq:
    """llama-3.3-70b-versatile — heavier reasoning: next-best-action, compliance scanning."""
    global _reasoning_llm
    if _reasoning_llm is None:
        _reasoning_llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_reasoning_model,
            temperature=0.2,
        )
    return _reasoning_llm


def call_json(llm: ChatGroq, system_prompt: str, user_content: str) -> dict:
    """
    Calls the LLM with instructions to return ONLY JSON, and parses it.
    Raises ValueError with the raw text if parsing fails, so callers can
    decide how to degrade gracefully.
    """
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt + "\n\nRespond with ONLY valid JSON. No markdown fences, no preamble."},
            {"role": "user", "content": user_content},
        ]
    )
    text = response.content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {text}") from e
