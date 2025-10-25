# Bank detector
# Copy content from artifact
"""
Utility modules for bank detection and PDF text extraction
"""

# ==================== utils/bank_detector.py ====================
import re
from typing import Optional
from config import BANK_IDENTIFIERS


class BankDetector:
    """Detects bank from statement text"""
    
    @staticmethod
    def detect(text: str) -> Optional[str]:
        """
        Detect bank from PDF text
        
        Args:
            text: Extracted PDF text
            
        Returns:
            Bank key (e.g., 'hdfc', 'axis') or None if unknown
        """
        text_upper = text.upper()
        
        # Check each bank's identifiers
        for bank_key, identifiers in BANK_IDENTIFIERS.items():
            for identifier in identifiers:
                if identifier.upper() in text_upper:
                    return bank_key
        
        return None

