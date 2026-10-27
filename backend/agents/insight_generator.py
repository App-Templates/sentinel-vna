"""
Insight Generator Agent (Node 7)
Cross-dimensional correlation analysis and prioritized findings.
Uses Claude Sonnet with template-based fallback.
"""

import json
import os
from pathlib import Path

from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.insight_generator")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "insight_generator_prompt.txt"

TRIAGE_DESCRIPTIONS = {
    "MIXED": "Both traffic (bacino) and coverage are declining, suggesting a broad supply-side issue.",
    "TRAFFIC_DRIVEN": "Bacino (traffic/impressions) is the primary driver of the revenue drop. Coverage is relatively stable.",
    "COVERAGE_DRIVEN": "Coverage decline is the main factor. Traffic is relatively stable but fewer impressions are being monetized.",
    "REVENUE_ONLY": "Revenue is declining without corresponding drops in traffic or coverage. This is incoherent and may indicate a pricing/demand issue.",
    "NO_ALERT": "No significant anomaly detected.",
}


def _format_contributors_summary(contributors: list) -> str:
    """Format contributors list into readable summary."""
    if not contributors:
        return "No contributor data available."
    lines = []
    for c in contributors[:5]:
        lines.append(
            f"- {c.get('display_name', c.get('publisher_id', 'Unknown'))}: "
            f"delta {c.get('delta_pct', 0):+.1f}%, quota of drop {c.get('quota_of_drop', 0):.1f}%"
        )
    return "\n".join(lines)


def _format_geo_summary(geo_breakdown: list) -> str:
    """Format geo breakdown into readable summary."""
    if not geo_breakdown:
        return "No geographic data available."
    lines = []
    for g in geo_breakdown:
        lines.append(
            f"- {g.get('cluster', 'Unknown')} ({g.get('cluster_name', '')}): "
            f"delta {g.get('delta_pct', 0):+.1f}%, quota {g.get('quota_of_drop', 0):.1f}%, "
            f"status: {g.get('status', 'unknown')}"
        )
    return "\n".join(lines)


def _format_env_summary(env_split: dict) -> str:
    """Format environment split into readable summary."""
    if not env_split:
        return "No environment data available."
    lines = []
    for env_name in ("WEB", "AMP", "APP"):
        e = env_split.get(env_name, {})
        if isinstance(e, dict):
            lines.append(
                f"- {env_name}: current {e.get('revenue_current', 0):,.0f} EUR, "
                f"baseline {e.get('revenue_baseline', 0):,.0f} EUR, "
                f"delta {e.get('delta_pct', 0):+.1f}%"
            )
    amp_drift = env_split.get("amp_drift_detected", False)
    if amp_drift:
        lines.append("- ** AMP DRIFT DETECTED **")
    return "\n".join(lines)


