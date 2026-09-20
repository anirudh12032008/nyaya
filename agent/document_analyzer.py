"""AI-powered legal document analyzer for Nyaya."""

from __future__ import annotations

from typing import Any

from agent.client import HAIKU, ask


SYSTEM_PROMPT = """
You are Nyaya's Legal Document Analyzer.

Your task is to analyze a legal document and extract useful,
fact-based information for the user.

Return ONLY valid JSON with exactly these keys:

{
  "document_type": "",
  "parties": [],
  "important_dates": [],
  "laws_and_sections": [],
  "key_clauses": [],
  "obligations": [],
  "deadlines": [],
  "potential_risks": [],
  "required_actions": [],
  "simple_explanation": ""
}

Rules:
- Do not invent facts.
- Only extract information supported by the document.
- If information is unavailable, use an empty list or "Not specified".
- Mention exact law/section names when present.
- Potential risks must be framed as issues to review, not definitive legal conclusions.
- Keep the explanation simple and understandable.
- This is informational analysis, not legal advice.
"""


def analyze_document(document_text: str) -> dict[str, Any]:
    """Analyze a legal document using Nyaya's existing AI client."""

    if not document_text or not document_text.strip():
        return {
            "error": "The document does not contain readable text."
        }

    # Prevent extremely large documents from creating an oversized request.
    document_text = document_text[:30000]

    user_prompt = f"""
Analyze the following legal document.

DOCUMENT:
----------------
{document_text}
----------------

Return the requested JSON structure only.
"""

    try:
        result = ask(
            HAIKU,
            SYSTEM_PROMPT,
            user_prompt,
            json_mode=True,
            temperature=0.0,
            max_tokens=4096,
        )

        if not isinstance(result, dict):
            return {
                "error": "The analyzer returned an unexpected response format."
            }

        return result

    except Exception as exc:
        return {
            "error": f"Document analysis failed: {exc}"
        }