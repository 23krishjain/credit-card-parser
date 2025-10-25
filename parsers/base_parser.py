# Base parser
# Copy content from 
"""
Base parser class that all bank-specific parsers inherit from
Ensures consistent interface and data structure
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import re


@dataclass
class Transaction:
    """Standard transaction data structure"""
    date: str
    description: str
    amount: str
    category: str = "Other"
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class StatementData:
    """Standard statement data structure returned by all parsers"""
    bank_name: str
    card_last_4: str = "NOT_FOUND"
    statement_date: str = "NOT_FOUND"
    payment_due_date: str = "NOT_FOUND"
    total_amount_due: str = "NOT_FOUND"
    minimum_payment: str = "NOT_FOUND"
    statement_period_start: str = "NOT_FOUND"
    statement_period_end: str = "NOT_FOUND"
    credit_limit: str = "NOT_FOUND"
    available_credit: str = "NOT_FOUND"
    
    # Metadata
    extraction_method: str = "regex"
    confidence_score: float = 0.0
    transactions: List[Transaction] = field(default_factory=list)
    raw_text_preview: str = ""
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["transaction_count"] = len(self.transactions)
        return data
    
    def calculate_confidence(self) -> float:
        """Calculate extraction confidence based on found fields"""
        required = [
            self.card_last_4,
            self.statement_date,
            self.payment_due_date,
            self.total_amount_due,
            self.minimum_payment,
        ]
        found = sum(1 for field in required if field != "NOT_FOUND")
        self.confidence_score = found / len(required)
        return self.confidence_score
    
    def is_valid(self) -> bool:
        """Check if minimum required fields are present"""
        return (
            self.card_last_4 != "NOT_FOUND" and
            self.total_amount_due != "NOT_FOUND" and
            self.payment_due_date != "NOT_FOUND"
        )


class BaseParser(ABC):
    """
    Abstract base class for all parsers (regex and AI)
    Enforces consistent interface and provides common utilities
    """
    
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
    
    @abstractmethod
    def parse(self, text: str) -> StatementData:
        """
        Main parsing method - must be implemented by all subclasses
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            StatementData object with extracted information
        """
        pass
    
    def clean_amount(self, amount_str: str) -> str:
        """
        Clean and standardize amount strings Handles: ₹22,935.00, Rs. 22935, 22.935,00 etc.
        """
        if not amount_str or amount_str == "NOT_FOUND":
            return amount_str
        
        # Remove currency symbols and indicators (but NOT decimal point yet)
        cleaned = re.sub(r'[₹$£Rs]|INR|USD|DR|Cr|CR|dr|cr', '', amount_str)
        cleaned = cleaned.strip()
        
        # Remove spaces
        cleaned = cleaned.replace(' ', '')
        
        # Handle Indian number format: 25,625.00 → 25625.00
        # Remove commas ONLY if there's a decimal point
        if '.' in cleaned:
            cleaned = cleaned.replace(',', '')
        # If no decimal, assume commas are thousand separators
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '')
        
        # Keep only digits and ONE decimal point
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        # Handle multiple decimals (keep only the last one)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        
        # CRITICAL: Ensure we have decimal for amounts
        # If amount looks complete but missing decimals, add .00
        if cleaned and '.' not in cleaned and len(cleaned) <= 10:
            # Don't add decimals - return as is for now
            pass
        
        return cleaned.strip()
    
    def extract_with_pattern(self, text: str, patterns: List[str]) -> str:
        """
        Try multiple regex patterns and return first match
        
        Args:
            text: Text to search in
            patterns: List of regex patterns to try
            
        Returns:
            Matched value or "NOT_FOUND"
        """
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    # Clean whitespace
                    value = re.sub(r'\s+', ' ', value)
                    if value:
                        return value
            except (re.error, IndexError) as e:
                continue
        
        return "NOT_FOUND"
    
    def validate_card_number(self, card_num: str) -> bool:
        """Validate that card number is exactly 4 digits"""
        return bool(re.match(r'^\d{4}$', card_num))
    
    def validate_date(self, date_str: str) -> bool:
        """Validate date format"""
        date_pattern = r'^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}$'
        return bool(re.match(date_pattern, date_str))
    
    def categorize_transaction(self, description: str) -> str:
        """
        Categorize transaction based on merchant/description
        (Can be extended with more sophisticated categorization)
        """
        desc_lower = description.lower()
        
        categories = {
            "Groceries": ["grocery", "supermarket", "zepto", "blinkit", "bigbasket", "dmart"],
            "Dining": ["restaurant", "cafe", "swiggy", "zomato", "food", "starbucks", "mcdonald"],
            "Transportation": ["uber", "ola", "fuel", "petrol", "gas", "parking"],
            "Shopping": ["amazon", "flipkart", "myntra", "store", "mall"],
            "Entertainment": ["netflix", "prime", "spotify", "movie", "cinema"],
            "Utilities": ["electric", "water", "internet", "phone", "recharge"],
            "Bills": ["payment", "paytm", "phonepe", "gpay"],
        }
        
        for category, keywords in categories.items():
            if any(kw in desc_lower for kw in keywords):
                return category
        
        return "Other"
    
    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions from text (basic implementation) Override in subclass for bank-specific logic"""
        transactions = []
        
        # Pattern 1: Indian format (DD/MM/YYYY Description Amount)
        pattern1 = r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.[\d]{2})\s*(?:Cr|Dr)?'
        
        # Pattern 2: US format - "MM/DD DESCRIPTION $Amount"
        # Example: "01/03 STARBUCKS #2847 $5.67"
        pattern2 = r'(\d{2}/\d{2})\s+([A-Z0-9][A-Z0-9\s\*#\-\.]+?)\s+\$?([\d,]+\.[\d]{2})'
        
        # Try Indian format first
        matches = list(re.finditer(pattern1, text))
        
        if matches:
            for match in matches:
                date = match.group(1)
                description = match.group(2).strip()[:100]
                amount = self.clean_amount(match.group(3))
                
                if amount and float(amount) > 0:
                    transactions.append(Transaction(
                        date=date,
                        description=description,
                        amount=f"₹{amount}",
                        category=self.categorize_transaction(description)
                    ))
        else:
            # Try US format
            year_match = re.search(r'Statement Period[:\s]*(\d{2}/\d{2}/)?(\d{4})', text)
            year = year_match.group(2) if year_match else "2024"
            
            for match in re.finditer(pattern2, text):
                date_partial = match.group(1)  # MM/DD
                description = match.group(2).strip()[:100]
                amount = self.clean_amount(match.group(3))
                
                full_date = f"{date_partial}/{year}"
                
                if amount and float(amount) > 0:
                    transactions.append(Transaction(
                        date=full_date,
                        description=description,
                        amount=f"₹{amount}",
                        category=self.categorize_transaction(description)
                    ))
        
        return transactions