def _template_fallback(state: AlertState) -> AlertState:
    """Generate template-based insights without LLM."""
    logger.info("Using template-based insight generation")

    delta = state.get("delta", {})
    contributors = state.get("contributors", [])
    geo_breakdown = state.get("geo_breakdown", [])
    env_split = state.get("environment_split", {})
    triage = state.get("triage_label", "UNKNOWN")
    severity = state.get("severity", "P1")

    findings = []
    rank = 1

    # Finding 1: Main driver based on triage
    if triage == "TRAFFIC_DRIVEN":
        findings.append({
            "rank": rank,
            "title": f"Traffic-driven revenue decline of {delta.get('revenue_pct', 0):+.1f}%",
            "description": (
                f"Bacino (impressions) dropped {delta.get('bacino_pct', 0):+.1f}% while "
                f"coverage changed only {delta.get('coverage_pct', 0):+.1f}%. "
                "The revenue decline is primarily driven by reduced traffic volume."
            ),
            "business_impact": f"Revenue gap of {delta.get('revenue_abs', 0):,.0f} EUR vs baseline.",
            "recommended_action": "Investigate traffic sources and publisher inventory levels.",
            "dimensions_involved": ["triage"],
        })
        rank += 1
    elif triage == "COVERAGE_DRIVEN":
        findings.append({
            "rank": rank,
            "title": f"Coverage-driven revenue decline of {delta.get('revenue_pct', 0):+.1f}%",
            "description": (
                f"Coverage dropped {delta.get('coverage_pct', 0):+.1f}% while "
                f"bacino changed only {delta.get('bacino_pct', 0):+.1f}%. "
                "Fewer impressions are being filled despite stable traffic."
            ),
            "business_impact": f"Revenue gap of {delta.get('revenue_abs', 0):,.0f} EUR vs baseline.",
            "recommended_action": "Check demand partner status, floor prices, and bid landscape.",
            "dimensions_involved": ["triage"],
        })
        rank += 1
    elif triage == "MIXED":
        findings.append({
            "rank": rank,
            "title": f"Combined traffic and coverage decline ({delta.get('revenue_pct', 0):+.1f}%)",
            "description": (
                f"Both bacino ({delta.get('bacino_pct', 0):+.1f}%) and "
                f"coverage ({delta.get('coverage_pct', 0):+.1f}%) are declining. "
                "This suggests a broad supply-side issue."
            ),
            "business_impact": f"Revenue gap of {delta.get('revenue_abs', 0):,.0f} EUR vs baseline.",
            "recommended_action": "Check for platform-wide issues, ad server health, and demand partner status.",
            "dimensions_involved": ["triage"],
        })
        rank += 1
    elif triage == "REVENUE_ONLY":
        findings.append({
            "rank": rank,
            "title": "Incoherent revenue decline without traffic/coverage drop",
            "description": (
                f"Revenue dropped {delta.get('revenue_pct', 0):+.1f}% but bacino and coverage "
                "remain within normal ranges. This may indicate pricing/CPM pressure."
            ),
            "business_impact": f"Revenue gap of {delta.get('revenue_abs', 0):,.0f} EUR vs baseline.",
            "recommended_action": "Review CPM trends, demand partner bid patterns, and floor price settings.",
            "dimensions_involved": ["triage"],
        })
        rank += 1

    # Finding 2: Top contributor concentration
    if contributors:
        top3_quota = sum(c.get("quota_of_drop", 0) for c in contributors[:3])
        top1 = contributors[0] if contributors else {}
        top1_name = top1.get("display_name", top1.get("publisher_id", "Unknown"))
        if top3_quota > 60:
            findings.append({
                "rank": rank,
                "title": f"{top1_name} accounts for {top1.get('quota_of_drop', 0):.0f}% of the drop",
                "description": (
                    f"Top 3 publishers contribute {top3_quota:.0f}% of the total revenue decline. "
                    f"{top1_name} alone represents {top1.get('quota_of_drop', 0):.0f}% "
                    f"with a {top1.get('delta_pct', 0):+.1f}% drop."
                ),
                "business_impact": "Concentrated risk -- recovery depends on specific publisher resolution.",
                "recommended_action": f"Prioritize outreach to {top1_name} and check for site/inventory issues.",
                "dimensions_involved": ["contributor"],
            })
        else:
            findings.append({
                "rank": rank,
                "title": "Revenue drop distributed across publishers",
                "description": (
                    f"No single publisher exceeds {top1.get('quota_of_drop', 0):.0f}% of the drop. "
                    "The distributed nature suggests a systemic issue."
                ),
                "business_impact": "Systemic issues are harder to resolve through individual publisher actions.",
                "recommended_action": "Investigate demand-side changes, platform health, or market conditions.",
                "dimensions_involved": ["contributor"],
            })
        rank += 1

    # Finding 3: Geo or AMP drift
    amp_drift = env_split.get("amp_drift_detected", False)
    if amp_drift:
        amp_data = env_split.get("AMP", {})
        findings.append({
            "rank": rank,
            "title": f"AMP environment drift detected ({amp_data.get('delta_pct', 0):+.1f}%)",
            "description": (
                "AMP revenue is declining significantly faster than WEB and APP environments. "
                "This may reflect ongoing AMP deprecation trends."
            ),
            "business_impact": f"AMP contributing {amp_data.get('revenue_current', 0):,.0f} EUR, down from {amp_data.get('revenue_baseline', 0):,.0f} EUR.",
            "recommended_action": "Accelerate AMP-to-web migration for affected publishers.",
            "dimensions_involved": ["environment"],
        })
        rank += 1
    elif geo_breakdown:
        top_geo = geo_breakdown[0] if geo_breakdown else {}
        if top_geo.get("quota_of_drop", 0) > 70:
            findings.append({
                "rank": rank,
                "title": f"{top_geo.get('cluster', 'Unknown')} accounts for {top_geo.get('quota_of_drop', 0):.0f}% of geographic impact",
                "description": (
                    f"The decline is concentrated in {top_geo.get('cluster_name', top_geo.get('cluster', ''))}. "
                    "Other regions show different patterns."
                ),
                "business_impact": "Region-specific issue may have targeted resolution path.",
                "recommended_action": f"Investigate {top_geo.get('cluster', 'Unknown')}-specific demand changes or publisher issues.",
                "dimensions_involved": ["geo"],
            })
            rank += 1

    # Determine confidence
    if len(findings) >= 2 and severity == "P0":
        diagnosis_confidence = "high"
    elif len(findings) >= 1:
        diagnosis_confidence = "medium"
    else:
        diagnosis_confidence = "low"

    # Build overall summary
    rev_pct = delta.get("revenue_pct", 0)
    summary_parts = [f"Revenue is down {rev_pct:+.1f}% vs 7-day baseline."]
    if findings:
        summary_parts.append(findings[0].get("title", ""))
    if len(findings) > 1:
        summary_parts.append(findings[1].get("title", ""))

    next_steps = []
    for f in findings[:3]:
        action = f.get("recommended_action", "")
        if action:
            next_steps.append(action)
    if not next_steps:
        next_steps = ["Monitor for changes in next window", "Review dashboards manually"]

    insights = {
        "top_findings": findings,
        "diagnosis_confidence": diagnosis_confidence,
        "overall_summary": " ".join(summary_parts),
        "next_steps": next_steps,
        "cache_staleness_risk": False,
    }

    return {
        **state,
        "insights": insights,
    }


