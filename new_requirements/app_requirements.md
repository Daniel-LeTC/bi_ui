# **SYSTEM BLUEPRINT: SANDJEST AI ANALYST (V2.0)**

Author: Tech Lead Bro  
Status: Draft for Implementation  
Core Principle: Stateless, Secure, & Scalable.

## **PHẦN 1: BACKEND LOGIC (FASTAPI \+ DUCKDB ENGINE)**

### **⚠️ CORE CHALLENGE: DUCKDB CONCURRENCY**

Vấn đề: DuckDB đơn luồng ghi (Single Writer). Nếu Ingestion đang ghi mà AI nhảy vào đọc file đó \-\> Crash/Lock.  
Giải pháp: Tách biệt tuyệt đối luồng GHI và ĐỌC.

### **STEP 1: CONCURRENCY & DATA LAKE MANAGEMENT**

#### **1.1. Ingestion Strategy (The Writer)**

* **Trigger:** Chạy theo lịch (Cronjob/n8n Schedule) lúc giờ thấp điểm phù hợp (cái này bên schedule trigger n8n của scrape set sau).  
* **Logic "Atomic Write" (Ghi nguyên tử \- Bắt buộc):**  
  * **Không ghi trực tiếp** vào file đang tồn tại.  
  * **Bước 1:** Scrape data \-\> Dump ra CSV.  
  * **Bước 2:** Convert CSV \-\> Parquet tại folder \_temp/.  
  * **Bước 3 (Critical):** Dùng lệnh os.rename (hoặc mv) để di chuyển file từ \_temp/ sang data\_lake/. Hành động này diễn ra trong tích tắc, giảm thiểu tối đa rủi ro lock file.  
* **TODO Code Skeleton:**  
  def ingest\_data():  
      \# 1\. Acquire Lock (File lock hoặc Redis lock để chặn 2 process ingest chạy cùng lúc)  
      \# 2\. Process CSV \-\> Parquet in TEMP\_DIR  
      \# 3\. Move Parquet to DATA\_LAKE\_DIR (Atomic Operation)  
      \# 4\. Release Lock  
      Pass  
* **LƯU Ý RẤT QUAN TRỌNG, CÁC PHẦN NÀY THUỘC SCRAPE\_BOT, CHÚNG TA ĐÃ CODE XONG, PHẦN NÀO CHƯA THỎA SẼ QUAY LẠI SAU (NOTED AT: 12PM 2025-12-23)**

#### **1.2. Query Strategy (The Reader \- Per-Request Isolation)**

* **Nguyên tắc:** "Mỗi User một cái nồi riêng". Không share connection global.  
* **Logic:**  
  * Khi có request API /tools/execute-sql:  
  * Khởi tạo con \= duckdb.connect(':memory:') (RAM only).  
  * Dùng read\_only=True (nếu mount trực tiếp DB file) hoặc chỉ đơn giản là query file Parquet (Parquet file bản chất là read-only).  
  * **Cấu hình RAM:** Set memory\_limit='2GB' cho mỗi connection để tránh OOM (Out of Memory) nếu user query ngu.

### **STEP 2: AUTHENTICATION & CONTEXT INJECTION (THE PASSPORT)**

#### **2.1. Token Handling**

* **Input:** Header Authorization: Bearer \<jwt\_token\> (Token lấy từ PPC Tool cũ).  
* **Logic Middleware:**  
  * Decode JWT (dùng Secret Key của hệ thống cũ).  
  * Extract Payload: user\_id, role, scopes (Permission).  
  * **Fallback:** Nếu Token không chứa scope (do hệ thống cũ lởm), phải có logic gọi về DB Permission để lấy quyền dựa trên user\_id.

#### **2.2. Context Object**

* Tạo class UserContext:  
  class UserContext(BaseModel):  
      user\_id: str  
      role: str  \# 'admin', 'sales', 'manager'  
      allowed\_brands: List\[str\] \# \['Sandjest', 'Coquella'\]  
      read\_only\_mode: bool \= True

