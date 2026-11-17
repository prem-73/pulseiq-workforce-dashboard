import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="PulseIQ Workforce Analytics",
    layout="wide"
)

DATA_PATH = Path(__file__).parent / "data" / "department_month.csv"

st.title("PulseIQ Workforce Analytics")
st.caption("Workforce | Payroll | Attendance | Department Insights")

if not DATA_PATH.exists():
    st.error("Dashboard data file not found.")
    st.stop()

df = pd.read_csv(DATA_PATH)

required = [
    "department_name", "year", "month", "gross_pay",
    "net_pay", "attendance_records", "present_records",
    "current_headcount", "month_label"
]

missing = [col for col in required if col not in df.columns]

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

df["month_label"] = df["month_label"].astype(str)

months = sorted(df["month_label"].dropna().unique())
departments = sorted(df["department_name"].dropna().unique())

st.sidebar.header("Dashboard Filters")

selected_month = st.sidebar.selectbox(
    "Select Month",
    ["All"] + months,
    index=len(months)
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

headcount = latest_data["current_headcount"].sum()
gross_pay = filtered["gross_pay"].sum()
net_pay = filtered["net_pay"].sum()

attendance_records = filtered["attendance_records"].sum()
present_records = filtered["present_records"].sum()

attendance_rate = (
    present_records / attendance_records * 100
    if attendance_records > 0 else None
)

st.subheader("Executive Summary")
st.caption(f"Latest observed reporting period: {latest_month}")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Headcount", f"{headcount:,.0f}")
c2.metric("Gross Payroll", f"INR {gross_pay:,.0f}")
c3.metric("Net Payroll", f"INR {net_pay:,.0f}")
c4.metric(
    "Attendance Rate",
    f"{attendance_rate:.1f}%" if attendance_rate is not None else "N/A"
)

st.divider()

st.subheader("Department-wise Headcount")

dept_data = latest_data.groupby(
    "department_name", as_index=False
)["current_headcount"].sum()

fig = px.bar(
    dept_data,
    x="department_name",
    y="current_headcount",
    title="Headcount by Department",
    labels={
        "department_name": "Department",
        "current_headcount": "Headcount"
    }
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly Payroll Trend")

payroll_trend = filtered.groupby(
    "month_label", as_index=False
)[["gross_pay", "net_pay"]].sum()

payroll_trend = payroll_trend.sort_values("month_label")

fig2 = px.line(
    payroll_trend,
    x="month_label",
    y=["gross_pay", "net_pay"],
    markers=True,
    title="Monthly Gross and Net Payroll",
    labels={
        "month_label": "Month",
        "value": "Payroll (INR)",
        "variable": "Payroll Type"
    }
)

st.plotly_chart(fig2, use_container_width=True)

st.subheader("Department Data")

st.dataframe(
    latest_data[
        [
            "department_name",
            "current_headcount",
            "gross_pay",
            "net_pay",
            "present_records",
            "attendance_records"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Source: Department-level aggregated internship dataset. "
    "Figures represent available source records, not live HR data."
)



