import re
import pdfplumber
import io
from typing import Union


class PDFTextExtractor:
    """Extracts text from PDF files"""
    
    @staticmethod
    def extract(pdf_file: Union[str, io.BytesIO]) -> str:
        """
        Extract text from PDF
        
        Args:
            pdf_file: File path or BytesIO object
            
        Returns:
            Extracted text as string
        """
        try:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Normalize line breaks
                        cleaned = re.sub(r'[\r\n]+', '\n', page_text)
                        full_text += cleaned + "\n"
                
                return full_text
        
        except Exception as e:
            raise Exception(f"PDF text extraction failed: {str(e)}")
