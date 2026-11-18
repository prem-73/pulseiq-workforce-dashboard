from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

import os
import json
from urllib.request import urlopen
from urllib.error import URLError
import os
import json
from urllib.request import urlopen
from urllib.error import URLError

from role_permissions import (
    ROLE_ASSIGNMENTS,
    get_user_permissions,
    get_allowed_metrics,
    get_minimum_group_size,
    can_access_metric,
    suppress_small_groups,
)

st.set_page_config(page_title="PulseIQ Workforce Analytics", layout="wide")
BASE = Path(__file__).parent
DATA = BASE / "data"

st.title("PulseIQ Workforce Analytics")
st.caption("Task 18 | Self-service KPI Explorer with privacy controls")
# ==========================================
# TASK 19 - METRICS API DATA FRESHNESS
# ==========================================

API_BASE_URL = os.getenv("PULSEIQ_API_URL", "").rstrip("/")

st.subheader("Task 19 - Data Freshness")

if API_BASE_URL:
    try:
        with urlopen(
            f"{API_BASE_URL}/freshness",
            timeout=5
        ) as response:

            freshness = json.loads(
                response.read().decode("utf-8")
            )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Last Data Refresh",
            freshness.get("last_refresh", "Unknown")
        )

        col2.metric(
            "ETL Status",
            freshness.get("etl_status", "Unknown")
        )

        col3.metric(
            "Freshness Status",
            freshness.get("freshness_status", "Unknown").upper()
        )

        st.caption(
            f"Total Rows: {freshness.get('total_rows_in', 0)} | "
            f"Passed: {freshness.get('total_rows_passed', 0)} | "
            f"Quarantined: {freshness.get('total_rows_quarantined', 0)}"
        )

    except (URLError, TimeoutError, ValueError, KeyError):
        st.warning(
            "Data freshness information is unavailable."
        )

else:
    st.info("Metrics API URL is not configured.")

# ==========================================
# END TASK 19
# ==========================================
# Demo identity switcher only; this is not authentication.
demo_users_path = DATA / "demo_users.csv"
if demo_users_path.exists():
    demo_users = pd.read_csv(demo_users_path)
    available_users = [
        str(u) for u in demo_users["username"].tolist()
        if str(u) in ROLE_ASSIGNMENTS
    ]
else:
    available_users = list(ROLE_ASSIGNMENTS)

if not available_users:
    st.error("No configured demo users found.")
    st.stop()

username = st.sidebar.selectbox("Demo user", available_users)
identity = get_user_permissions(username)
if identity is None:
    st.error("Unknown demo user.")
    st.stop()

role = identity["role"]
st.sidebar.success(f"Role: {role}")
st.sidebar.caption(
    "Demo role selector only — not secure authentication. "
    "Do not use with real production HR data."
)

metric_dictionary_path = DATA / "metric_dictionary.csv"
if metric_dictionary_path.exists():
    metric_dictionary = pd.read_csv(metric_dictionary_path)
else:
    metric_dictionary = pd.DataFrame(columns=["metric_id", "minimum_group_size"])

dept_path = DATA / "department_month.csv"
if not dept_path.exists():
    st.error("Missing data/department_month.csv")
    st.stop()

dept = pd.read_csv(dept_path)
required_dept = {
    "month", "department_name", "gross_pay", "employer_cost",
    "headcount_end", "attendance_rate", "hires", "exits",
}
missing = sorted(required_dept - set(dept.columns))
if missing:
    st.error(f"Department dataset is missing columns: {missing}")
    st.stop()

dept["month"] = pd.to_datetime(dept["month"], errors="coerce")
for col in ["gross_pay", "employer_cost", "headcount_end", "attendance_rate", "hires", "exits"]:
    dept[col] = pd.to_numeric(dept[col], errors="coerce").fillna(0)

