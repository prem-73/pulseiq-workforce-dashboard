# PulseIQ Task 19 - Public Metrics API

This is a deployable FastAPI service for the five approved aggregate metrics.
It intentionally contains aggregate values and ETL metadata only. Do not add
the local DuckDB database or raw row-level workforce data to this repository.

## Deploy with Render

1. Add the `api/` folder, `requirements.txt`, and `render.yaml` to the root of
   `prem-73/pulseiq-workforce-dashboard`.
2. Commit and push them to `main`.
3. In Render, choose **New + -> Blueprint**, connect the GitHub repository,
   and select the `render.yaml` blueprint.
4. Wait for the service to finish deploying. Render will provide a public URL.
5. Test `<PUBLIC_API_URL>/health`, `/metrics`, `/freshness`, `/docs`, and each
   `/lineage/{metric_id}` endpoint.
6. In Streamlit Community Cloud, open the app's settings/secrets and set:
   `PULSEIQ_API_URL = "https://YOUR-RENDER-SERVICE.onrender.com"`
   Save and reboot/redeploy the Streamlit app.

## Endpoints

- `GET /health`
- `GET /metrics`
- `GET /metrics/{metric_id}`
- `GET /lineage/{metric_id}`
- `GET /freshness`
- `GET /docs`

Metric IDs: `headcount`, `salary_total`, `present_records`,
`approved_leaves`, `payroll_net_total`.

## Important freshness limitation

This package uses the verified ETL snapshot timestamp
`2026-11-18T20:00:28+05:30` and counts (500 in, 485 passed, 15 quarantined).
The freshness status changes to `stale` after 24 hours. Update these constants
only after a new ETL run has completed and its aggregate counts are verified.
This is an aggregate snapshot API, not a live connection to the local DuckDB.

## Privacy

Never commit `pulseiq.duckdb`, raw CSVs, employee names/emails, salary rows,
payroll rows, or attrition-risk records. The API is intentionally aggregate-only.
