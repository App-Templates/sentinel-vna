"""
AWS Athena connector for Value Network Alerting.
Queries Athena for revenue/bacino/coverage metrics, with retry and graceful fallback.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.utils.logger import get_logger

logger = get_logger("connector.athena")

# Whitelist of allowed channel_group values.
# Phase 17.4 D2CLOSE-02 (D-04): expanded from {GOOGLE, OPEN_BIDDING} to all 8
# canonical v1.2 schema channels. Production AWS credentials remain
# out-of-scope for Phase 17.4 (D-06 — Phase 21 v1.4 activation); this
# connector is code-ready with mock-based unit tests + graceful fallback
# via _get_athena_client returning None when creds are missing.
# Source of truth: backend/db/models.py CHANNEL_GROUP_CHECK_VALUES.
ALLOWED_CHANNEL_GROUPS = {
    "GOOGLE",                    # legacy alias (Phase 08 SCHEMA-01 8-value canonical list)
    "GOOGLE_ADEX",
    "OPEN_BIDDING",
    "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC",
    "TAM",
    "DIRECT",
    "DEAL",
}

# Regex for ISO date validation (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS variants)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")

# Whitelist for identifiers (database/table names): only alphanumeric + underscore
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "data" / "datasource_config.json"


def _load_athena_config() -> dict:
    """Load Athena section from datasource_config.json."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        return config.get("athena", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read datasource config: %s", e)
        return {}


