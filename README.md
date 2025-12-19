# 📊 Internal PPC Analytics App (Frontend)

Đây là phân hệ giao diện người dùng (UI) được xây dựng bằng **Streamlit**. Nó đóng vai trò là lớp hiển thị (Presentation Layer) và lớp điều khiển (Control Layer) cho toàn bộ hệ thống phân tích quảng cáo.

---

## 🏗️ Kiến trúc & Luồng dữ liệu (Architecture)

App hoạt động theo cơ chế **Stateless Frontend** nhưng có **Session State** để duy trì ngữ cảnh người dùng.

1.  **Data Source (Nguồn dữ liệu):**
    *   App **KHÔNG** có Database riêng.
    *   Nó đọc dữ liệu trực tiếp từ **Data Lake (Local Parquet)** do Backend (`scrape_tool`) tạo ra.
    *   *Path mặc định:* `../scrape_tool/exports/Master_PPC_Data.parquet`.

2.  **Interaction (Tương tác):**
    *   **Read:** Trang Dashboard và AI Assistant chỉ đọc file Parquet (Read-only).
    *   **Write/Action:** Trang Data Admin gọi ngược lại Backend thông qua `subprocess` (CLI Command) để kích hoạt quá trình cào dữ liệu mới.

---

## 🛠️ Cài đặt & Cấu hình (Installation)

Yêu cầu: Python 3.12+ và `uv`.

### 1. Khởi tạo môi trường
```bash
cd app
uv sync
```
*Lệnh này sẽ cài đặt: `streamlit`, `polars`, `plotly`, `pandas`, `pyarrow`.*

### 2. Cấu hình (Configuration)
App sử dụng các biến môi trường hoặc giá trị mặc định trong code:

*   **Mật khẩu Admin:** Được định nghĩa trong `app/auth.py`.
    *   Mặc định: `secret123` (hoặc set biến môi trường `ADMIN_PASS`).
*   **Đường dẫn dữ liệu:** Được định nghĩa đầu file trong các trang `pages/`.

### 3. Khởi chạy
```bash
uv run streamlit run main.py
```
Truy cập: `http://localhost:8501`

---

## 📖 Hướng dẫn chi tiết từng Module

### 1. Dashboard (`pages/01_📊_Dashboard.py`)
*   **Chức năng:** Hiển thị tổng quan sức khỏe tài khoản (Revenue, Ad Spend, TACOS).
*   **Logic:**
    *   Sử dụng `polars` để đọc file Parquet (Lazy load nếu file lớn).
    *   `st.cache_data`: Cache lại kết quả đọc để không phải load lại file mỗi khi user click chuột (Tăng tốc độ).
    *   Biểu đồ được vẽ bằng `plotly.express` cho tính tương tác cao.

### 2. AI Assistant (`pages/02_🤖_AI_Assistant.py`) - *Quan trọng*
Đây là lớp đệm logic (Buffer Layer) trước khi tích hợp API LLM thật.

*   **Logic "Context Aware" (Nhận thức ngữ cảnh):**
    *   Hệ thống sử dụng `st.session_state['last_active_df']` để lưu bảng dữ liệu của câu trả lời gần nhất.
    *   **Router Simulation:** Hàm `simulate_ai_router` sẽ phân tích câu hỏi của user:
        *   Nếu chứa từ khóa nối tiếp (*"lọc", "sắp xếp", "trong đó"*): Query trên `last_active_df`.
        *   Nếu là câu hỏi mới: Query lại từ Master Data gốc.
*   **Tính năng Export:**
    *   **Download CSV:** Cho phép user tải kết quả chat về máy.
    *   **Snapshot PBI:** Lưu dataframe hiện tại thành file Parquet vào folder `exports/snapshots/`. PowerBI sẽ trỏ vào folder này để lấy dữ liệu Ad-hoc.

### 3. Data Admin (`pages/99_⚙️_Data_Admin.py`)
*   **Gatekeeper:** Sử dụng `auth.check_password()` để chặn truy cập trái phép.
*   **Remote Trigger:**
    *   Thay vì import code Python trực tiếp (gây conflict thư viện), module này dùng `subprocess.Popen` để gọi lệnh CLI sang thư mục `scrape_tool`.
    *   **Real-time Log:** Sử dụng vòng lặp đọc `stdout` để hiển thị log chạy của Bot ngay trên màn hình Web giúp user biết tiến độ.

---

## 📂 Giải thích cấu trúc Code

```text
app/
├── main.py                 # Trang chủ (Landing Page) - Điều hướng chính.
├── auth.py                 # Module xác thực Admin (Password check).
├── pyproject.toml          # Quản lý dependencies riêng của App UI.
└── pages/                  # Streamlit tự động nhận diện file trong này làm menu.
    ├── 01_📊_Dashboard.py  # Code hiển thị báo cáo.
    ├── 02_🤖_AI_Assistant.py # Code Chatbot & Logic Router.
    └── 99_⚙️_Data_Admin.py # Code Admin & Subprocess Call.
```

## ⚠️ Troubleshooting (Xử lý sự cố thường gặp)

1.  **Lỗi "File not found" / "Chưa có dữ liệu":**
    *   *Nguyên nhân:* Chưa chạy Scraper lần nào nên chưa có file `Master_PPC_Data.parquet`.
    *   *Khắc phục:* Vào trang **Data Admin** -> Chạy cào dữ liệu một lần (có thể dùng chế độ Dry-run hoặc cào 1 ngày ngắn).

2.  **Lỗi "Module not found" khi chạy Admin:**
    *   *Nguyên nhân:* App không tìm thấy đường dẫn sang `scrape_tool`.
    *   *Khắc phục:* Kiểm tra đoạn code `sys.path.append` trong `99_Data_Admin.py`. Nó phải trỏ đúng về thư mục cha.

3.  **Lỗi "Unrecognized engine" khi đọc Excel (trong log Admin):**
    *   *Khắc phục:* Đảm bảo bên `scrape_tool` đã cài `fastexcel` và code đã update (đã fix trong phiên bản hiện tại).
