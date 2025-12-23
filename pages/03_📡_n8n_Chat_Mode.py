import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv
import pandas as pd
import sqlglot

load_dotenv()

st.set_page_config(page_title="n8n AI Chat", page_icon="📡", layout="wide")

st.title("📡 n8n Connected AI Assistant")
st.caption("UI Interface -> n8n Orchestrator -> AI Core")

# --- CONFIG ---
# Webhook URL từ n8n (Production Flow)
DEFAULT_WEBHOOK = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/query-agent")

# --- SESSION STATE ---
if "n8n_messages" not in st.session_state:
    st.session_state.n8n_messages = [
        {"role": "assistant", "content": "Kết nối n8n đã sẵn sàng. Flow này chạy qua Workflow Orchestrator."}
    ]

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔌 Connection Settings")
    webhook_url = st.text_input("n8n Webhook URL", value=DEFAULT_WEBHOOK)
    
    st.divider()
    
    # Mock Auth for testing
    token_option = st.selectbox(
        "Simulate User Token:",
        ["admin_secret", "group_ab", "group_bc", "group_ac"],
        format_func=lambda x: f"User: {x}"
    )
    
    if st.button("🗑️ Clear History"):
        st.session_state.n8n_messages = []
        st.rerun()

# --- CSS HACK ---
st.markdown("""
<style>
    code {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CHAT INTERFACE ---
for msg in st.session_state.n8n_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(msg["data"], use_container_width=True)
        if "sql" in msg and msg["sql"]:
            with st.expander("🔍 View SQL (Processed by Core)"):
                try:
                    fmt_sql = sqlglot.transpile(msg["sql"], read="duckdb", pretty=True)[0]
                except:
                    fmt_sql = msg["sql"]
                st.code(fmt_sql, language="sql")

if prompt := st.chat_input("Gửi request sang n8n..."):
    # 1. Render User Input
    st.chat_message("user").markdown(prompt)
    st.session_state.n8n_messages.append({"role": "user", "content": prompt})
    
    # 2. Call n8n Webhook
    with st.chat_message("assistant"):
        with st.spinner("📡 Sending to n8n Workflow..."):
            try:
                # CLEAN HISTORY: Remove DataFrame objects which are not JSON serializable
                clean_history = []
                for msg in st.session_state.n8n_messages[-6:]:
                    clean_msg = {"role": msg["role"], "content": msg["content"]}
                    clean_history.append(clean_msg)

                payload = {
                    "question": prompt,
                    "token": token_option,
                    "history": clean_history
                }
                
                # CALL WEBHOOK
                response = requests.post(webhook_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                    except json.JSONDecodeError:
                        st.error(f"❌ n8n returned invalid JSON. Raw output:\n{response.text}")
                        st.session_state.n8n_messages.append({"role": "assistant", "content": f"n8n Response Error: {response.text}"})
                        st.stop()
                    
                    # Expect structure from n8n: { "message": "...", "sql": "...", "data": [...] }
                    message_text = res_json.get("message", "No message returned.")
                    sql_text = res_json.get("sql")
                    raw_data = res_json.get("data")
                    
                    st.markdown(message_text)
                    
                    display_data = None
                    if raw_data:
                        display_data = pd.DataFrame(raw_data)
                        st.dataframe(display_data, use_container_width=True)
                        
                    if sql_text:
                        with st.expander("🔍 View SQL"):
                            try:
                                fmt_sql = sqlglot.transpile(sql_text, read="duckdb", pretty=True)[0]
                            except:
                                fmt_sql = sql_text
                            st.code(fmt_sql, language="sql")
                    
                    # Save to history
                    st.session_state.n8n_messages.append({
                        "role": "assistant",
                        "content": message_text,
                        "data": display_data,
                        "sql": sql_text
                    })
                    
                else:
                    err_msg = f"❌ n8n Error ({response.status_code}): {response.text}"
                    st.error(err_msg)
                    st.session_state.n8n_messages.append({"role": "assistant", "content": err_msg})
                    
            except Exception as e:
                err_msg = f"❌ Connection Failed: {str(e)}"
                st.error(err_msg)
                st.session_state.n8n_messages.append({"role": "assistant", "content": err_msg})
