import streamlit as st
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import sqlglot

# Load Environment Variables explicitly
load_dotenv()

# --- PAGE CONFIG ---
st.set_page_config(page_title="PPC AI Analyst", page_icon="🤖", layout="wide")

# --- CUSTOM PPC TOOL THEME (ULTIMATE CONTRAST FIX) ---
st.markdown("""
<style>
    /* 1. Global Font */
    html, body, [class*="css"] {
        font-family: ui-sans-serif, system-ui, sans-serif !important;
    }

    /* 2. Color Palette */
    :root {
        --sidebar-bg: #1e293b; 
        --sidebar-text: #f1f5f9; 
        --primary-blue: #4361ee; 
        --bg-main: #f8fafc; 
        --border-color: #e2e8f0;
        --sidebar-widget-bg: #0f172a; 
    }

    /* 3. Main Content Area */
    .stApp {
        background-color: var(--bg-main);
    }

    /* 4. SIDEBAR - NUCLEAR OPTION */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: var(--sidebar-text) !important;
    }

    /* Navigation Links */
    section[data-testid="stSidebarNav"] a,
    section[data-testid="stSidebarNav"] span {
        color: var(--sidebar-text) !important;
    }

    /* Expander FIX */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: var(--sidebar-widget-bg) !important;
        border: 1px solid #475569 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details {
        background-color: var(--sidebar-widget-bg) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background-color: var(--sidebar-widget-bg) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background-color: #1e293b !important;
    }

    /* Widgets (Selectbox, Input) */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important; 
        color: white !important;
        border: 1px solid #475569 !important;
    }

    /* Sidebar Button */
    section[data-testid="stSidebar"] .stButton button {
        background-color: var(--primary-blue) !important;
        color: white !important;
        border: none !important;
    }

    /* 6. Chat Bubbles - Reset to Dark Text */
    .stChatMessage {
        border: 1px solid var(--border-color);
        border-radius: 12px;
        background-color: white;
        margin-bottom: 1rem;
    }
    .stChatMessage * {
        color: #1e293b !important;
    }
    
    /* Status Widget */
    [data-testid="stStatusWidget"] {
        background-color: #ffffff;
    }
    [data-testid="stStatusWidget"] * {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# Import core modules
from core.context import get_user_context
from core.engine import DataEngine
from core.ai import AIEngine
from core.agent import PerformanceAgent

# --- MOCK ENGINE FOR DEMO ---
class MockAIEngine:
    """Fake AI for Demo/Testing when API Quota is exhausted"""
    def generate_sql(self, question, schema, history=None):
        q = question.lower()
        sql = None
        explanation = "DEMO MODE: Generating mock SQL based on keywords."
        
        if "doanh thu" in q or "revenue" in q:
            if "niche" in q or "brand" in q:
                sql = 'SELECT "Main niche", SUM(Revenue) as Total_Rev FROM secure_sales GROUP BY "Main niche" ORDER BY Total_Rev DESC LIMIT 5'
                explanation = "Calculated Total Revenue per Niche (Top 5)."
            else:
                sql = 'SELECT SUM(Revenue) as Total_Revenue FROM secure_sales'
                explanation = "Calculated Total Overall Revenue."
                
        elif "bleeding" in q or "đốt tiền" in q:
            sql = 'SELECT "Main niche", "Product Name", "Ads Spend", "Unit Sold" FROM secure_sales WHERE "Ads Spend" > 0 AND "Unit Sold" = 0 ORDER BY "Ads Spend" DESC LIMIT 10'
            explanation = "Identified bleeding products (Spend > 0, Sales = 0)."
            
        elif "hiệu quả" in q or "performance" in q:
            sql = 'SELECT "Main niche", SUM(Revenue) as Rev, SUM("Ads Spend") as Spend, (SUM("Ads Spend")/SUM(Revenue)) as ACOS FROM secure_sales GROUP BY "Main niche" HAVING SUM(Revenue) > 0 ORDER BY ACOS ASC LIMIT 5'
            explanation = "Analyzed Best Performing Niches by ACOS."
            
        else:
            sql = 'SELECT * FROM secure_sales LIMIT 5'
            explanation = "DEMO: Returned sample data (Unrecognized intent)."
            
        return {"sql": sql, "explanation": explanation}

# --- CORE INITIALIZATION ---
@st.cache_resource
def init_agent(api_key, data_path, use_mock=False):
    data_engine = DataEngine(data_path, brand_col="Main niche")
    if use_mock:
        ai_engine = MockAIEngine()
    else:
        ai_engine = AIEngine(api_key)
    return PerformanceAgent(data_engine, ai_engine)

@st.cache_data
def get_all_niches(_agent):
    return _agent.data_engine.get_all_brands()

# --- HELPER: EXPORT BUTTONS ---
SNAPSHOT_DIR = os.path.abspath("../scrape_tool/exports/snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def render_export_buttons(df, key_suffix):
    c1, c2 = st.columns([1, 1])
    with c1:
        try:
            csv_data = df.to_csv(index=False).encode('utf-8')
        except AttributeError:
            csv_data = df.to_pandas().to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv_data, f"export_{key_suffix}.csv", "text/csv", key=f"btn_csv_{key_suffix}", use_container_width=True)
    with c2:
        if st.button("📸 Save PBI Snapshot", key=f"btn_pbi_{key_suffix}", use_container_width=True):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{ts}_{key_suffix[:5]}.parquet"
            filepath = os.path.join(SNAPSHOT_DIR, filename)
            try:
                df.write_parquet(filepath)
            except AttributeError:
                df.to_pandas().to_parquet(filepath)
            st.toast(f"✅ Saved Snapshot: {filename}", icon="💾")

# --- SETUP ENV & PATHS ---
api_key = os.getenv("GEMINI_API_KEY")
DATA_PATH = os.path.abspath("../scrape_tool/exports/Big_Master_PPC_Data.parquet")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.abspath("../scrape_tool/exports/Master_PPC_Data.parquet")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("Settings")
    use_mock = st.toggle("🛠️ Demo / Mock Mode", value=False)
    with st.expander("👤 User Identity", expanded=True):
        token_option = st.selectbox("Access Role:", ["admin_secret", "group_ab", "group_bc", "group_ac"], format_func=lambda x: {"admin_secret": "👑 Full Admin", "group_ab": "🛒 Sales (Niche A-B)", "group_bc": "🛒 Sales (Niche B-C)", "group_ac": "🛒 Sales (Niche A-C)"}.get(x, x))
    if st.button("New Chat Session"):
        st.session_state.messages = [{"role": "assistant", "content": "Xin chào, tôi là trợ lý phân tích dữ liệu. Bạn muốn tìm hiểu thông tin gì hôm nay?"}]
        st.rerun()
    st.divider()
    st.caption(f"📁 Source: {os.path.basename(DATA_PATH)}")

# Init User Context
agent = init_agent(api_key, DATA_PATH, use_mock=use_mock)
all_niches = get_all_niches(agent)
user_ctx = get_user_context(token_option, all_niches)

# --- MAIN HEADER ---
st.title("🤖 AI Data Assistant")
st.markdown("Truy vấn hiệu suất quảng cáo bằng ngôn ngữ tự nhiên.")
st.divider()

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Xin chào, tôi là trợ lý phân tích dữ liệu. Bạn muốn tìm hiểu thông tin gì hôm nay?"}]

# --- CHAT INTERFACE ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display Data & Export Buttons
        if "data" in msg and msg["data"] is not None:
            df = msg["data"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            render_export_buttons(df, f"hist_{i}")
            
        # Display SQL & Metrics (THE FEATURE YOU ASKED)
        if "sql" in msg and msg["sql"]:
            metrics_info = ""
            if "metrics" in msg and msg["metrics"]:
                m = msg["metrics"]
                metrics_info = f" | ⏱️ AI: {m.get('ai_thinking', 0):.2f}s | ⚡ DB: {m.get('db_execution', 0):.3f}s"
            
            with st.expander(f"Technical Details (SQL){metrics_info}"):
                try:
                    formatted_sql = sqlglot.transpile(msg["sql"], read="duckdb", pretty=True)[0]
                except:
                    formatted_sql = msg["sql"]
                st.code(formatted_sql, language="sql")

# --- USER INPUT ---
if prompt := st.chat_input("Nhập câu hỏi..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.status("Đang xử lý yêu cầu...", expanded=True) as status:
            st.write("🧠 Đang phân tích ý định (AI Thinking)...")
            response = agent.process_request(prompt, user_ctx, st.session_state.messages)
            
            metrics = response.get("metrics", {})
            ai_time = metrics.get("ai_thinking", 0)
            db_time = metrics.get("db_execution", 0)
            
            st.write(f"⚡ Đang truy vấn dữ liệu (DuckDB)...")
            
            if response["status"] == "success":
                status.update(label=f"Hoàn tất (AI: {ai_time:.2f}s, DB: {db_time:.3f}s)", state="complete", expanded=False)
                st.markdown(response["message"])
                df = response["data"]
                st.dataframe(df, use_container_width=True, hide_index=True)
                render_export_buttons(df, f"new_{int(datetime.now().timestamp())}")
                
                # Show SQL Expander in new message
                with st.expander(f"Technical Details (SQL) | ⏱️ AI: {ai_time:.2f}s | ⚡ DB: {db_time:.3f}s"):
                    try:
                        formatted_sql = sqlglot.transpile(response["sql"], read="duckdb", pretty=True)[0]
                    except:
                        formatted_sql = response["sql"]
                    st.code(formatted_sql, language="sql")
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response["message"],
                    "data": df,
                    "sql": response["sql"],
                    "metrics": metrics
                })
                
            elif response["status"] == "chat":
                status.update(label=f"Phản hồi (AI: {ai_time:.2f}s)", state="complete", expanded=False)
                st.markdown(response["message"])
                st.session_state.messages.append({"role": "assistant", "content": response["message"], "metrics": metrics})
                
            elif response["status"] == "sql_error":
                status.update(label="Lỗi truy vấn", state="error", expanded=True)
                st.error("Không thể thực hiện truy vấn.")
                if "sql" in response:
                    st.code(response["sql"], language="sql")
                st.session_state.messages.append({"role": "assistant", "content": "Truy vấn thất bại."})
            else:
                status.update(label="Lỗi hệ thống", state="error")
                st.error(f"Error: {response['message']}")
