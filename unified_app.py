import streamlit as st
import pandas as pd
import json
import tempfile
import os
from pathlib import Path
import base64
from datetime import datetime

# Import the parser class
from parser_unified import UniversalCreditCardParser, CreditCardStatement

# Configure the page
st.set_page_config(
    page_title="Universal Credit Card Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .transaction-table {
        font-size: 0.9em;
    }
    .bank-logo {
        font-size: 1.5em;
        font-weight: bold;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    .hdfc { background-color: #004c8c; color: white; }
    .icici { background-color: #ff6f00; color: white; }
    .sbi { background-color: #4caf50; color: white; }
    .axis { background-color: #951b81; color: white; }
    .kotak { background-color: #00a0e3; color: white; }
    .chase { background-color: #117aca; color: white; }
    .amex { background-color: #0070ba; color: white; }
    .citi { background-color: #0066a1; color: white; }
    .discover { background-color: #ff6000; color: white; }
    .bofa { background-color: #de1d3e; color: white; }
</style>
""", unsafe_allow_html=True)

class UnifiedCreditCardApp:
    def __init__(self):
        self.parser = UniversalCreditCardParser()
        self.supported_banks = [
            "HDFC", "ICICI", "SBI", "Axis", "Kotak", 
            "Chase", "Amex", "Citi", "Discover", "BankOfAmerica"
        ]
    
    def get_bank_style(self, bank_name):
        """Get CSS class for bank styling"""
        bank_classes = {
            'HDFC': 'hdfc',
            'ICICI': 'icici', 
            'SBI': 'sbi',
            'Axis': 'axis',
            'Kotak': 'kotak',
            'Chase': 'chase',
            'Amex': 'amex',
            'Citi': 'citi',
            'Discover': 'discover',
            'BankOfAmerica': 'bofa'
        }
        return bank_classes.get(bank_name, 'info-box')
    
    def display_bank_logo(self, bank_name):
        """Display bank logo with styling"""
        style_class = self.get_bank_style(bank_name)
        st.markdown(f'<div class="bank-logo {style_class}">{bank_name}</div>', unsafe_allow_html=True)
    
    def display_statement_summary(self, statement):
        """Display statement summary in a nice format"""
        st.markdown("### 📊 Statement Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Card Issuer", statement.card_issuer)
            st.metric("Billing Start", statement.billing_cycle_start)
        
        with col2:
            st.metric("Last 4 Digits", statement.card_last_four)
            st.metric("Billing End", statement.billing_cycle_end)
        
        with col3:
            st.metric("Payment Due", statement.payment_due_date)
            st.metric("Available Credit", statement.available_credit)
        
        with col4:
            st.metric("Total Balance", statement.total_balance)
            st.metric("Min Payment", statement.minimum_payment)
    
    def display_transactions(self, statement):
        """Display transactions in a table"""
        st.markdown(f"### 💳 Transactions ({len(statement.transactions)})")
        
        if not statement.transactions:
            st.warning("No transactions found in the statement")
            return
        
        # Create DataFrame for display
        transactions_data = []
        for txn in statement.transactions:
            transactions_data.append({
                'Date': txn.date,
                'Description': txn.description,
                'Amount': txn.amount,
                'Category': txn.category
            })
        
        df = pd.DataFrame(transactions_data)
        
        # Display with Streamlit
        st.dataframe(
            df,
            use_container_width=True,
            height=min(400, len(transactions_data) * 35 + 38)
        )
        
        # Show category breakdown
        if len(statement.transactions) > 0:
            st.markdown("#### 📈 Spending by Category")
            category_counts = df['Category'].value_counts()
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.bar_chart(category_counts)
            
            with col2:
                st.write("Category Breakdown:")
                for category, count in category_counts.items():
                    st.write(f"- {category}: {count}")
    
    def get_download_link(self, statement, filename):
        """Generate download link for JSON results"""
        json_str = statement.to_json()
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download JSON Results</a>'
        return href
    
    def run(self):
        """Main application runner"""
        # Header
        st.markdown('<div class="main-header">💳 Universal Credit Card Statement Parser</div>', unsafe_allow_html=True)
        
        # Sidebar
        st.sidebar.title("About")
        st.sidebar.info("""
        **Supported Banks:**
        - 🇮🇳 Indian: HDFC, ICICI, SBI, Axis, Kotak
        - 🇺🇸 International: Chase, Amex, Citi, Discover, Bank of America
        
        **Features:**
        - Automatic bank detection
        - Transaction categorization
        - Multiple extraction methods
        - Scanned PDF support (OCR)
        - JSON export
        """)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Parser Capabilities")
        
        capabilities = self.parser.capabilities
        for method, available in capabilities.items():
            status = "✅" if available else "❌"
            st.sidebar.write(f"{status} {method.upper()}")
        
        # Main content area
        st.markdown("""
        ### 📤 Upload Your Credit Card Statement
        
        Upload a PDF statement from any supported bank. The parser will automatically:
        - Detect your bank
        - Extract key information
        - Categorize transactions
        - Provide downloadable results
        """)
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a PDF file", 
            type="pdf",
            help="Upload your credit card statement in PDF format"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / 1024:.2f} KB"
            }
            st.write("File details:", file_details)
            
            # Processing options
            col1, col2 = st.columns(2)
            with col1:
                use_advanced = st.checkbox("Use advanced table extraction", value=True, 
                                         help="Use Camelot/Tabula for better table detection")
            with col2:
                show_raw_text = st.checkbox("Show extracted text preview", value=False)
            
            # Process the file
            if st.button("🚀 Parse Statement", type="primary"):
                with st.spinner("Processing your statement... This may take a few seconds."):
                    try:
                        # Save uploaded file to temporary location
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        # Parse the statement
                        statement = self.parser.parse(tmp_path, use_advanced_methods=use_advanced)
                        
                        # Clean up temporary file
                        os.unlink(tmp_path)
                        
                        if statement:
                            # Display success message
                            st.markdown('<div class="success-box">✅ Statement parsed successfully!</div>', unsafe_allow_html=True)
                            
                            # Display bank logo
                            self.display_bank_logo(statement.card_issuer)
                            
                            # Display extraction info
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.info(f"**Extraction Method:** {statement.extraction_method}")
                            with col2:
                                st.info(f"**Scanned PDF:** {statement.is_scanned}")
                            with col3:
                                st.info(f"**Transactions Found:** {len(statement.transactions)}")
                            
                            # Display statement summary
                            self.display_statement_summary(statement)
                            
                            # Display transactions
                            self.display_transactions(statement)
                            
                            # Download section
                            st.markdown("---")
                            st.markdown("### 📥 Download Results")
                            
                            # Generate filename
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            download_filename = f"{statement.card_issuer}_statement_{timestamp}.json"
                            
                            # Download link
                            st.markdown(self.get_download_link(statement, download_filename), unsafe_allow_html=True)
                            
                            # Show raw text preview if requested
                            if show_raw_text and hasattr(statement, 'raw_text_preview'):
                                with st.expander("Raw Text Preview (First 500 chars)"):
                                    st.text(statement.raw_text_preview)
                        
                        else:
                            st.error("❌ Failed to parse the statement. Please try another file or check the format.")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing file: {str(e)}")
                        st.info("💡 Try enabling/disabling advanced extraction or check if the PDF is scanned.")
            
            else:
                # Show preview before processing
                st.info("👆 Click 'Parse Statement' to analyze your credit card statement")
        
        else:
            # Demo section when no file is uploaded
            st.markdown("---")
            st.markdown("### 🎯 How It Works")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 1. Upload")
                st.write("Upload your credit card statement PDF")
            
            with col2:
                st.markdown("#### 2. Parse")
                st.write("Automatic detection and extraction")
            
            with col3:
                st.markdown("#### 3. Analyze")
                st.write("View transactions and download results")
            
            st.markdown("---")
            st.markdown("### 💡 Tips for Best Results")
            st.write("""
            - **Clear PDFs**: Use digital statements rather than scanned copies when possible
            - **Complete pages**: Ensure all pages are included
            - **Standard formats**: Statements from major banks work best
            - **File size**: Keep files under 10MB for faster processing
            """)

def main():
    app = UnifiedCreditCardApp()
    app.run()

if __name__ == "__main__":
    main()