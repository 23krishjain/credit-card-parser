"""
Combined Bank Parsers - HDFC, AXIS, ICICI, IDFC, Syndicate
All regex-based parsers in one file with optimized patterns and transaction extraction
"""

import re
from typing import List
from parsers.base_parser import BaseParser, StatementData, Transaction


# ==================== HDFC BANK PARSER ====================
class HDFCParser(BaseParser):
    """Parser for HDFC Bank credit card statements"""
    
    def __init__(self):
        super().__init__("HDFC Bank")
        
        self.patterns = {
            "card_last_4": [
                r"Card\s+No[:\s]*\d{4}\s+\d{2}XX\s+XXXX\s+(\d{4})",
                r"Card\s+No[:\s]*[\dX\s]+(\d{4})",
                r"Card\s+ending\s+in[:\s]*(\d{4})",
            ],
            "statement_date": [
                r"Statement\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
                r"Statement\s+for.*?Statement\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
            ],
            "payment_due_date": [
                r"Payment\s+Due\s+Date\s+Total\s+Dues\s+Minimum\s+Amount\s+Due[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})",
                r"Payment\s+Due\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
            ],
            "total_amount_due": [
                r"Payment\s+Due\s+Date\s+Total\s+Dues\s+Minimum\s+Amount\s+Due[\s\S]{0,100}?\d{2}/\d{2}/\d{4}\s+([\d,]+\.[\d]{2})",
                r"Total\s+Dues[\s\S]{0,50}?([\d,]+\.[\d]{2})",
            ],
            "minimum_payment": [
                r"Minimum\s+Amount\s+Due[\s\S]{0,150}?\d{2}/\d{2}/\d{4}\s+[\d,]+\.[\d]{2}\s+([\d,]+\.[\d]{2})",
                r"Minimum\s+Amount\s+Due\s+([\d,]+\.[\d]{2})",
            ],
            "statement_period_start": [
                r"Statement\s+Period[:\s]*(\d{2}/\d{2}/\d{4})\s*to",
            ],
            "statement_period_end": [
                r"Statement\s+Period[:\s]*\d{2}/\d{2}/\d{4}\s*to\s*(\d{2}/\d{2}/\d{4})",
            ],
            "credit_limit": [
                r"Credit\s+Limit\s+Available\s+Credit\s+Limit[\s\S]{0,100}?([\d,]+(?:\.[\d]{2})?)",
                r"Credit\s+Limit[:\s]+([\d,]+(?:\.[\d]{2})?)",
            ],
            "available_credit": [
                r"Available\s+Credit\s+Limit[\s\S]{0,100}?([\d,]+\.[\d]{2})",
                r"Credit\s+Limit\s+Available\s+Credit\s+Limit[\s\S]{0,100}?[\d,]+\s+([\d,]+\.[\d]{2})",
            ],
        }
    
    def parse(self, text: str) -> StatementData:
        """Parse HDFC statement text"""
        
        statement = StatementData(
            bank_name=self.bank_name,
            extraction_method="regex_hdfc",
            raw_text_preview=text[:500]
        )
        
        statement.card_last_4 = self.extract_with_pattern(text, self.patterns["card_last_4"])
        statement.statement_date = self.extract_with_pattern(text, self.patterns["statement_date"])
        statement.payment_due_date = self.extract_with_pattern(text, self.patterns["payment_due_date"])
        
        total_due = self.extract_with_pattern(text, self.patterns["total_amount_due"])
        statement.total_amount_due = self.clean_amount(total_due) if total_due != "NOT_FOUND" else "NOT_FOUND"
        
        min_pay = self.extract_with_pattern(text, self.patterns["minimum_payment"])
        statement.minimum_payment = self.clean_amount(min_pay) if min_pay != "NOT_FOUND" else "NOT_FOUND"
        
        statement.statement_period_start = self.extract_with_pattern(text, self.patterns["statement_period_start"])
        statement.statement_period_end = self.extract_with_pattern(text, self.patterns["statement_period_end"])
        
        credit_lim = self.extract_with_pattern(text, self.patterns["credit_limit"])
        statement.credit_limit = self.clean_amount(credit_lim) if credit_lim != "NOT_FOUND" else "NOT_FOUND"
        
        avail_credit = self.extract_with_pattern(text, self.patterns["available_credit"])
        statement.available_credit = self.clean_amount(avail_credit) if avail_credit != "NOT_FOUND" else "NOT_FOUND"
        
        statement.transactions = self.extract_transactions(text)
        statement.calculate_confidence()
        
        return statement
    
    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions from HDFC statement"""
        transactions = []
        
        # Find Domestic Transactions section
        trans_section = re.search(r"(?:Domestic\s+Transactions|Transaction\s+Details)[\s\S]*", text, re.IGNORECASE)
        trans_text = trans_section.group(0) if trans_section else text
        
        # Split into lines and process each
        lines = trans_text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Must start with date DD/MM/YYYY
            if not re.match(r'^\d{2}/\d{2}/\d{4}', line):
                continue
            
            # Parse: DATE DESCRIPTION AMOUNT (optional Cr)
            # Look for date at start
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            if not date_match:
                continue
            
            date = date_match.group(1)
            rest = date_match.group(2)
            
            # Find amount at the end (number with 2 decimals, optional Cr)
            # Pattern: digits,digits.digits (optional Cr) at end
            amount_match = re.search(r'([\d,]+\.[\d]{2})\s*(Cr)?\s*$', rest)
            if not amount_match:
                continue
            
            amount = amount_match.group(1)
            is_credit = amount_match.group(2) == 'Cr'
            
            # Description is everything between date and amount
            description = rest[:amount_match.start()].strip()
            
            # Skip if description is too short or looks like a header
            if len(description) < 5:
                continue
            
            # Skip table headers
            if any(skip in description.upper() for skip in ['PAYMENT DUE DATE', 'TOTAL DUES', 'MINIMUM AMOUNT', 'CREDIT LIMIT']):
                continue
            
            # Clean amount
            cleaned_amount = self.clean_amount(amount)
            if not cleaned_amount:
                continue
            
            # Allow zero or very small amounts (like waivers)
            try:
                if float(cleaned_amount) < 0:
                    continue
            except:
                continue
            
            # Clean description - remove extra spaces
            description = re.sub(r'\s+', ' ', description)[:150]
            
            # Format amount with Cr indicator
            if is_credit:
                amount_display = f"₹{cleaned_amount} Cr"
            else:
                amount_display = f"₹{cleaned_amount}"
            
            transactions.append(Transaction(
                date=date,
                description=description,
                amount=amount_display,
                category=self.categorize_transaction(description)
            ))
        
        # Remove duplicates
        seen = set()
        unique_transactions = []
        for txn in transactions:
            key = f"{txn.date}_{txn.description[:40]}_{txn.amount}"
            if key not in seen:
                seen.add(key)
                unique_transactions.append(txn)
        
        return unique_transactions

# ==================== AXIS BANK PARSER ====================
class AxisParser(BaseParser):
    """Parser for Axis Bank credit card statements"""
    
    def __init__(self):
        super().__init__("Axis Bank")
        self.patterns = {
            "card_last_4": [
                r"Credit\s+Card\s+Number[:\s]*.*?[\*Xx]{4,}[\s\-]*(\d{4})",
                r"[\*Xx]{12,}[\s\-]*(\d{4})",
            ],
            "statement_date": [
                r"Statement\s+Generation\s+Date[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})",
                r"Generation\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
            ],
            "payment_due_date": [
                r"Payment\s+Due\s+Date[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})",
            ],
            "total_amount_due": [
                r"Total\s+Payment\s+Due\s+Minimum\s+Payment\s+Due[\s\S]{0,200}?([\d,]+\.[\d]{2})\s+Dr",
                r"Total\s+Payment\s+Due[:\s]*(?:Rs\.?\s*|₹\s*)?([\d,]+\.[\d]{2})",
            ],
            "minimum_payment": [
                r"Minimum\s+Payment\s+Due[\s\S]{0,200}?([\d,]+\.[\d]{2})\s+Dr",
            ],
            "statement_period_start": [
                r"Statement\s+Period[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})\s*[-–]",
                r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*\d{2}/\d{2}/\d{4}",
            ],
            "statement_period_end": [
                r"Statement\s+Period[\s\S]{0,100}?\d{2}/\d{2}/\d{4}\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
                r"\d{2}/\d{2}/\d{4}\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
            ],
            "credit_limit": [
                r"Credit\s+Limit\s+Available\s+Credit\s+Limit[\s\S]{0,150}?([\d,]+\.[\d]{2})",
                r"Credit\s+Limit[:\s]+([\d,]+\.[\d]{2})",
            ],
            "available_credit": [
                r"Available\s+Credit\s+Limit[\s\S]{0,150}?([\d,]+\.[\d]{2})",
                r"Credit\s+Limit\s+Available\s+Credit\s+Limit[\s\S]{0,150}?[\d,]+\.[\d]{2}\s+([\d,]+\.[\d]{2})",
            ],
        }
    
    def parse(self, text: str) -> StatementData:

        statement = StatementData(bank_name=self.bank_name, extraction_method="regex_axis")
        
        statement.card_last_4 = self.extract_with_pattern(text, self.patterns["card_last_4"])
        statement.statement_date = self.extract_with_pattern(text, self.patterns["statement_date"])
        statement.payment_due_date = self.extract_with_pattern(text, self.patterns["payment_due_date"])
        
        total = self.extract_with_pattern(text, self.patterns["total_amount_due"])
        statement.total_amount_due = self.clean_amount(total) if total != "NOT_FOUND" else "NOT_FOUND"
        
        min_pay = self.extract_with_pattern(text, self.patterns["minimum_payment"])
        statement.minimum_payment = self.clean_amount(min_pay) if min_pay != "NOT_FOUND" else "NOT_FOUND"
        
        statement.statement_period_start = self.extract_with_pattern(text, self.patterns["statement_period_start"])
        statement.statement_period_end = self.extract_with_pattern(text, self.patterns["statement_period_end"])
        
        credit = self.extract_with_pattern(text, self.patterns["credit_limit"])
        statement.credit_limit = self.clean_amount(credit) if credit != "NOT_FOUND" else "NOT_FOUND"
        
        avail = self.extract_with_pattern(text, self.patterns["available_credit"])
        statement.available_credit = self.clean_amount(avail) if avail != "NOT_FOUND" else "NOT_FOUND"
        
        # THIS LINE CALLS extract_transactions below
        statement.transactions = self.extract_transactions(text)
        
        statement.calculate_confidence()
        return statement
    

        """Extract transactions from AXIS statement - Table format"""
        print("🚨 AXIS extract_transactions CALLED!")
        transactions = []
        
        # Find Account Summary section
        summary_match = re.search(r'Account\s+Summary[\s\S]*?(?:EMI\s+BALANCES|\*{3,}|End\s+of\s+Statement|$)', text, re.IGNORECASE)
        trans_text = summary_match.group(0) if summary_match else text
        print(f"📋 Processing {len(trans_text)} chars from Account Summary")
        
        lines = trans_text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Must start with date DD/MM/YYYY
            if not re.match(r'^\d{2}/\d{2}/\d{4}', line):
                continue
            
            print(f"📅 Line {i}: {line[:120]}")
            
            # Split by whitespace
            parts = line.split()
            
            if len(parts) < 3:
                continue
            
            date = parts[0]
            
            # Last part should be Dr or Cr
            if parts[-1] not in ['Dr', 'Cr']:
                continue
            
            dr_cr = parts[-1]
            
            # Second to last should be amount (number with decimal)
            amount_str = parts[-2].replace(',', '')
            if not re.match(r'^\d+\.\d{2}$', amount_str):
                continue
            
            amount_str = parts[-2]  # Keep commas for cleaning
            
            # Description is everything between date and amount
            description = ' '.join(parts[1:-2])
            
            # Clean amount
            cleaned_amount = self.clean_amount(amount_str)
            if not cleaned_amount or float(cleaned_amount) < 1:
                continue
            
            # Skip credits
            if dr_cr == 'Cr':
                print(f"⏭️  Skipping credit: {description}")
                continue
            
            print(f"✅ Added: {date} | {description[:40]} | ₹{cleaned_amount}")
            
            transactions.append(Transaction(
                date=date,
                description=description[:100],
                amount=f"₹{cleaned_amount}",
                category=self.categorize_transaction(description)
            ))
        
        print(f"🎯 Total transactions extracted: {len(transactions)}")
        return transactions
    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions from AXIS statement - Table format"""
        transactions = []
        
        # Find where Account Summary starts
        summary_start = re.search(r'Account\s+Summary', text, re.IGNORECASE)
        if summary_start:
            trans_text = text[summary_start.start():]
        else:
            trans_text = text
        
        lines = trans_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Must start with date DD/MM/YYYY
            if not re.match(r'^\d{2}/\d{2}/\d{4}', line):
                continue
            
            # Split by whitespace
            parts = line.split()
            
            if len(parts) < 3:
                continue
            
            date = parts[0]
            
            # Last part should be Dr or Cr
            if parts[-1] not in ['Dr', 'Cr']:
                continue
            
            dr_cr = parts[-1]
            
            # Second to last should be amount
            amount_candidate = parts[-2].replace(',', '')
            if not re.match(r'^\d+\.\d{2}$', amount_candidate):
                continue
            
            amount_str = parts[-2]
            
            # Description is everything between date and amount
            description = ' '.join(parts[1:-2])
            
            # Clean amount
            cleaned_amount = self.clean_amount(amount_str)
            if not cleaned_amount or float(cleaned_amount) < 0.01:
                continue
            
            # Add Cr/Dr indicator to amount
            if dr_cr == 'Cr':
                amount_display = f"₹{cleaned_amount} Cr"
            else:
                amount_display = f"₹{cleaned_amount}"
            
            transactions.append(Transaction(
                date=date,
                description=description[:100],
                amount=amount_display,
                category=self.categorize_transaction(description)
            ))
        
        return transactions
