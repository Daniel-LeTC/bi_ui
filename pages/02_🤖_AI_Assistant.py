import streamlit as st
import polars as pl
import os
import time
from datetime import datetime

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.title("🤖 AI Data Assistant (Buffer Layer)")
st.caption("Mô phỏng lớp đệm AI: Tiếp nhận Query -> Phân tích Intent -> Truy xuất dữ liệu.")

# Path config
DATA_PATH = "../scrape_tool/exports/Master_PPC_Data.parquet"
SNAPSHOT_DIR = "../scrape_tool/exports/snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("⚙️ AI Simulation Control")
    st.info("Vì chưa có API, các tùy chọn này giúp mô phỏng quyết định của AI.")
    
    force_context = st.checkbox("🔒 Khóa Context (Force Follow-up)", value=False, 
                                help="Nếu bật, AI sẽ luôn query trên kết quả tìm kiếm trước đó thay vì Master Data.")
    
    st.divider()
    if st.button("🗑️ Clear History"):
        st.session_state.messages = [{"role": "assistant", "content": "Tech Lead đây. Data đã sẵn sàng."}]
        st.session_state.last_active_df = None
        st.rerun()

# --- DATA LOADER ---
@st.cache_data
def load_data():
    if os.path.exists(DATA_PATH):
        try:
            return pl.read_parquet(DATA_PATH)
        except:
            return None
    return None

master_df = load_data()

# --- STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_active_df" not in st.session_state:
    st.session_state.last_active_df = None

# --- AI ROUTER LOGIC (MOCK) ---
def simulate_ai_router(prompt, has_history):
    """
    Giả lập logic của AI để xác định Intent (Mục đích) của user.
    Output: (is_followup, reason)
    """
    # 1. Manual Override từ Sidebar
    if force_context:
        if has_history:
            return True, "User ép buộc dùng Context cũ (Sidebar setting)."
        else:
            return False, "User ép context nhưng chưa có lịch sử -> Buộc dùng Master Data."

    # 2. Mock Logic (Sẽ thay bằng LLM API Call sau này)
    # Prompt cho LLM thực tế sẽ là:
    # "User hỏi: '{prompt}'. Lịch sử trước đó có data không? Nếu có, câu này là lọc tiếp hay hỏi mới? Trả về JSON."
    
    prompt_lower = prompt.lower()
    keywords_followup = ["trong đó", "lọc ra", "sắp xếp", "sort", "filter", "lấy", "còn lại"]
    
    # Logic tạm thời (vẫn dùng keyword nhưng minh bạch hóa output)
    if has_history and any(w in prompt_lower for w in keywords_followup):
        return True, f"AI phát hiện từ khóa nối tiếp: {[w for w in keywords_followup if w in prompt_lower]}"
    
    return False, "AI nhận định đây là câu hỏi mới (New Topic)."

# --- UI RENDER HISTORY ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message:
            df_display = message["data"]
            st.dataframe(df_display, height=200)
            
            # Action Buttons
            c1, c2 = st.columns([1, 4])
            with c1:
                csv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Tải CSV", csv, f"result_{idx}.csv", "text/csv", key=f"dl_{idx}")
            with c2:
                if st.button("💾 Snapshot PBI", key=f"snap_{idx}"):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = os.path.join(SNAPSHOT_DIR, f"snapshot_{ts}.parquet")
                    pl.from_pandas(df_display).write_parquet(path)
                    st.toast(f"✅ Saved: {path}")

# --- CHAT INPUT ---
if prompt := st.chat_input("Hỏi gì đi bro..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        status_placeholder = st.empty() # Chỗ hiển thị suy nghĩ của AI
        
        msg_placeholder.markdown("⏳ *AI đang phân tích Intent...*")
        time.sleep(0.5)

        # 1. Router Phase
        has_history = st.session_state.last_active_df is not None
        is_followup, reason = simulate_ai_router(prompt, has_history)
        
        # Hiển thị suy nghĩ (Transparency)
        status_placeholder.info(f"🧠 **Thinking:** {reason}")
        
        # 2. Data Selection Phase
        if is_followup:
            source_df = pl.from_pandas(st.session_state.last_active_df)
            source_name = "Context (Kết quả trước)"
        else:
            source_df = master_df
            source_name = "Master Data (Gốc)"

        # 3. Execution Phase (Mock Query)
        response_text = ""
        response_df = None
        
        if source_df is not None:
            try:
                prompt_lower = prompt.lower()
                # Mock Query Logic
                if "doanh thu" in prompt_lower or "revenue" in prompt_lower:
                    if "Revenue (Actual)" in source_df.columns:
                        response_df = source_df.sort("Revenue (Actual)", descending=True).head(10).to_pandas()
                        response_text = f"Top 10 Doanh thu từ **{source_name}**:"
                    else:
                        response_text = "Dữ liệu hiện tại không có cột Revenue."
                        
                elif "đốt tiền" in prompt_lower or "bleeding" in prompt_lower:
                    response_df = source_df.filter(
                        (pl.col("Unit sold (Actual)") == 0) & 
                        (pl.col("Ads Spend (Actual)") > 30)
                    ).to_pandas()
                    response_text = f"Danh sách Bleeding từ **{source_name}**:"
                
                elif "lọc" in prompt_lower: # Mock filter
                     response_df = source_df.head(5).to_pandas()
                     response_text = f"Đã lọc mẫu 5 dòng từ **{source_name}** (Mock Filter):"

                else:
                    response_text = "Chưa hiểu câu lệnh (Mock API). Thử: 'Top doanh thu', 'Đốt tiền'."
            except Exception as e:
                response_text = f"Lỗi thực thi: {e}"
        else:
            response_text = "Chưa có dữ liệu gốc."

        # 4. Final Render
        msg_placeholder.markdown(response_text)
        if response_df is not None:
            st.dataframe(response_df, height=200)
            st.session_state.last_active_df = response_df
        
        # Save history
        msg_obj = {"role": "assistant", "content": response_text}
        if response_df is not None:
            msg_obj["data"] = response_df
        st.session_state.messages.append(msg_obj)
        
        # Rerun to show buttons
        st.rerun()