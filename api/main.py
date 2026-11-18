from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PulseIQ Metrics API",
    description="Public API for approved aggregate workforce metrics and data lineage.",
    version="1.0.0",
)

# This deployment package deliberately contains aggregate figures only.
# Do not add raw employee, salary, attendance, leave, payroll, or attrition records.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your Streamlit app domain after deployment if desired.
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

LAST_REFRESH = "2026-11-18T20:00:28+05:30"
ETL_STATUS = "SUCCESS"
ROWS_IN = 500
ROWS_PASSED = 485
ROWS_QUARANTINED = 15

METRICS = {
    "headcount": {
        "metric_id": "headcount",
        "name": "Headcount",
        "value": 100,
        "unit": "employees",
        "definition": "Count of distinct current employees.",
        "source": "dim_employee",
        "lineage": [
            "employees.csv",
            "load_to_duckdb.py",
            "raw_employees",
            "etl.py + data_contracts.json",
            "employees",
            "build_warehouse.py",
            "dim_employee",
            "metric_headcount",
            "Streamlit Dashboard",
        ],
    },
    "salary_total": {
        "metric_id": "salary_total",
        "name": "Salary Total",
        "value": 4530000.0,
        "unit": "currency units",
        "definition": "Sum of salaries.salary_amount.",
        "source": "salaries.salary_amount",
        "lineage": [
            "salaries.csv", "load_to_duckdb.py", "raw_salaries",
            "etl.py + data_contracts.json", "salaries",
            "metric_salary_total", "Streamlit Dashboard",
        ],
    },
    "present_records": {
        "metric_id": "present_records",
        "name": "Present Records",
        "value": 70,
        "unit": "records",
        "definition": "Count of attendance rows where status is Present.",
        "source": "attendance.status",
        "lineage": [
            "attendance.csv", "load_to_duckdb.py", "raw_attendance",
            "etl.py + data_contracts.json", "attendance",
            "metric_present_records", "Streamlit Dashboard",
        ],
    },
    "approved_leaves": {
        "metric_id": "approved_leaves",
        "name": "Approved Leaves",
        "value": 50,
        "unit": "records",
        "definition": "Count of leave rows where status is Approved.",
        "source": "leave.status",
        "lineage": [
            "leave.csv", "load_to_duckdb.py", "raw_leave",
            "etl.py + data_contracts.json", "leave",
            "metric_approved_leaves", "Streamlit Dashboard",
        ],
    },
    "payroll_net_total": {
        "metric_id": "payroll_net_total",
        "name": "Net Payroll Total",
        "value": 4260000.0,
        "unit": "currency units",
        "definition": "Sum of payroll.net_pay.",
        "source": "payroll.net_pay",
        "lineage": [
            "payroll.csv", "load_to_duckdb.py", "raw_payroll",
            "etl.py + data_contracts.json", "payroll",
            "metric_payroll_net_total", "Streamlit Dashboard",
        ],
    },
}

def freshness_status():
    try:
        refreshed = datetime.fromisoformat(LAST_REFRESH)
        now = datetime.now(refreshed.tzinfo) if refreshed.tzinfo else datetime.now()
        age_hours = (now - refreshed).total_seconds() / 3600
        return "fresh" if 0 <= age_hours <= 24 else "stale"
    except (TypeError, ValueError):
        return "unknown"

def metric_response(metric):
    return {
        **metric,
        "last_refresh": LAST_REFRESH,
        "freshness_status": freshness_status(),
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "PulseIQ Metrics API"}

@app.get("/metrics")
def all_metrics():
    return {
        "metrics": [metric_response(item) for item in METRICS.values()],
        "count": len(METRICS),
    }

@app.get("/metrics/{metric_id}")
def one_metric(metric_id: str):
    metric = METRICS.get(metric_id)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Unknown metric_id: {metric_id}")
    return metric_response(metric)

@app.get("/lineage/{metric_id}")
def one_lineage(metric_id: str):
    metric = METRICS.get(metric_id)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Unknown metric_id: {metric_id}")
    return {
        "metric_id": metric_id,
        "metric_name": metric["name"],
        "source": metric["source"],
        "lineage": metric["lineage"],
        "note": (
            "Headcount reads from dim_employee. The other four metric views read "
            "their cleaned staging tables directly; warehouse fact tables are "
            "separate downstream outputs, not sources for these metric views."
        ),
    }

@app.get("/freshness")
def freshness():
    return {
        "last_refresh": LAST_REFRESH,
        "etl_status": ETL_STATUS,
        "total_rows_in": ROWS_IN,
        "total_rows_passed": ROWS_PASSED,
        "total_rows_quarantined": ROWS_QUARANTINED,
        "freshness_status": freshness_status(),
        "note": "Aggregate ETL run metadata snapshot; refresh values when a new ETL run is approved.",
    }
