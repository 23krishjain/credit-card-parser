Universal Credit Card Statement Parser

A powerful, universal parser that extracts transactions and key details from credit card statements of 10+ major banks — both Indian and international.
Built with a modular architecture and a user-friendly Streamlit interface.

🏦 Supported Banks
🇮🇳 Indian Banks

HDFC Bank

ICICI Bank

State Bank of India (SBI)

Axis Bank

Kotak Mahindra Bank

🌍 International Banks

Chase

American Express (Amex)

Citibank

Discover

Bank of America

🚀 Features

Automatic Bank Detection — Identifies the bank from the PDF content

Smart Transaction Extraction — Extracts data using pdfplumber, Camelot, Tabula, and OCR (for scanned PDFs)

Transaction Categorization — Auto-classifies spending patterns

Scanned PDF Support — Converts image-based statements to text using OCR

Multiple Export Formats — Clean JSON output for easy integration

Interactive Web Interface — Built with Streamlit for simple, intuitive use

🧩 Project Structure
credit-card-parser/
├── parser_unified.py        # Main parser logic (core library)
├── unified_app.py           # Streamlit web app
├── requirements.txt         # Dependencies list
├── sample_statements/       # Sample test PDFs
│   ├── testCase01.pdf       # HDFC Bank sample
│   ├── chase_statement.pdf  # Chase Bank sample
│   ├── amex_statement.pdf   # Amex sample
│   └── citi_statement.pdf   # Citibank sample
└── results/                 # Output directory for parsed results

⚙️ Installation & Setup

Clone the repository

git clone https://github.com/23krishjain/credit-card-parser.git
cd credit-card-parser


Create and activate a virtual environment (recommended)

python -m venv venv
source venv/bin/activate      # For Mac/Linux
venv\Scripts\activate         # For Windows


Install dependencies

pip install -r requirements.txt


Run the Streamlit app

streamlit run unified_app.py

📦 Requirements
# Core Application
streamlit==1.28.0
pandas==2.0.3

# PDF Text Extraction
pdfplumber==0.10.0

# Advanced Table Extraction
camelot-py[base]==0.10.1
tabula-py==2.7.0

# OCR for Scanned PDFs
pytesseract==0.3.10
pdf2image==1.16.3
pillow==10.0.0

# File Upload Support
python-multipart==0.0.6

🧠 How It Works

Upload your credit card statement (PDF) through the web app.

The system automatically detects the bank and statement type.

It extracts, cleans, and structures transactions into a unified JSON format.

The parsed data is displayed and saved in the results/ directory.

🧾 Output Example (JSON)
{
  "bank": "HDFC Bank",
  "statement_period": "01 Jun 2024 - 30 Jun 2024",
  "transactions": [
    {
      "date": "2024-06-05",
      "description": "Amazon Purchase",
      "amount": 2499.00,
      "category": "Shopping"
    },
    {
      "date": "2024-06-10",
      "description": "Uber Ride",
      "amount": 312.50,
      "category": "Transport"
    }
  ],
  "total_due": 4811.50
}

🧪 Sample Test Files

You can test the parser using sample statements in the sample_statements/ folder:

amex_statement.pdf

chase_statement.pdf

citi_statement.pdf

testCase01.pdf (HDFC)

💡 Future Improvements

Add more international banks

Export to CSV / Excel formats

Integrate with budgeting dashboards

Improve OCR accuracy with AI-based models

🧑‍💻 Author

Krish Jain
📧 23krishjain@gmail.com
💼 23krishjain