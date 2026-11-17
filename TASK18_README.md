# PulseIQ Task 18 package

## Files
- `app.py`: Streamlit KPI explorer and role-specific views.
- `role_permissions.py`: server-side role checks and privacy suppression.
- `test_task18.py`: automated role/privacy tests.

## Install and run
From the deployment repository root:
```powershell
python -m pip install -r requirements.txt
python -m unittest -v test_task18.py
streamlit run app.py
```

Required deployment data:
- `data/department_month.csv`
- `data/dim_department.csv`
- `data/demo_users.csv`
- `data/metric_dictionary.csv`
- `data/task8/dim_team.csv`
- `data/task8/fact_task.csv`

## Demo roles
- `admin.demo`: all available aggregate metrics.
- `hr.demo`: department D01 only.
- `manager.demo`: Team A only, task metrics.
- `exec.demo`: company-level KPIs only.

These are demo identities, not authentication. HR=D01 and Manager=Team A are illustrative assignments and must be replaced with verified mappings for any real deployment.

## Privacy behavior
- Department-level people/payroll metrics use `headcount_end` as the population proxy in the monthly aggregate source.
- Attrition metrics have a minimum threshold of 10; other blank thresholds default to 5.
- Team task metrics use task-record counts and the metric dictionary's task threshold.
- Primary and complementary suppression are applied to department/team breakdowns. When suppression occurs, grand totals are not shown.
- No employee-level salary/risk rows or data downloads are exposed.
- The team dimension does not contain a department key, so team is a separate drill-down, not a verified child of department.

## Important limitations
- Demo role selection is not secure authentication.
- Admin sees all available aggregate data, not individual salary details; no individual salary rows are deployed.
- Metric coverage is limited to columns present in the supplied aggregate/team datasets. Metrics unavailable in those files are not fabricated.
- The monthly refresh workflow only refreshes from the committed monthly source CSV; it does not connect to a live HR system.