# ==================== ICICI BANK PARSER ====================
class ICICIParser(BaseParser):
    """Parser for ICICI Bank credit card statements"""
    
    def __init__(self):
        super().__init__("ICICI Bank")
        self.patterns = {
            "card_last_4": [
                r"Card\s+Number[:\s]*.*?[\dXx]+(\d{4})",
                r"XXXX\s+(\d{4})",
            ],
            "statement_date": [
                r"Statement\s+Generation\s+Date[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})",
                r"Statement\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
            ],
            "payment_due_date": [
                r"Due\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
                r"Payment\s+Due\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
            ],
            "total_amount_due": [
                r"(?:Your\s+)?Total\s+Amount\s+Due[:\s]*(?:Rs\.?\s*|₹\s*)?([\d,]+\.?\d{0,2})",
                r"Total\s+Due[:\s]*(?:Rs\.?\s*|₹\s*)?([\d,]+\.?\d{0,2})",
            ],
            "minimum_payment": [
                r"Minimum\s+Amount\s+Due[:\s]*(?:Rs\.?\s*|₹\s*)?([\d,]+\.?\d{0,2})",
            ],
            "statement_period_start": [
                r"Statement\s+Period[\s\S]{0,100}?(\d{2}/\d{2}/\d{4})\s*[-–]",
                r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*\d{2}/\d{2}/\d{4}",  # First date in "14/08/2025 - 12/09/2025"
            ],
            "statement_period_end": [
                r"Statement\s+Period[\s\S]{0,100}?\d{2}/\d{2}/\d{4}\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
                r"\d{2}/\d{2}/\d{4}\s*[-–]\s*(\d{2}/\d{2}/\d{4})",  # Second date
            ],
            "credit_limit": [
                r"Credit\s+Limit[:\s]+([\d,]+\.?\d{0,2})",
            ],
            "available_credit": [
                r"Available\s+Credit\s+Limit[\s\S]{0,100}?([\d,]+\.[\d]{2})",
                r"Credit\s+Limit\s+Available\s+Credit\s+Limit[\s\S]{0,150}?[\d,]+\.[\d]{2}\s+([\d,]+\.[\d]{2})",
            ],
        }
    
    def parse(self, text: str) -> StatementData:
        statement = StatementData(bank_name=self.bank_name, extraction_method="regex_icici")
        
        statement.card_last_4 = self.extract_with_pattern(text, self.patterns["card_last_4"])
        statement.statement_date = self.extract_with_pattern(text, self.patterns["statement_date"])
        statement.payment_due_date = self.extract_with_pattern(text, self.patterns["payment_due_date"])
        
        total = self.extract_with_pattern(text, self.patterns["total_amount_due"])
        statement.total_amount_due = self.clean_amount(total) if total != "NOT_FOUND" else "NOT_FOUND"
        
        min_pay = self.extract_with_pattern(text, self.patterns["minimum_payment"])
        statement.minimum_payment = self.clean_amount(min_pay) if min_pay != "NOT_FOUND" else "NOT_FOUND"
        
        statement.statement_period_start = self.extract_with_pattern(text, self.patterns["statement_period_start"])
        statement.statement_period_end = self.extract_with_pattern(text, self.patterns["statement_period_end"])
        
        credit = self.extract_with_pattern(text, self.patterns["credit_limit"])
        statement.credit_limit = self.clean_amount(credit) if credit != "NOT_FOUND" else "NOT_FOUND"
        
        avail = self.extract_with_pattern(text, self.patterns["available_credit"])
        statement.available_credit = self.clean_amount(avail) if avail != "NOT_FOUND" else "NOT_FOUND"
        
        statement.transactions = self.extract_transactions(text)
        statement.calculate_confidence()
        
        return statement


