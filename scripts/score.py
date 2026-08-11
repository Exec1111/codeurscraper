"""LLM-based relevance scoring against natural-language criteria."""

import json
import os

from openai import OpenAI

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")

STAGE_A_SYSTEM = """Tu notes des missions freelance, agrégées depuis plusieurs sites
(codeur.com, free-work.com, ...), par rapport aux critères de recherche d'un
utilisateur. Tu ne vois qu'un extrait tronqué de chaque mission (pas la
description complète) : sois indulgent, le but de cette étape est juste
d'éliminer le bruit évident, pas d'être précis.

Réponds uniquement avec un JSON de la forme :
{"results": [{"id": <id>, "score": <0-100>}, ...]}
Un score haut = correspond bien aux critères. Un score bas = hors sujet ou
explicitement exclu par les critères. N'invente pas d'id, garde exactement
les mêmes que ceux fournis en entrée (des chaînes de caractères)."""

STAGE_B_SYSTEM = """Tu notes des missions freelance, agrégées depuis plusieurs sites
(codeur.com, free-work.com, ...), par rapport aux critères de recherche d'un
utilisateur. Cette fois tu as la description complète de chaque mission :
sois précis et exigeant.

Réponds uniquement avec un JSON de la forme :
{"results": [{"id": <id>, "score": <0-100>, "reason": "<1-2 phrases en
français expliquant la note>"}, ...]}
N'invente pas d'id, garde exactement les mêmes que ceux fournis en entrée (des
chaînes de caractères)."""


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _call(system: str, criteria: str, payload: list[dict]) -> dict[int, dict]:
    if not payload:
        return {}

    client = _client()
    user_content = (
        f"Critères de recherche de l'utilisateur:\n{criteria}\n\n"
        f"Missions à noter (JSON):\n{json.dumps(payload, ensure_ascii=False)}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    results = parsed.get("results", [])
    return {str(item["id"]): item for item in results if "id" in item}


def score_snippets(criteria: str, listings: list[dict]) -> dict[str, dict]:
    payload = [
        {
            "id": item["id"],
            "title": item["title"],
            "snippet": item["snippet"],
            "tags": item["tags"],
            "budget": item["budget"],
            "offers": item["offers"],
        }
        for item in listings
    ]
    return _call(STAGE_A_SYSTEM, criteria, payload)


def score_full_descriptions(criteria: str, listings: list[dict]) -> dict[str, dict]:
    payload = [
        {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "tags": item["tags"],
            "budget": item["budget"],
            "offers": item["offers"],
        }
        for item in listings
    ]
    return _call(STAGE_B_SYSTEM, criteria, payload)
