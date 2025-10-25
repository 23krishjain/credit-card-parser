# Main parser
# Copy content from artifact
"""
Unified Credit Card Statement Parser - Main Orchestrator
Automatically routes to regex parser or AI fallback based on bank detection
"""

import io
from typing import Union, Dict, Any
from pathlib import Path

# Import utilities
from utils.text_extractor import PDFTextExtractor
from utils.bank_detector import BankDetector

# Import parsers
from parsers.regex.combined_parsers import (
    HDFCParser, AxisParser, ICICIParser, IDFCParser, SyndicateParser
)
from parsers.ai_parser import GeminiAIParser
from parsers.base_parser import StatementData

from config import REGEX_SUPPORTED_BANKS, GEMINI_API_KEY


class UnifiedCreditCardParser:
    """
    Main parser orchestrator
    - Detects bank automatically
    - Routes to appropriate regex parser
    - Falls back to AI for unsupported banks or low-confidence results
    """
    
    def __init__(self):
        # Initialize all regex parsers
        self.regex_parsers = {
            "hdfc": HDFCParser(),
            "axis": AxisParser(),
            "icici": ICICIParser(),
            "idfc": IDFCParser(),
            "syndicate": SyndicateParser(),
        }
        
        # Initialize AI parser
        self.ai_parser = GeminiAIParser()
        
        # Text extractor
        self.text_extractor = PDFTextExtractor()
        
        # Bank detector
        self.bank_detector = BankDetector()
    
    def parse(self, pdf_file: Union[str, io.BytesIO], force_ai: bool = False) -> Dict[str, Any]:
        """
        Main parsing method
        
        Args:
            pdf_file: PDF file path or BytesIO object
            force_ai: If True, skip regex and use AI directly
            
        Returns:
            Dictionary with parsed statement data
        """
        try:
            # Step 1: Extract text from PDF
            print("📄 Extracting text from PDF...")
            full_text = self.text_extractor.extract(pdf_file)
            
            if not full_text or len(full_text.strip()) < 100:
                return {
                    "status": "FAILED",
                    "reason": "Could not extract sufficient text from PDF",
                    "extraction_method": "none"
                }
            
            print(f"✅ Extracted {len(full_text)} characters")
            
            # Step 2: Detect bank
            print("🔍 Detecting bank...")
            detected_bank = self.bank_detector.detect(full_text)
            print(f"🏦 Detected: {detected_bank or 'Unknown'}")
            
            # Step 3: Choose parsing strategy
            if force_ai or not detected_bank or detected_bank not in REGEX_SUPPORTED_BANKS:
                # Use AI parser
                print("🤖 Using AI parser...")
                statement = self.ai_parser.parse(full_text, detected_bank)
            else:
                # Use regex parser
                print(f"⚡ Using regex parser for {detected_bank.upper()}...")
                statement = self.regex_parsers[detected_bank].parse(full_text)
                
                # Check confidence - enhance with AI if needed
                if (detected_bank == "axis" and len(statement.transactions) == 0) or statement.confidence_score < 0.8:
                    if GEMINI_API_KEY:
                        print(f"⚠️ Low confidence or no transactions, enhancing with AI...")
                        statement = self.ai_parser.enhance_regex_results(statement, full_text)
            
            # Step 4: Convert to dict and return
            result = statement.to_dict()
            result["status"] = "SUCCESS" if statement.is_valid() else "PARTIAL"
            
            print(f"✅ Parsing complete! Confidence: {statement.confidence_score:.2%}")
            print(f"📊 Method: {statement.extraction_method}")
            
            return result
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "status": "FAILED",
                "reason": str(e),
                "extraction_method": "error"
            }
    
    def parse_batch(self, pdf_files: list) -> list:
        """Parse multiple PDFs"""
        results = []
        for pdf_file in pdf_files:
            print(f"\n{'='*70}")
            print(f"Processing: {pdf_file}")
            print(f"{'='*70}")
            result = self.parse(pdf_file)
            results.append(result)
        return results


# ==================== STANDALONE USAGE ====================
def main():
    """Command-line usage example"""
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python unified_parser.py <pdf_file> [--ai]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    force_ai = "--ai" in sys.argv
    
    parser = UnifiedCreditCardParser()
    result = parser.parse(pdf_path, force_ai=force_ai)
    
    # Pretty print result
    print("\n" + "="*70)
    print("EXTRACTION RESULTS")
    print("="*70)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()