# ==================== IDFC FIRST BANK PARSER ====================
class IDFCParser(BaseParser):
    """Parser for IDFC First Bank credit card statements"""
    
    def __init__(self):
        super().__init__("IDFC First Bank")
        self.patterns = {
            "card_last_4": [
                r"Card\s+Number[:\s]*[Xx]{4}\s+[Xx]{4}\s+[Xx]{4}\s+(\d{4})",
                r"Account\s+Number[:\s]*.*?[Xx]{4,}[\s\-]*(\d{4})",
            ],
            "statement_date": [
                r"Statement\s+Date[:\s]*(\d{2}/\d{2}/\d{4})",
                r"\d{2}/\d{2}/\d{4}\s*-\s*(\d{2}/\d{2}/\d{4})",
            ],
            "payment_due_date": [
                r"Payment\s+Due\s+Date[:\s\S]{0,100}?(\d{2}/\d{2}/\d{4})",
            ],
            "total_amount_due": [
                r"Total\s+Amount\s+Due[\s\S]{0,100}?[₹`]?\s*([\d,]+\.?[\d]{0,2})",
                r"STATEMENT\s+SUMMARY[\s\S]{1,300}?Total\s+Amount\s+Due[\s\S]{0,50}?[₹`]?\s*([\d,]+\.[\d]{2})",
            ],
            "minimum_payment": [
                r"Minimum\s+Amount\s+Due[\s\S]{0,100}?[₹`]?\s*([\d,]+\.?[\d]{0,2})",
            ],
            "statement_period_start": [
                r"Statement\s+Period[:\s]*From:\s*(\d{2}/\d{2}/\d{4})",
            ],
            "statement_period_end": [
                r"Statement\s+Period[:\s]*From:\s*\d{2}/\d{2}/\d{4}\s*To:\s*(\d{2}/\d{2}/\d{4})",
            ],
            "credit_limit": [
                r"Credit\s+Limit[:\s]+[₹`]?\s*([\d,]+(?:\.\d{2})?)",
            ],
            "available_credit": [
                r"Available\s+Credit\s+Limit[:\s]+[₹`]?\s*([\d,]+(?:\.\d{2})?)",
            ],
        }
    
    def parse(self, text: str) -> StatementData:
        statement = StatementData(bank_name=self.bank_name, extraction_method="regex_idfc")
        
        statement.card_last_4 = self.extract_with_pattern(text, self.patterns["card_last_4"])
        statement.statement_date = self.extract_with_pattern(text, self.patterns["statement_date"])
        statement.payment_due_date = self.extract_with_pattern(text, self.patterns["payment_due_date"])
        
        total = self.extract_with_pattern(text, self.patterns["total_amount_due"])
        statement.total_amount_due = self.clean_amount(total) if total != "NOT_FOUND" else "NOT_FOUND"
        
        min_pay = self.extract_with_pattern(text, self.patterns["minimum_payment"])
        statement.minimum_payment = self.clean_amount(min_pay) if min_pay != "NOT_FOUND" else "NOT_FOUND"
        
        statement.statement_period_start = self.extract_with_pattern(text, self.patterns["statement_period_start"])
        statement.statement_period_end = self.extract_with_pattern(text, self.patterns["statement_period_end"])
        
        credit = self.extract_with_pattern(text, self.patterns["credit_limit"])
        statement.credit_limit = self.clean_amount(credit) if credit != "NOT_FOUND" else "NOT_FOUND"
        
        avail = self.extract_with_pattern(text, self.patterns["available_credit"])
        statement.available_credit = self.clean_amount(avail) if avail != "NOT_FOUND" else "NOT_FOUND"
        
        statement.transactions = self.extract_transactions(text)
        statement.calculate_confidence()
        
        return statement


