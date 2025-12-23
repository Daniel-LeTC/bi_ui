import os
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Setup page config
st.set_page_config(
    page_title="PPC Analytics Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title (Generic & Clean)
st.title("🚀 PPC Analytics Hub")

# Quick Stats Overview
st.subheader("📌 System Status")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Last Sync", value="Today", delta="Ready")
with col2:
    st.metric(label="Active SKUs", value="--", delta="N/A")
with col3:
    st.metric(label="Ad Spend", value="--", delta="N/A")

st.markdown("---")
st.info("👈 Select **Dashboard** to view reports or **AI Assistant** to query data.")