def _get_athena_client(region: str):
    """Create a boto3 Athena client. Returns None if boto3 is unavailable or credentials are missing."""
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, BotoCoreError
    except ImportError:
        logger.error("boto3 is not installed. Install it with: pip install boto3")
        return None

    try:
        client = boto3.client("athena", region_name=region)
        # Verify credentials are available by calling STS
        sts = boto3.client("sts", region_name=region)
        sts.get_caller_identity()
        return client
    except NoCredentialsError:
        logger.warning("AWS credentials not configured. Athena connector unavailable.")
        return None
    except BotoCoreError as e:
        logger.warning("Failed to create Athena client: %s", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error creating Athena client: %s", e)
        return None


def _validate_inputs(
    channel_group: str,
    start_time: str,
    end_time: str,
    database: str,
    table_name: str,
) -> None:
    """Validate all query inputs. Raises ValueError on invalid input."""
    if channel_group not in ALLOWED_CHANNEL_GROUPS:
        raise ValueError(
            f"Invalid channel_group '{channel_group}'. "
            f"Allowed values: {sorted(ALLOWED_CHANNEL_GROUPS)}"
        )
    if not _DATE_RE.match(start_time):
        raise ValueError(f"Invalid start_time format: '{start_time}'. Expected YYYY-MM-DD[THH:MM[:SS]]")
    if not _DATE_RE.match(end_time):
        raise ValueError(f"Invalid end_time format: '{end_time}'. Expected YYYY-MM-DD[THH:MM[:SS]]")
    if not _IDENTIFIER_RE.match(database):
        raise ValueError(f"Invalid database name: '{database}'")
    if not _IDENTIFIER_RE.match(table_name):
        raise ValueError(f"Invalid table_name: '{table_name}'")


def _wait_for_query(
    client,
    execution_id: str,
    timeout_seconds: int = 30,
    poll_interval: float = 1.0,
) -> Optional[str]:
    """Poll Athena until query completes or times out. Returns final state or None on timeout."""
    deadline = time.time() + timeout_seconds
    attempt = 0

    while time.time() < deadline:
        try:
            resp = client.get_query_execution(QueryExecutionId=execution_id)
            state = resp["QueryExecution"]["Status"]["State"]

            if state in ("SUCCEEDED",):
                return state
            if state in ("FAILED", "CANCELLED"):
                reason = resp["QueryExecution"]["Status"].get("StateChangeReason", "unknown")
                logger.error("Athena query %s: %s — %s", state, execution_id, reason)
                return state

            # QUEUED or RUNNING — keep waiting
            time.sleep(min(poll_interval * (1.2 ** attempt), 5.0))
            attempt += 1

        except Exception as e:
            logger.error("Error polling Athena query %s: %s", execution_id, e)
            return None

    logger.error("Athena query timed out after %ds: %s", timeout_seconds, execution_id)
    return None


def fetch_from_athena(
    channel_group: str,
    start_time: str,
    end_time: str,
    max_retries: int = 2,
    base_delay: float = 2.0,
) -> Optional[pd.DataFrame]:
    """
    Query AWS Athena for metrics and return a DataFrame.

    Parameters
    ----------
    channel_group : str
        Channel group to filter (e.g. "GOOGLE", "OPEN_BIDDING").
    start_time : str
        ISO-format start timestamp.
    end_time : str
        ISO-format end timestamp.
    max_retries : int
        Number of retry attempts on transient errors.
    base_delay : float
        Base delay in seconds for exponential backoff.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with columns: timestamp, channel_group, geo_cluster, environment,
        publisher_id, revenue, bacino, coverage. Returns None on any failure.
    """
    config = _load_athena_config()

    if not config.get("enabled"):
        logger.info("Athena connector is disabled in config")
        return None

    region = config.get("region", "eu-west-1")
    database = config.get("database", "adkaora")
    workgroup = config.get("workgroup", "primary")
    s3_output = config.get("s3_output", "")
    table_name = config.get("table_name", "value_network_metrics")
    timeout_seconds = config.get("timeout_seconds", 30)

    if not s3_output:
        logger.error("Athena s3_output is not configured")
        return None

    client = _get_athena_client(region)
    if client is None:
        return None

    # Defense in depth: validate inputs (whitelist) BEFORE building the query
    try:
        _validate_inputs(channel_group, start_time, end_time, database, table_name)
    except ValueError as e:
        logger.error("Input validation failed: %s", e)
        return None

    # Build parameterized query — identifiers (database/table) are validated above,
    # user-controlled values use Athena ExecutionParameters (? placeholders)
    query = (
        f"SELECT "
        f"  timestamp, "
        f"  channel_group, "
        f"  environment, "
        f"  geo_cluster, "
        f"  publisher_id, "
        f"  revenue, "
        f"  ad_requests AS bacino, "
        f"  CASE WHEN ad_requests > 0 THEN CAST(impressions AS DOUBLE) / ad_requests ELSE 0 END AS coverage "
        f"FROM {database}.{table_name} "
        f"WHERE channel_group = ? "
        f"  AND timestamp >= ? "
        f"  AND timestamp <= ?"
    )
    query_params = [channel_group, start_time, end_time]
    logger.info("Athena query: %s | params: %s", query[:200], query_params)

    for attempt in range(max_retries + 1):
        try:
            # Start query execution with parameterized values
            start_resp = client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": database},
                WorkGroup=workgroup,
                ResultConfiguration={"OutputLocation": s3_output},
                ExecutionParameters=query_params,
            )
            execution_id = start_resp["QueryExecutionId"]
            logger.info("Athena query started: %s (attempt %d/%d)", execution_id, attempt + 1, max_retries + 1)

            # Wait for completion
            state = _wait_for_query(client, execution_id, timeout_seconds)

            if state == "SUCCEEDED":
                # Read results from S3 output
                result_resp = client.get_query_results(
                    QueryExecutionId=execution_id,
                    MaxResults=10000,
                )

                # Parse Athena results into DataFrame
                columns = [
                    col["Name"]
                    for col in result_resp["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
                ]
                rows = []
                for row in result_resp["ResultSet"]["Rows"][1:]:  # skip header row
                    rows.append([datum.get("VarCharValue", "") for datum in row["Data"]])

                if not rows:
                    logger.warning("Athena query returned 0 rows")
                    return None

                df = pd.DataFrame(rows, columns=columns)

                # Cast numeric columns
                for col in ("revenue", "bacino", "coverage"):
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                logger.info("Athena returned %d rows", len(df))
                return df

            elif state in ("FAILED", "CANCELLED"):
                # Non-transient failure, don't retry
                logger.error("Athena query failed with state: %s", state)
                return None

            else:
                # Timeout or poll error — retry with backoff
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Athena query inconclusive (attempt %d/%d), retrying in %.1fs",
                        attempt + 1, max_retries + 1, delay,
                    )
                    time.sleep(delay)

        except Exception as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Athena error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, max_retries + 1, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error("Athena connector failed after %d attempts: %s", max_retries + 1, e)
                return None

    logger.error("Athena connector exhausted all %d retry attempts", max_retries + 1)
    return None
