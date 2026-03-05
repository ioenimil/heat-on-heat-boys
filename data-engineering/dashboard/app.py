import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.pages import (
    agent_performance,
    daily_volume,
    department_workload,
    home,
    sla_metrics,
)

st.set_page_config(
    page_title="ServiceHub Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("ServiceHub")
st.sidebar.caption("Analytics Workspace")
st.sidebar.markdown("---")
st.sidebar.caption("Internal ticketing analytics dashboard")

selected_page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "SLA Metrics",
        "Daily Volume",
        "Agent Performance",
        "Department Workload",
    ],
    key="main_navigation",
)

if selected_page == "Home":
    home.render()
elif selected_page == "SLA Metrics":
    sla_metrics.render()
elif selected_page == "Daily Volume":
    daily_volume.render()
elif selected_page == "Agent Performance":
    agent_performance.render()
else:
    department_workload.render()