### **STEP 3: DYNAMIC GUARDRAILS (THE SHIELD \- CỰC QUAN TRỌNG)**

Mục tiêu: Ngăn chặn AI truy cập data không được phép. Sử dụng kỹ thuật **"Shadow View"**.

#### **3.1. Logic "Cái Lồng Giam" (View Injection)**

Quy trình thực thi khi chạy SQL:

1. **Init Connection:** Mở connection in-memory.  
2. **Load Raw Data:**  
   CREATE VIEW raw\_sales AS SELECT \* FROM 'data\_lake/sales/\*/\*.parquet';

3. **Apply Security Layer (Shadowing):**  
   * Dựa vào UserContext.allowed\_brands.  
   * Tạo view secure\_sales đè lên logic lọc.

\# Logic Python generate SQL  
if 'ALL' in allowed\_brands:  
    sql \= "CREATE VIEW secure\_sales AS SELECT \* FROM raw\_sales"  
else:  
    brands\_tuple \= tuple(allowed\_brands)  
    sql \= f"CREATE VIEW secure\_sales AS SELECT \* FROM raw\_sales WHERE Brand\_Name IN {brands\_tuple}"

con.execute(sql)

4. **Execute User Query:**  
   * Bắt buộc câu SQL của AI phải query từ secure\_sales. Nếu AI query raw\_sales, trả về lỗi "Table not found" (vì ta không public tên bảng raw cho AI biết).

#### **3.2. Syntax Guard**

* Dùng sqlglot hoặc Regex check nhanh các từ khóa cấm: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE.  
* Nếu phát hiện \-\> **Raise Exception 403 Forbidden**.

### **STEP 4: AI ENGINE INTELLIGENCE (THE BRAIN)**

#### **4.1. Schema Awareness**

* **Dynamic Schema:** Không hardcode string schema.  
* **Hàm get\_schema():**  
  * Query DESCRIBE secure\_sales.  
  * Format output dạng: Column Name (Type) \- Description (nếu có mapping).  
  * Trả về text để inject vào System Prompt.

#### **4.2. Time Awareness**

* AI rất ngu về thời gian tương đối.  
* **Luôn inject:** Current Date: {datetime.now().strftime('%Y-%m-%d %A')}.  
* Giải thích rõ: "Last month" nghĩa là từ ngày X đến ngày Y.

#### **4.3. Self-Correction Loop (Cơ chế tự sửa sai)**

* **Logic:**  
  def run\_ai\_query(question, context, retries=2):  
      schema \= get\_schema()  
      messages \= build\_prompt(question, schema, context)

      for i in range(retries):  
          sql \= llm\_generate(messages)  
          try:  
              \# Chạy thử SQL  
              validate\_sql(sql) \# Check từ khóa cấm  
              result \= con.execute(sql).df()  
              return result, sql  
          except DuckDBError as e:  
              \# Nếu lỗi \-\> Ném lỗi ngược lại cho AI  
              messages.append({"role": "user", "content": f"Query Failed: {str(e)}. Fix the SQL."})  
              continue

      raise Exception("AI quá ngu, đã thử 2 lần vẫn lỗi.")

## **PHẦN 2: INTEGRATION (N8N \+ FASTAPI)**

### **STEP 4B: API INTERFACE & N8N WORKFLOW**

#### **4B.1. FastAPI Endpoints (Tools cho n8n)**

FastAPI đóng vai trò là "Tool Provider".

1. **POST /tools/schema**:  
   * Input: User Token (để biết user được xem bảng nào).  
   * Output: Schema String (của bảng secure\_sales).  
2. **POST /tools/execute**:  
   * Input: User Token, SQL Query.  
   * Logic: Validate Token \-\> Build Secure View \-\> Run SQL \-\> Return JSON.

#### **4B.2. n8n Workflow (The Orchestrator)**

Sơ đồ Node trong n8n:

