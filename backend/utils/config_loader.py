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


class DualThresholdLevelConfig(BaseModel):
    revenue_drop_percent: float
    yesterday_delta_percent: float
    ma_14d_divergence_percent: float


class DualThresholdsConfig(BaseModel):
    enabled: bool
    operational: DualThresholdLevelConfig
    attention: DualThresholdLevelConfig
    attention_severity: str


class YesterdayComparisonConfig(BaseModel):
    enabled: bool
    threshold_percent: float
    severity_mapping: dict[str, str]


class MovingAverage14dConfig(BaseModel):
    enabled: bool
    divergence_threshold_percent: float
    sustained_hours: int
    severity: str


class ComparativeAlertingConfig(BaseModel):
    yesterday_comparison: YesterdayComparisonConfig
    moving_average_14d: MovingAverage14dConfig


class MarginThresholdConfig(BaseModel):
    drop_percent: float
    duration_hours: int


class MarginAlertConfig(BaseModel):
    enabled: bool
    ecpm_drop_thresholds: dict[str, MarginThresholdConfig]  # P1, P2
    min_impressions: int
    baseline_weeks: int


class CoverageZeroAlertConfig(BaseModel):
    enabled: bool
    coverage_threshold: float
    min_bacino: int
    consecutive_hours: int
    severity: str
    baseline_weeks: int


class PricingRuleAlertConfig(BaseModel):
    enabled: bool
    coverage_drop_threshold: float
    cpm_spike_threshold: float
    correlation_strength: float
    severity: str
    min_impressions: int
    baseline_weeks: int


class NearZeroConfig(BaseModel):
    revenue_threshold_eur: float
    coverage_threshold: float
    consecutive_periods: int


class LeadingIndicatorConfig(BaseModel):
    """v1.2 leading-indicator early-warning section (ctr/viewability drops vs 7w baseline).

    Added 2026-04-23 (Phase 09 Plan 03) to fix silent drift between
    config/alerting_rules.yaml and AlertingConfig — anomaly_detector._detect_leading_indicators
    (line 641) reads `config.leading_indicator.{enabled,metrics,drop_threshold_pct,
    baseline_weeks,severity}`; prior to this fix, BaseModel's default extra='ignore'
    stripped the YAML section and any LIVE/BACKTEST pipeline run crashed with
    'AlertingConfig object has no attribute leading_indicator'.
    """
    enabled: bool
    metrics: list[str]
    drop_threshold_pct: float
    baseline_weeks: int
    severity: str


class CrossChannelDetectionConfig(BaseModel):
    """v1.2 cross-channel detection (DIRECT ↑ while Open Market ↓ — probable direct campaign).

    Added 2026-04-23 (Phase 09 Plan 03) — same drift as LeadingIndicatorConfig.
    Referenced at anomaly_detector.py:717 via `config.cross_channel_detection`.
    """
    enabled: bool
    direct_increase_threshold_pct: float
    open_market_drop_threshold_pct: float
    channels_open_market: list[str]
    channel_direct: str


class GrossMarginAlertConfig(BaseModel):
    """v1.2 gross-margin A8 trigger (gross margin % below threshold).

    Added 2026-04-23 (Phase 09 Plan 03) — same drift as LeadingIndicatorConfig.
    Referenced at anomaly_detector.py:599 via `config.gross_margin_alert`.
    """
    enabled: bool
    threshold_pct: float
    severity: str
    baseline_weeks: int
    min_impressions: int


class SilentFailureMonitorConfig(BaseModel):
    """Phase 10 MONITOR-02: watchdog for pipeline silent-failure pattern.

    Fires a Slack P0 meta-alert when `pipeline_runs_last_24h > 0 AND
    alerts_last_24h == 0` (runs happening, alerts not flowing). Added
    2026-04-23 post-R-04 chirurgico review of the 2026-01-22 -> 2026-04-22
    silent-failure incident.

    default_factory-safe at AlertingConfig level (WR-03 lesson from Phase 09):
    missing section defaults to enabled=False, watchdog is silent until
    explicitly activated via config.
    """
    enabled: bool = False
    cron_interval_minutes: int = Field(default=60, ge=1, le=1440)
    slack_channel_override: Optional[str] = None  # If set, overrides slack_notifications.webhook_url


class TriageConfig(BaseModel):
    traffic_driven_threshold: float
    coverage_driven_threshold: float


class TopContributorsConfig(BaseModel):
    top_n: int
    min_quota_percent: float


class WeekendScheduleConfig(BaseModel):
    enabled: bool
    times_per_day: int
    run_hours: list[int]


class SchedulingConfig(BaseModel):
    interval_hours: int
    recheck_interval_minutes: int
    channels: list[str]
    weekend_schedule: WeekendScheduleConfig

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: list[str]) -> list[str]:
        allowed = {
            "GOOGLE_ADEX", "OPEN_BIDDING",
            "HEADER_BIDDING_MAGNITE", "HEADER_BIDDING_PUBMATIC",
            "TAM", "DIRECT", "DEAL",
            # Legacy
            "GOOGLE",
        }
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
    comparative_alerting: ComparativeAlertingConfig
    dual_thresholds: DualThresholdsConfig
    margin_alert: MarginAlertConfig
    coverage_zero_alert: CoverageZeroAlertConfig
    pricing_rule_alert: PricingRuleAlertConfig
    near_zero: NearZeroConfig
    triage: TriageConfig
    top_contributors: TopContributorsConfig
    geo_clusters: dict[str, list[str]]
    top_publishers: list[str]
    scheduling: SchedulingConfig
    data_sources: DataSourcesConfig
    notifications: NotificationsConfig
    # v1.2 sections present in config/alerting_rules.yaml; added 2026-04-23 to
    # close the silent drift that broke Phase 09 Plan 03 backfill (Rule 3 fix).
    leading_indicator: LeadingIndicatorConfig
    cross_channel_detection: CrossChannelDetectionConfig
    gross_margin_alert: GrossMarginAlertConfig
    # Phase 10 MONITOR-02 (default_factory: missing section must NOT crash pipeline per WR-03).
    silent_failure_monitor: SilentFailureMonitorConfig = Field(default_factory=SilentFailureMonitorConfig)


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
