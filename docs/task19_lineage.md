# Task 19 – Metrics API and Data Lineage

## 1. Overview

PulseIQ Metrics API exposes five key workforce metrics through FastAPI.

Each metric includes:
- Metric value
- Definition
- Source table
- Last refresh timestamp
- Freshness status
- Data lineage

## 2. Metrics List

| Metric | Source | Value |
|---|---|---:|
| Headcount | dim_employee | 100 |
| Salary Total | salaries | 4530000 |
| Present Records | attendance | 70 |
| Approved Leaves | leave | 50 |
| Net Payroll Total | payroll | 4260000 |

## 3. Data Lineage Diagram

### Headcount

```mermaid
flowchart LR
    A[employees.csv] --> B[load_to_duckdb.py]
    B --> C[raw_employees]
    C --> D[etl.py + data_contracts.json]
    D --> E[employees]
    E --> F[build_warehouse.py]
    F --> G[dim_employee]
    G --> H[metric_headcount]
    H --> I[Streamlit Dashboard]