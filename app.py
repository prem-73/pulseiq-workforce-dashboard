import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="PulseIQ Workforce Analytics",
    layout="wide"
)

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "department_month.csv"

st.title("PulseIQ Workforce Analytics")
st.caption("Workforce | Payroll | Attendance | Productivity | Department Insights")

if not DATA_PATH.exists():
    st.error("Dashboard data file not found.")
    st.stop()

df = pd.read_csv(DATA_PATH)

required = [
    "department_name", "month", "month_label",
    "gross_pay", "employer_cost", "headcount_end",
    "attendance_rate", "hires", "exits",
    "overtime_pay", "tasks", "tasks_done"
]

missing = [col for col in required if col not in df.columns]

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

df["month"] = pd.to_datetime(df["month"])
df["month_label"] = df["month_label"].astype(str)

months = sorted(df["month_label"].dropna().unique())
departments = sorted(df["department_name"].dropna().unique())

st.sidebar.header("Dashboard Filters")

selected_month = st.sidebar.selectbox(
    "Select Month",
    ["All"] + months,
    index=0
)

selected_departments = st.sidebar.multiselect(
    "Select Departments",
    departments,
    default=departments
)

filtered = df[df["department_name"].isin(selected_departments)].copy()

if selected_month != "All":
    filtered = filtered[filtered["month_label"] == selected_month]

if filtered.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

latest_month = filtered["month_label"].max()
latest_data = filtered[filtered["month_label"] == latest_month]

headcount = latest_data["headcount_end"].sum()
gross_pay = latest_data["gross_pay"].sum()
employer_cost = latest_data["employer_cost"].sum()
attendance_rate = latest_data["attendance_rate"].mean() * 100

st.subheader("Executive Summary")
st.caption(f"Reporting period: {latest_month}")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Headcount", f"{headcount:,.0f}")
c2.metric("Gross Payroll", f"INR {gross_pay:,.0f}")
c3.metric("Employer Cost", f"INR {employer_cost:,.0f}")
c4.metric("Average Department Attendance", f"{attendance_rate:.1f}%")

st.divider()

st.subheader("Department-wise Headcount")

dept_data = latest_data.groupby(
    "department_name", as_index=False
)["headcount_end"].sum()

fig = px.bar(
    dept_data,
    x="department_name",
    y="headcount_end",
    title="Headcount by Department",
    labels={
        "department_name": "Department",
        "headcount_end": "Headcount"
    }
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly Payroll Trend")

payroll_trend = filtered.groupby(
    "month_label", as_index=False
)[["gross_pay", "employer_cost"]].sum()

payroll_trend = payroll_trend.sort_values("month_label")

fig2 = px.line(
    payroll_trend,
    x="month_label",
    y=["gross_pay", "employer_cost"],
    markers=True,
    title="Monthly Gross Payroll and Employer Cost",
    labels={
        "month_label": "Month",
        "value": "Amount (INR)",
        "variable": "Cost Type"
    }
)

st.plotly_chart(fig2, use_container_width=True)

st.subheader("Attendance by Department")

attendance_data = latest_data[
    ["department_name", "attendance_rate"]
].copy()

attendance_data["attendance_rate"] *= 100

fig3 = px.bar(
    attendance_data,
    x="department_name",
    y="attendance_rate",
    title="Department Attendance Rate",
    labels={
        "department_name": "Department",
        "attendance_rate": "Attendance Rate (%)"
    }
)

st.plotly_chart(fig3, use_container_width=True)

st.subheader("Department Data")

display_columns = [
    "department_name",
    "headcount_end",
    "gross_pay",
    "employer_cost",
    "attendance_rate",
    "hires",
    "exits",
    "overtime_pay",
    "tasks",
    "tasks_done"
]

display_data = latest_data[display_columns].copy()
display_data["attendance_rate"] *= 100
display_data = display_data.rename(
    columns={"attendance_rate": "attendance_rate_pct"}
)

st.dataframe(
    display_data,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Source: Department-level aggregated internship dataset. "
    "Attendance KPI is the simple average of department attendance rates. "
    "Figures represent available source records, not live HR data."
)
