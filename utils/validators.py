# Validators
# Copy content from artifact
import re
from datetime import datetime
from typing import Optional


class DataValidator:
    """Validates extracted data"""
    
    @staticmethod
    def validate_card_number(card_num: str) -> bool:
        """Validate card last 4 digits"""
        return bool(re.match(r'^\d{4}$', card_num))
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date format"""
        patterns = [
            r'^\d{1,2}/\d{1,2}/\d{4}$',
            r'^\d{1,2}-\d{1,2}-\d{4}$',
            r'^\d{2}\s[A-Z]{3}\s\d{4}$',
        ]
        return any(re.match(p, date_str) for p in patterns)
    
    @staticmethod
    def validate_amount(amount: str) -> bool:
        """Validate amount format"""
        try:
            # Remove any remaining symbols
            cleaned = re.sub(r'[^\d.]', '', amount)
            float_val = float(cleaned)
            return float_val >= 0
        except:
            return False
    
    @staticmethod
    def clean_and_validate_amount(amount: str) -> Optional[str]:
        """Clean and validate amount, return None if invalid"""
        if not amount or amount == "NOT_FOUND":
            return None
        
        cleaned = re.sub(r'[^\d.]', '', amount)
        
        if DataValidator.validate_amount(cleaned):
            return cleaned
        
        return None