# ==================== SYNDICATE BANK PARSER ====================
class SyndicateParser(BaseParser):
    """Parser for Syndicate Bank credit card statements"""
    
    def __init__(self):
        super().__init__("Syndicate Bank")
        self.patterns = {
            "card_last_4": [
                r"Credit\s+Card\s+No[:\s]*.*?(\d{4})",
                r"Card\s+Account\s+Number[\s\S]{0,50}?(\d{4})",
            ],
            "statement_date": [
                r"Statement\s+Date[:\s]*(\d{2}\s[A-Z]{3}\s\d{4})",
            ],
            "payment_due_date": [
                r"Payment\s+Due\s+Date[:\s]*(\d{2}\s[A-Z]{3}\s\d{4})",
            ],
            "total_amount_due": [
                r"Total\s+Payment\s+Due[:\s]+([\d,]+\.?\d{0,2})",
            ],
            "minimum_payment": [
                r"Minimum\s+Payment\s+Due[:\s]+([\d,]+\.?\d{0,2})",
            ],
            "credit_limit": [
                r"Credit\s+Limit[:\s]+([\d,]+\.?\d{0,2})",
            ],
            "available_credit": [
                r"Available\s+Credit\s+Limit[:\s]+([\d,]+\.?\d{0,2})",
            ],
        }
    
    def parse(self, text: str) -> StatementData:
        statement = StatementData(bank_name=self.bank_name, extraction_method="regex_syndicate")
        
        statement.card_last_4 = self.extract_with_pattern(text, self.patterns["card_last_4"])
        statement.statement_date = self.extract_with_pattern(text, self.patterns["statement_date"])
        statement.payment_due_date = self.extract_with_pattern(text, self.patterns["payment_due_date"])
        
        total = self.extract_with_pattern(text, self.patterns["total_amount_due"])
        statement.total_amount_due = self.clean_amount(total) if total != "NOT_FOUND" else "NOT_FOUND"
        
        min_pay = self.extract_with_pattern(text, self.patterns["minimum_payment"])
        statement.minimum_payment = self.clean_amount(min_pay) if min_pay != "NOT_FOUND" else "NOT_FOUND"
        
        credit = self.extract_with_pattern(text, self.patterns["credit_limit"])
        statement.credit_limit = self.clean_amount(credit) if credit != "NOT_FOUND" else "NOT_FOUND"
        
        avail = self.extract_with_pattern(text, self.patterns["available_credit"])
        statement.available_credit = self.clean_amount(avail) if avail != "NOT_FOUND" else "NOT_FOUND"
        
        statement.transactions = self.extract_transactions(text)
        statement.calculate_confidence()
        
        return statement