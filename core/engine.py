import duckdb
import sqlglot
import polars as pl

from .context import UserContext


class DataEngine:
    def __init__(self, db_path: str, brand_col: str = "Brand"):
        self.db_path = db_path
        self.brand_col = brand_col
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
        """
        # 1. Load Raw
        con.execute(
            f"CREATE VIEW raw_sales AS SELECT * FROM read_parquet('{self.db_path}')"
        )
        
        # 2. Check if brand column exists in schema
        # Lấy danh sách cột để verify, tránh crash nếu sai tên cột config
        cols = [row[0] for row in con.execute("DESCRIBE raw_sales").fetchall()]
        
        # 3. Apply Guardrails
        if "ALL" in context.allowed_brands:
            sql = "CREATE VIEW secure_sales AS SELECT * FROM raw_sales"
        else:
            if self.brand_col not in cols:
                # CRITICAL FAIL-SAFE: Nếu file data không có cột để lọc quyền -> Block luôn cho an toàn
                # Hoặc chỉ cho phép nếu User là Admin? Hiện tại: Block All nếu không khớp schema.
                sql = "CREATE VIEW secure_sales AS SELECT * FROM raw_sales WHERE 1=0"
            else:
                # ESCAPE SINGLE QUOTES: Quan trọng để chống SQL Injection
                safe_brands = [b.replace("'", "''") for b in context.allowed_brands]
                brands_str = ", ".join([f"'{b}'" for b in safe_brands])
                
                if not safe_brands:
                    sql = "CREATE VIEW secure_sales AS SELECT * FROM raw_sales WHERE 1=0"
                else:
                    # Dùng f-string với tên cột động
                    sql = f'CREATE VIEW secure_sales AS SELECT * FROM raw_sales WHERE "{self.brand_col}" IN ({brands_str})'

        con.execute(sql)

    def validate_sql(self, sql: str) -> bool:
        """
        Kiểm tra SQL Injection cơ bản & Từ khóa cấm.
        """
        try:
            # Parse with DuckDB dialect explicitly to support QUALIFY, etc.
            parsed = sqlglot.parse_one(sql, read="duckdb")
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

    def execute_query(self, sql: str, context: UserContext) -> pl.DataFrame:
        """
        Hàm execute chính.
        Returns: Polars DataFrame
        """
        con = self._init_connection()
        try:
            self._setup_shadow_view(con, context)
            self.validate_sql(sql)

            # Thực thi -> Trả về Polars
            # DuckDB support .pl() natively
            return con.execute(sql).pl()
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

    def get_all_brands(self) -> list:
        """
        Helper cho Auth: Lấy danh sách tất cả Brand/Niche có trong DB.
        Dùng để map quyền group A/B/C vào list cụ thể.
        """
        con = self._init_connection()
        try:
            # Load Raw View
            con.execute(f"CREATE VIEW raw_sales AS SELECT * FROM read_parquet('{self.db_path}')")
            
            # Check column existence
            cols = [row[0] for row in con.execute("DESCRIBE raw_sales").fetchall()]
            if self.brand_col not in cols:
                return []
                
            # Query Distinct
            res = con.execute(f'SELECT DISTINCT "{self.brand_col}" FROM raw_sales WHERE "{self.brand_col}" IS NOT NULL').fetchall()
            return [row[0] for row in res]
        except Exception:
            return []
        finally:
            con.close()