def _llm_analysis(state: AlertState) -> AlertState:
    """LLM-enhanced insight generation using Claude Sonnet."""
    from backend.utils.llm_retry import call_llm_with_retry

    delta = state.get("delta", {})
    contributors = state.get("contributors", [])
    geo_breakdown = state.get("geo_breakdown", [])
    env_split = state.get("environment_split", {})
    triage = state.get("triage_label", "UNKNOWN")

    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        return _template_fallback(state)

    prompt = template.format(
        alert_rule=state.get("alert_rule", "A1"),
        severity=state.get("severity", "P1"),
        channel_group=state.get("channel_group", "GOOGLE"),
        timestamp=state.get("timestamp", ""),
        triage_label=triage,
        rev_current=f"{state.get('current_metrics', {}).get('revenue', 0):,.2f}",
        rev_baseline=f"{state.get('baseline_metrics', {}).get('revenue', 0):,.2f}",
        rev_delta=f"{delta.get('revenue_abs', 0):,.2f}",
        rev_delta_pct=f"{delta.get('revenue_pct', 0):+.1f}",
        triage_description=TRIAGE_DESCRIPTIONS.get(triage, "Unknown classification"),
        contributors_summary=_format_contributors_summary(contributors),
        geo_summary=_format_geo_summary(geo_breakdown),
        environment_summary=_format_env_summary(env_split),
        cache_warning="Data served from real-time fetch." if state.get("data_source") != "cache" else "WARNING: Data served from cache, may be stale.",
    )

    raw_text = call_llm_with_retry(
        model="claude-sonnet-4-5-20250929",
        prompt=prompt,
        max_tokens=2048,
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
        insights = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse LLM insight response, using template fallback")
        return _template_fallback(state)

    return {
        **state,
        "insights": insights,
    }


def insight_generator_agent(state: AlertState) -> AlertState:
    """Main entry point for insight generation."""
    logger.info("Insight generator started")
    errors = list(state.get("execution_errors", []))

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    try:
        if has_api_key:
            try:
                result = _llm_analysis(state)
                logger.info("LLM insight generation complete")
                return {**result, "execution_errors": errors}
            except Exception as e:
                logger.warning("LLM insight generation failed (%s), using template", e)
                errors.append(f"LLM insight generation failed: {e}")

        result = _template_fallback(state)
        logger.info("Template insight generation complete")
        return {**result, "execution_errors": errors}

    except Exception as e:
        logger.error("Insight generation failed: %s", e)
        errors.append(f"Insight generation error: {e}")
        return {
            **state,
            "insights": {
                "top_findings": [],
                "diagnosis_confidence": "low",
                "overall_summary": f"Insight generation failed: {e}",
                "next_steps": ["Review alert manually"],
                "cache_staleness_risk": False,
            },
            "execution_errors": errors,
        }
