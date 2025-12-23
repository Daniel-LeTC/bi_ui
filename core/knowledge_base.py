class BusinessKnowledgeBase:
    """
    Kho chứa kiến thức nghiệp vụ (Domain Knowledge).
    Hiện tại là MOCKUP. Sau này sẽ load từ DB hoặc Config File.
    """
    
    def get_injectable_context(self) -> str:
        """
        Tổng hợp tất cả context nghiệp vụ để bơm vào System Prompt.
        """
        return f"""
        ### BUSINESS CONTEXT (CRITICAL):
        {self._get_definitions()}
        {self._get_calculations()}
        {self._get_phase_logic()}
        """

    def _get_definitions(self) -> str:
        # TODO: Define terms clearly. Wait for Business Team verification.
        return """
        - **ASIN**: Amazon Standard Identification Number (Product ID).
        - **SKU**: Stock Keeping Unit.
        - **Bleeding**: Products consuming budget but not generating sales.
        - **Organic Rank**: Position of product in search results without ads.
        """

    def _get_calculations(self) -> str:
        # TODO: Clarify formulas with Mr. Talent/Finance.
        return """
        - **ROAS**: Revenue / Ads Spend.
        - **TACOS**: Total Ads Cost / Total Revenue (Organic + Ads).
        - **Conversion Rate (CVR)**: Orders / Clicks.
        """

    def _get_phase_logic(self) -> str:
        # TODO: Implement dynamic phase detection logic? 
        # For now, just static rules.
        return """
        - **Phase 1 (Launch)**: Focus on Impressions/Clicks. High ACOS allowed.
        - **Phase 2 (Scale)**: Focus on Sales/Rank. Moderate ACOS.
        - **Phase 3 (Maintain)**: Focus on Profit. Low ACOS/TACOS required.
        """

    def get_dynamic_rules(self, current_date: str) -> str:
        """
        Ví dụ logic thay đổi theo thời gian (VD: Q4 cho phép ACOS cao hơn).
        TODO: Implement logic based on input date.
        """
        return "NOTE: In Q4 (Oct-Dec), 'High Spend' threshold increases by 20%."