1. **Webhook:** Nhận question \+ token.  
2. **HTTP Request (Auth & Schema):** Gọi POST /tools/schema. Nếu Token lỗi \-\> Trả lỗi ngay.  
3. **AI Chain (OpenAI):**  
   * System Prompt: "You are a Data Analyst... Use schema provided... Output JSON SQL."  
   * Context: Output của node trước.  
4. **Code Node:** Parse JSON lấy sql.  
5. **HTTP Request (Exec):** Gọi POST /tools/execute.  
6. **Response:** Trả kết quả về Webhook.

## **PHẦN 3: FRONTEND LOGIC (STREAMLIT UI)**

### **STEP 5: AUTH & SESSION**

#### **5.1. Token Retrieval (Smart)**

* **Priority 1:** Lấy từ Query Param ?token=... (Trường hợp nhúng iFrame từ Dashboard cũ).  
* **Priority 2:** Lấy từ st.session\_state (Nếu đã lưu).  
* **Validate:** Gọi thử 1 API nhẹ (/me) để check token sống hay chết. Nếu chết \-\> Hiện màn hình "Session Expired".

#### **5.2. Session State**

* st.session\_state.messages: List history chat.  
* st.session\_state.token: JWT Token.  
* st.session\_state.user\_info: {role, brands}.

### **STEP 6: UI UX "DE-PHÈN-IZATION"**

#### **6.1. Custom CSS (Hack UI)**

* Ẩn Header/Footer mặc định.  
* Chỉnh font chữ, màu nền cho giống Branding của công ty.

#### **6.2. Smart Feedback**

* Dùng st.status hoặc st.spinner cho các tác vụ \> 2 giây.  
* **Thinking Process:** (Optional) Nếu n8n trả về các bước trung gian ("Đang đọc schema...", "Đang gen SQL..."), hiện lên cho nguy hiểm.

### **STEP 7: VISUALIZATION SKELETON (LOGIC HIỂN THỊ)**

\# Skeleton Logic  
if result\_type \== 'dataframe':  
    df \= pd.DataFrame(data)  
      
    \# Heuristic 1: Time Series  
    if 'date' in df.columns and len(df) \> 1 and len(df.columns) \== 2:  
        st.line\_chart(df, x='date')  
          
    \# Heuristic 2: Categorical Comparison  
    elif 'brand' in df.columns or 'category' in df.columns:  
        st.bar\_chart(df)  
          
    \# Heuristic 3: Table (Default)  
    else:  
        st.dataframe(df, use\_container\_width=True)

elif result\_type \== 'value':  
    st.metric(label="Kết quả", value=data)

## **PHẦN 4: TEST & VALIDATION STRATEGY**

### **1\. Unit Test (Backend)**

* **Test Auth:** Gửi token rởm \-\> Expect 401\.  
* **Test Guardrail:**  
  * User A (Sandjest) gửi SQL SELECT \* FROM secure\_sales \-\> Expect: Chỉ thấy Sandjest.  
  * User A cố tình gửi SELECT \* FROM raw\_sales \-\> Expect: Error (Table not found).  
* **Test SQL Injection:** Gửi DROP TABLE \-\> Expect: 403\.

### **2\. Integration Test (n8n)**

* Chạy workflow với câu hỏi mock.  
* Kiểm tra JSON đầu ra của node AI có đúng format không.

### **3\. Load Test (Concurrency)**

* Dùng locust giả lập 10 user chat cùng lúc.  
* Kiểm tra xem DuckDB có bị lock không (Mong đợi: Không, vì dùng connection in-memory riêng biệt).

### **4\. Edge Cases (Các ca khó đỡ)**

* Data rỗng (Ngày hôm nay chưa có sales).  
* Câu hỏi vô nghĩa ("Mày ăn cơm chưa?").  
* SQL chạy quá lâu (\> 30s) \-\> Cần setup timeout cho DuckDB connection.

**Note:** Đây là bản Blueprint để mày bắt đầu code. Cứ bám theo sườn này, phần nào chưa rõ logic thì ping tao. Triển khai theo thứ tự: **Backend Core \-\> Auth \-\> n8n \-\> Frontend**.