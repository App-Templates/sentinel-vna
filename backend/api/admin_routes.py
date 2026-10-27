from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.agents.notifier import send_daily_digest
from backend.api.rate_limit import limiter

from backend.scheduler.scheduler import is_scheduler_running
from backend.utils.config_loader import AlertingConfig, ConfigLoader, get_config
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin")

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "data" / "datasource_config.json"
ALERTING_RULES_PATH = BASE_DIR / "config" / "alerting_rules.yaml"

# Allowed base directories for credentials_path
_ALLOWED_CREDS_DIRS = [
    str(BASE_DIR / "data"),
    str(BASE_DIR / "config"),
    str(BASE_DIR),
]


def _validate_credentials_path(creds_path: str) -> None:
    """Validate that credentials_path doesn't escape allowed directories.

    Raises HTTPException(400) if the path is unsafe.
    """
    if not creds_path:
        return
    resolved = os.path.realpath(creds_path)
    for allowed in _ALLOWED_CREDS_DIRS:
        allowed_resolved = os.path.realpath(allowed)
        if resolved.startswith(allowed_resolved + os.sep) or resolved == allowed_resolved:
            return
    raise HTTPException(
        status_code=400,
        detail=f"credentials_path must be under the project directory ({BASE_DIR}). "
        f"Resolved path '{resolved}' is not allowed.",
    )

# Parquet file paths
PARQUET_FILES = {
    "hourly": BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet",
    "daily": BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet",
    # Legacy aliases pointing to the unified daily file
    "daily_channel": BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet",
    "daily_adrequests": BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet",
}


def _default_config() -> dict:
    return {
        "active_source": "parquet",
        "athena": {
            "enabled": False,
            "region": "",
            "database": "",
            "workgroup": "",
            "s3_output": "",
        },
        "gam": {
            "enabled": False,
            "network_code": "",
            "credentials_path": "",
        },
        "scheduler": {
            "interval_hours": 2,
            "recheck_interval_minutes": 5,
        },
    }


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read datasource config, using defaults")
    return _default_config()


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _parquet_info(path: Path) -> dict:
    """Get status info for a parquet file."""
    if not path.exists():
        return {"status": "not_found", "rows": 0, "date_range": []}
    try:
        import pandas as pd

        df = pd.read_parquet(path)
        rows = len(df)
        date_col = "timestamp" if "timestamp" in df.columns else "date"
        dates = pd.to_datetime(df[date_col])
        date_range = [str(dates.min().date()), str(dates.max().date())]
        return {"status": "loaded", "rows": rows, "date_range": date_range}
    except Exception as e:
        return {"status": f"error: {e}", "rows": 0, "date_range": []}


def _build_response(config: dict) -> dict:
    """Build full datasource response with live parquet stats."""
    # Parquet info
    hourly_info = _parquet_info(PARQUET_FILES["hourly"])
    daily_channel_info = _parquet_info(PARQUET_FILES["daily_channel"])
    daily_adrequests_info = _parquet_info(PARQUET_FILES["daily_adrequests"])

    parquet = {
        "hourly_path": str(PARQUET_FILES["hourly"].relative_to(BASE_DIR)),
        "hourly_status": hourly_info["status"],
        "hourly_rows": hourly_info["rows"],
        "hourly_date_range": hourly_info["date_range"],
        "daily_channel_path": str(PARQUET_FILES["daily_channel"].relative_to(BASE_DIR)),
        "daily_channel_status": daily_channel_info["status"],
        "daily_channel_rows": daily_channel_info["rows"],
        "daily_channel_date_range": daily_channel_info["date_range"],
        "daily_adrequests_path": str(PARQUET_FILES["daily_adrequests"].relative_to(BASE_DIR)),
        "daily_adrequests_status": daily_adrequests_info["status"],
        "daily_adrequests_rows": daily_adrequests_info["rows"],
        "daily_adrequests_date_range": daily_adrequests_info["date_range"],
    }

    # Athena
    athena_cfg = config.get("athena", {})
    athena = {
        "enabled": athena_cfg.get("enabled", False),
        "region": athena_cfg.get("region", ""),
        "database": athena_cfg.get("database", ""),
        "workgroup": athena_cfg.get("workgroup", ""),
        "s3_output": athena_cfg.get("s3_output", ""),
        "status": "configured" if athena_cfg.get("enabled") else "not_configured",
    }

    # GAM
    gam_cfg = config.get("gam", {})
    gam = {
        "enabled": gam_cfg.get("enabled", False),
        "network_code": gam_cfg.get("network_code", ""),
        "credentials_path": gam_cfg.get("credentials_path", ""),
        "status": "configured" if gam_cfg.get("enabled") else "not_configured",
    }

    # Scheduler
    sched_cfg = config.get("scheduler", {})
    scheduler = {
        "running": is_scheduler_running(),
        "interval_hours": sched_cfg.get("interval_hours", 2),
        "recheck_interval_minutes": sched_cfg.get("recheck_interval_minutes", 5),
    }

    return {
        "active_source": config.get("active_source", "parquet"),
        "parquet": parquet,
        "athena": athena,
        "gam": gam,
        "scheduler": scheduler,
    }


