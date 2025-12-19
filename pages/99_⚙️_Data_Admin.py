import streamlit as st
import sys
import os
import subprocess
from datetime import datetime, timedelta

# Add parent dir to sys.path to allow importing from scrape_tool if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scrape_tool')))

try:
    from app.auth import check_password
except ImportError:
    # Handle running from different context
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from app.auth import check_password

st.set_page_config(page_title="Data Admin", page_icon="⚙️")

st.title("⚙️ Quản trị Dữ liệu (Data Admin)")

if not check_password():
    st.stop()

st.success("🔓 Đã xác thực quyền Admin.")

st.subheader("🛠️ Công cụ Cào dữ liệu (Scraper)")

with st.form("scrape_form"):
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Ngày bắt đầu", value=datetime.today() - timedelta(days=7))
    with c2:
        end_date = st.date_input("Ngày kết thúc", value=datetime.today())
        
    step = st.selectbox("Chế độ gộp (Granularity)", ["day", "month", "total"])
    dry_run = st.checkbox("Chạy thử (Dry Run) - Không lấy data thật")
    
    submitted = st.form_submit_button("🚀 Kích hoạt Scraper")

if submitted:
    st.info(f"Đang gửi lệnh cào từ {start_date} đến {end_date} (Mode: {step})...")
    
    # Construct command
    cmd = [
        "uv", "run", "main.py",
        "--start", str(start_date),
        "--end", str(end_date),
        "--step", step
    ]
    
    if dry_run:
        cmd.append("--dry-run")
        
    # Execute
    placeholder = st.empty()
    logs = ""
    
    try:
        # Run subprocess from the scrape_tool directory
        process = subprocess.Popen(
            cmd,
            cwd="../scrape_tool",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream logs
        with placeholder.container():
            st.write("⏳ Đang xử lý...")
            log_box = st.empty()
            
            for line in process.stdout:
                logs += line
                log_box.code(logs, language="bash")
                
        process.wait()
        
        if process.returncode == 0:
            st.success("✅ Hoàn thành nhiệm vụ!")
        else:
            st.error("❌ Có lỗi xảy ra. Vui lòng kiểm tra log.")
            
    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