# Ensure a department key is available for HR's assigned-department filter.
if "department_id" not in dept.columns:
    dim_path = DATA / "dim_department.csv"
    if dim_path.exists():
        dim = pd.read_csv(dim_path)
        if {"department_id", "department_name"}.issubset(dim.columns):
            dept = dept.merge(
                dim[["department_id", "department_name"]].drop_duplicates(),
                on="department_name", how="left"
            )
if "department_id" not in dept.columns:
    st.error("Department ID is unavailable; cannot enforce HR department restriction.")
    st.stop()

months = sorted(dept["month"].dropna().unique())
if not months:
    st.error("No valid reporting months in department dataset.")
    st.stop()
month_labels = [pd.Timestamp(m).strftime("%Y-%m") for m in months]
selected_month_label = st.sidebar.selectbox("Reporting month", month_labels, index=len(month_labels)-1)
selected_month = pd.Timestamp(selected_month_label + "-01")
dept_month = dept[dept["month"].dt.to_period("M") == selected_month.to_period("M")].copy()

st.info(
    "Privacy rules are applied in the data layer before tables/charts are rendered. "
    "Small groups are suppressed; no row-level employee or salary records are displayed."
)

# Department-level KPI definitions. Rates are shown using source values; attendance
# follows the source dashboard's documented simple-average caveat.
department_metrics = {
    "M01": ("Headcount", "headcount_end", "sum", "people"),
    "M02": ("Hires", "hires", "sum", "people"),
    "M03": ("Exits", "exits", "sum", "people"),
    "M07": ("Gross payroll", "gross_pay", "sum", "INR"),
    "M09": ("Employer cost", "employer_cost", "sum", "INR"),
    "M13": ("Attendance rate", "attendance_rate", "mean_pct", "%"),
}
# Include attrition only when the source contains the metric. Threshold is 10.
if "attrition_rate_monthly_pct" in dept_month.columns:
    dept_month["attrition_rate_monthly_pct"] = pd.to_numeric(
        dept_month["attrition_rate_monthly_pct"], errors="coerce"
    )
    department_metrics["M04"] = (
        "Monthly attrition rate", "attrition_rate_monthly_pct", "mean", "%"
    )
if "overtime_share_pct" in dept_month.columns:
    dept_month["overtime_share_pct"] = pd.to_numeric(
        dept_month["overtime_share_pct"], errors="coerce"
    )
    department_metrics["M11"] = ("Overtime share", "overtime_share_pct", "mean", "%")

def metric_value(series, aggregation):
    value = series.sum() if aggregation == "sum" else series.mean()
    return float(value) if pd.notna(value) else 0.0

def format_value(value, unit):
    if pd.isna(value):
        return "—"
    if unit == "INR":
        return f"INR {value:,.0f}"
    if unit == "%":
        # Attendance in source is a fraction; other percentage columns are already pct.
        return f"{value:,.2f}%"
    return f"{value:,.0f}"

def department_population(frame):
    return pd.to_numeric(frame["headcount_end"], errors="coerce").fillna(0)

def build_department_groups(frame, metric_id):
    label, source_col, aggregation, unit = department_metrics[metric_id]
    temp = frame.copy()
    temp["__population"] = department_population(temp)
    grouped = temp.groupby(["department_id", "department_name"], dropna=False).agg(
        population=("__population", "max"),
        raw_value=(source_col, aggregation),
    ).reset_index()
    # Attendance source values are fractions in the Task 17 dashboard.
    if metric_id == "M13":
        grouped["raw_value"] = grouped["raw_value"] * 100
    return grouped, label, unit

