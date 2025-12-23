from pydantic import BaseModel
from typing import List, Optional

# TODO: Define UserContext Model
# Logic: Đây là object duy nhất được truyền xuyên suốt hệ thống để xác định quyền hạn.
class UserContext(BaseModel):
    user_id: str
    role: str  # 'admin', 'sales', 'manager'
    allowed_brands: List[str]  # e.g., ['Sandjest', 'Coquella'] or ['ALL']
    
    # TODO: Add logic to check permission helper
    def can_view_brand(self, brand: str) -> bool:
        if 'ALL' in self.allowed_brands:
            return True
        return brand in self.allowed_brands

# TODO: Implement Token Decoder
def get_user_context(token: Optional[str] = None) -> UserContext:
    """
    Giả lập logic decode JWT.
    
    TODO:
    1. Nếu token None -> Trả về Guest hoặc Raise Error (tùy config).
    2. Nếu token có thật -> Decode JWT -> Map vào UserContext.
    3. (Critical) Nếu hệ thống cũ không trả scope -> Call DB Permission để lấy allowed_brands.
    """
    # MOCK LOGIC for Development
    if token == "admin_secret":
        return UserContext(user_id="admin", role="admin", allowed_brands=["ALL"])
    elif token == "sales_sj":
        return UserContext(user_id="user_1", role="sales", allowed_brands=["Sandjest"])
    
    # Default/Fallback
    return UserContext(user_id="guest", role="viewer", allowed_brands=[])
