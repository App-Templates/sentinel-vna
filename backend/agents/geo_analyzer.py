"""
Geo Analyzer Agent (Node 6b - parallel)
Analyzes revenue drops by geographic cluster.
Uses Claude Haiku with pure-Python fallback.
"""

import json
import os
from pathlib import Path
from typing import List

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.geo_analyzer")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "geo_analyzer_prompt.txt"

GEO_CLUSTER_NAMES = {
    "ITA": "Italy",
    "ES": "Spain",
    "OTHER": "Other (BR, MX, AR, PT, CO, etc.)",
}


def _compute_geo_breakdown(state: AlertState) -> List[dict]:
    """Compute per-geo-cluster contribution to total drop."""
    delta = state.get("delta", {})
    geo_deltas = delta.get("geo", {})

    if not geo_deltas:
        return []

    total_drop = delta.get("revenue_abs", 0)
    if total_drop >= 0:
        total_drop = sum(
            g.get("revenue_delta_abs", 0)
            for g in geo_deltas.values()
            if g.get("revenue_delta_abs", 0) < 0
        )
        if total_drop >= 0:
            total_drop = -1

    breakdown = []
    for cluster, gdata in geo_deltas.items():
        delta_abs = gdata.get("revenue_delta_abs", 0)
        delta_pct = gdata.get("revenue_delta_pct", 0)
        rev_current = gdata.get("revenue_current", 0)
        rev_baseline = gdata.get("revenue_baseline", 0)

        quota = round((delta_abs / total_drop) * 100, 2) if total_drop != 0 else 0

        if delta_pct <= -5:
            status = "declining"
        elif delta_pct >= 2:
            status = "growing"
        else:
            status = "stable"

        breakdown.append({
            "cluster": cluster,
            "cluster_name": GEO_CLUSTER_NAMES.get(cluster, cluster),
            "revenue_current": rev_current,
            "revenue_baseline": rev_baseline,
            "delta_eur": delta_abs,
            "delta_pct": delta_pct,
            "quota_of_drop": abs(quota) if delta_abs < 0 else 0,
            "status": status,
        })

    # Sort by drop magnitude
    breakdown.sort(key=lambda x: x["delta_eur"])

    return breakdown


def _statistical_analysis(state: AlertState) -> AlertState:
    """Pure-Python geo analysis."""
    breakdown = _compute_geo_breakdown(state)

    return {
        **state,
        "geo_breakdown": breakdown,
    }


def _llm_analysis(state: AlertState) -> AlertState:
    """LLM-enhanced geo analysis."""
    from backend.utils.llm_retry import call_llm_with_retry

    breakdown = _compute_geo_breakdown(state)
    delta = state.get("delta", {})

    table_lines = ["| Cluster | Current | Baseline | Delta EUR | Delta % | Quota % | Status |"]
    table_lines.append("|---------|---------|----------|-----------|---------|---------|--------|")
    for g in breakdown:
        table_lines.append(
            f"| {g['cluster']} | {g['revenue_current']:,.0f} | "
            f"{g['revenue_baseline']:,.0f} | {g['delta_eur']:,.0f} | "
            f"{g['delta_pct']:+.1f}% | {g['quota_of_drop']:.1f}% | {g['status']} |"
        )

    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        return _statistical_analysis(state)

    prompt = template.format(
        channel_group=state.get("channel_group", "GOOGLE"),
        total_rev_delta=f"{delta.get('revenue_abs', 0):,.0f}",
        total_rev_delta_pct=f"{delta.get('revenue_pct', 0):+.1f}",
        severity=state.get("severity", "P1"),
        geo_table="\n".join(table_lines),
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
        llm_analysis = result.get("geo_analysis", [])
        # Merge LLM statuses back
        status_map = {g.get("cluster"): g.get("status", "unknown") for g in llm_analysis}
        for g in breakdown:
            if g["cluster"] in status_map:
                g["status"] = status_map[g["cluster"]]
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse LLM geo response, using statistical results")

    return {
        **state,
        "geo_breakdown": breakdown,
    }


def geo_analyzer_agent(state: AlertState) -> AlertState:
    """Main entry point for geo analysis."""
    logger.info("Geo analyzer started")
    errors = list(state.get("execution_errors", []))

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    try:
        if has_api_key:
            try:
                result = _llm_analysis(state)
                logger.info("LLM geo analysis complete, %d clusters", len(result.get("geo_breakdown", [])))
                return {**result, "execution_errors": errors}
            except Exception as e:
                logger.warning("LLM geo analysis failed (%s), using fallback", e)
                errors.append(f"LLM geo analysis failed: {e}")

        result = _statistical_analysis(state)
        logger.info("Statistical geo analysis complete, %d clusters", len(result.get("geo_breakdown", [])))
        return {**result, "execution_errors": errors}

    except Exception as e:
        logger.error("Geo analysis failed: %s", e)
        errors.append(f"Geo analysis error: {e}")
        return {
            **state,
            "geo_breakdown": [],
            "execution_errors": errors,
        }