def render_safe_groups(grouped, metric_id, value_label, unit, label_col):
    safe_input = grouped.rename(columns={
        "population": "__population",
        "raw_value": "__value",
        label_col: "__label",
    })
    safe_display, suppressed = suppress_small_groups(
        safe_input, metric_id, "__population", "__value", "__label", metric_dictionary
    )
    safe_display["KPI value"] = safe_display["KPI value"].apply(
        lambda x: format_value(x, unit) if pd.notna(x) else "Suppressed"
    )
    safe_display = safe_display[["Group", "KPI value", "Population / records"]]
    if suppressed:
        st.warning(
            "Primary and complementary suppression applied. "
            "Grand total is hidden to reduce inference from suppressed groups."
        )
    st.dataframe(safe_display, use_container_width=True, hide_index=True)
    return safe_display, suppressed

def load_team_data():
    team_dim_path = DATA / "task8" / "dim_team.csv"
    task_path = DATA / "task8" / "fact_task.csv"
    if not team_dim_path.exists() or not task_path.exists():
        return None, None, "Team data files are missing."
    teams = pd.read_csv(team_dim_path)
    tasks = pd.read_csv(task_path)
    needed_team = {"team_id", "team_name", "team_size"}
    needed_task = {"task_id", "team_id", "status", "story_points", "started_at", "completed_at", "due_date"}
    if not needed_team.issubset(teams.columns) or not needed_task.issubset(tasks.columns):
        return None, None, "Team/task files do not have the expected columns."
    for col in ["started_at", "completed_at", "due_date"]:
        tasks[col] = pd.to_datetime(tasks[col], errors="coerce")
    tasks["story_points"] = pd.to_numeric(tasks["story_points"], errors="coerce").fillna(0)
    return teams, tasks, None

def build_team_groups(teams, tasks, metric_id):
    joined = tasks.merge(teams[["team_id", "team_name", "team_size"]], on="team_id", how="inner")
    status = joined["status"].astype(str).str.strip().str.lower()
    completed = status.isin({"done", "completed", "closed", "resolved"})
    joined["__completed"] = completed
    joined["__cycle_days"] = (
        joined["completed_at"] - joined["started_at"]
    ).dt.total_seconds() / 86400
    if metric_id == "M22":
        grouped = joined.groupby(["team_id", "team_name"], as_index=False).agg(
            records=("task_id", "count"), completed=("__completed", "sum")
        )
        grouped["raw_value"] = grouped["completed"] / grouped["records"].replace(0, pd.NA) * 100
        return grouped, "Task completion rate", "%"
    if metric_id == "M23":
        eligible = joined[joined["due_date"].notna() & joined["completed_at"].notna()].copy()
        eligible["__on_time"] = eligible["completed_at"] <= eligible["due_date"]
        grouped = eligible.groupby(["team_id", "team_name"], as_index=False).agg(
            records=("task_id", "count"), on_time=("__on_time", "sum")
        )
        grouped["raw_value"] = grouped["on_time"] / grouped["records"].replace(0, pd.NA) * 100
        return grouped, "On-time delivery rate", "%"
    completed_rows = joined[joined["__completed"]].copy()
    if metric_id == "M24":
        grouped = completed_rows.groupby(["team_id", "team_name"], as_index=False).agg(
            records=("task_id", "count"), raw_value=("story_points", "sum")
        )
        return grouped, "Completed story points (velocity)", "points"
    grouped = completed_rows.groupby(["team_id", "team_name"], as_index=False).agg(
        records=("task_id", "count"), raw_value=("__cycle_days", "mean")
    )
    return grouped, "Average cycle time", "days"

