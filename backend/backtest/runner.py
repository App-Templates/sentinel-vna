from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta
from typing import Any

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

logger = get_logger(__name__)

# Try to import real data runner
try:
    from backend.backtest.runner_real import BacktestRunnerReal
    USE_REAL_DATA = True
except ImportError:
    USE_REAL_DATA = False
    logger.warning("Real data runner not available, using synthetic mode")


class BacktestRunner:
    def __init__(self, start_date: str, end_date: str, step_hours: int = 2):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.step_hours = step_hours
        self.config = get_config()

        # Try to use real data if available
        if USE_REAL_DATA:
            try:
                self.real_runner = BacktestRunnerReal(start_date, end_date, step_hours)
                logger.info("Real data runner initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize real data runner: {e}")
                self.real_runner = None
        else:
            self.real_runner = None

    def run(self, backtest_id: str) -> dict[str, Any]:
        # Try real data first
        if self.real_runner is not None:
            try:
                result = self.real_runner.run(backtest_id)
                if result.get("status") == "COMPLETED":
                    logger.info("Backtest completed using real data")
                    return result
            except Exception as e:
                logger.warning(f"Real data backtest failed: {e}, falling back to synthetic")

        # Fall back to synthetic backtest
        return self._run_synthetic(backtest_id)

    def _run_synthetic(self, backtest_id: str) -> dict[str, Any]:
        logger.info(
            "Starting backtest %s from %s to %s (step=%dh)",
            backtest_id, self.start_date.date(), self.end_date.date(), self.step_hours,
        )

        alerts_generated: list[dict[str, Any]] = []
        total_checks = 0
        current = self.start_date

        channels = [ChannelGroup.GOOGLE, ChannelGroup.OPEN_BIDDING]

        while current <= self.end_date:
            for channel in channels:
                total_checks += 1
                alert_data = self._simulate_check(current, channel, backtest_id)
                if alert_data is not None:
                    alerts_generated.append(alert_data)
            current += timedelta(hours=self.step_hours)

        result = {
            "backtest_id": backtest_id,
            "status": "COMPLETED",
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "step_hours": self.step_hours,
            "total_checks": total_checks,
            "alerts_generated": len(alerts_generated),
            "alerts": alerts_generated,
        }

        save_backtest_result(result)
        logger.info(
            "Backtest %s completed: %d checks, %d alerts",
            backtest_id, total_checks, len(alerts_generated),
        )
        return result

    def _simulate_check(
        self, ts: datetime, channel: ChannelGroup, backtest_id: str
    ) -> dict[str, Any] | None:
        random.seed(int(ts.timestamp()) + hash(channel.value))

        baseline = random.uniform(5000, 50000)
        drop_roll = random.random()

        if drop_roll < 0.06:
            severity = Severity.P0
            delta_pct = random.uniform(
                self.config.revenue_anomaly.P0.drop_percent - 10,
                self.config.revenue_anomaly.P0.drop_percent,
            )
            rule = AlertRule.A1
        elif drop_roll < 0.15:
            severity = Severity.P1
            delta_pct = random.uniform(
                self.config.revenue_anomaly.P1.drop_percent - 5,
                self.config.revenue_anomaly.P1.drop_percent,
            )
            rule = AlertRule.A1
        elif drop_roll < 0.25:
            severity = Severity.P2
            delta_pct = random.uniform(
                self.config.revenue_anomaly.P2.drop_percent - 3,
                self.config.revenue_anomaly.P2.drop_percent,
            )
            rule = random.choice([AlertRule.A1, AlertRule.A2, AlertRule.A3])
        else:
            return None

        current = baseline * (1 + delta_pct / 100)

        triage_options = ["TRAFFIC_DRIVEN", "COVERAGE_DRIVEN", "MIXED", "REVENUE_ONLY"]
        triage_label = random.choice(triage_options)

        top_pubs = self.config.top_publishers[:5]
        contributors = [
            {
                "publisher": pub,
                "delta_pct": round(random.uniform(-30, -2), 2),
                "revenue_impact": round(random.uniform(-5000, -100), 2),
            }
            for pub in top_pubs
        ]

        geo_keys = list(self.config.geo_clusters.keys())
        geo_breakdown = [
            {"geo": g, "delta_pct": round(random.uniform(-20, 5), 2)}
            for g in geo_keys
        ]

        env_split = {
            "WEB": round(random.uniform(30, 50), 1),
            "AMP": round(random.uniform(30, 50), 1),
            "APP": round(random.uniform(5, 20), 1),
        }

        alert_id = generate_alert_id(severity, ts)

        try:
            alert = AlertModel(
                alert_id=alert_id,
                timestamp=ts,
                severity=severity,
                channel_group=channel,
                status=AlertStatus.OPEN,
                alert_rule=rule,
                revenue_current=round(current, 2),
                revenue_baseline=round(baseline, 2),
                revenue_delta_pct=round(delta_pct, 2),
                triage_label=triage_label,
                contributors_json=json.dumps(contributors),
                geo_breakdown_json=json.dumps(geo_breakdown),
                environment_split_json=json.dumps(env_split),
                insights_json=json.dumps({
                    "backtest_id": backtest_id,
                    "simulated": True,
                    "summary": f"Simulated {severity.value} alert for {channel.value}",
                }),
                execution_time_sec=round(random.uniform(0.5, 5.0), 2),
                data_source="backtest",
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
            "severity": severity.value,
            "channel_group": channel.value,
            "alert_rule": rule.value,
            "revenue_delta_pct": round(delta_pct, 2),
            "triage_label": triage_label,
        }
