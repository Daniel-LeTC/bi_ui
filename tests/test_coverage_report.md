# 🛡️ System Test Coverage Report
**Date:** 2025-12-24
**Status:** ✅ ALL 19 TESTS PASSED

Báo cáo này liệt kê chi tiết các bài kiểm tra (Test Cases) đã được thực hiện để đảm bảo tính ổn định của hệ thống trước khi deploy hoặc demo.

---

## 1. 🧠 AI Core (`tests/test_ai_core.py`)
*Kiểm tra khả năng hiểu ngôn ngữ tự nhiên và chuyển đổi sang SQL của AI Engine (Sử dụng Mock để tránh tốn tiền API).*

| Test Case | Mô tả | Kỳ vọng (Expected Output) |
| :--- | :--- | :--- |
| `test_ai_generate_simple_sql` | Kiểm tra tạo SQL đơn giản. <br>Query: "Tổng doanh thu Brand_A" | SQL trả về phải có `SUM(Revenue)` và `WHERE Brand = 'Brand_A'`. |
| `test_ai_bleeding_knowledge` | Kiểm tra định nghĩa nghiệp vụ "Bleeding" (Đốt tiền). <br>Query: "Sản phẩm đang bleeding" | SQL trả về phải có điều kiện `Ads Spend > 0 AND Units Sold = 0`. |

## 2. ⚙️ Engine Core (`tests/test_engine_core.py`)
*Kiểm tra khả năng xử lý dữ liệu, kết nối DuckDB và tính chính xác toán học.*

| Test Case | Mô tả | Kỳ vọng (Expected Output) |
| :--- | :--- | :--- |
| `test_engine_initialization_fail` | Khởi tạo Engine với file Parquet không tồn tại. | Hệ thống phải bắn ra Exception (Crash an toàn). |
| `test_secure_view_multi_brand` | User có quyền xem nhiều Brand (A & B) nhưng không xem C. | Kết quả trả về chứa Brand A, B. **Không được chứa Brand C**. |
| `test_aggregation_precision` | Tính tổng Revenue số thực (Float). | Tổng `100.5 + 200.0 + 50.0` phải bằng chính xác `350.5` (Không bị lỗi làm tròn). |
| `test_schema_extraction_format` | Lấy Schema để bơm cho AI. | String trả về phải đúng format `- Column (TYPE)`. |
| `test_brand_name_injection_and_quotes` | Tên Brand chứa ký tự đặc biệt (`Brand's A`). | Query không bị lỗi SQL Syntax. |

## 3. 🔄 Integration Flow (`tests/test_integration_flow.py`)
*Kiểm tra luồng đi từ User Request -> Agent -> AI -> SQL -> Data -> Response (End-to-End).*

| Test Case | Mô tả | Kỳ vọng (Expected Output) |
| :--- | :--- | :--- |
| `test_full_flow_revenue_query` | User hỏi doanh thu (Happy Path). | Status: `success`, Data trả về đúng con số đã Mock. |
| `test_full_flow_permission_block` | User hỏi về Brand bị cấm (Forbidden Brand). | Status: `success` (Query chạy được), nhưng Data trả về `0` hoặc `Null`. |

## 4. 🧹 Parser Robustness (`tests/test_parser_robustness.py`)
*Kiểm tra độ "trâu bò" của bộ Parser khi xử lý output lộn xộn từ AI.*

| Test Case | Mô tả | Kỳ vọng (Expected Output) |
| :--- | :--- | :--- |
| `test_parser_clean_json` | Input JSON chuẩn. | Parse thành công Dict. |
| `test_parser_markdown_block` | Input bọc trong ```json ... ```. | Tự động strip markdown và parse thành công. |
| `test_parser_messy_text` | Input có lời dẫn ("Here is code: ..."). | Dùng Regex trích xuất JSON nằm giữa text. |
| `test_parser_nested_braces` | JSON chứa ngoặc nhọn lồng nhau (Nested objects). | Parse đúng cấu trúc lồng nhau. |
| `test_parser_broken_json` | Input là text thường, không có JSON. | Trả về `None` (Không crash). |
| `test_parser_partial_json_fail` | JSON bị cắt cụt (Syntax Error). | Trả về `None` (Không crash). |

## 5. 💀 Skeleton & Security (`tests/test_skeleton.py`)
*Kiểm tra các thành phần cơ sở và bảo mật SQL Injection.*

| Test Case | Mô tả | Kỳ vọng (Expected Output) |
| :--- | :--- | :--- |
| `test_security_context_logic` | Unit test class `UserContext`. | Hàm `can_view_brand()` trả về đúng True/False. |
| `test_shadow_view_isolation` | Kiểm tra tính năng "Shadow View" của DuckDB. | Query `SELECT *` chỉ nhìn thấy dữ liệu được phép thấy. |
| `test_sql_injection_guard` | Cố tình chạy lệnh `DROP TABLE`. | Hệ thống chặn lại và báo lỗi `Forbidden`. |
| `test_knowledge_base_injection` | Kiểm tra inject Business Context. | Context string phải chứa các từ khóa nghiệp vụ (như "Bleeding"). |

---
**Tổng kết:** Hệ thống đã được "bê tông hóa" ở cả 3 tầng:
1.  **Logic:** AI hiểu nghiệp vụ.
2.  **An toàn:** User không thể xem trộm data người khác (RLS).
3.  **Ổn định:** Parser chấp hết mọi thể loại output rác.
