from pydantic import BaseModel
from typing import List, Optional

# TODO: [CRITICAL] AUTHENTICATION INTEGRATION
# Hiện tại logic Auth đang là MOCKUP hardcode để dev và test tính năng phân quyền.
# Khi tích hợp với hệ thống thật, cần:
# 1. Implement JWT Decoder để parse token từ Header.
# 2. Gọi API Permission của hệ thống cũ để lấy danh sách 'allowed_brands' (hoặc 'allowed_niches') chuẩn xác.
# 3. Map user_id và scopes vào UserContext.
# KHÔNG ĐƯỢC deploy lên Production nếu chưa thay thế logic này!

class UserContext(BaseModel):
    user_id: str
    role: str  # 'admin', 'sales', 'manager'
    allowed_brands: List[str]  # e.g., ['Hunting', 'Dad'] or ['ALL']
    
    def can_view_brand(self, brand: str) -> bool:
        if 'ALL' in self.allowed_brands:
            return True
        return brand in self.allowed_brands

def get_user_context(token: str, all_niches: List[str] = []) -> UserContext:
    """
    Giả lập logic phân quyền dựa trên token và danh sách niche hiện có.
    Logic chia phe:
    - Group AB: Niche bắt đầu bằng A hoặc B.
    - Group BC: Niche bắt đầu bằng B hoặc C.
    - Group AC: Niche bắt đầu bằng A hoặc C.
    """
    
    if token == "admin_secret":
        return UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    
    # Filter niches based on token rule
    allowed = []
    
    if token == "group_ab":
        allowed = [n for n in all_niches if n and n[0].upper() in ['A', 'B']]
        role = "sales_ab"
    elif token == "group_bc":
        allowed = [n for n in all_niches if n and n[0].upper() in ['B', 'C']]
        role = "sales_bc"
    elif token == "group_ac":
        allowed = [n for n in all_niches if n and n[0].upper() in ['A', 'C']]
        role = "sales_ac"
    else:
        # Guest
        return UserContext(user_id="guest", role="viewer", allowed_brands=[])
        
    return UserContext(user_id="user_1", role=role, allowed_brands=allowed)