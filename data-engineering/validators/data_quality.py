"""
Validates extracted DataFrames before they enter the transformer layer.

Two severity levels:
  CRITICAL  - pipeline halts.
  WARNING   - bad rows are quarantined and pipeline continues on clean subset.
"""

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

VALID_CATEGORIES = {"IT_SUPPORT", "FACILITIES", "HR_REQUEST"}
VALID_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_STATUSES = {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"}

EXPECTED_SLA_COMBINATIONS = {
    (category, priority)
    for category in VALID_CATEGORIES
    for priority in VALID_PRIORITIES
}

RESOLVED_STATUSES = {"RESOLVED", "CLOSED"}
NON_OPEN_STATUSES = {"ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"}


class DataQualityError(Exception):
    """Raised when a CRITICAL data quality check fails."""


def validate_sla_policies(sla_df: pd.DataFrame) -> None:
    logger.info("Validating SLA policies (%d rows)", len(sla_df))
    errors = []

    if sla_df.empty:
        raise DataQualityError(
            "sla_policies table is empty. Backend seed has not run. "
            "Cannot compute SLA metrics."
        )

    required_cols = {
        "category",
        "priority",
        "response_time_hours",
        "resolution_time_hours",
    }
    missing_cols = required_cols - set(sla_df.columns)
    if missing_cols:
        raise DataQualityError(
            f"sla_policies is missing required columns: {missing_cols}"
        )

    actual_combinations = set(zip(sla_df["category"], sla_df["priority"]))
    missing_combinations = EXPECTED_SLA_COMBINATIONS - actual_combinations
    if missing_combinations:
        errors.append(
            f"Missing SLA policy rows for combinations: {missing_combinations}. "
            "Tickets in these categories may have NULL sla_deadline."
        )

    bad_resolution = sla_df[sla_df["resolution_time_hours"] <= 0]
    if not bad_resolution.empty:
        errors.append(
            f"{len(bad_resolution)} rows have resolution_time_hours <= 0: "
            f"{bad_resolution[['category', 'priority', 'resolution_time_hours']].to_dict('records')}"
        )

    bad_response = sla_df[sla_df["response_time_hours"] <= 0]
    if not bad_response.empty:
        errors.append(
            f"{len(bad_response)} rows have response_time_hours <= 0: "
            f"{bad_response[['category', 'priority', 'response_time_hours']].to_dict('records')}"
        )

    null_counts = sla_df[list(required_cols)].isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if not null_cols.empty:
        errors.append(f"Nulls found in sla_policies: {null_cols.to_dict()}")

    if errors:
        raise DataQualityError(
            "SLA policy validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        )

    logger.info("SLA policy validation passed - all required policies are present.")


def validate_service_requests(
    requests_df: pd.DataFrame,
    sla_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    del sla_df  # reserved for cross-table checks
    logger.info("Validating service requests (%d rows)", len(requests_df))

    required_cols = {
        "id",
        "category",
        "priority",
        "status",
        "requester_id",
        "created_at",
        "updated_at",
        "sla_deadline",
        "is_sla_breached",
    }
    missing_cols = required_cols - set(requests_df.columns)
    if missing_cols:
        raise DataQualityError(
            f"service_requests is missing required columns: {missing_cols}. "
            "Schema may have changed."
        )

    df = requests_df.copy()
    quarantine_rows = []

    optional_cols = ["resolved_at", "first_response_at", "closed_at", "assigned_to_id"]
    for column in optional_cols:
        if column not in df.columns:
            df[column] = pd.NA

    for column in (
        "created_at",
        "resolved_at",
        "first_response_at",
        "sla_deadline",
        "updated_at",
        "closed_at",
    ):
        df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")

    bad_category = df[~df["category"].isin(VALID_CATEGORIES)]
    if not bad_category.empty:
        logger.warning(
            "QUARANTINE: %d rows have invalid category values: %s",
            len(bad_category),
            bad_category["category"].dropna().unique().tolist(),
        )
        bad_category = bad_category.copy()
        bad_category["quarantine_reason"] = "invalid_category"
        quarantine_rows.append(bad_category)
        df = df[df["category"].isin(VALID_CATEGORIES)]

    bad_priority = df[~df["priority"].isin(VALID_PRIORITIES)]
    if not bad_priority.empty:
        logger.warning(
            "QUARANTINE: %d rows have invalid priority values: %s",
            len(bad_priority),
            bad_priority["priority"].dropna().unique().tolist(),
        )
        bad_priority = bad_priority.copy()
        bad_priority["quarantine_reason"] = "invalid_priority"
        quarantine_rows.append(bad_priority)
        df = df[df["priority"].isin(VALID_PRIORITIES)]

    bad_status = df[~df["status"].isin(VALID_STATUSES)]
    if not bad_status.empty:
        logger.warning(
            "QUARANTINE: %d rows have invalid status values: %s",
            len(bad_status),
            bad_status["status"].dropna().unique().tolist(),
        )
        bad_status = bad_status.copy()
        bad_status["quarantine_reason"] = "invalid_status"
        quarantine_rows.append(bad_status)
        df = df[df["status"].isin(VALID_STATUSES)]

    critical_null_mask = df["requester_id"].isnull() | df["created_at"].isnull()
    bad_nulls = df[critical_null_mask]
    if not bad_nulls.empty:
        logger.warning(
            "QUARANTINE: %d rows have NULL in requester_id or created_at",
            len(bad_nulls),
        )
        bad_nulls = bad_nulls.copy()
        bad_nulls["quarantine_reason"] = "null_in_required_field"
        quarantine_rows.append(bad_nulls)
        df = df[~critical_null_mask]

    resolved_rows = df["resolved_at"].notna()
    bad_resolution_time = df[resolved_rows & (df["resolved_at"] < df["created_at"])]
    if not bad_resolution_time.empty:
        logger.warning(
            "QUARANTINE: %d rows have resolved_at < created_at",
            len(bad_resolution_time),
        )
        bad_resolution_time = bad_resolution_time.copy()
        bad_resolution_time["quarantine_reason"] = "resolved_at_before_created_at"
        quarantine_rows.append(bad_resolution_time)
        df = df[~(resolved_rows & (df["resolved_at"] < df["created_at"]))]

    response_rows = df["first_response_at"].notna()
    bad_response_time = df[response_rows & (df["first_response_at"] < df["created_at"])]
    if not bad_response_time.empty:
        logger.warning(
            "QUARANTINE: %d rows have first_response_at < created_at",
            len(bad_response_time),
        )
        bad_response_time = bad_response_time.copy()
        bad_response_time["quarantine_reason"] = "first_response_at_before_created_at"
        quarantine_rows.append(bad_response_time)
        df = df[~(response_rows & (df["first_response_at"] < df["created_at"]))]

    both_present = df["closed_at"].notna() & df["resolved_at"].notna()
    bad_close_time = df[both_present & (df["closed_at"] < df["resolved_at"])]
    if not bad_close_time.empty:
        logger.warning(
            "QUARANTINE: %d rows have closed_at < resolved_at",
            len(bad_close_time),
        )
        bad_close_time = bad_close_time.copy()
        bad_close_time["quarantine_reason"] = "closed_at_before_resolved_at"
        quarantine_rows.append(bad_close_time)
        df = df[~(both_present & (df["closed_at"] < df["resolved_at"]))]

    resolved_status_mask = df["status"].isin(RESOLVED_STATUSES)
    missing_resolved_at = df[resolved_status_mask & df["resolved_at"].isnull()]
    if not missing_resolved_at.empty:
        logger.warning(
            "QUARANTINE: %d RESOLVED/CLOSED rows missing resolved_at",
            len(missing_resolved_at),
        )
        missing_resolved_at = missing_resolved_at.copy()
        missing_resolved_at["quarantine_reason"] = "resolved_status_missing_resolved_at"
        quarantine_rows.append(missing_resolved_at)
        df = df[~(resolved_status_mask & df["resolved_at"].isnull())]

    non_open_mask = df["status"].isin(NON_OPEN_STATUSES)
    missing_agent = df[non_open_mask & df["assigned_to_id"].isnull()]
    if not missing_agent.empty:
        logger.warning(
            "DATA WARNING: %d non-OPEN rows have no assigned_to_id.",
            len(missing_agent),
        )

    open_mask = df["status"] == "OPEN"
    open_with_resolved = df[open_mask & df["resolved_at"].notna()]
    if not open_with_resolved.empty:
        logger.warning(
            "QUARANTINE: %d OPEN rows have resolved_at",
            len(open_with_resolved),
        )
        open_with_resolved = open_with_resolved.copy()
        open_with_resolved["quarantine_reason"] = "open_status_has_resolved_at"
        quarantine_rows.append(open_with_resolved)
        df = df[~(open_mask & df["resolved_at"].notna())]

    both_present = df["resolved_at"].notna() & df["sla_deadline"].notna()
    actual_breach = df[
        both_present
        & (df["resolved_at"] > df["sla_deadline"])
        & (~df["is_sla_breached"].fillna(False).astype(bool))
    ]
    if not actual_breach.empty:
        logger.warning(
            "SLA INCONSISTENCY: %d rows resolved after deadline but is_sla_breached=FALSE.",
            len(actual_breach),
        )

    quarantine_df = (
        pd.concat(quarantine_rows, ignore_index=True)
        if quarantine_rows
        else pd.DataFrame(columns=list(df.columns) + ["quarantine_reason"])
    )

    total_in = len(requests_df)
    total_out = len(df)
    removed = total_in - total_out

    if removed > 0:
        logger.warning(
            "Validation complete: %d/%d rows quarantined (%.1f%%). Clean rows=%d.",
            removed,
            total_in,
            (removed / total_in * 100) if total_in > 0 else 0.0,
            total_out,
        )
    else:
        logger.info("Validation complete: all %d rows passed.", total_in)

    return df, quarantine_df


def log_quarantine_summary(quarantine_df: pd.DataFrame) -> None:
    if quarantine_df is None or quarantine_df.empty:
        return

    summary = (
        quarantine_df.groupby("quarantine_reason")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    logger.warning("=== QUARANTINE SUMMARY ===")
    for _, row in summary.iterrows():
        logger.warning("  %-45s %d rows", row["quarantine_reason"], row["count"])
    logger.warning("  %-45s %d rows total", "TOTAL QUARANTINED", len(quarantine_df))
    logger.warning("==========================")

