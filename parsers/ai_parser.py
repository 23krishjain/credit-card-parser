# AI parser
# Copy content from artifact
"""
AI-powered parser using Google Gemini
Used as fallback when regex parsers fail or for unsupported banks
"""

import json
import requests
from typing import Dict, Any, Optional
from .base_parser import BaseParser, StatementData, Transaction
from config import GEMINI_API_KEY, GEMINI_API_URL, AI_PARSER_CONFIG


class GeminiAIParser(BaseParser):
    """
    AI-powered parser using Google Gemini
    Extracts structured data from any credit card statement
    """
    
    def __init__(self, bank_name: str = "Unknown"):
        super().__init__(bank_name)
        self.api_key = GEMINI_API_KEY
        self.api_url = f"{GEMINI_API_URL}?key={self.api_key}"
    
    def parse(self, text: str, bank_name: Optional[str] = None) -> StatementData:
        """
        Parse statement using Gemini AI
        
        Args:
            text: Extracted PDF text
            bank_name: Optional bank name for context
            
        Returns:
            StatementData with extracted information
        """
        if not self.api_key or self.api_key == "":
            return self._create_failed_statement("Gemini API key not configured")
        
        # Truncate text if too long (Gemini has token limits)
        text_to_send = text[:15000] if len(text) > 15000 else text
        
        try:
            extracted_data = self._call_gemini_api(text_to_send, bank_name)
            
            if extracted_data.get("status") == "success":
                return self._create_statement_from_ai(extracted_data, text)
            else:
                return self._create_failed_statement(extracted_data.get("error", "AI extraction failed"))
        
        except Exception as e:
            return self._create_failed_statement(f"AI Parser error: {str(e)}")
    
    def _call_gemini_api(self, text: str, bank_name: Optional[str]) -> Dict[str, Any]:
        """Call Gemini API with structured extraction prompt"""
        
        # Define response schema for structured output
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "bank_name": {"type": "STRING"},
                "card_last_4": {"type": "STRING"},
                "statement_date": {"type": "STRING"},
                "payment_due_date": {"type": "STRING"},
                "total_amount_due": {"type": "STRING"},
                "minimum_payment": {"type": "STRING"},
                "statement_period_start": {"type": "STRING"},
                "statement_period_end": {"type": "STRING"},
                "credit_limit": {"type": "STRING"},
                "available_credit": {"type": "STRING"},
            },
            "required": [
                "bank_name", "card_last_4", "statement_date", 
                "payment_due_date", "total_amount_due", "minimum_payment"
            ]
        }
        
        # Craft system instruction
        system_prompt = f"""You are an expert financial document parser specializing in credit card statements.

Your task is to extract EXACTLY these fields from the credit card statement text:
1. bank_name - The issuing bank (e.g., "HDFC Bank", "Axis Bank")
2. card_last_4 - Last 4 digits of card number (e.g., "1234")
3. statement_date - Statement generation date (format: DD/MM/YYYY)
4. payment_due_date - Payment due date (format: DD/MM/YYYY)
5. total_amount_due - Total amount to be paid (clean number, e.g., "25625.00")
6. minimum_payment - Minimum payment required (clean number, e.g., "1290.00")
7. statement_period_start - Billing period start date (format: DD/MM/YYYY)
8. statement_period_end - Billing period end date (format: DD/MM/YYYY)
9. credit_limit - Total credit limit (clean number)
10. available_credit - Available credit (clean number)

CRITICAL RULES:
- Return "NOT_FOUND" if a field cannot be found
- For amounts: remove currency symbols (₹, Rs, $), remove commas, keep only digits and decimal point
- For total_amount_due: NEVER return zero or negative values - find the actual outstanding balance
- For dates: use DD/MM/YYYY format
- For card_last_4: extract ONLY the last 4 digits, nothing else
- Bank name hint: {bank_name if bank_name else "detect from statement"}

Return ONLY valid JSON matching the schema. No explanations."""

        user_query = f"Extract credit card statement data from this text:\n\n{text}"
        
        # Prepare API payload
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
                "temperature": AI_PARSER_CONFIG["temperature"],
                "topP": AI_PARSER_CONFIG["top_p"],
                "maxOutputTokens": AI_PARSER_CONFIG["max_tokens"],
            },
        }
        
        # Make API request
        response = requests.post(
            self.api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        
        if result.get("candidates"):
            json_text = result["candidates"][0]["content"]["parts"][0]["text"]
            extracted_data = json.loads(json_text)
            extracted_data["status"] = "success"
            return extracted_data
        
        return {"status": "failed", "error": "Empty response from AI"}
    
    def _create_statement_from_ai(self, ai_data: Dict[str, Any], full_text: str) -> StatementData:
        """Convert AI response to StatementData object"""
        
        # Clean amounts
        total_due = self.clean_amount(ai_data.get("total_amount_due", "NOT_FOUND"))
        min_pay = self.clean_amount(ai_data.get("minimum_payment", "NOT_FOUND"))
        credit_lim = self.clean_amount(ai_data.get("credit_limit", "NOT_FOUND"))
        avail_credit = self.clean_amount(ai_data.get("available_credit", "NOT_FOUND"))
        
        statement = StatementData(
            bank_name=ai_data.get("bank_name", "Unknown Bank"),
            card_last_4=ai_data.get("card_last_4", "NOT_FOUND"),
            statement_date=ai_data.get("statement_date", "NOT_FOUND"),
            payment_due_date=ai_data.get("payment_due_date", "NOT_FOUND"),
            total_amount_due=total_due if total_due else "NOT_FOUND",
            minimum_payment=min_pay if min_pay else "NOT_FOUND",
            statement_period_start=ai_data.get("statement_period_start", "NOT_FOUND"),
            statement_period_end=ai_data.get("statement_period_end", "NOT_FOUND"),
            credit_limit=credit_lim if credit_lim else "NOT_FOUND",
            available_credit=avail_credit if avail_credit else "NOT_FOUND",
            extraction_method="ai_gemini",
            raw_text_preview=full_text[:500]
        )
        
        # Try to extract transactions
        statement.transactions = self.extract_transactions(full_text)
        
        # Calculate confidence
        statement.calculate_confidence()
        
        return statement
    
    def _create_failed_statement(self, error_message: str) -> StatementData:
        """Create a statement object for failed parsing"""
        statement = StatementData(
            bank_name="Unknown",
            extraction_method="ai_gemini_failed",
        )
        statement.errors.append(error_message)
        return statement
    
    def enhance_regex_results(self, statement: StatementData, full_text: str) -> StatementData:
        """
        Enhance incomplete regex results with AI
        Only extracts missing fields, preserves regex-found data
        """
        if not self.api_key or self.api_key == "":
            return statement
        
        # Check which fields are missing
        missing_fields = []
        if statement.card_last_4 == "NOT_FOUND":
            missing_fields.append("card_last_4")
        if statement.total_amount_due == "NOT_FOUND":
            missing_fields.append("total_amount_due")
        if statement.payment_due_date == "NOT_FOUND":
            missing_fields.append("payment_due_date")
        if statement.minimum_payment == "NOT_FOUND":
            missing_fields.append("minimum_payment")
        
        # If nothing is missing, return as is
        if not missing_fields:
            return statement
        
        # Use AI to fill missing fields
        try:
            ai_data = self._call_gemini_api(full_text[:15000], statement.bank_name)
            
            if ai_data.get("status") == "success":
                # Only update missing fields
                for field in missing_fields:
                    if field in ai_data and ai_data[field] != "NOT_FOUND":
                        value = ai_data[field]
                        
                        # Clean amounts
                        if field in ["total_amount_due", "minimum_payment", "credit_limit", "available_credit"]:
                            value = self.clean_amount(value)
                        
                        setattr(statement, field, value)
                
                # Update extraction method to indicate AI enhancement
                statement.extraction_method = f"{statement.extraction_method}+ai_enhanced"
        
        except Exception as e:
            statement.errors.append(f"AI enhancement failed: {str(e)}")
        
        # Recalculate confidence
        statement.calculate_confidence()
        
        return statement