def render_team_explorer(selected_metric_id):
    teams, tasks, error = load_team_data()
    if error:
        st.error(error)
        return
    team_id = identity.get("team_id")
    if role == "MANAGER":
        teams = teams[teams["team_id"] == team_id]
        tasks = tasks[tasks["team_id"] == team_id]
    grouped, title, unit = build_team_groups(teams, tasks, selected_metric_id)
    if grouped.empty:
        st.warning("No task data for this role/metric.")
        return
    safe_input = grouped.rename(columns={
        "records": "__records",
        "raw_value": "__value",
        "team_name": "__label",
    })
    safe_display, suppressed = suppress_small_groups(
        safe_input, selected_metric_id, "__records", "__value", "__label", metric_dictionary
    )
    safe_display["KPI value"] = safe_display["KPI value"].apply(
        lambda x: format_value(x, unit) if pd.notna(x) else "Suppressed"
    )
    st.subheader(title)
    if suppressed:
        st.warning("Small team/task groups suppressed; grand total is not displayed.")
    st.dataframe(
        safe_display[["Group", "KPI value", "Population / records"]],
        use_container_width=True, hide_index=True
    )
    visible = safe_display[safe_display["KPI value"] != "Suppressed"].copy()
    if not visible.empty:
        chart = px.bar(visible, x="Group", y="KPI value", title=title)
        # Chart uses raw values only from visible groups; use a safe numeric copy.
        raw_visible = grouped[grouped["team_name"].isin(visible["Group"])]
        if not raw_visible.empty:
            chart = px.bar(raw_visible, x="team_name", y="raw_value", title=title)
            st.plotly_chart(chart, use_container_width=True)

# Role-specific access and explorer
st.header("Self-service KPI Explorer")
allowed = get_allowed_metrics(role)

if role == "EXECUTIVE":
    st.caption("Executive view: company-level KPIs only. Department and team breakdowns are unavailable.")
    metric_choices = [m for m in ["M01", "M02", "M03", "M07", "M09", "M13", "M04", "M11"] if m in department_metrics]
    metric_labels = {m: department_metrics[m][0] for m in metric_choices}
    chosen = st.selectbox("Choose company KPI", metric_choices, format_func=lambda x: metric_labels[x])
    if not can_access_metric(role, chosen, "company"):
        st.error("Access denied.")
        st.stop()
    label, source_col, aggregation, unit = department_metrics[chosen]
    pop = department_population(dept_month).sum()
    threshold = get_minimum_group_size(chosen, metric_dictionary)
    if pop < threshold:
        st.warning(f"Company KPI suppressed: population {int(pop)} is below minimum {threshold}.")
    else:
        val = metric_value(dept_month[source_col], aggregation)
        if chosen == "M13":
            val *= 100
        st.metric(label, format_value(val, unit))
        st.caption(f"Company-level result for {selected_month_label}; no department/team detail shown.")
elif role == "MANAGER":
    st.caption("Manager view: assigned demo team only. Team-level task metrics only.")
    team_metric_choices = ["M22", "M23", "M24", "M25"]
    chosen = st.selectbox(
        "Choose team KPI", team_metric_choices,
        format_func=lambda x: {
            "M22": "Task completion rate",
            "M23": "On-time delivery rate",
            "M24": "Velocity (completed story points)",
            "M25": "Average cycle time",
        }[x],
    )
    if not can_access_metric(role, chosen, "team"):
        st.error("Access denied.")
        st.stop()
    render_team_explorer(chosen)
elif role == "HR":
    st.caption("HR view: assigned department D01 only. Department-level aggregates; no employee salary details.")
    metric_choices = [m for m in ["M01", "M02", "M03", "M07", "M09", "M13", "M04", "M11"] if m in department_metrics]
    metric_labels = {m: department_metrics[m][0] for m in metric_choices}
    chosen = st.selectbox("Choose department KPI", metric_choices, format_func=lambda x: metric_labels[x])
    if not can_access_metric(role, chosen, "department"):
        st.error("Access denied.")
        st.stop()
    own = dept_month[dept_month["department_id"].astype(str) == str(identity["department_id"])]
    grouped, label, unit = build_department_groups(own, chosen)
    if grouped.empty:
        st.warning("No data for the assigned department.")
    else:
        threshold = get_minimum_group_size(chosen, metric_dictionary)
        pop = int(grouped["population"].max())
        if pop < threshold:
            st.warning(f"Department KPI suppressed: population {pop} is below minimum {threshold}.")
        else:
            value = float(grouped["raw_value"].iloc[0])
            if chosen == "M13":
                value *= 100
            st.metric(label, format_value(value, unit))
            st.caption("Only the assigned department is available in this demo view.")
