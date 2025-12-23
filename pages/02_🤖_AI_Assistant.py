import streamlit as st
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import sqlglot

# Load Environment Variables explicitly
load_dotenv()

# --- CSS HACK: WRAP SQL CODE ---
st.markdown("""
<style>
    code {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

# Import core modules
from core.context import get_user_context
from core.engine import DataEngine
from core.ai import AIEngine
from core.agent import PerformanceAgent

st.set_page_config(page_title="AI Data Assistant", page_icon="🤖", layout="wide")

# --- UI HEADER ---
st.title("🤖 AI Data Assistant")
st.caption("Natural Language Query Engine powered by Gemini 2.5 Flash & DuckDB")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Chào bro, tao là AI Analyst. Hỏi gì về data performance đi, tao check cho!"}
    ]

# --- CORE INITIALIZATION ---
@st.cache_resource
def init_agent(api_key, data_path):
    # Dùng cột "Main niche" làm cột phân quyền thay cho "Brand"
    data_engine = DataEngine(data_path, brand_col="Main niche")
    ai_engine = AIEngine(api_key)
    return PerformanceAgent(data_engine, ai_engine)

@st.cache_data
def get_all_niches(_agent):
    """Cache list niche để không query đi query lại"""
    return _agent.data_engine.get_all_brands()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Missing GEMINI_API_KEY in environment.")
    st.stop()

# DATA PATH: Switch to Big Data (1M rows)
DATA_PATH = os.path.abspath("../scrape_tool/exports/Big_Master_PPC_Data.parquet")
# Nếu file 1M chưa có (hoặc lỗi), fallback về file thường
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.abspath("../scrape_tool/exports/Master_PPC_Data.parquet")

agent = init_agent(api_key, DATA_PATH)
all_niches = get_all_niches(agent)

# --- SIDEBAR & CONFIG ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Mock Token selection - Updated Logic
    token_option = st.selectbox(
        "Select User Role (Mock):",
        ["admin_secret", "group_ab", "group_bc", "group_ac"],
        format_func=lambda x: {
            "admin_secret": "Admin (Full Access)",
            "group_ab": "Sales (Niche A-B)",
            "group_bc": "Sales (Niche B-C)",
            "group_ac": "Sales (Niche A-C)"
        }.get(x, x)
    )
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "History đã được dọn dẹp. Bắt đầu lại nào!"}
        ]
        st.rerun()
    
    st.divider()
    st.info(f"💡 System loaded with {len(all_niches)} niches from {os.path.basename(DATA_PATH)}.")

# Init User Context
user_ctx = get_user_context(token_option, all_niches)

# --- CHAT UI ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "data" in msg:
            st.dataframe(msg["data"], use_container_width=True)
        if "sql" in msg:
            with st.expander("🔍 View SQL"):
                try:
                    formatted_sql = sqlglot.transpile(msg["sql"], read="duckdb", pretty=True)[0]
                except:
                    formatted_sql = msg["sql"]
                st.code(formatted_sql, language="sql")

if prompt := st.chat_input("Nhập câu hỏi tại đây... (VD: Tổng doanh thu niche bắt đầu bằng A)"):
    # Render User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 AI đang suy nghĩ..."):
            # Gọi Agent xử lý
            response = agent.process_request(prompt, user_ctx, st.session_state.messages)
            
            # Xử lý các loại kết quả trả về từ Agent
            if response["status"] == "success":
                st.markdown(response["message"])
                df = response["data"]
                st.dataframe(df, use_container_width=True)
                
                with st.expander("🔍 View SQL"):
                    try:
                        formatted_sql = sqlglot.transpile(response["sql"], read="duckdb", pretty=True)[0]
                    except:
                        formatted_sql = response["sql"]
                    st.code(formatted_sql, language="sql")
                
                # Lưu vào history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response["message"],
                    "data": df,
                    "sql": response["sql"]
                })
                
            elif response["status"] == "chat":
                st.markdown(response["message"])
                st.session_state.messages.append({"role": "assistant", "content": response["message"]})
                
            elif response["status"] == "sql_error":
                st.error(response["message"])
                with st.expander("🔍 View Failed SQL"):
                    try:
                        formatted_sql = sqlglot.transpile(response["sql"], read="duckdb", pretty=True)[0]
                    except:
                        formatted_sql = response["sql"]
                    st.code(formatted_sql, language="sql")
                st.session_state.messages.append({"role": "assistant", "content": f"Lỗi SQL rồi bro: {response['message']}"})
                
            else:
                st.error(f"❌ Error: {response['message']}")