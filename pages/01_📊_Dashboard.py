import streamlit as st
import polars as pl
import plotly.express as px
import os

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Hiệu suất Quảng cáo (PPC Performance)")

# Load Data (Mock path for now, will update to use config)
DATA_PATH = "../scrape_tool/exports/Master_PPC_Data.parquet"

@st.cache_data
def load_data():
    if os.path.exists(DATA_PATH):
        try:
            return pl.read_parquet(DATA_PATH)
        except Exception as e:
            st.error(f"Lỗi đọc file Parquet: {e}")
            return None
    return None

df = load_data()

if df is not None:
    st.write(f"Dữ liệu cập nhật lần cuối: {os.path.getmtime(DATA_PATH)}")
    
    # Filter Date
    dates = df["Report_Date"].unique().sort()
    
    # Top Metrics
    total_rev = df["Revenue (Actual)"].sum()
    total_spend = df["Ads Spend (Actual)"].sum()
    tacos = (total_spend / total_rev * 100) if total_rev else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Revenue", f"${total_rev:,.2f}")
    m2.metric("Total Ad Spend", f"${total_spend:,.2f}")
    m3.metric("TACOS", f"{tacos:.2f}%", delta_color="inverse")
    
    # Chart
    st.subheader("📈 Xu hướng doanh thu theo ngày")
    daily_trend = df.group_by("Report_Date").agg([
        pl.col("Revenue (Actual)").sum(),
        pl.col("Ads Spend (Actual)").sum()
    ]).sort("Report_Date")
    
    fig = px.line(daily_trend.to_pandas(), x="Report_Date", y=["Revenue (Actual)", "Ads Spend (Actual)"])
    st.plotly_chart(fig, use_container_width=True)
    
    # Data Table
    st.subheader("📋 Chi tiết dữ liệu")
    st.dataframe(df.to_pandas(), use_container_width=True)

else:
    st.warning("⚠️ Chưa có dữ liệu. Vui lòng sang trang 'Data Admin' để cào dữ liệu mới nhất.")