else:  # ADMIN
    st.caption("Admin view: all available aggregate KPIs. Employee-level records are not included in this demo.")
    view_level = st.radio("Drill-down level", ["Company", "Department", "Team"], horizontal=True)
    if view_level in {"Company", "Department"}:
        metric_choices = list(department_metrics.keys())
        metric_labels = {m: department_metrics[m][0] for m in metric_choices}
        chosen = st.selectbox("Choose KPI", metric_choices, format_func=lambda x: metric_labels[x])
        access_level = "company" if view_level == "Company" else "department"
        if not can_access_metric(role, chosen, access_level):
            st.error("Access denied.")
            st.stop()
        if view_level == "Company":
            label, source_col, aggregation, unit = department_metrics[chosen]
            population = int(department_population(dept_month).sum())
            threshold = get_minimum_group_size(chosen, metric_dictionary)
            if population < threshold:
                st.warning("Company KPI suppressed by minimum group-size policy.")
            else:
                value = metric_value(dept_month[source_col], aggregation)
                if chosen == "M13":
                    value *= 100
                st.metric(label, format_value(value, unit))
        else:
            grouped, label, unit = build_department_groups(dept_month, chosen)
            st.subheader(label + " by department")
            safe_display, suppressed = render_safe_groups(
                grouped, chosen, label, unit, "department_name"
            )
            if not suppressed:
                chart_data = grouped.copy()
                chart = px.bar(chart_data, x="department_name", y="raw_value", title=label + " by department")
                st.plotly_chart(chart, use_container_width=True)
    else:
        team_metric_choices = ["M22", "M23", "M24", "M25"]
        chosen = st.selectbox(
            "Choose team KPI", team_metric_choices,
            format_func=lambda x: {
                "M22": "Task completion rate",
                "M23": "On-time delivery rate",
                "M24": "Velocity (completed story points)",
                "M25": "Average cycle time",
            }[x],
        )
        if not can_access_metric(role, chosen, "team"):
            st.error("Access denied.")
            st.stop()
        render_team_explorer(chosen)

st.divider()
st.subheader("Task 17 Workforce Dashboard")
st.caption("The existing Task 17 dashboard is retained as role-filtered aggregate views.")
if role in {"ADMIN", "HR"}:
    if role == "HR":
        legacy = dept_month[dept_month["department_id"].astype(str) == str(identity["department_id"])]
    else:
        legacy = dept_month
    if not legacy.empty:
        # dept_month already contains only the selected month; retain all
        # permitted department rows for the summary aggregation.
        latest = legacy
        c1, c2, c3 = st.columns(3)
        c1.metric("Headcount", f"{latest['headcount_end'].sum():,.0f}")
        c2.metric("Gross Payroll", f"INR {latest['gross_pay'].sum():,.0f}")
        c3.metric("Employer Cost", f"INR {latest['employer_cost'].sum():,.0f}")
elif role == "EXECUTIVE":
    # Company-level view: aggregate all departments for the selected month.
    c1, c2, c3 = st.columns(3)
    c1.metric("Company headcount", f"{dept_month['headcount_end'].sum():,.0f}")
    c2.metric("Company gross payroll", f"INR {dept_month['gross_pay'].sum():,.0f}")
    c3.metric("Company employer cost", f"INR {dept_month['employer_cost'].sum():,.0f}")
else:
    st.caption("Manager role sees team KPIs above; department/payroll views are not available.")

st.caption(
    "Source: approved aggregated internship datasets. "
    "The team dimension has no department_id mapping, so team is a separate drill-down "
    "rather than a child of a department. HR and Manager assignments are demo mappings "
    "(HR=D01, Manager=Team A). Blank metric thresholds default to 5; sensitive metrics "
    "use at least 10. No CSV download or row-level employee view is provided."
)
