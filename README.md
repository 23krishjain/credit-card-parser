# Universal Credit Card Statement Parser 💳

A powerful, universal parser that extracts transactions and key details from credit card statements of 10+ major banks — both Indian and international. Built with a modular architecture and a user-friendly Streamlit interface.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/1399040c-0e6b-42e8-b1d2-e4e8b2d344a0" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/b90190dd-3139-4486-9605-a89feba0d579" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/0a38af1b-48be-42bc-a99f-32c719b808d2" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/f90a31ba-95de-4651-a032-b024850b68b0" />



---

## 🏦 Supported Banks

### 🇮🇳 Indian Banks
- HDFC Bank
- ICICI Bank
- State Bank of India (SBI)
- Axis Bank
- Kotak Mahindra Bank

### 🌍 International Banks
- Chase
- American Express (Amex)
- Citibank
- Discover
- Bank of America

---

## 🚀 Features
- **Automatic Bank Detection** — Identifies the bank from PDF content
- **Smart Transaction Extraction** — Uses pdfplumber, Camelot, Tabula, and OCR for scanned PDFs
- **Transaction Categorization** — Auto-classifies spending patterns
- **Scanned PDF Support** — Converts image-based statements to text using OCR
- **Multiple Export Formats** — Clean JSON output for easy integration
- **Interactive Web Interface** — Built with Streamlit

---

### 🧩 Project Structure
```text
credit-card-parser/
├── parser_unified.py       # Core parser logic
├── unified_app.py          # Streamlit web app
├── requirements.txt        # Dependencies list
├── runtime.txt             # Python runtime version
├── Dockerfile              # Dockerfile for Render deployment
├── render-build.sh         # (Optional) System installs if needed
├── sample_statements/      # Sample PDF statements for testing
└── results/                # Output directory for parsed results
````

---

## ⚙️ Installation & Setup (Local)

### 1. Clone the repository

```bash
git clone https://github.com/23krishjain/credit-card-parser.git
cd credit-card-parser
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit app

```bash
streamlit run unified_app.py
```

---

## 🧠 How It Works

1. Upload your credit card statement (PDF) through the web app.
2. The system automatically detects the bank and statement type.
3. It extracts, cleans, and structures transactions into a unified JSON format.
4. The parsed data is displayed and saved in the `results/` directory.

---

## 🧾 Output Example (JSON)

```json
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
```

---

## 🧪 Sample Test Files

Use the PDFs in the `sample_statements/` folder to test the parser:

* `amex_statement.pdf`
* `chase_statement.pdf`
* `citi_statement.pdf`
* `testCase01.pdf` (HDFC)

---

## 📦 Deployment on Render (Docker)

Ensure the following files are present:

* `Dockerfile`
* `.dockerignore`
* `render-build.sh`

### Steps:

1. Commit and push your code to GitHub.
2. On Render:

   * Create a new → Web Service → Docker
   * Connect your repo → Select the main branch
   * Build & deploy
3. Access your app at `https://<your-app-name>.onrender.com`

### Build Command (Render):

```bash
bash render-build.sh && pip install -r requirements.txt
```

### Start Command:

```bash
streamlit run unified_app.py --server.port $PORT --server.address 0.0.0.0
```

💡 Tip: Streamlit apps on Render should use `/tmp` for temporary file storage.

---

## 🔮 Future Improvements

* Add support for more international banks
* Export transactions to CSV / Excel formats
* Integrate with budgeting dashboards
* Improve OCR accuracy using AI-based models

---

## 👨‍💻 Author

**Krish Jain**
📧 [23krishjain@gmail.com](mailto:23krishjain@gmail.com)

```

