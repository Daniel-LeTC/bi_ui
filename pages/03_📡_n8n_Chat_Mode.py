import streamlit as st
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import sqlglot

load_dotenv()

# --- PAGE CONFIG ---
st.set_page_config(page_title="n8n Integration", page_icon="🔗", layout="wide")

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
    
    /* Ép tất cả chữ trong sidebar thành màu trắng */
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

st.title("n8n Connected Assistant")
st.caption("Workflow Orchestration Interface.")
st.divider()

# --- CONFIG ---
DEFAULT_WEBHOOK = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/query-agent")

# --- SESSION STATE ---
if "n8n_messages" not in st.session_state:
    st.session_state.n8n_messages = [
        {"role": "assistant", "content": "Kết nối n8n đã sẵn sàng."}
    ]

# --- SIDEBAR ---
with st.sidebar:
    st.header("Connection")
    
    webhook_url = st.text_input("Webhook URL", value=DEFAULT_WEBHOOK)
    
    with st.expander("🔐 Authentication Simulation", expanded=True):
        token_option = st.selectbox(
            "User Identity:",
            ["admin_secret", "group_ab", "group_bc", "group_ac"],
            format_func=lambda x: f"Role: {x}"
        )
    
    st.divider()
    
    if st.button("Clear History"):
        st.session_state.n8n_messages = []
        st.rerun()

# --- CHAT INTERFACE ---
for msg in st.session_state.n8n_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display Data
        if "data" in msg and msg["data"] is not None:
            df = msg["data"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"n8n_export_{datetime.now().strftime('%H%M%S')}.csv",
                mime='text/csv',
                key=f"dl_{datetime.now().timestamp()}"
            )

        # Display SQL
        if "sql" in msg and msg["sql"]:
            with st.expander("Technical Details"):
                try:
                    fmt_sql = sqlglot.transpile(msg["sql"], read="duckdb", pretty=True)[0]
                except:
                    fmt_sql = msg["sql"]
                st.code(fmt_sql, language="sql")

# --- USER INPUT ---
if prompt := st.chat_input("Gửi yêu cầu..."):
    # Render User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.n8n_messages.append({"role": "user", "content": prompt})
    
    # Call n8n Webhook
    with st.chat_message("assistant"):
        with st.status("📡 Gửi yêu cầu sang n8n...", expanded=True) as status:
            try:
                # Prepare Payload
                clean_history = []
                for msg in st.session_state.n8n_messages[-6:]:
                    clean_msg = {"role": msg["role"], "content": msg["content"]}
                    clean_history.append(clean_msg)

                payload = {
                    "question": prompt,
                    "token": token_option,
                    "history": clean_history
                }
                
                status.write("Waiting for Workflow response...")
                
                # CALL WEBHOOK
                response = requests.post(webhook_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    status.update(label="Thành công", state="complete", expanded=False)
                    
                    try:
                        res_json = response.json()
                    except json.JSONDecodeError:
                        st.error("Invalid JSON response.")
                        st.stop()
                    
                    message_text = res_json.get("message", "No message.")
                    sql_text = res_json.get("sql")
                    raw_data = res_json.get("data")
                    
                    st.markdown(message_text)
                    
                    display_data = None
                    if raw_data:
                        display_data = pd.DataFrame(raw_data)
                        st.dataframe(display_data, use_container_width=True, hide_index=True)
                        st.download_button("Download CSV", display_data.to_csv(index=False).encode('utf-8'), "n8n_data.csv", "text/csv")
                        
                    if sql_text:
                        with st.expander("Technical Details"):
                            try:
                                fmt_sql = sqlglot.transpile(sql_text, read="duckdb", pretty=True)[0]
                            except:
                                fmt_sql = sql_text
                            st.code(fmt_sql, language="sql")
                    
                    # Save History
                    st.session_state.n8n_messages.append({
                        "role": "assistant",
                        "content": message_text,
                        "data": display_data,
                        "sql": sql_text
                    })
                    
                else:
                    status.update(label="Lỗi kết nối", state="error")
                    st.error(f"n8n trả về lỗi ({response.status_code}): {response.text}")
                    
            except Exception as e:
                status.update(label="Lỗi hệ thống", state="error")
                st.error(f"Không thể kết nối n8n: {str(e)}")