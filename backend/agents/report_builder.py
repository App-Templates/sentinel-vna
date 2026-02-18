"""
Report Builder Agent (Node 8)
Generates alert_id, JSON payload, and markdown report.
Uses Claude Haiku for polished report with template fallback.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.db.models import Severity, generate_alert_id
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.report_builder")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "report_builder_prompt.txt"

SEVERITY_EMOJI = {"P0": "\U0001f534", "P1": "\U0001f7e0", "P2": "\U0001f7e1"}


def _build_alert_payload(state: AlertState, alert_id: str) -> dict:
    """Build the complete JSON alert payload."""
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})
    delta = state.get("delta", {})

    return {
        "alert_id": alert_id,
        "timestamp": state.get("timestamp", ""),
        "severity": state.get("severity", "P1"),
        "channel_group": state.get("channel_group", "GOOGLE"),
        "alert_rule": state.get("alert_rule", "A1"),
        "triage_label": state.get("triage_label", "UNKNOWN"),
        "mode": state.get("mode", "LIVE"),
        "revenue": {
            "current": current.get("revenue", 0),
            "baseline": baseline.get("revenue", 0),
            "delta_abs": delta.get("revenue_abs", 0),
            "delta_pct": delta.get("revenue_pct", 0),
        },
        "bacino": {
            "current": current.get("bacino", 0),
            "baseline": baseline.get("bacino", 0),
            "delta_pct": delta.get("bacino_pct", 0),
        },
        "coverage": {
            "current": current.get("coverage", 0),
            "baseline": baseline.get("coverage", 0),
            "delta_pct": delta.get("coverage_pct", 0),
        },
        "z_score": state.get("z_score", 0),
        "confidence": state.get("confidence", 0),
        "contributors": state.get("contributors", []),
        "geo_breakdown": state.get("geo_breakdown", []),
        "environment_split": state.get("environment_split", {}),
        "insights": state.get("insights", {}),
        "execution_start": state.get("execution_start", ""),
        "data_source": state.get("data_source", "synthetic"),
    }


def _build_template_report(state: AlertState, alert_id: str) -> str:
    """Build markdown report from template."""
    severity = state.get("severity", "P1")
    emoji = SEVERITY_EMOJI.get(severity, "")
    delta = state.get("delta", {})
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})
    contributors = state.get("contributors", [])
    geo_breakdown = state.get("geo_breakdown", [])
    env_split = state.get("environment_split", {})
    insights = state.get("insights", {})
    triage = state.get("triage_label", "UNKNOWN")

    lines = []
    lines.append(f"# {emoji} {severity} Alert: Revenue Drop {delta.get('revenue_pct', 0):+.1f}% | {state.get('channel_group', 'GOOGLE')}")
    lines.append("")
    lines.append(f"**Alert ID:** {alert_id}")
    lines.append(f"**Time:** {state.get('timestamp', '')} | **Channel:** {state.get('channel_group', '')} | **Rule:** {state.get('alert_rule', '')} | **Mode:** {state.get('mode', 'LIVE')}")
    lines.append("")

    # Impact Summary
    lines.append("## Impact Summary")
    lines.append(
        f"Revenue dropped **{delta.get('revenue_pct', 0):+.1f}%** vs 7-day baseline "
        f"(EUR {current.get('revenue', 0):,.0f} vs EUR {baseline.get('revenue', 0):,.0f})."
    )
    lines.append(f"Classification: **{triage}** | Confidence: {state.get('confidence', 0):.0%} | Z-score: {state.get('z_score', 0):.2f}")
    lines.append("")

    # Key Findings
    findings = insights.get("top_findings", [])
    if findings:
        lines.append("## Key Findings")
        for f in findings[:3]:
            lines.append(f"{f.get('rank', '-')}. **{f.get('title', 'N/A')}**")
            lines.append(f"   {f.get('description', '')}")
        lines.append("")

    # Contributors table
    if contributors:
        lines.append("## Top Contributors")
        lines.append("| Publisher | Current | Baseline | Delta % | Share of Drop |")
        lines.append("|-----------|---------|----------|---------|---------------|")
        for c in contributors[:10]:
            name = c.get("display_name", c.get("publisher_id", "?"))
            lines.append(
                f"| {name} | {c.get('revenue_current', 0):,.0f} | "
                f"{c.get('revenue_baseline', 0):,.0f} | "
                f"{c.get('delta_pct', 0):+.1f}% | "
                f"{c.get('quota_of_drop', 0):.1f}% |"
            )
        lines.append("")

    # Geo breakdown
    if geo_breakdown:
        lines.append("## Geographic Impact")
        lines.append("| Region | Current | Baseline | Delta % | Share | Status |")
        lines.append("|--------|---------|----------|---------|-------|--------|")
        for g in geo_breakdown:
            lines.append(
                f"| {g.get('cluster', '?')} | {g.get('revenue_current', 0):,.0f} | "
                f"{g.get('revenue_baseline', 0):,.0f} | "
                f"{g.get('delta_pct', 0):+.1f}% | "
                f"{g.get('quota_of_drop', 0):.1f}% | {g.get('status', '?')} |"
            )
        lines.append("")

    # Environment split
    if env_split:
        lines.append("## Environment Breakdown")
        lines.append("| Environment | Current | Baseline | Delta % |")
        lines.append("|-------------|---------|----------|---------|")
        for env_name in ("WEB", "AMP", "APP"):
            e = env_split.get(env_name, {})
            if isinstance(e, dict):
                lines.append(
                    f"| {env_name} | {e.get('revenue_current', 0):,.0f} | "
                    f"{e.get('revenue_baseline', 0):,.0f} | "
                    f"{e.get('delta_pct', 0):+.1f}% |"
                )
        if env_split.get("amp_drift_detected"):
            lines.append("\n> **AMP Drift Detected:** AMP revenue declining faster than other environments.")
        lines.append("")

    # Next steps
    next_steps = insights.get("next_steps", [])
    if next_steps:
        lines.append("## Next Steps")
        for step in next_steps:
            lines.append(f"- [ ] {step}")
        lines.append("")

    # Diagnosis confidence
    lines.append(f"---\n*Diagnosis confidence: {insights.get('diagnosis_confidence', 'medium')} | Data source: {state.get('data_source', 'synthetic')}*")

    return "\n".join(lines)


def _llm_report(state: AlertState, alert_id: str) -> str:
    """Use LLM to generate a polished report."""
    from backend.utils.llm_retry import call_llm_with_retry

    delta = state.get("delta", {})
    insights = state.get("insights", {})
    contributors = state.get("contributors", [])
    geo_breakdown = state.get("geo_breakdown", [])
    env_split = state.get("environment_split", {})

    # Format summaries
    contrib_lines = []
    for c in contributors[:5]:
        contrib_lines.append(f"- {c.get('display_name', '?')}: {c.get('delta_pct', 0):+.1f}%, quota {c.get('quota_of_drop', 0):.1f}%")

    geo_lines = []
    for g in geo_breakdown:
        geo_lines.append(f"- {g.get('cluster', '?')}: {g.get('delta_pct', 0):+.1f}%, quota {g.get('quota_of_drop', 0):.1f}%")

    env_lines = []
    for e in ("WEB", "AMP", "APP"):
        ed = env_split.get(e, {})
        if isinstance(ed, dict):
            env_lines.append(f"- {e}: {ed.get('delta_pct', 0):+.1f}%")

    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        return _build_template_report(state, alert_id)

    prompt = template.format(
        alert_id=alert_id,
        timestamp=state.get("timestamp", ""),
        severity=state.get("severity", "P1"),
        channel_group=state.get("channel_group", "GOOGLE"),
        alert_rule=state.get("alert_rule", "A1"),
        triage_label=state.get("triage_label", "UNKNOWN"),
        rev_current=f"{state.get('current_metrics', {}).get('revenue', 0):,.2f}",
        rev_baseline=f"{state.get('baseline_metrics', {}).get('revenue', 0):,.2f}",
        rev_delta=f"{delta.get('revenue_abs', 0):,.2f}",
        rev_delta_pct=f"{delta.get('revenue_pct', 0):+.1f}",
        insights_summary=insights.get("overall_summary", "No insights available"),
        contributors_summary="\n".join(contrib_lines) if contrib_lines else "No contributor data",
        geo_summary="\n".join(geo_lines) if geo_lines else "No geo data",
        environment_summary="\n".join(env_lines) if env_lines else "No environment data",
    )

    raw_text = call_llm_with_retry(
        model="claude-haiku-4-5-20251001",
        prompt=prompt,
        max_tokens=2048,
    )
    if raw_text is None:
        raise RuntimeError("LLM call failed after retries")

    return raw_text


def _build_a0_report(state: AlertState, alert_id: str) -> str:
    """Build markdown report for A0 data gap alert."""
    severity = state.get("severity", "P1")
    emoji = SEVERITY_EMOJI.get(severity, "")
    gap_info = state.get("alert_payload", {})

    lines = []
    lines.append(f"# {emoji} {severity} Alert: Data Gap Detected | {state.get('channel_group', 'GOOGLE')}")
    lines.append("")
    lines.append(f"**Alert ID:** {alert_id}")
    lines.append(f"**Time:** {state.get('timestamp', '')} | **Channel:** {state.get('channel_group', '')} | **Rule:** A0 | **Mode:** {state.get('mode', 'LIVE')}")
    lines.append("")
    lines.append("## Data Gap Details")
    lines.append(f"**Gap Type:** {gap_info.get('gap_type', 'UNKNOWN')}")
    if gap_info.get("gap_type") == "BASELINE_INSUFFICIENT":
        lines.append(
            f"Baseline data insufficient: **{gap_info.get('data_points_available', 0)}** points available, "
            f"**{gap_info.get('data_points_required', 4)}** required."
        )
    elif gap_info.get("gap_type") == "NULL_CURRENT_METRICS":
        missing = gap_info.get("missing_fields", [])
        lines.append(f"Current metrics contain null values for: **{', '.join(missing)}**")
    lines.append(f"**Estimated Gap Duration:** ~{gap_info.get('gap_hours_estimated', '?')} hours")
    if gap_info.get("last_available_timestamp"):
        lines.append(f"**Last Available Data:** {gap_info['last_available_timestamp']}")
    lines.append("")
    lines.append("## Classification")
    lines.append("**Triage:** DATA_GAP (technical alert, no revenue analysis required)")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("- [ ] Check data pipeline / ETL status")
    lines.append("- [ ] Verify Athena/GAM data source availability")
    lines.append("- [ ] Check for upstream data provider issues")
    lines.append("- [ ] Monitor for data recovery")
    lines.append("")
    lines.append(f"---\n*Data source: {state.get('data_source', 'unknown')} | This is an automated data gap alert (A0)*")

    return "\n".join(lines)


def report_builder_agent(state: AlertState) -> AlertState:
    """Main entry point for report building."""
    logger.info("Report builder started")
    errors = list(state.get("execution_errors", []))

    # Generate alert ID
    severity_str = state.get("severity", "P1")
    try:
        severity_enum = Severity(severity_str)
    except ValueError:
        severity_enum = Severity.P1

    ts_str = state.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        ts = datetime.now(timezone.utc)

    alert_id = generate_alert_id(severity_enum, ts)

    # A0: data gap alert has its own report format
    if state.get("alert_rule") == "A0":
        logger.info("Building A0 data gap report")
        # Preserve gap info from data_validator, add alert_id
        gap_payload = dict(state.get("alert_payload", {}))
        gap_payload["alert_id"] = alert_id
        markdown_report = _build_a0_report(state, alert_id)
        logger.info("A0 report built: alert_id=%s", alert_id)
        return {
            **state,
            "alert_payload": gap_payload,
            "markdown_report": markdown_report,
            "execution_errors": errors,
        }

    # Build alert payload
    alert_payload = _build_alert_payload(state, alert_id)

    # Build markdown report
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    markdown_report = ""

    if has_api_key:
        try:
            markdown_report = _llm_report(state, alert_id)
            logger.info("LLM report generated")
        except Exception as e:
            logger.warning("LLM report generation failed (%s), using template", e)
            errors.append(f"LLM report generation failed: {e}")

    if not markdown_report:
        markdown_report = _build_template_report(state, alert_id)
        logger.info("Template report generated")

    logger.info("Report built: alert_id=%s, severity=%s", alert_id, severity_str)

    return {
        **state,
        "alert_payload": alert_payload,
        "markdown_report": markdown_report,
        "execution_errors": errors,
    }
