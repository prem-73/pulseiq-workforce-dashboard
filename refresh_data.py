import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"

source = pd.read_csv(DATA / "monthly_source.csv")
departments = pd.read_csv(DATA / "dim_department.csv")

required = [
    "department_id", "month", "employer_cost", "gross_pay",
    "overtime_pay", "employees_paid", "overtime_hours",
    "late_arrivals", "attendance_rate", "headcount_end",
    "hires", "exits", "attrition_rate_monthly_pct",
    "tasks", "tasks_done", "story_points_done",
    "task_completion_rate_pct", "cost_per_head",
    "overtime_share_pct"
]

missing = [col for col in required if col not in source.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

result = source.merge(
    departments[["department_id", "department_name"]],
    on="department_id",
    how="left",
    validate="many_to_one"
)

if result["department_name"].isna().any():
    raise ValueError("Unknown department IDs found.")

result["month"] = pd.to_datetime(result["month"])
result["month_label"] = result["month"].dt.strftime("%Y-%m")
result["year"] = result["month"].dt.year
result["month_number"] = result["month"].dt.month

result = result.sort_values(["month", "department_name"])

result.to_csv(DATA / "department_month.csv", index=False)

latest_month = result["month"].max().strftime("%Y-%m")

(DATA / "refresh_status.txt").write_text(
    f"Latest reporting month: {latest_month}\n"
    f"Records: {len(result)}\n"
    f"Refresh completed successfully.\n",
    encoding="utf-8"
)

print("Refresh completed successfully.")
print("Records:", len(result))
print("Latest month:", latest_month)
print("Departments:", result["department_name"].nunique())
