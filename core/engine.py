import duckdb
import sqlglot

from .context import UserContext


class DataEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # TODO: Cấu hình connection pool nếu cần, nhưng với DuckDB in-memory thì init per request là an toàn nhất.

    def _init_connection(self):
        """
        Khởi tạo connection in-memory.
        TODO: Set memory_limit='2GB' để tránh user query xàm làm sập app.
        """
        con = duckdb.connect(":memory:")
        con.execute("SET memory_limit='2GB';")
        return con

    def _setup_shadow_view(self, con, context: UserContext):
        """
        CORE SECURITY LOGIC: Shadow View Injection.

        TODO:
        1. Tạo view 'raw_sales' từ file parquet thật (self.db_path).
        2. Dựa vào context.allowed_brands để tạo view 'secure_sales'.
           - Nếu allowed_brands == ['ALL'] -> SELECT * FROM raw_sales
           - Nếu có list brands -> SELECT * FROM raw_sales WHERE Brand IN (...)
        3. User/AI chỉ được biết sự tồn tại của 'secure_sales'.
        """
        # 1. Load Raw
        con.execute(
            f"CREATE VIEW raw_sales AS SELECT * FROM read_parquet('{self.db_path}')"
        )

        # 2. Apply Guardrails
        if "ALL" in context.allowed_brands:
            sql = "CREATE VIEW secure_sales AS SELECT * FROM raw_sales"
        else:
            brands = [f"'{b}'" for b in context.allowed_brands]
            brands_str = ", ".join(brands)
            if not brands:
                # Trường hợp không có quyền brand nào -> View rỗng
                sql = "CREATE VIEW secure_sales AS SELECT * FROM raw_sales WHERE 1=0"
            else:
                sql = f'CREATE VIEW secure_sales AS SELECT * FROM raw_sales WHERE "Brand" IN ({brands_str})'

        con.execute(sql)

    def validate_sql(self, sql: str) -> bool:
        """
        Kiểm tra SQL Injection cơ bản & Từ khóa cấm.

        TODO:
        1. Dùng sqlglot để parse.
        2. Blacklist: DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE.
        3. Whitelist tables: Chỉ cho phép query trên 'secure_sales'.
        """
        try:
            parsed = sqlglot.parse_one(sql)
            # Check command type
            if parsed.find(
                sqlglot.exp.Drop,
                sqlglot.exp.Delete,
                sqlglot.exp.Insert,
                sqlglot.exp.Update,
            ):
                raise ValueError("Forbidden: Write operations are not allowed.")
            return True
        except Exception as e:
            raise ValueError(f"Invalid SQL: {str(e)}")

    def execute_query(self, sql: str, context: UserContext):
        """
        Hàm execute chính.

        Flow:
        1. Init Connection.
        2. Setup Shadow View (để áp permission).
        3. Validate SQL.
        4. Run SQL -> Return DF.
        5. Close Connection.
        """
        con = self._init_connection()
        try:
            self._setup_shadow_view(con, context)
            self.validate_sql(sql)

            # Thực thi
            df = con.execute(sql).df()
            return df
        except Exception as e:
            raise e
        finally:
            con.close()

    def get_schema_info(self, context: UserContext) -> str:
        """
        Lấy schema của bảng secure_sales để đưa cho AI.
        """
        con = self._init_connection()
        try:
            self._setup_shadow_view(con, context)
            # DESCRIBE secure_sales
            schema = con.execute("DESCRIBE secure_sales").fetchall()
            # Format string: "Column (Type)"
            return "\n".join([f"- {row[0]} ({row[1]})" for row in schema])
        finally:
            con.close()
