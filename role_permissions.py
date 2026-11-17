"""Role permissions and privacy controls for the PulseIQ Task 18 demo.

Demo role selection is not authentication. Replace it with an identity provider
before using this application with real users or production HR data.
"""
from __future__ import annotations

import pandas as pd

ROLE_ASSIGNMENTS = {
    "admin.demo": {"role": "ADMIN", "department_id": None, "team_id": None},
    "hr.demo": {"role": "HR", "department_id": "D01", "team_id": None},
    "manager.demo": {"role": "MANAGER", "department_id": None, "team_id": 1},
    "exec.demo": {"role": "EXECUTIVE", "department_id": None, "team_id": None},
}

HR_METRICS = {
    "M01", "M02", "M03", "M04", "M05", "M06",
    "M07", "M08", "M09", "M10", "M11", "M12",
    "M13", "M14", "M15", "M27",
}
MANAGER_METRICS = {"M22", "M23", "M24", "M25"}
SENSITIVE_METRICS = {"M04", "M05", "M06", "M27"}
DEFAULT_MINIMUM_GROUP_SIZE = 5


def get_user_permissions(username: str):
    return ROLE_ASSIGNMENTS.get(username)


def get_allowed_metrics(role: str):
    if role == "ADMIN":
        return "ALL"
    if role == "HR":
        return HR_METRICS.copy()
    if role == "MANAGER":
        return MANAGER_METRICS.copy()
    if role == "EXECUTIVE":
        return "COMPANY_ONLY"
    return set()


def get_minimum_group_size(metric_id: str, metric_dictionary: pd.DataFrame) -> int:
    """Read numeric threshold; blank/unknown values fail closed to 5."""
    if "metric_id" not in metric_dictionary.columns or "minimum_group_size" not in metric_dictionary.columns:
        return DEFAULT_MINIMUM_GROUP_SIZE

    rows = metric_dictionary.loc[
        metric_dictionary["metric_id"].astype(str).str.strip() == str(metric_id)
    ]
    if rows.empty:
        return DEFAULT_MINIMUM_GROUP_SIZE

    value = rows.iloc[0]["minimum_group_size"]
    if pd.isna(value) or not str(value).strip():
        threshold = DEFAULT_MINIMUM_GROUP_SIZE
    else:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        threshold = int(digits) if digits else DEFAULT_MINIMUM_GROUP_SIZE

    if metric_id in SENSITIVE_METRICS:
        threshold = max(threshold, 10)
    return max(threshold, DEFAULT_MINIMUM_GROUP_SIZE)


def is_group_visible(metric_id: str, group_size: int, metric_dictionary: pd.DataFrame) -> bool:
    return int(group_size) >= get_minimum_group_size(metric_id, metric_dictionary)


def can_access_metric(role: str, metric_id: str, level: str = "company") -> bool:
    """Server-side role/level check. HR is restricted to assigned department."""
    allowed = get_allowed_metrics(role)
    if role == "ADMIN":
        return True
    if role == "HR":
        return metric_id in allowed and level == "department"
    if role == "MANAGER":
        return metric_id in allowed and level == "team"
    if role == "EXECUTIVE":
        return level == "company"
    return False


def suppress_small_groups(
    frame: pd.DataFrame,
    metric_id: str,
    group_size_column: str,
    value_column: str,
    label_column: str,
    metric_dictionary: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """Return a safe display-only copy with primary + secondary suppression.

    If any group is primarily suppressed, the smallest remaining visible group
    is also suppressed to reduce differencing/inference risk. Do not display
    grand totals when this function reports suppression.
    """
    threshold = get_minimum_group_size(metric_id, metric_dictionary)
    result = frame[[label_column, group_size_column, value_column]].copy()
    result["__suppressed"] = result[group_size_column].fillna(0).astype(float) < threshold
    primary_found = bool(result["__suppressed"].any())

    if primary_found:
        visible = result.loc[~result["__suppressed"]]
        if not visible.empty:
            secondary_index = visible[group_size_column].astype(float).idxmin()
            result.loc[secondary_index, "__suppressed"] = True

    any_suppressed = bool(result["__suppressed"].any())
    result.loc[result["__suppressed"], label_column] = "Suppressed group"
    result.loc[result["__suppressed"], value_column] = pd.NA
    result.loc[result["__suppressed"], group_size_column] = pd.NA
    result = result.rename(columns={
        label_column: "Group",
        value_column: "KPI value",
        group_size_column: "Population / records",
    })
    result = result.drop(columns=["__suppressed"])
    return result, any_suppressed
