import os
import threading
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class DataGapConfig(BaseModel):
    enabled: bool
    max_gap_hours: int
    severity: str


class SeverityLevel(BaseModel):
    drop_percent: float
    duration_hours: int


class RevenueAnomalyConfig(BaseModel):
    P0: SeverityLevel
    P1: SeverityLevel
    P2: SeverityLevel


class DriftDetectionConfig(BaseModel):
    enabled: bool
    window_days: int
    threshold_percent: float


class DriftRegressionConfig(BaseModel):
    enabled: bool
    window_days_min: int
    window_days_max: int
    slope_threshold_percent_per_day: float
    cumulative_drop_threshold_percent: float
    min_data_points: int


class NearZeroConfig(BaseModel):
    revenue_threshold_eur: float
    coverage_threshold: float
    consecutive_periods: int


class TriageConfig(BaseModel):
    traffic_driven_threshold: float
    coverage_driven_threshold: float


class TopContributorsConfig(BaseModel):
    top_n: int
    min_quota_percent: float


class SchedulingConfig(BaseModel):
    interval_hours: int
    recheck_interval_minutes: int
    channels: list[str]

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: list[str]) -> list[str]:
        allowed = {"GOOGLE", "OPEN_BIDDING"}
        for ch in v:
            if ch not in allowed:
                raise ValueError(f"Invalid channel: {ch}. Allowed: {allowed}")
        return v


class DataSourcesConfig(BaseModel):
    athena_timeout_seconds: int
    athena_retry_count: int
    cache_ttl_hours: int


class NotificationsConfig(BaseModel):
    slack_enabled: bool
    email_enabled: bool


class AlertingConfig(BaseModel):
    version: str
    last_updated: str
    data_gap: DataGapConfig
    revenue_anomaly: RevenueAnomalyConfig
    drift_detection: DriftDetectionConfig
    drift_regression: DriftRegressionConfig
    near_zero: NearZeroConfig
    triage: TriageConfig
    top_contributors: TopContributorsConfig
    geo_clusters: dict[str, list[str]]
    top_publishers: list[str]
    scheduling: SchedulingConfig
    data_sources: DataSourcesConfig
    notifications: NotificationsConfig


class ConfigLoader:
    _instance: Optional["ConfigLoader"] = None
    _lock: threading.Lock = threading.Lock()
    _config: Optional[AlertingConfig] = None

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[str] = None) -> AlertingConfig:
        if self._config is not None:
            return self._config

        if config_path is None:
            config_path = os.environ.get(
                "VNA_CONFIG_PATH",
                str(
                    Path(__file__).resolve().parent.parent.parent
                    / "config"
                    / "alerting_rules.yaml"
                ),
            )

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        if raw is None:
            raise ValueError(f"Config file is empty: {path}")

        self._config = AlertingConfig(**raw)
        return self._config

    def reload(self, config_path: Optional[str] = None) -> AlertingConfig:
        self._config = None
        return self.load(config_path)

    @property
    def config(self) -> AlertingConfig:
        if self._config is None:
            return self.load()
        return self._config


def get_config(config_path: Optional[str] = None) -> AlertingConfig:
    return ConfigLoader().load(config_path)
