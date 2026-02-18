"""
Contributor Analyzer Agent (Node 6a - parallel)
Identifies top publishers contributing to revenue drop.
Uses Claude Haiku for name normalization with pure-Python fallback.
"""

import json
import os
from pathlib import Path
from typing import List

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.contributor_analyzer")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "contributor_analyzer_prompt.txt"

# Known publisher display names for fallback
PUBLISHER_DISPLAY_NAMES = {
    "vocento": "Vocento",
    "prensaiberica": "Prensa Iberica",
    "mondadori": "Mondadori",
    "elespanol": "El Espanol",
    "dorvan": "Dorvan",
    "unidadeditorial": "Unidad Editorial",
    "thecore": "The Core",
    "alayansmedia": "Alayans Media",
    "grupogodo": "Grupo Godo",
    "piemme": "Piemme",
    "talksmedia": "Talks Media",
    "adplay": "AdPlay",
    "grupojoly": "Grupo Joly",
    "mediamond": "Mediamond",
    "eleconomista": "El Economista",
    "magellano": "Magellano",
    "movingup": "Moving Up",
    "infobae": "Infobae",
    "speed": "Speed",
    "terralatam": "Terra Latam",
    "mediaset": "Mediaset",
    "rpdigital": "RP Digital",
    "sociedadevicradesportiva": "Sociedade Vicra Desportiva",
    "larazon": "La Razon",
    "veesible": "Veesible",
    "svgruppe": "SV Gruppe",
    "larepublica": "La Repubblica",
    "webboh": "Webboh",
    "elnacional": "El Nacional",
    "grupoperfilbr": "Grupo Perfil BR",
    "eluniversal": "El Universal",
    "cofina": "Cofina",
    "grupomultimedios": "Grupo Multimedios",
    "noticiasilimitadas": "Noticias Ilimitadas",
    "yobee": "Yobee",
    "sportnetwork": "Sport Network",
}


def _compute_contributors(state: AlertState) -> List[dict]:
    """Compute per-publisher contribution to total revenue drop."""
    delta = state.get("delta", {})
    pub_deltas = delta.get("publishers", {})

    if not pub_deltas:
        return []

    # Total revenue drop (absolute)
    total_drop = delta.get("revenue_abs", 0)
    if total_drop >= 0:
        # No drop, still compute relative positions
        total_drop = sum(
            p.get("revenue_delta_abs", 0)
            for p in pub_deltas.values()
            if p.get("revenue_delta_abs", 0) < 0
        )
        if total_drop >= 0:
            total_drop = -1  # prevent division by zero

    contributors = []
    for pub_id, pub_data in pub_deltas.items():
        delta_abs = pub_data.get("revenue_delta_abs", 0)
        delta_pct = pub_data.get("revenue_delta_pct", 0)
        rev_current = pub_data.get("revenue_current", 0)
        rev_baseline = pub_data.get("revenue_baseline", 0)

        # Quota of drop: how much of the total drop is from this publisher
        quota = round((delta_abs / total_drop) * 100, 2) if total_drop != 0 else 0

        contributors.append({
            "publisher_id": pub_id,
            "display_name": PUBLISHER_DISPLAY_NAMES.get(pub_id, pub_id.title()),
            "revenue_current": rev_current,
            "revenue_baseline": rev_baseline,
            "delta_eur": delta_abs,
            "delta_pct": delta_pct,
            "quota_of_drop": abs(quota) if delta_abs < 0 else 0,
        })

    # Sort by absolute drop magnitude (largest drops first)
    contributors.sort(key=lambda x: x["delta_eur"])

    return contributors


def _statistical_analysis(state: AlertState) -> AlertState:
    """Pure-Python contributor analysis without LLM."""
    config = get_config()
    top_n = config.top_contributors.top_n
    min_quota = config.top_contributors.min_quota_percent

    all_contributors = _compute_contributors(state)

    # Filter: top_n and minimum quota
    filtered = [
        c for c in all_contributors[:top_n]
        if c["quota_of_drop"] >= min_quota or c["delta_eur"] < 0
    ][:top_n]

    # Concentration index: sum of top 3 quotas / 100
    top3_quota = sum(c["quota_of_drop"] for c in filtered[:3])
    concentration = round(top3_quota / 100, 2)

    return {
        **state,
        "contributors": filtered,
    }


def _llm_analysis(state: AlertState) -> AlertState:
    """LLM-enhanced contributor analysis for name normalization."""
    from backend.utils.llm_retry import call_llm_with_retry

    config = get_config()
    all_contributors = _compute_contributors(state)
    top_n = config.top_contributors.top_n
    filtered = all_contributors[:top_n]

    # Build table for prompt
    table_lines = ["| Publisher | Current | Baseline | Delta EUR | Delta % | Quota % |"]
    table_lines.append("|-----------|---------|----------|-----------|---------|---------|")
    for c in filtered:
        table_lines.append(
            f"| {c['publisher_id']} | {c['revenue_current']:,.0f} | "
            f"{c['revenue_baseline']:,.0f} | {c['delta_eur']:,.0f} | "
            f"{c['delta_pct']:+.1f}% | {c['quota_of_drop']:.1f}% |"
        )

    delta = state.get("delta", {})
    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        return _statistical_analysis(state)

    prompt = template.format(
        channel_group=state.get("channel_group", "GOOGLE"),
        total_rev_delta=f"{delta.get('revenue_abs', 0):,.0f}",
        total_rev_delta_pct=f"{delta.get('revenue_pct', 0):+.1f}",
        severity=state.get("severity", "P1"),
        triage_label=state.get("triage_label", "UNKNOWN"),
        contributors_table="\n".join(table_lines),
    )

    raw_text = call_llm_with_retry(
        model="claude-haiku-4-5-20251001",
        prompt=prompt,
        max_tokens=1024,
    )
    if raw_text is None:
        raise RuntimeError("LLM call failed after retries")
    try:
        if "```json" in raw_text:
            json_str = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_str = raw_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw_text.strip()
        result = json.loads(json_str)
        normalized = result.get("normalized_contributors", filtered)
        # Merge LLM display names back
        name_map = {c["publisher_id"]: c.get("display_name", c["publisher_id"]) for c in normalized}
        for c in filtered:
            if c["publisher_id"] in name_map:
                c["display_name"] = name_map[c["publisher_id"]]
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse LLM contributor response, using fallback names")

    return {
        **state,
        "contributors": filtered,
    }


def contributor_analyzer_agent(state: AlertState) -> AlertState:
    """Main entry point for contributor analysis."""
    logger.info("Contributor analyzer started")
    errors = list(state.get("execution_errors", []))

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    try:
        if has_api_key:
            try:
                result = _llm_analysis(state)
                logger.info("LLM contributor analysis complete, %d contributors", len(result.get("contributors", [])))
                return {**result, "execution_errors": errors}
            except Exception as e:
                logger.warning("LLM contributor analysis failed (%s), using fallback", e)
                errors.append(f"LLM contributor analysis failed: {e}")

        result = _statistical_analysis(state)
        logger.info("Statistical contributor analysis complete, %d contributors", len(result.get("contributors", [])))
        return {**result, "execution_errors": errors}

    except Exception as e:
        logger.error("Contributor analysis failed: %s", e)
        errors.append(f"Contributor analysis error: {e}")
        return {
            **state,
            "contributors": [],
            "execution_errors": errors,
        }
