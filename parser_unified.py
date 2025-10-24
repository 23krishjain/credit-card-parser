"""
Universal Credit Card Statement Parser - Merged Version
Supports: Chase, Amex, Citi, Discover, Bank of America, HDFC, ICICI, SBI, Axis, Kotak
Combines best features from v2 and v3 for maximum compatibility
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pdfplumber

# Try importing advanced libraries
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class Transaction:
    """Individual transaction data"""
    date: str
    description: str
    amount: str
    category: str = "Unknown"


@dataclass
class CreditCardStatement:
    """Extracted credit card statement data"""
    card_issuer: str
    card_last_four: str
    billing_cycle_start: str
    billing_cycle_end: str
    payment_due_date: str
    total_balance: str
    minimum_payment: str
    available_credit: str
    transactions: List[Transaction]
    extraction_method: str = "pdfplumber"
    is_scanned: bool = False
    raw_text_preview: str = ""
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['transaction_count'] = len(self.transactions)
        data['transactions'] = [asdict(t) for t in self.transactions]
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class UniversalCreditCardParser:
    """Universal parser supporting both American and Indian banks"""
    
    # Comprehensive issuer patterns
    ISSUER_PATTERNS = {
        'HDFC': {
            'issuer_keywords': ['hdfc', 'hdfc bank', 'statement of account'],
            'last_four': [
                r'Card No[:\s]*\d{4}\s*\d{2}XX\s*XXXX\s*(\d{4})',
                r'Card No[:\s]*[\dX\s]+(\d{4})',
                r'Card ending in[:\s]*(\d{4})',
            ],
            'statement_period': [
                r'Statement Date[:\s]*(\d{2}/\d{2}/\d{4})',
                r'Statement for.*?(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*(\d{2}/\d{2}/\d{4})',
                r'(\d{2}/\d{2}/\d{4})\s+[\d,]+\.[\d]+\s+[\d,]+\.[\d]+',
            ],
            'total_due': [
                r'Total Dues[^\d]*?([\d,]+\.[\d]+)',
                r'(\d{2}/\d{2}/\d{4})\s+([\d,]+\.[\d]+)\s+[\d,]+\.[\d]+',
            ],
            'minimum_payment': [
                r'Minimum Amount Due[^\d]*?([\d,]+\.[\d]+)',
                r'(\d{2}/\d{2}/\d{4})\s+[\d,]+\.[\d]+\s+([\d,]+\.[\d]+)',
            ],
            'credit_limit': [
                r'Credit Limit\s+([\d,]+\.?[\d]*)\s+[\d,]+',
                r'Credit Limit[:\s]+([\d,]+)',
            ],
            'available_credit': [
                r'Available Credit Limit\s+([\d,]+\.[\d]+)',
                r'Credit Limit\s+[\d,]+\.?[\d]*\s+([\d,]+\.[\d]+)',
            ],
            'date_format': 'DD/MM/YYYY',
            'currency_symbol': '₹',
        },
        'ICICI': {
            'issuer_keywords': ['icici', 'icici bank'],
            'last_four': [r'Card No[.\s:]*\*+(\d{4})', r'XX+\s*(\d{4})'],
            'statement_period': [r'Statement Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})'],
            'due_date': [r'Payment Due Date[:\s]*(\d{2}/\d{2}/\d{4})'],
            'total_due': [r'Total Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'minimum_payment': [r'Minimum Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'credit_limit': [r'Credit Limit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'available_credit': [r'Available Credit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'date_format': 'DD/MM/YYYY',
            'currency_symbol': '₹',
        },
        'SBI': {
            'issuer_keywords': ['sbi', 'state bank', 'state bank of india'],
            'last_four': [r'Card Number[:\s]*\*+(\d{4})', r'Card ending[:\s]*(\d{4})'],
            'statement_period': [r'Statement Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})'],
            'due_date': [r'Payment Due on[:\s]*(\d{2}/\d{2}/\d{4})'],
            'total_due': [r'Total Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'minimum_payment': [r'Minimum Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'credit_limit': [r'Credit Limit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'available_credit': [r'Available Credit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'date_format': 'DD/MM/YYYY',
            'currency_symbol': '₹',
        },
        'Axis': {
            'issuer_keywords': ['axis', 'axis bank'],
            'last_four': [r'Card No[.\s:]*\*+(\d{4})', r'Card ending[:\s]*(\d{4})'],
            'statement_period': [r'Statement Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})'],
            'due_date': [r'Payment Due Date[:\s]*(\d{2}/\d{2}/\d{4})'],
            'total_due': [r'Total Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'minimum_payment': [r'Minimum Payment[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'credit_limit': [r'Credit Limit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'available_credit': [r'Available Credit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'date_format': 'DD/MM/YYYY',
            'currency_symbol': '₹',
        },
        'Kotak': {
            'issuer_keywords': ['kotak', 'kotak mahindra'],
            'last_four': [r'Card Number[:\s]*\*+(\d{4})', r'Card ending[:\s]*(\d{4})'],
            'statement_period': [r'Statement Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})'],
            'due_date': [r'Payment Due Date[:\s]*(\d{2}/\d{2}/\d{4})'],
            'total_due': [r'Total Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'minimum_payment': [r'Minimum Amount Due[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'credit_limit': [r'Total Credit Limit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'available_credit': [r'Available Credit Limit[:\s]*Rs\.?\s*([\d,]+\.?\d*)'],
            'date_format': 'DD/MM/YYYY',
            'currency_symbol': '₹',
        },
        'Chase': {
            'issuer_keywords': ['chase', 'jpmorgan chase'],
            'last_four': [
                r'Account.*?ending in[:\s]+(\d{4})',
                r'Account[:\s]+.*?(\d{4})',
                r'Account Number:.*?(\d{4})',
            ],
            'statement_period': [
                r'Statement Period[:\s]*(\d{1,2}/\d{1,2}/\d{4})\s*to\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'total_due': [
                r'New Balance[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Amount Due|Balance)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'minimum_payment': [
                r'Minimum Payment Due[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Minimum Payment|Minimum Due)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'credit_limit': [
                r'Credit Limit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'available_credit': [
                r'Available Credit[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Available Credit|Credit Available)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'date_format': 'MM/DD/YYYY',
            'currency_symbol': '$',
        },
        'Amex': {
            'issuer_keywords': ['american express', 'amex'],
            'last_four': [
                r'Account Ending[:\s]*(\d{4})',
                r'Account.*?(\d{4})',
                r'-(\d{4})',
            ],
            'statement_period': [
                r'Statement Closing Date[:\s]*([A-Za-z]+ \d{1,2}, \d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*([A-Za-z]+ \d{1,2}, \d{4})',
                r'(?:Please Pay By)[:\s]*([A-Za-z]+ \d{1,2}, \d{4})',
            ],
            'total_due': [
                r'Total New Balance[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Total Amount Due|New Balance)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'minimum_payment': [
                r'Minimum Payment Due[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'credit_limit': [
                r'Total Credit Limit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'available_credit': [
                r'Total Available Credit[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Credit Available|Available Credit)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'date_format': 'MonthName DD, YYYY',
            'currency_symbol': '$',
        },
        'Citi': {
            'issuer_keywords': ['citibank', 'citi'],
            'last_four': [
                r'Account Number.*?(\d{4})',
                r'xxxx\s*(\d{4})',
                r'Account.*?ending in[:\s]+(\d{4})',
            ],
            'statement_period': [
                r'Statement Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'total_due': [
                r'New Balance[:\s]*\$\s*([\d,]+\.\d{2})',
                r'(?:Total Balance)[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'minimum_payment': [
                r'Minimum Payment[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'credit_limit': [
                r'Credit Limit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'available_credit': [
                r'Available Credit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'date_format': 'MM/DD/YYYY',
            'currency_symbol': '$',
        },
        'Discover': {
            'issuer_keywords': ['discover'],
            'last_four': [
                r'Account.*?(\d{4})',
                r'ending in[:\s]+(\d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'total_due': [
                r'New Balance[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'minimum_payment': [
                r'Minimum Payment[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'credit_limit': [
                r'Credit Limit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'available_credit': [
                r'Credit Available[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'date_format': 'MM/DD/YYYY',
            'currency_symbol': '$',
        },
        'BankOfAmerica': {
            'issuer_keywords': ['bank of america', 'bofa'],
            'last_four': [
                r'Account.*?(\d{4})',
                r'ending in[:\s]+(\d{4})',
            ],
            'due_date': [
                r'Payment Due Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'total_due': [
                r'New Balance[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'minimum_payment': [
                r'Minimum Payment Due[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'credit_limit': [
                r'Credit Limit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'available_credit': [
                r'Available Credit[:\s]*\$\s*([\d,]+\.\d{2})',
            ],
            'date_format': 'MM/DD/YYYY',
            'currency_symbol': '$',
        },
    }
    
    def __init__(self):
        self.capabilities = self._check_capabilities()
    
    def _check_capabilities(self) -> Dict[str, bool]:
        """Check which extraction methods are available"""
        caps = {
            'pdfplumber': True,
            'camelot': CAMELOT_AVAILABLE,
            'tabula': TABULA_AVAILABLE,
            'ocr': OCR_AVAILABLE
        }
        
        print(f"\n📊 Parser Capabilities:")
        for method, available in caps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {method.upper()}")
        print()
        
        return caps
    
    def _is_scanned_pdf(self, pdf_path: str) -> bool:
        """Check if PDF is scanned (image-based)"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if not text or len(text.strip()) < 50:
                    return True
                
                if len(first_page.images) > 0 and len(text.strip()) < 200:
                    return True
                
                return False
        except:
            return False
    
    def extract_text_with_ocr(self, pdf_path: str) -> str:
        """Extract text from scanned PDF using OCR"""
        if not OCR_AVAILABLE:
            raise Exception("OCR not available. Install pytesseract and pdf2image")
        
        print("🔍 Detected scanned PDF. Using OCR...")
        
        try:
            images = convert_from_path(pdf_path, dpi=300)
            
            full_text = ""
            for i, image in enumerate(images):
                print(f"  Processing page {i+1}/{len(images)}...")
                text = pytesseract.image_to_string(image)
                full_text += text + "\n"
            
            print(f"✅ OCR completed. Extracted {len(full_text)} characters")
            return full_text
        
        except Exception as e:
            raise Exception(f"OCR failed: {e}")
    
    def detect_issuer(self, text: str) -> str:
        """Detect card issuer from PDF text - prioritize Indian banks"""
        text_lower = text.lower()
        
        # Check Indian banks FIRST (higher priority)
        indian_banks = ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']
        for issuer in indian_banks:
            patterns = self.ISSUER_PATTERNS[issuer]
            for keyword in patterns['issuer_keywords']:
                if keyword.lower() in text_lower:
                    return issuer
        
        # Then check American/International banks
        for issuer, patterns in self.ISSUER_PATTERNS.items():
            if issuer in indian_banks:
                continue
            for keyword in patterns['issuer_keywords']:
                if keyword.lower() in text_lower:
                    return issuer
        
        return 'Unknown'
    
    def parse_indian_date(self, date_str: str) -> Optional[str]:
        """Parse Indian date format DD/MM/YYYY to MM/DD/YYYY"""
        if not date_str:
            return None
        
        try:
            if '/' in date_str and len(date_str.split('/')) == 3:
                parts = date_str.split('/')
                if len(parts[0]) <= 2 and int(parts[0]) > 12:  # Likely DD/MM/YYYY
                    day, month, year = parts
                    return f"{month}/{day}/{year}"
            return date_str
        except:
            return date_str
    
    def format_amount(self, amount_str: str, currency_symbol: str, is_credit: bool = False) -> str:
        """Format amount string with currency symbol and commas"""
        try:
            # Clean the amount string
            amount_clean = amount_str.replace(',', '').replace('Rs.', '').replace('Rs', '').replace('₹', '').replace('$', '').strip()
            amount_float = float(amount_clean)
            
            if currency_symbol == '₹':
                formatted = f"₹{amount_float:,.2f}"
            else:
                formatted = f"${amount_float:,.2f}"
                
            # Add CR indicator for credit transactions
            if is_credit:
                formatted = f"{formatted} CR"
                
            return formatted
        except:
            return amount_str
    
    def extract_hdfc_fields_special(self, text: str) -> Dict[str, str]:
        """Specialized extractor for HDFC bank (table-formatted fields)"""
        fields = {}
        
        # Card number: "Card No: 6529 15XX XXXX 0184"
        card_match = re.search(r'Card No[:\s]*[\dX\s]+?(\d{4})\s*(?:\n|$)', text, re.IGNORECASE)
        if card_match:
            fields['card_last_four'] = card_match.group(1)
        
        # Statement Date: "Statement Date:13/06/2025"
        stmt_match = re.search(r'Statement Date[:\s]*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if stmt_match:
            fields['statement_date'] = stmt_match.group(1)
        
        stmt_period_match = re.search(r'Statement Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if stmt_period_match:
         fields['statement_start'] = self.parse_indian_date(stmt_period_match.group(1))
         fields['statement_end'] = self.parse_indian_date(stmt_period_match.group(2))
        
        # Payment Due Date line: "03/07/2025 25,625.00 1,290.00"
        due_line_match = re.search(
            r'Payment Due Date\s+Total Dues\s+Minimum Amount Due\s*\n.*?\n.*?(\d{2}/\d{2}/\d{4})\s+([\d,]+\.[\d]+)\s+([\d,]+\.[\d]+)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if due_line_match:
            fields['payment_due_date'] = self.parse_indian_date(due_line_match.group(1))
            fields['total_balance'] = self.format_amount(due_line_match.group(2), '₹')
            fields['minimum_payment'] = self.format_amount(due_line_match.group(3), '₹')
        
        # Credit Limit line: "Credit Limit Available Credit Limit Available Cash Limit"
        # Next line: "25,000 0.00 0.00"
        credit_match = re.search(
            r'Credit Limit\s+Available Credit Limit\s+Available Cash Limit\s*\n\s*([\d,]+)\s+([\d,]+\.[\d]+)\s+([\d,]+\.[\d]+)',
            text,
            re.IGNORECASE
        )
        
        if credit_match:
            fields['credit_limit'] = self.format_amount(credit_match.group(1), '₹')
            fields['available_credit'] = self.format_amount(credit_match.group(2), '₹')
        
        return fields
    
    def extract_field(self, text: str, patterns: List[str], issuer: str = 'Unknown') -> str:
        """Extract field using regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                value = value.strip()
                
                # Convert Indian dates
                if issuer in ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']:
                    if re.match(r'\d{2}/\d{2}/\d{4}', value):
                        value = self.parse_indian_date(value) or value
                
                return value
        return 'Not found'
    
    def _extract_hdfc_transactions(self, text: str) -> List[Transaction]:
        transactions = []
        lines = text.split('\n')
        
        print(f"🔍 Processing HDFC transactions from {len(lines)} lines...")
        
        # Pattern for HDFC transaction lines: "13/05/2025 NAMAN VIPUL SHAH 447.52"
        # or "13/05/2025 ZEPTO MARKETPLACE PRIV 680.00"
        transaction_pattern = r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*$'
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Try to match transaction pattern
            match = re.match(transaction_pattern, line)
            if match:
                date = match.group(1)
                description = match.group(2).strip()
                amount = match.group(3)
                
                # Clean up description
                description = ' '.join(description.split())
                
                # Format amount with ₹ symbol
                formatted_amount = self.format_amount(amount, '₹')
                
                transactions.append(Transaction(
                    date=self.parse_indian_date(date),
                    description=description[:100],
                    amount=formatted_amount,
                    category=self.categorize_transaction(description)
                ))
                print(f"✅ Found transaction: {date} | {description[:30]} | {formatted_amount}")
        
        # If pattern matching fails, try line-by-line parsing as fallback
        if len(transactions) == 0:
            print("🔄 Using fallback HDFC transaction parsing...")
            current_txn = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for date at start of line
                date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
                
                if date_match:
                    # If we have a previous transaction, save it
                    if current_txn and current_txn.get('amount'):
                        transactions.append(Transaction(
                            date=self.parse_indian_date(current_txn['date']),
                            description=current_txn['description'][:100],
                            amount=self.format_amount(current_txn['amount'], '₹'),
                            category=self.categorize_transaction(current_txn['description'])
                        ))
                    
                    date = date_match.group(1)
                    rest = date_match.group(2).strip()
                    
                    # Try to find amount at the end
                    amount_match = re.search(r'([\d,]+\.\d{2})\s*$', rest)
                    
                    if amount_match:
                        amount = amount_match.group(1)
                        description = rest[:amount_match.start()].strip()
                    else:
                        description = rest
                        amount = None
                    
                    current_txn = {
                        'date': date,
                        'description': description,
                        'amount': amount
                    }
                
                elif current_txn:
                    # Continue building description or find amount
                    amount_match = re.search(r'([\d,]+\.\d{2})\s*$', line)
                    
                    if amount_match and not current_txn.get('amount'):
                        current_txn['amount'] = amount_match.group(1)
                        remaining = line[:amount_match.start()].strip()
                        if remaining:
                            current_txn['description'] += ' ' + remaining
                    else:
                        current_txn['description'] += ' ' + line
            
            # Don't forget the last transaction
            if current_txn and current_txn.get('amount'):
                transactions.append(Transaction(
                    date=self.parse_indian_date(current_txn['date']),
                    description=current_txn['description'][:100],
                    amount=self.format_amount(current_txn['amount'], '₹'),
                    category=self.categorize_transaction(current_txn['description'])
                ))
        
        print(f"🎯 Total HDFC transactions found: {len(transactions)}")
        return transactions

    def extract_transactions_from_text(self, text: str, issuer: str) -> List[Transaction]:
        """Extract transactions from text based on issuer - FIXED VERSION"""
        transactions = []
        currency = self.ISSUER_PATTERNS.get(issuer, {}).get('currency_symbol', '$')
        
        print(f"🔍 Extracting transactions for {issuer}...")
        if issuer == 'HDFC':
            print("🔍 Using HDFC-specific transaction extraction...")
            
            # Pattern for HDFC transaction lines with credit indicator
            hdfc_pattern = r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr)?\s*$'
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Try to match HDFC transaction pattern
                match = re.match(hdfc_pattern, line, re.IGNORECASE)
                if match:
                    date = match.group(1)
                    description = match.group(2).strip()
                    amount = match.group(3)
                    is_credit = match.group(4)  # This will be 'Cr' if it's a credit
                    
                    # Format amount with ₹ symbol and add CR indicator
                    formatted_amount = self.format_amount(amount, '₹')
                    if is_credit:
                        formatted_amount = f"{formatted_amount} CR"
                    
                    transactions.append(Transaction(
                        date=self.parse_indian_date(date),
                        description=description[:100],
                        amount=formatted_amount,
                        category=self.categorize_transaction(description)
                    ))
            
            print(f"✅ Found {len(transactions)} HDFC transactions")
            return transactions
        
        # Chase-specific pattern - handle table format
        if issuer == 'Chase':
            # Pattern for Chase: "01/03 STARBUCKS #2847 $5.67"
            chase_pattern = r'(\d{1,2}/\d{1,2})\s+([A-Z][^$\n]+?)\s+(\$\d+\.\d{2})'
            matches = re.finditer(chase_pattern, text, re.MULTILINE)
            
            for match in matches:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount = match.group(3)
                
                # Convert to full date (assuming current year)
                full_date = f"{date_str}/2024"
                
                transactions.append(Transaction(
                    date=full_date,
                    description=description,
                    amount=amount,
                    category=self.categorize_transaction(description)
                ))
            
            print(f"✅ Found {len(transactions)} Chase transactions")
        
        # Amex-specific pattern
        elif issuer == 'Amex':
            # Pattern for Amex: "01/03/2024 Starbucks $5.67" or "Jan 03, 2024 Starbucks $5.67"
            amex_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{4})\s+([A-Za-z][^$\n]+?)\s+(\$\d+\.\d{2})',
                r'([A-Za-z]+ \d{1,2}, \d{4})\s+([A-Za-z][^$\n]+?)\s+(\$\d+\.\d{2})'
            ]
            
            for pattern in amex_patterns:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount = match.group(3)
                    
                    transactions.append(Transaction(
                        date=date_str,
                        description=description,
                        amount=amount,
                        category=self.categorize_transaction(description)
                    ))
            
            print(f"✅ Found {len(transactions)} Amex transactions")
        
        # Citi-specific pattern  
        elif issuer == 'Citi':
            # Pattern for Citi: "01/03/2024 STARBUCKS $5.67"
            citi_pattern = r'(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z][^$\n]+?)\s+(\$\d+\.\d{2})'
            matches = re.finditer(citi_pattern, text, re.MULTILINE)
            
            for match in matches:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount = match.group(3)
                
                transactions.append(Transaction(
                    date=date_str,
                    description=description,
                    amount=amount,
                    category=self.categorize_transaction(description)
                ))
            
            print(f"✅ Found {len(transactions)} Citi transactions")
        
        # Generic fallback patterns for other banks
        else:
            patterns = [
                # Pattern for "MM/DD Description $Amount"
                r'(\d{1,2}/\d{1,2})\s+([A-Za-z][^$\n]+?)\s+(\$?[\d,]+\.\d{2})',
                # Pattern for "MM/DD/YYYY Description $Amount"  
                r'(\d{1,2}/\d{1,2}/\d{4})\s+([A-Za-z][^$\n]+?)\s+(\$?[\d,]+\.\d{2})',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount = match.group(3)
                    
                    # Ensure amount has dollar sign
                    if not amount.startswith('$'):
                        amount = f"${amount}"
                    
                    # Handle partial dates
                    if len(date_str.split('/')) == 2:  # MM/DD only
                        date_str = f"{date_str}/2024"  # Use statement year
                    
                    transactions.append(Transaction(
                        date=date_str,
                        description=description[:80],  # Limit description length
                        amount=amount,
                        category=self.categorize_transaction(description)
                    ))
            
            print(f"✅ Found {len(transactions)} transactions for {issuer}")
        
        # Remove duplicates
        unique_transactions = []
        seen = set()
        for txn in transactions:
            key = f"{txn.date}_{txn.description[:30]}_{txn.amount}"
            if key not in seen:
                seen.add(key)
                unique_transactions.append(txn)
        
        return unique_transactions
    
    def extract_transactions_camelot(self, pdf_path: str, issuer: str) -> List[Transaction]:
        if not CAMELOT_AVAILABLE:
            print("⚠️ Camelot not available")
            return []
        
        print("📊 Using Camelot for table extraction...")
        transactions = []
        
        try:
            # Try both lattice and stream for better results
            tables = camelot.read_pdf(
                str(pdf_path),
                pages='all',
                flavor='lattice',
                strip_text='\n',
                line_scale=40  # Better for HDFC tables
            )
            print(f"✅ Camelot loaded {len(tables)} tables")
            if len(tables) == 0:
                print("⚠️ Lattice failed, trying stream...")
                tables = camelot.read_pdf(
                    str(pdf_path), 
                    pages='all', 
                    flavor='stream',
                    edge_tol=50
                )
            
            print(f"  Found {len(tables)} tables with Camelot")
            
            currency = self.ISSUER_PATTERNS.get(issuer, {}).get('currency_symbol', '$')
            is_indian = issuer in ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']
            
            for table_idx, table in enumerate(tables):
                df = table.df
                print(f"  Table {table_idx+1}: {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Skip if table is too small
                if df.shape[0] <= 1 or df.shape[1] < 2:
                    continue
                    
                for idx, row in df.iterrows():
                    if idx == 0:  # Skip header row
                        continue
                    
                    row_data = [str(cell).strip() for cell in row if str(cell).strip() and str(cell).strip() != 'nan']
                    
                    if len(row_data) < 2:  # Need at least date and description
                        continue
                    
                    # Look for date in first few columns
                    for col_idx, cell in enumerate(row_data[:2]):
                        date_match = None
                        if is_indian:
                            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', cell)
                        else:
                            date_match = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{4})?)', cell)
                        
                        if date_match:
                            date = date_match.group(1)
                            
                            # Get description from next column
                            description = ""
                            if col_idx + 1 < len(row_data):
                                description = row_data[col_idx + 1]
                            
                            # Get amount from last column
                            amount = ""
                            if len(row_data) > 1:
                                amount_candidate = row_data[-1]
                                # Clean and validate amount
                                clean_amount = re.sub(r'[^\d.]', '', amount_candidate.replace(',', ''))
                                if clean_amount and re.match(r'^\d+\.?\d*$', clean_amount):
                                    amount = amount_candidate
                            
                            if description and amount:
                                if is_indian:
                                    date = self.parse_indian_date(date) or date
                                
                                # Format amount
                                formatted_amount = self.format_amount(amount, currency)
                                
                                transactions.append(Transaction(
                                    date=date,
                                    description=description.strip()[:80],
                                    amount=formatted_amount,
                                    category=self.categorize_transaction(description)
                                ))
                            break
            
            print(f"✅ Extracted {len(transactions)} transactions with Camelot")
            return transactions
            
        except Exception as e:
            print(f"  Camelot extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_transactions_tabula(self, pdf_path: str, issuer: str) -> List[Transaction]:
        """Extract transactions using Tabula"""
        if not TABULA_AVAILABLE:
            return []
        
        print("📊 Using Tabula for table extraction...")
        transactions = []
        
        try:
            dfs = tabula.read_pdf(str(pdf_path), pages='all', multiple_tables=True)
            
            print(f"  Found {len(dfs)} tables with Tabula")
            
            currency = self.ISSUER_PATTERNS.get(issuer, {}).get('currency_symbol', '$')
            is_indian = issuer in ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']
            
            for df in dfs:
                for idx, row in df.iterrows():
                    if idx == 0:  # Skip header row
                        continue
                        
                    row_values = [str(val).strip() for val in row.values if str(val).strip() and str(val).strip() != 'nan']
                    
                    for i, val in enumerate(row_values):
                        date_match = None
                        if is_indian:
                            date_match = re.search(r'\d{2}/\d{2}/\d{4}', val)
                        else:
                            date_match = re.search(r'\d{1,2}/\d{1,2}(?:/\d{4})?', val)
                        
                        if date_match:
                            date = date_match.group(0)
                            description = row_values[i+1] if i+1 < len(row_values) else ""
                            amount = row_values[-1] if row_values else ""
                            
                            if date and description and re.search(r'[\d,.]+', amount):
                                if is_indian:
                                    date = self.parse_indian_date(date) or date
                                
                                # Format amount
                                formatted_amount = self.format_amount(amount, currency)
                                
                                transactions.append(Transaction(
                                    date=date,
                                    description=description.strip()[:80],
                                    amount=formatted_amount,
                                    category=self.categorize_transaction(description)
                                ))
                            break
            
            print(f"✅ Extracted {len(transactions)} transactions with Tabula")
            return transactions
        
        except Exception as e:
            print(f"  Tabula extraction failed: {e}")
            return []
    
    def categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        description = description.lower()
        
        categories = {
            'Dining': [
                'restaurant', 'cafe', 'food', 'starbucks', 'mc donald', 'mcdonald',
                'kfc', 'domino', 'chipotle', 'panera', 'subway', 'wendys', 'taco bell',
                'swiggy', 'zomato', 'uber eats', 'dunzo', 'box8', 'faasos',
                'pizza', 'burger', 'dining', 'innovative food', 'kitchen', 'bistro',
                'eatery', 'coffee', 'bar'
            ],
            'Groceries': [
                'grocery', 'supermarket', 'market', 'walmart', 'target', 'costco', 
                'whole foods', 'trader joe', 'kroger', 'safeway',
                'zepto', 'blinkit', 'blink commerce', 'bigbasket', 'grofers', 'instamart', 
                'dmart', 'reliance', 'more', 'big bazaar', 'jiomart', 'fresh', 'vegetables'
            ],
            'Transportation': [
                'uber', 'lyft', 'gas', 'fuel', 'shell', 'exxon', 'chevron', 'bp',
                'ola', 'rapido', 'meru', 'petrol', 'hp petrol', 'bharat petroleum', 
                'indian oil', 'nayara', 'auto service', 'taxi', 'ato borivali',
                'satyashanti auto', 'parking', 'airline', 'delta', 'metro'
            ],
            'Shopping': [
                'amazon', 'best buy', 'apple store', 'target', 'macys', 'nordstrom',
                'flipkart', 'myntra', 'ajio', 'meesho', 'shoppers stop', 'lifestyle',
                'store', 'shop', 'mall', 'retail', 'snapdeal'
            ],
            'Entertainment': [
                'netflix', 'spotify', 'prime', 'hulu', 'disney', 'hotstar', 
                'youtube', 'apple music', 'movie', 'cinema', 'pvr', 'inox',
                'gaming', 'playstation', 'xbox', 'theater', 'zee5', 'sony liv'
            ],
            'Utilities': [
                'electric', 'electricity', 'water', 'internet', 'phone', 'mobile',
                'verizon', 'at&t', 'tmobile', 'airtel', 'jio', 'vodafone', 'bsnl',
                'bill payment', 'recharge', 'broadband', 'wifi'
            ],
            'Travel': [
                'airline', 'flight', 'hotel', 'booking', 'delta', 'united', 'hilton',
                'makemytrip', 'goibibo', 'yatra', 'cleartrip', 'oyo', 'airbnb',
                'irctc', 'railway', 'marriott', 'rental', 'resort', 'lodge'
            ],
            'Bills': [
                'paytm', 'phonepe', 'googlepay', 'gpay', 'bhim', 'payment gateway',
                'wallet', 'digital payment', 'cc payment', 'payzapp'
            ],
            'Fees': [
                'late fee', 'finance charge', 'annual fee', 'service charge',
                'gst', 'igst', 'cgst', 'sgst', 'surcharge', 'penalty',
                'interest', 'processing fee', 'waiver', 'finance charges', 'atm'
            ],
        }
        
        for category, keywords in categories.items():
            if any(keyword in description for keyword in keywords):
                return category
        
        return 'Other'
    
    def parse(self, pdf_path: str, use_advanced_methods: bool = True) -> Optional[CreditCardStatement]:
        """Parse credit card statement with universal support"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"\n{'='*70}")
        print(f"Parsing: {pdf_path}")
        print(f"{'='*70}\n")
        
        # Check if scanned
        is_scanned = self._is_scanned_pdf(pdf_path)
        
        # Extract text
        if is_scanned and OCR_AVAILABLE:
            text = self.extract_text_with_ocr(pdf_path)
            extraction_method = "OCR"
        else:
            with pdfplumber.open(pdf_path) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            extraction_method = "pdfplumber"
        
        # Detect issuer
        issuer = self.detect_issuer(text)
        print(f"📊 Detected issuer: {issuer}")
        
        patterns = self.ISSUER_PATTERNS.get(issuer, self.ISSUER_PATTERNS['Chase'])
        currency = patterns.get('currency_symbol', '$')
        
        # Extract fields - Special handling for HDFC
        if issuer == 'HDFC':
            hdfc_fields = self.extract_hdfc_fields_special(text)
            card_last_four = hdfc_fields.get('card_last_four', 'Not found')
            statement_date = hdfc_fields.get('statement_date', 'Not found')
            
            # SIMPLER BILLING CYCLE CALCULATION FOR HDFC
            if statement_date != 'Not found':
                try:
                    # Parse statement date (DD/MM/YYYY)
                    from datetime import datetime, timedelta
                    stmt_date_obj = datetime.strptime(statement_date, '%d/%m/%Y')
                    
                    # Billing end is statement date
                    statement_end = statement_date
                    
                    # Billing start is approximately 30 days before (standard billing cycle)
                    billing_start_obj = stmt_date_obj - timedelta(days=30)
                    statement_start = billing_start_obj.strftime('%d/%m/%Y')
                    
                except Exception as e:
                    print(f"⚠️ Error calculating HDFC billing cycle: {e}")
                    statement_start = 'Not found'
                    statement_end = statement_date
            else:
                statement_start = 'Not found'
                statement_end = 'Not found'
            
            due_date = hdfc_fields.get('payment_due_date', 'Not found')
            total_balance = hdfc_fields.get('total_balance', 'Not found')
            minimum_payment = hdfc_fields.get('minimum_payment', 'Not found')
            available_credit = hdfc_fields.get('available_credit', 'Not found')
            credit_limit = hdfc_fields.get('credit_limit', 'Not found')
        else:
            # Regular extraction for other banks
            card_last_four = self.extract_field(text, patterns.get('last_four', []), issuer)
            due_date = self.extract_field(text, patterns.get('due_date', []), issuer)
            total_balance = self.extract_field(text, patterns.get('total_due', []), issuer)
            minimum_payment = self.extract_field(text, patterns.get('minimum_payment', []), issuer)
            available_credit = self.extract_field(text, patterns.get('available_credit', []), issuer)
            credit_limit = self.extract_field(text, patterns.get('credit_limit', []), issuer)
            
            # Extract statement period
            period_patterns = patterns.get('statement_period', [])
            statement_start = self.extract_field(text, period_patterns, issuer)
            statement_end = 'Not found'
            
            for pattern in period_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and len(match.groups()) >= 2:
                    statement_start = match.group(1)
                    statement_end = match.group(2)
                    if issuer in ['ICICI', 'SBI', 'Axis', 'Kotak']:
                        statement_start = self.parse_indian_date(statement_start) or statement_start
                        statement_end = self.parse_indian_date(statement_end) or statement_end
                    break
            
            # Format amounts with currency
            if total_balance != 'Not found' and currency not in total_balance:
                total_balance = self.format_amount(total_balance, currency)
            if minimum_payment != 'Not found' and currency not in minimum_payment:
                minimum_payment = self.format_amount(minimum_payment, currency)
            if available_credit != 'Not found' and currency not in available_credit:
                available_credit = self.format_amount(available_credit, currency)
            if credit_limit != 'Not found' and currency not in credit_limit:
                credit_limit = self.format_amount(credit_limit, currency)
        
        # Extract transactions using multiple methods
        # Extract transactions using multiple methods
        all_transactions = []

        # For HDFC, prefer text-based extraction first since their tables are tricky
        if issuer == 'HDFC':
            print("📊 Using text-based extraction for HDFC...")
            all_transactions = self.extract_transactions_from_text(text, issuer)
            extraction_method += " (HDFC text)"
            
            # Still try Camelot as backup but don't rely on it
            if use_advanced_methods and CAMELOT_AVAILABLE and len(all_transactions) < 3:
                print("🔄 Trying Camelot as backup for HDFC...")
                camelot_trans = self.extract_transactions_camelot(pdf_path, issuer)
                if camelot_trans:
                    all_transactions.extend(camelot_trans)
                    extraction_method += " + Camelot backup"
        else:
            text_trans = self.extract_transactions_from_text(text, issuer)
            if text_trans:
                all_transactions.extend(text_trans)
            extraction_method += " (text)"
            # For other banks, use the original logic
            if use_advanced_methods:
                # Try Camelot first (best for structured tables)
                if CAMELOT_AVAILABLE:
                    camelot_trans = self.extract_transactions_camelot(pdf_path, issuer)
                    if camelot_trans:
                        all_transactions.extend(camelot_trans)
                        extraction_method += " + Camelot"
                
                # Try Tabula if Camelot didn't work
                if not all_transactions and TABULA_AVAILABLE:
                    tabula_trans = self.extract_transactions_tabula(pdf_path, issuer)
                    if tabula_trans:
                        all_transactions.extend(tabula_trans)
                        extraction_method += " + Tabula"

            # Fallback to text-based extraction
            if not all_transactions:
                print("📊 Using text-based extraction...")
                all_transactions = self.extract_transactions_from_text(text, issuer)
                extraction_method += " (text)"
        
        # Remove duplicates
        seen = set()
        unique_transactions = []
        for trans in all_transactions:
            key = f"{trans.date}_{trans.description[:30]}_{trans.amount}"
            if key not in seen:
                seen.add(key)
                unique_transactions.append(trans)
        
        print(f"✅ Extracted {len(unique_transactions)} unique transactions")
        print(f"📝 Extraction method: {extraction_method}\n")
        
        # Create statement object
        statement = CreditCardStatement(
            card_issuer=issuer,
            card_last_four=card_last_four,
            billing_cycle_start=statement_start,
            billing_cycle_end=statement_end,
            payment_due_date=due_date,
            total_balance=total_balance,
            minimum_payment=minimum_payment,
            available_credit=available_credit,
            transactions=unique_transactions,
            extraction_method=extraction_method,
            is_scanned=is_scanned,
            raw_text_preview=text[:500]
        )
        
        return statement


def main():
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python parser_unified.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    parser = UniversalCreditCardParser()
    
    try:
        statement = parser.parse(pdf_file, use_advanced_methods=True)
        
        if statement:
            result = statement.to_dict()
            
            print(f"{'='*70}")
            print("EXTRACTION RESULTS")
            print(f"{'='*70}")
            print(f"Method Used:          {result['extraction_method']}")
            print(f"Is Scanned PDF:       {result['is_scanned']}")
            print(f"Card Issuer:          {result['card_issuer']}")
            print(f"Card Last 4:          {result['card_last_four']}")
            print(f"Billing Cycle:        {result['billing_cycle_start']} to {result['billing_cycle_end']}")
            print(f"Payment Due:          {result['payment_due_date']}")
            print(f"Total Balance:        {result['total_balance']}")
            print(f"Minimum Payment:      {result['minimum_payment']}")
            print(f"Available Credit:     {result['available_credit']}")
            
            print(f"\n💳 TRANSACTIONS: {result['transaction_count']}")
            print('─'*70)
            
            for idx, txn in enumerate(result['transactions'][:20], 1):
                print(f"{idx:2d}. {txn['date']:12s} | {txn['description'][:40]:40s} | {txn['amount']:>12s} | {txn['category']}")
            
            if result['transaction_count'] > 20:
                print(f"\n... and {result['transaction_count'] - 20} more transactions")
            
            # Save to JSON
            output_dir = Path('results')
            output_dir.mkdir(exist_ok=True)
            
            output_file = output_dir / f"{Path(pdf_file).stem}_parsed_unified.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(statement.to_json())
            
            print(f"\n✅ Results saved to: {output_file}")
            print('='*70)
    
    except FileNotFoundError:
        print(f"❌ Error: PDF file not found: {pdf_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()