@router.get("/datasources")
@limiter.limit("60/minute")
def get_datasources(request: Request):
    config = _load_config()
    return _build_response(config)


class DatasourceUpdateRequest(BaseModel):
    active_source: Optional[str] = None
    athena: Optional[Dict[str, Any]] = None
    gam: Optional[Dict[str, Any]] = None
    scheduler: Optional[Dict[str, Any]] = None


@router.post("/datasources")
@limiter.limit("10/hour")
def update_datasources(request: Request, body: DatasourceUpdateRequest):
    config = _load_config()

    if body.active_source is not None:
        config["active_source"] = body.active_source
    if body.athena is not None:
        config["athena"] = {**config.get("athena", {}), **body.athena}
    if body.gam is not None:
        creds_path = body.gam.get("credentials_path")
        if creds_path:
            _validate_credentials_path(creds_path)
        config["gam"] = {**config.get("gam", {}), **body.gam}
    if body.scheduler is not None:
        config["scheduler"] = {**config.get("scheduler", {}), **body.scheduler}

    _save_config(config)
    return _build_response(config)


class TestConnectionRequest(BaseModel):
    source: str  # "parquet", "athena", or "gam"


@router.post("/datasources/test")
@limiter.limit("10/hour")
def test_connection(request: Request, body: TestConnectionRequest):
    if body.source == "parquet":
        results = {}
        for name, path in PARQUET_FILES.items():
            if not path.exists():
                results[name] = {"ok": False, "error": f"File not found: {path}"}
            else:
                try:
                    import pandas as pd

                    df = pd.read_parquet(path)
                    results[name] = {"ok": True, "rows": len(df)}
                except Exception as e:
                    results[name] = {"ok": False, "error": str(e)}
        all_ok = all(r["ok"] for r in results.values())
        return {"source": "parquet", "ok": all_ok, "details": results}

    elif body.source == "athena":
        config = _load_config()
        athena_cfg = config.get("athena", {})
        if not athena_cfg.get("enabled"):
            return {"source": "athena", "ok": False, "error": "Athena is not enabled"}
        try:
            import boto3

            client = boto3.client("athena", region_name=athena_cfg.get("region", "us-east-1"))
            response = client.start_query_execution(
                QueryString="SELECT 1",
                QueryExecutionContext={"Database": athena_cfg.get("database", "default")},
                WorkGroup=athena_cfg.get("workgroup", "primary"),
                ResultConfiguration={"OutputLocation": athena_cfg.get("s3_output", "")},
            )
            return {"source": "athena", "ok": True, "query_execution_id": response["QueryExecutionId"]}
        except Exception as e:
            return {"source": "athena", "ok": False, "error": str(e)}

    elif body.source == "gam":
        config = _load_config()
        gam_cfg = config.get("gam", {})
        if not gam_cfg.get("enabled"):
            return {"source": "gam", "ok": False, "error": "GAM is not enabled"}
        creds_path = gam_cfg.get("credentials_path", "")
        if creds_path:
            _validate_credentials_path(creds_path)
        if not creds_path or not os.path.exists(creds_path):
            return {"source": "gam", "ok": False, "error": f"Credentials file not found: {creds_path}"}
        return {"source": "gam", "ok": True, "message": "Credentials file exists (auth not tested)"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown source: {body.source}")


# ---------------------------------------------------------------------------
# Alerting Rules endpoints
# ---------------------------------------------------------------------------


class SeverityLevelUpdate(BaseModel):
    drop_percent: Optional[float] = None
    duration_hours: Optional[int] = None


class RevenueAnomalyUpdate(BaseModel):
    P0: Optional[SeverityLevelUpdate] = None
    P1: Optional[SeverityLevelUpdate] = None
    P2: Optional[SeverityLevelUpdate] = None


class DriftDetectionUpdate(BaseModel):
    enabled: Optional[bool] = None
    window_days: Optional[int] = None
    threshold_percent: Optional[float] = None


class NearZeroUpdate(BaseModel):
    revenue_threshold_eur: Optional[float] = None
    coverage_threshold: Optional[float] = None
    consecutive_periods: Optional[int] = None


class TriageUpdate(BaseModel):
    traffic_driven_threshold: Optional[float] = None
    coverage_driven_threshold: Optional[float] = None


class TopContributorsUpdate(BaseModel):
    top_n: Optional[int] = None
    min_quota_percent: Optional[float] = None


class AlertingRulesUpdate(BaseModel):
    revenue_anomaly: Optional[RevenueAnomalyUpdate] = None
    drift_detection: Optional[DriftDetectionUpdate] = None
    near_zero: Optional[NearZeroUpdate] = None
    triage: Optional[TriageUpdate] = None
    top_contributors: Optional[TopContributorsUpdate] = None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning updated base."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@router.get("/alerting-rules")
@limiter.limit("60/minute")
def get_alerting_rules(request: Request):
    """Return current alerting rules configuration as JSON."""
    config = get_config()
    return config.model_dump()


@router.put("/alerting-rules")
@limiter.limit("10/hour")
def update_alerting_rules(request: Request, body: AlertingRulesUpdate):
    """Update editable alerting rules fields, validate, persist YAML and reload."""
    # Read current YAML as raw dict
    try:
        with open(ALERTING_RULES_PATH, "r") as f:
            current = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")

    # Build partial dict from request (exclude unset fields)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Deep-merge updates into current config
    _deep_merge(current, updates)

    # Update last_updated timestamp
    current["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Validate merged config with Pydantic before writing
    try:
        AlertingConfig(**current)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    # Write YAML
    try:
        with open(ALERTING_RULES_PATH, "w") as f:
            yaml.dump(current, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {e}")

    # Reload singleton
    updated_config = ConfigLoader().reload()
    return updated_config.model_dump()


# ---------------------------------------------------------------------------
# Slack Configuration endpoints
# ---------------------------------------------------------------------------


class SlackConfigUpdate(BaseModel):
    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    immediate_severities: Optional[list[str]] = None
    digest_severities: Optional[list[str]] = None
    digest_time_utc: Optional[str] = None


@router.get("/slack-config")
@limiter.limit("60/minute")
def get_slack_config(request: Request):
    """Return current Slack notification configuration from alerting_rules.yaml."""
    try:
        with open(ALERTING_RULES_PATH, "r") as f:
            config = yaml.safe_load(f)

        slack_config = config.get("slack_notifications", {})
        return {
            "webhook_url": slack_config.get("webhook_url", ""),
            "channel": slack_config.get("channel", "sentinel-alerts"),
            "immediate_severities": slack_config.get("immediate_severities", ["P0"]),
            "digest_severities": slack_config.get("digest_severities", ["P1", "P2"]),
            "digest_time_utc": slack_config.get("digest_time_utc", "08:00"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Slack config: {e}")


@router.put("/slack-config")
@limiter.limit("10/hour")
def update_slack_config(request: Request, body: SlackConfigUpdate):
    """Update Slack notification configuration in alerting_rules.yaml."""
    try:
        # Read current YAML
        with open(ALERTING_RULES_PATH, "r") as f:
            config = yaml.safe_load(f)

        # Update slack_notifications section
        if "slack_notifications" not in config:
            config["slack_notifications"] = {}

        updates = body.model_dump(exclude_none=True)
        config["slack_notifications"].update(updates)

        # Update timestamp
        config["last_updated"] = datetime.utcnow().isoformat() + "Z"

        # Write YAML
        with open(ALERTING_RULES_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        # Reload config singleton
        ConfigLoader().reload()

        # Return updated config
        slack_config = config.get("slack_notifications", {})
        return {
            "webhook_url": slack_config.get("webhook_url", ""),
            "channel": slack_config.get("channel", "sentinel-alerts"),
            "immediate_severities": slack_config.get("immediate_severities", ["P0"]),
            "digest_severities": slack_config.get("digest_severities", ["P1", "P2"]),
            "digest_time_utc": slack_config.get("digest_time_utc", "08:00"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Slack config: {e}")


class TestSlackRequest(BaseModel):
    webhook_url: str


@router.post("/test-slack")
@limiter.limit("10/hour")
def test_slack(request: Request, body: TestSlackRequest):
    """Test Slack webhook connectivity by sending a test message."""
    from urllib.request import Request as URLRequest, urlopen
    from urllib.error import URLError

    if not body.webhook_url:
        return {"success": False, "message": "Webhook URL is required"}

    try:
        payload = json.dumps({"text": "SENTINEL test notification from admin panel"}).encode("utf-8")
        req = URLRequest(
            body.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return {"success": True, "message": "Test message sent successfully"}
            else:
                return {"success": False, "message": f"Slack returned status {resp.status}"}

    except URLError as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to send test message: {str(e)}"}


@router.post("/trigger-digest")
@limiter.limit("10/hour")
def trigger_digest(request: Request):
    """Manually trigger daily digest send (for testing without waiting for scheduled time)."""
    try:
        result = send_daily_digest()
        return {
            "success": result["sent"],
            "alert_count": result["alert_count"],
            "message": result["message"],
        }
    except Exception as e:
        logger.error("Failed to trigger digest: %s", e)
        return {"success": False, "alert_count": 0, "message": f"Error: {str(e)}"}
