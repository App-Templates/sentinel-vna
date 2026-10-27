"""
Backtest Runner with Real Parquet Data
Runs backtesting on real hourly data (Nov-Dec 2025)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from backend.db.models import (
    AlertModel,
    AlertRule,
    AlertStatus,
    ChannelGroup,
    Severity,
    generate_alert_id,
)
from backend.db.operations import create_alert, save_backtest_result
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState
from backend.workflow.graph import create_workflow

logger = get_logger(__name__)

# Path to hourly aggregated data
BASE_DIR = Path(__file__).parent.parent.parent
HOURLY_PARQUET = BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"


class BacktestRunnerReal:
    """Backtest runner using real parquet data"""

    def __init__(self, start_date: str, end_date: str, step_hours: int = 2):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.step_hours = step_hours
        self.config = get_config()
        self.df_hourly = None

    def load_data(self) -> bool:
        """Load hourly parquet data"""
        if not os.path.exists(HOURLY_PARQUET):
            logger.error(f"Hourly parquet not found at {HOURLY_PARQUET}")
            return False

        try:
            self.df_hourly = pd.read_parquet(HOURLY_PARQUET)
            self.df_hourly['timestamp'] = pd.to_datetime(self.df_hourly['timestamp'])
            logger.info(
                f"Loaded hourly data: {len(self.df_hourly):,} rows, "
                f"date range {self.df_hourly['timestamp'].min()} to {self.df_hourly['timestamp'].max()}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load hourly parquet: {e}")
            return False

    def run(self, backtest_id: str) -> dict[str, Any]:
        """Run backtest on real data"""
        logger.info(
            "Starting backtest %s from %s to %s (step=%dh) [REAL DATA MODE]",
            backtest_id, self.start_date.date(), self.end_date.date(), self.step_hours,
        )

        # Load data
        if not self.load_data():
            logger.error("Failed to load data, aborting backtest")
            return {
                "backtest_id": backtest_id,
                "status": "FAILED",
                "error": "Failed to load hourly parquet data"
            }

        # Get actual date range from data
        data_start = self.df_hourly['timestamp'].min()
        data_end = self.df_hourly['timestamp'].max()

        logger.info(f"Data available from {data_start} to {data_end}")

        # Adjust backtest range to available data
        current = max(self.start_date, data_start.to_pydatetime())
        end = min(self.end_date, data_end.to_pydatetime())

        if current > end:
            logger.error("Backtest date range is outside available data range")
            return {
                "backtest_id": backtest_id,
                "status": "FAILED",
                "error": f"Date range {self.start_date.date()} to {self.end_date.date()} outside data range"
            }

        logger.info(f"Adjusted backtest range: {current.date()} to {end.date()}")

        alerts_generated: list[dict[str, Any]] = []
        total_checks = 0
        channels = [ChannelGroup.GOOGLE, ChannelGroup.OPEN_BIDDING]

        # Create workflow
        workflow = create_workflow()

        while current <= end:
            for channel in channels:
                total_checks += 1

                # Run through the actual workflow for this timestamp
                alert_data = self._run_workflow_check(
                    current, channel, backtest_id, workflow
                )

                if alert_data is not None:
                    alerts_generated.append(alert_data)

                if total_checks % 100 == 0:
                    logger.info(f"Processed {total_checks} checks, {len(alerts_generated)} alerts generated")

            current += timedelta(hours=self.step_hours)

        result = {
            "backtest_id": backtest_id,
            "status": "COMPLETED",
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "actual_start": current.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "step_hours": self.step_hours,
            "total_checks": total_checks,
            "alerts_generated": len(alerts_generated),
            "alerts": alerts_generated,
            "data_source": "real_parquet",
        }

        save_backtest_result(result)
        logger.info(
            "Backtest %s completed: %d checks, %d alerts (%.1f%% trigger rate)",
            backtest_id, total_checks, len(alerts_generated),
            100.0 * len(alerts_generated) / total_checks if total_checks > 0 else 0
        )
        return result

    def _run_workflow_check(
        self,
        ts: datetime,
        channel: ChannelGroup,
        backtest_id: str,
        workflow
    ) -> dict[str, Any] | None:
        """
        Run the full anomaly detection workflow for a given timestamp.
        Returns alert dict if an alert was generated, None otherwise.
        """
        # Create initial state
        initial_state: AlertState = {
            "timestamp": ts.isoformat(),
            "channel_group": channel.value,
            "trigger_type": "A1",  # Will be determined by detector
            "severity": None,
            "current_metrics": {},
            "baseline_metrics": {},
            "historical_stats": {},
            "delta": {},
            "triage": {},
            "insights": {},
            "alert_id": None,
            "should_alert": False,
            "execution_errors": [],
            "config_version": self.config.version,
            "data_source": "backtest_real",
        }

        try:
            # Run workflow
            final_state = workflow.invoke(initial_state)

            # Check if alert was triggered
            if not final_state.get("should_alert", False):
                return None

            # Extract alert data
            severity = final_state.get("severity")
            if severity is None:
                return None

            alert_rule_str = final_state.get("trigger_type", "A1")
            try:
                alert_rule = AlertRule[alert_rule_str]
            except (KeyError, TypeError):
                alert_rule = AlertRule.A1

            current_metrics = final_state.get("current_metrics", {})
            baseline_metrics = final_state.get("baseline_metrics", {})
            delta = final_state.get("delta", {})
            triage = final_state.get("triage", {})
            insights = final_state.get("insights", {})

            revenue_current = current_metrics.get("revenue", 0.0)
            revenue_baseline = baseline_metrics.get("revenue", 0.0)
            revenue_delta_pct = delta.get("revenue_delta_pct", 0.0)

            triage_label = triage.get("primary_driver", "unknown")

            # Build contributors from publisher deltas
            contributors = []
            pub_deltas = delta.get("publishers", {})
            for pub, pub_delta in sorted(
                pub_deltas.items(),
                key=lambda x: abs(x[1].get("delta_pct", 0)),
                reverse=True
            )[:5]:
                contributors.append({
                    "publisher": pub,
                    "delta_pct": round(pub_delta.get("delta_pct", 0.0), 2),
                    "revenue_impact": round(pub_delta.get("revenue_delta", 0.0), 2),
                })

            # Geo breakdown
            geo_breakdown = []
            geo_deltas = delta.get("geo", {})
            for geo, geo_delta in geo_deltas.items():
                geo_breakdown.append({
                    "geo": geo,
                    "delta_pct": round(geo_delta.get("delta_pct", 0.0), 2),
                })

            # Environment split
            env_deltas = delta.get("environment", {})
            env_split = {}
            total_env_rev = sum(
                current_metrics.get("environment", {}).get(e, {}).get("revenue", 0)
                for e in env_deltas.keys()
            )
            if total_env_rev > 0:
                for e in env_deltas.keys():
                    env_rev = current_metrics.get("environment", {}).get(e, {}).get("revenue", 0)
                    env_split[e.lower()] = round(100.0 * env_rev / total_env_rev, 1)

            # Generate alert ID
            try:
                severity_enum = Severity[severity] if isinstance(severity, str) else severity
            except (KeyError, TypeError):
                severity_enum = Severity.P2

            alert_id = generate_alert_id(severity_enum, ts)

            # Create alert model
            try:
                alert = AlertModel(
                    alert_id=alert_id,
                    timestamp=ts,
                    severity=severity_enum,
                    channel_group=channel,
                    status=AlertStatus.OPEN,
                    alert_rule=alert_rule,
                    revenue_current=round(revenue_current, 2),
                    revenue_baseline=round(revenue_baseline, 2),
                    revenue_delta_pct=round(revenue_delta_pct, 2),
                    triage_label=triage_label,
                    contributors_json=json.dumps(contributors),
                    geo_breakdown_json=json.dumps(geo_breakdown),
                    environment_split_json=json.dumps(env_split),
                    insights_json=json.dumps({
                        "backtest_id": backtest_id,
                        "real_data": True,
                        "summary": insights.get("summary", "Real data backtest alert"),
                        "key_findings": insights.get("key_findings", []),
                    }),
                    execution_time_sec=round(final_state.get("execution_time_sec", 0.0), 2),
                    data_source="backtest_real",
                    config_version=self.config.version,
                    created_at=ts,
                    updated_at=ts,
                )
                create_alert(alert)
            except Exception as exc:
                logger.warning("Backtest alert creation failed at %s: %s", ts, exc)
                return None

            return {
                "alert_id": alert_id,
                "timestamp": ts.isoformat(),
                "severity": severity_enum.value,
                "channel_group": channel.value,
                "alert_rule": alert_rule.value,
                "revenue_delta_pct": round(revenue_delta_pct, 2),
                "triage_label": triage_label,
            }

        except Exception as exc:
            logger.warning(f"Workflow execution failed for {ts} / {channel.value}: {exc}")
            return None


# Keep backward compatibility with original BacktestRunner
class BacktestRunner(BacktestRunnerReal):
    """Alias for backward compatibility"""
    pass
