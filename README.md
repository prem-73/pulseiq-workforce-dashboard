# PulseIQ Workforce Analytics

A Streamlit dashboard for workforce analytics.

## Features
- Executive KPI summary
- Department-wise headcount
- Monthly payroll trend
- Attendance rate
- Department and month filters

## Technology
- Python
- Streamlit
- Pandas
- Plotly

## Run locally
pip install -r requirements.txt
streamlit run app.py

## Data
Uses department-level aggregated internship data.

## Hosting Platform Comparison

| Platform | Free Option | Sleep Behaviour | Selected |
|---|---|---|---|
| Streamlit Community Cloud | Yes | Sleeps after 12 hours inactivity | Yes |
| Render | Yes | Sleeps after 15 minutes inactivity | No |
| Hugging Face Spaces | Limited free options | Depends on hardware and Space | No |

### Hosting Decision

Streamlit Community Cloud was selected because the application
is built with Streamlit and supports direct GitHub deployment.
It provides free public hosting and is suitable for this
lightweight workforce analytics dashboard.

### Deployment URL

https://pulseiq-workforce-dashboard.streamlit.app/

