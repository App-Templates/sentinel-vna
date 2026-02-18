"""
Google Ad Manager (GAM) connector for Value Network Alerting.
Uses the GAM API (REST) for reporting, with graceful fallback when
credentials or libraries are unavailable.
"""

import csv
import io
import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.utils.logger import get_logger

logger = get_logger("connector.gam")

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "data" / "datasource_config.json"

# Graceful import of Google auth/API libraries
try:
    from google.oauth2 import service_account
    from googleapiclient import discovery

    _HAS_GOOGLE_LIBS = True
except ImportError:
    _HAS_GOOGLE_LIBS = False

# GAM API scopes
_GAM_SCOPES = ["https://www.googleapis.com/auth/dfp"]
_GAM_API_VERSION = "v202405"


def _load_gam_config() -> dict:
    """Load GAM section from datasource_config.json."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        return config.get("gam", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read datasource config: %s", e)
        return {}


def _build_credentials(credentials_path: str, network_code: str):
    """
    Build Google service-account credentials for GAM.
    Returns (credentials, network_code) or (None, None) on failure.
    """
    if not _HAS_GOOGLE_LIBS:
        logger.error(
            "google-auth / google-api-python-client not installed. "
            "Install with: pip install google-auth google-api-python-client"
        )
        return None

    creds_path = Path(credentials_path)
    if not creds_path.exists():
        logger.error("GAM credentials file not found: %s", credentials_path)
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_path),
            scopes=_GAM_SCOPES,
        )
        # Delegate to GAM network
        credentials = credentials.with_subject(None)
        return credentials
    except Exception as e:
        logger.error("Failed to load GAM credentials: %s", e)
        return None


def _get_gam_service(credentials):
    """Create the GAM Ad Manager reporting service client."""
    try:
        service = discovery.build(
            "dfareporting",
            _GAM_API_VERSION,
            credentials=credentials,
            cache_discovery=False,
        )
        return service
    except Exception as e:
        logger.error("Failed to build GAM API service: %s", e)
        return None


def _run_report(
    network_code: str,
    credentials,
    channel_group: str,
    start_time: str,
    end_time: str,
    timeout_seconds: int = 30,
) -> Optional[str]:
    """
    Create and run a GAM report job, poll until complete, and return CSV content.

    This is a structural implementation. Field names and report job parameters
    need to be adjusted to match the actual GAM network setup.

    TODO: Map actual GAM dimension/metric names once GAM access is available.
    """
    try:
        service = discovery.build(
            "admanager",
            _GAM_API_VERSION,
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as e:
        logger.error("Failed to build GAM admanager service: %s", e)
        return None

    # Build the report job definition
    # TODO: Adjust dimension/metric names to match the actual GAM configuration
    report_job = {
        "reportQuery": {
            "dimensions": [
                "DATE",
                "AD_UNIT_NAME",      # maps to publisher_id
                "COUNTRY_NAME",      # maps to geo_cluster
                "DEVICE_CATEGORY",   # maps to environment (WEB/AMP/APP)
            ],
            "columns": [
                "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS",
                "TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE",
                "TOTAL_AD_REQUESTS",
            ],
            "dateRangeType": "CUSTOM_DATE",
            "startDate": {
                "year": int(start_time[:4]),
                "month": int(start_time[5:7]),
                "day": int(start_time[8:10]),
            },
            "endDate": {
                "year": int(end_time[:4]),
                "month": int(end_time[5:7]),
                "day": int(end_time[8:10]),
            },
        }
    }

    try:
        # Submit the report
        report_response = (
            service.networks()
            .reports()
            .run(networkCode=network_code, body=report_job)
            .execute()
        )
        report_id = report_response.get("id") or report_response.get("reportId")
        if not report_id:
            logger.error("GAM report submission did not return a report ID")
            return None

        logger.info("GAM report submitted: %s", report_id)

        # Poll for completion
        deadline = time.time() + timeout_seconds
        poll_interval = 2.0
        attempt = 0

        while time.time() < deadline:
            status_response = (
                service.networks()
                .reports()
                .get(networkCode=network_code, reportId=report_id)
                .execute()
            )
            status = status_response.get("status", "")

            if status == "COMPLETED":
                # Download the report as CSV
                csv_data = (
                    service.networks()
                    .reports()
                    .download(networkCode=network_code, reportId=report_id)
                    .execute()
                )
                return csv_data

            if status in ("FAILED", "CANCELLED"):
                logger.error("GAM report %s ended with status: %s", report_id, status)
                return None

            # Still running — wait with backoff
            time.sleep(min(poll_interval * (1.2 ** attempt), 5.0))
            attempt += 1

        logger.error("GAM report timed out after %ds: %s", timeout_seconds, report_id)
        return None

    except Exception as e:
        logger.error("GAM report execution error: %s", e)
        return None


def _parse_csv_to_dataframe(csv_content: str, channel_group: str) -> Optional[pd.DataFrame]:
    """
    Parse GAM CSV report output into a DataFrame matching the expected schema.

    Expected output columns: timestamp, channel_group, geo_cluster, environment,
    publisher_id, revenue, bacino, coverage

    TODO: Adjust column name mappings once actual GAM report format is confirmed.
    """
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
    except Exception as e:
        logger.error("Failed to parse GAM CSV: %s", e)
        return None

    if not rows:
        logger.warning("GAM CSV report contains 0 data rows")
        return None

    # Column mapping from GAM report to our schema
    # TODO: Verify these mappings against actual GAM report column headers
    GAM_COL_MAP = {
        "Dimension.DATE": "timestamp",
        "Dimension.AD_UNIT_NAME": "publisher_id",
        "Dimension.COUNTRY_NAME": "geo_raw",
        "Dimension.DEVICE_CATEGORY": "env_raw",
        "Column.TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE": "revenue",
        "Column.TOTAL_AD_REQUESTS": "bacino",
        "Column.TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS": "impressions",
    }

    # Geo mapping: country name -> cluster
    GEO_MAP = {
        "Italy": "ITA",
        "Spain": "ES",
    }
    # Everything else -> "OTHER"

    # Environment mapping: device category -> environment
    ENV_MAP = {
        "Desktop": "WEB",
        "Tablet": "WEB",
        "Mobile": "APP",
        "Connected TV": "APP",
    }
    # AMP detection would require additional info from the request URL

    parsed_rows = []
    for row in rows:
        mapped = {}
        for gam_col, our_col in GAM_COL_MAP.items():
            mapped[our_col] = row.get(gam_col, "")

        # Apply geo mapping
        geo_raw = mapped.pop("geo_raw", "")
        mapped["geo_cluster"] = GEO_MAP.get(geo_raw, "OTHER")

        # Apply environment mapping
        env_raw = mapped.pop("env_raw", "")
        mapped["environment"] = ENV_MAP.get(env_raw, "WEB")

        # Set channel_group from the query filter
        mapped["channel_group"] = channel_group

        parsed_rows.append(mapped)

    df = pd.DataFrame(parsed_rows)

    # Cast numeric columns
    for col in ("revenue", "bacino"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "impressions" in df.columns:
        df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0)
        # Calculate coverage = impressions / bacino
        df["coverage"] = df.apply(
            lambda r: r["impressions"] / r["bacino"] if r["bacino"] > 0 else 0.0,
            axis=1,
        )
    else:
        df["coverage"] = 0.0

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Keep only the expected schema columns
    expected_cols = [
        "timestamp", "channel_group", "geo_cluster", "environment",
        "publisher_id", "revenue", "bacino", "coverage",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "" if col in ("channel_group", "geo_cluster", "environment", "publisher_id") else 0.0

    df = df[expected_cols]

    logger.info("Parsed GAM report: %d rows", len(df))
    return df


def fetch_from_gam(
    channel_group: str,
    start_time: str,
    end_time: str,
) -> Optional[pd.DataFrame]:
    """
    Fetch metrics from Google Ad Manager API.

    Parameters
    ----------
    channel_group : str
        Channel group to filter (e.g. "GOOGLE", "OPEN_BIDDING").
    start_time : str
        ISO-format start timestamp.
    end_time : str
        ISO-format end timestamp.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with columns: timestamp, channel_group, geo_cluster, environment,
        publisher_id, revenue, bacino, coverage. Returns None on any failure.
    """
    config = _load_gam_config()

    if not config.get("enabled"):
        logger.info("GAM connector is disabled in config")
        return None

    if not _HAS_GOOGLE_LIBS:
        logger.warning(
            "GAM connector enabled but google-auth / google-api-python-client "
            "not installed. Skipping GAM."
        )
        return None

    network_code = config.get("network_code", "")
    credentials_path = config.get("credentials_path", "")
    timeout_seconds = config.get("timeout_seconds", 30)

    if not network_code:
        logger.error("GAM network_code is not configured")
        return None

    if not credentials_path:
        logger.error("GAM credentials_path is not configured")
        return None

    credentials = _build_credentials(credentials_path, network_code)
    if credentials is None:
        return None

    logger.info(
        "Attempting GAM fetch for %s [%s, %s]",
        channel_group, start_time, end_time,
    )

    csv_content = _run_report(
        network_code=network_code,
        credentials=credentials,
        channel_group=channel_group,
        start_time=start_time,
        end_time=end_time,
        timeout_seconds=timeout_seconds,
    )

    if csv_content is None:
        logger.warning("GAM report returned no data")
        return None

    return _parse_csv_to_dataframe(csv_content, channel_group)
