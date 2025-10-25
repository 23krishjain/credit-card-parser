"""
Configuration file for credit card parser
Contains bank identifiers, API settings, and field mappings
"""
from dotenv import load_dotenv
load_dotenv()
import os
from typing import Dict, List


# ==================== API CONFIGURATION ====================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash-exp"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# ==================== BANK IDENTIFIERS ====================
BANK_IDENTIFIERS = {
    "hdfc": ["HDFC BANK", "HDFC", "HDFC CREDIT CARD"],
    "axis": ["AXIS BANK", "AXIS", "FLIPKART AXIS"],
    "icici": ["ICICI BANK", "ICICI", "ICICI CREDIT"],
    "idfc": ["IDFC FIRST BANK", "IDFC FIRST", "IDFC BANK", "IDFC"],
    "syndicate": ["SYNDICATE BANK", "CANARA BANK", "GLOBAL CREDIT CARD"],
}

# ==================== SUPPORTED REGEX BANKS ====================
REGEX_SUPPORTED_BANKS = ["hdfc", "axis", "icici", "idfc", "syndicate"]

# ==================== STANDARD OUTPUT FIELDS ====================
REQUIRED_FIELDS = [
    "bank_name",
    "card_last_4",
    "statement_date",
    "payment_due_date",
    "total_amount_due",
    "minimum_payment",
    "statement_period_start",
    "statement_period_end",
    "credit_limit",
    "available_credit",
]

# ==================== DATE FORMATS ====================
DATE_FORMATS = [
    "%d/%m/%Y",  # 25/12/2024
    "%d-%m-%Y",  # 25-12-2024
    "%Y-%m-%d",  # 2024-12-25
    "%d %b %Y",  # 25 Dec 2024
    "%d %B %Y",  # 25 December 2024
    "%b %d, %Y", # Dec 25, 2024
]

# ==================== AMOUNT CLEANING PATTERNS ====================
CURRENCY_SYMBOLS = ["₹", "Rs.", "Rs", "INR", "$", "USD"]

# ==================== AI PARSER SETTINGS ====================
AI_PARSER_CONFIG = {
    "temperature": 0.0,
    "top_p": 0.95,
    "max_tokens": 2048,
    "response_mime_type": "application/json",
}

# ==================== EXTRACTION CONFIDENCE THRESHOLDS ====================
CONFIDENCE_THRESHOLDS = {
    "high": 0.9,    # All required fields found
    "medium": 0.7,  # Most fields found
    "low": 0.5,     # Some fields found
}

# ==================== VALIDATION RULES ====================
VALIDATION_RULES = {
    "card_last_4": r"^\d{4}$",
    "statement_date": r"^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}$",
    "amount": r"^[\d,]+\.?\d{0,2}$",
}