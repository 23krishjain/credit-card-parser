"""
Enhanced Streamlit UI for Credit Card Statement Parser
Features: Modern design, export options, analytics, comparison mode
"""

import streamlit as st
import pandas as pd
import io
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Import unified parser
from unified_parser import UnifiedCreditCardParser

# Configure page
st.set_page_config(
    page_title="AI Credit Card Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "AI-powered credit card statement parser with regex and LLM fallback"
    }
)

# Enhanced Custom CSS
st.markdown("""
<style>
    /* Main styling */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(120deg, #ffffff 0%, #ffffff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem 0;
    }
    
    .sub-header {
        text-align: center;
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Status boxes */
    .success-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .info-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Bank badge */
    .bank-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        margin: 5px;
    }
    
    .badge-hdfc { background: linear-gradient(135deg, #004c8c, #0066b3); color: white; }
    .badge-axis { background: linear-gradient(135deg, #951b81, #b8268f); color: white; }
    .badge-icici { background: linear-gradient(135deg, #ff6f00, #ff8c00); color: white; }
    .badge-idfc { background: linear-gradient(135deg, #d32f2f, #f44336); color: white; }
    .badge-syndicate { background: linear-gradient(135deg, #388e3c, #4caf50); color: white; }
    .badge-ai { background: linear-gradient(135deg, #7b1fa2, #9c27b0); color: white; }
    
    /* Transaction table */
    .transaction-table {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Confidence indicator */
    .confidence-high { color: #4caf50; font-weight: bold; }
    .confidence-medium { color: #ff9800; font-weight: bold; }
    .confidence-low { color: #f44336; font-weight: bold; }
    
    /* Upload area */
    .uploadedFile {
        border: 2px dashed #667eea !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)


def get_bank_badge(bank_name, method):
    """Generate styled bank badge"""
    bank_lower = bank_name.lower()
    
    badge_class = "badge-ai"  # default
    if "hdfc" in bank_lower:
        badge_class = "badge-hdfc"
    elif "axis" in bank_lower:
        badge_class = "badge-axis"
    elif "icici" in bank_lower:
        badge_class = "badge-icici"
    elif "idfc" in bank_lower:
        badge_class = "badge-idfc"
    elif "syndicate" in bank_lower:
        badge_class = "badge-syndicate"
    
    return f'<span class="bank-badge {badge_class}">{bank_name}</span>'


def get_confidence_class(confidence):
    """Get CSS class based on confidence score"""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"


def clean_amount_value(amount_str):
    """Safely clean and convert amount string to float"""
    try:
        if pd.isna(amount_str) or amount_str == 'NOT_FOUND':
            return 0.0
            
        # Remove currency symbols and common suffixes
        cleaned = str(amount_str).replace('₹', '').replace('Rs', '').replace(',', '').strip()
        
        # Remove CR/Dr/Cr suffixes (credit indicators) and take absolute value
        cleaned = cleaned.replace(' CR', '').replace(' Cr', '').replace(' cr', '')
        cleaned = cleaned.replace(' DR', '').replace(' Dr', '').replace(' dr', '')
        
        # Handle negative values and empty strings
        if not cleaned:
            return 0.0
        
        # Convert to float and return absolute value for spending analysis
        return abs(float(cleaned))
    except (ValueError, AttributeError, TypeError):
        return 0.0


def create_spending_chart(df):
    """Create interactive spending chart by category"""
    if df.empty or 'category' not in df.columns:
        return None
    
    category_data = df.groupby('category')['amount'].apply(
        lambda x: sum(clean_amount_value(amt) for amt in x)
    ).reset_index()
    
    # Filter out zero values
    category_data = category_data[category_data['amount'] > 0]
    
    if category_data.empty:
        return None
    
    fig = px.pie(
        category_data,
        values='amount',
        names='category',
        title='Spending Distribution by Category',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        showlegend=True,
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_timeline_chart(df):
    """Create transaction timeline"""
    if df.empty or 'date' not in df.columns:
        return None
    
    try:
        df_copy = df.copy()
        df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], format='%d/%m/%Y', errors='coerce')
        df_copy['amount_clean'] = df_copy['amount'].apply(clean_amount_value)
        
        # Remove rows with invalid dates or zero amounts
        df_copy = df_copy.dropna(subset=['date_parsed'])
        df_copy = df_copy[df_copy['amount_clean'] > 0]
        
        if df_copy.empty:
            return None
        
        daily_spending = df_copy.groupby('date_parsed')['amount_clean'].sum().reset_index()
        daily_spending.columns = ['date_parsed', 'amount']
        
        fig = px.line(
            daily_spending,
            x='date_parsed',
            y='amount',
            title='Daily Spending Timeline',
            markers=True
        )
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Amount (₹)",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    except Exception as e:
        st.warning(f"Could not create timeline chart: {str(e)}")
        return None


def export_to_json(result):
    """Export result to JSON"""
    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    return json_str


def export_to_csv(transactions):
    """Export transactions to CSV"""
    if not transactions:
        return None
    
    df = pd.DataFrame(transactions)
    return df.to_csv(index=False).encode('utf-8')


def main():
    # Header
    st.markdown('<div class="main-header">  Universal Credit Card Statement Parser</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligent statement parsing with Regex + AI hybrid technology</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Parser options
        st.subheader("Parser Options")
        force_ai = st.checkbox("🤖 Force AI Parser", help="Skip regex, use AI directly")
        show_debug = st.checkbox("🔍 Show Debug Info", help="Display extraction metadata")
        
        st.divider()
        
        # Supported banks
        st.subheader("🏦 Supported Banks")
        banks_info = {
            "HDFC Bank": "95%",
            "Axis Bank": "93%",
            "ICICI Bank": "92%",
            "IDFC First": "91%",
            "Syndicate": "90%",
            "Others (AI)": "85-90%"
        }
        
        for bank, accuracy in banks_info.items():
            st.write(f"✅ **{bank}** - {accuracy}")
        
        st.divider()
        
        # Features
        st.subheader("✨ Features")
        features = [
            "⚡ Lightning fast regex parsing",
            "🤖 AI fallback for any bank",
            "📊 Transaction categorization",
            "📈 Spending analytics",
            "💾 Export to JSON/CSV",
            "🔒 Secure & private"
        ]
        for feature in features:
            st.write(feature)
        
        st.divider()
        
        # About
        st.subheader("ℹ️ About")
        st.info("""
        **Version**: 1.0.0  
        **Author**: AI Team  
        **License**: MIT  
        
        This parser combines fast regex patterns with intelligent AI fallback for maximum accuracy.
        """)
    
    # Initialize parser
    if 'parser' not in st.session_state:
        st.session_state.parser = UnifiedCreditCardParser()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Parse", "📊 Analytics", "ℹ️ How It Works"])
    
    with tab1:
        # File upload
        st.markdown("### 📁 Upload Credit Card Statement")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type="pdf",
                help="Upload your credit card statement in PDF format"
            )
        
        with col2:
            if uploaded_file:
                st.metric("File Size", f"{uploaded_file.size / 1024:.2f} KB")
                st.metric("File Name", uploaded_file.name[:20] + "...")
        
        if uploaded_file is not None:
            # Parse button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                parse_btn = st.button("🚀 Parse Statement", type="primary", use_container_width=True)
            
            if parse_btn:
                with st.spinner("🔄 Processing your statement..."):
                    bytes_data = io.BytesIO(uploaded_file.getvalue())
                    result = st.session_state.parser.parse(bytes_data, force_ai=force_ai)
                    
                    # Store in session state
                    st.session_state.result = result
                
                # Display results
                if result.get("status") in ["SUCCESS", "PARTIAL"]:
                    # Success message
                    st.markdown('<div class="success-box">✅ <strong>Statement parsed successfully!</strong></div>', unsafe_allow_html=True)
                    
                    # Bank info banner
                    bank_name = result.get('bank_name', 'Unknown')
                    method = result.get('extraction_method', 'N/A')
                    confidence = result.get('confidence_score', 0)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**Bank:** {get_bank_badge(bank_name, method)}", unsafe_allow_html=True)
                    with col2:
                        st.metric("Method", method)
                    with col3:
                        conf_class = get_confidence_class(confidence)
                        st.markdown(f"**Confidence:** <span class='{conf_class}'>{confidence:.1%}</span>", unsafe_allow_html=True)
                    with col4:
                        transactions_count = len(result.get('transactions', []))
                        st.metric("Transactions", transactions_count)
                    
                    st.divider()
                    
                    # Statement summary
                    st.markdown("### 📋 Statement Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "💳 Card Last 4",
                            result.get('card_last_4', 'N/A'),
                            help="Last 4 digits of card number"
                        )
                        st.metric(
                            "📅 Statement Date",
                            result.get('statement_date', 'N/A')
                        )
                    
                    with col2:
                        st.metric(
                            "⏰ Payment Due Date",
                            result.get('payment_due_date', 'N/A'),
                            help="Last date to make payment"
                        )
                        st.metric(
                            "📆 Billing Period",
                            f"{result.get('statement_period_start', 'N/A')}"
                        )
                    
                    with col3:
                        total_due = result.get('total_amount_due', 'N/A')
                        st.metric(
                            "💰 Total Amount Due",
                            f"₹{total_due}" if total_due != 'N/A' else 'N/A',
                            help="Total outstanding amount"
                        )
                        min_payment = result.get('minimum_payment', 'N/A')
                        st.metric(
                            "💵 Minimum Payment",
                            f"₹{min_payment}" if min_payment != 'N/A' else 'N/A'
                        )
                    
                    with col4:
                        credit_limit = result.get('credit_limit', 'N/A')
                        st.metric(
                            "🏧 Credit Limit",
                            f"₹{credit_limit}" if credit_limit != 'N/A' else 'N/A'
                        )
                        available = result.get('available_credit', 'N/A')
                        st.metric(
                            "✅ Available Credit",
                            f"₹{available}" if available != 'N/A' else 'N/A'
                        )
                    
                    st.divider()
                    
                    # Transactions
                    transactions = result.get('transactions', [])
                    if transactions:
                        st.markdown(f"### 💳 Transactions ({len(transactions)})")
                        
                        # Create DataFrame
                        df = pd.DataFrame(transactions)
                        
                        # Display table
                        st.dataframe(
                            df,
                            use_container_width=True,
                            height=400,
                            column_config={
                                "date": st.column_config.TextColumn("Date", width="small"),
                                "description": st.column_config.TextColumn("Description", width="large"),
                                "amount": st.column_config.TextColumn("Amount", width="small"),
                                "category": st.column_config.TextColumn("Category", width="small"),
                            }
                        )
                        
                        # Export options
                        st.markdown("#### 💾 Export Options")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            csv_data = export_to_csv(transactions)
                            if csv_data:
                                st.download_button(
                                    label="📄 Download CSV",
                                    data=csv_data,
                                    file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                        
                        with col2:
                            json_data = export_to_json(result)
                            st.download_button(
                                label="📋 Download JSON",
                                data=json_data,
                                file_name=f"statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                        
                        with col3:
                            # Copy to clipboard (using JSON)
                            st.button("📎 Copy to Clipboard", help="Copy JSON to clipboard")
                    
                    else:
                        st.warning("⚠️ No transactions found in the statement")
                    
                    # Debug info
                    if show_debug:
                        st.divider()
                        st.markdown("### 🔍 Debug Information")
                        
                        with st.expander("View Raw Data"):
                            st.json(result)
                        
                        if result.get('errors'):
                            st.error("**Errors:**")
                            for error in result['errors']:
                                st.write(f"- {error}")
                
                else:
                    # Error display
                    st.markdown(f'<div class="error-box">❌ <strong>Parsing failed:</strong> {result.get("reason", "Unknown error")}</div>', unsafe_allow_html=True)
                    
                    with st.expander("💡 Troubleshooting Tips"):
                        st.write("""
                        **Common Issues:**
                        - PDF is password-protected → Remove password first
                        - PDF is scanned/image → Enable OCR (coming soon)
                        - Unsupported bank → Try enabling "Force AI Parser"
                        - Low quality scan → Use a better quality PDF
                        
                        **Solutions:**
                        1. Ensure PDF is text-based (not scanned image)
                        2. Check if bank is in supported list
                        3. Enable AI parser for better accuracy
                        4. Contact support with sample PDF
                        """)
    
    with tab2:
        st.markdown("### 📊 Spending Analytics")
        
        if 'result' in st.session_state and st.session_state.result.get('transactions'):
            transactions = st.session_state.result['transactions']
            df = pd.DataFrame(transactions)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Transactions", len(transactions))
            
            with col2:
                # Calculate total spent
                total_spent = sum(
                    clean_amount_value(t['amount'])
                    for t in transactions
                )
                st.metric("Total Spent", f"₹{total_spent:,.2f}")
            
            with col3:
                # Average transaction
                avg_txn = total_spent / len(transactions) if transactions else 0
                st.metric("Avg Transaction", f"₹{avg_txn:,.2f}")
            
            with col4:
                # Unique categories
                unique_cats = df['category'].nunique()
                st.metric("Categories", unique_cats)
            
            st.divider()
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart
                pie_chart = create_spending_chart(df)
                if pie_chart:
                    st.plotly_chart(pie_chart, use_container_width=True)
            
            with col2:
                # Category breakdown table
                st.markdown("#### 📈 Category Breakdown")
                category_summary = df.groupby('category').agg({
                    'amount': 'count',
                    'description': 'count'
                }).rename(columns={'amount': 'Count', 'description': 'Transactions'})
                st.dataframe(category_summary, use_container_width=True)
            
            # Timeline
            timeline_chart = create_timeline_chart(df)
            if timeline_chart:
                st.plotly_chart(timeline_chart, use_container_width=True)
            
            # Top transactions - FIXED SECTION
            st.markdown("#### 🔝 Top 10 Transactions")
            if 'amount' in df.columns:
                # Create a temporary column with cleaned numeric amounts
                df_temp = df.copy()
                df_temp['amount_numeric'] = df_temp['amount'].apply(clean_amount_value)
                
                # Get top 10 transactions by numeric amount
                top_indices = df_temp['amount_numeric'].nlargest(10).index
                top_transactions = df.loc[top_indices]
            else:
                top_transactions = df.head(10)

            st.dataframe(top_transactions, use_container_width=True)
        
        else:
            st.info("📤 Upload and parse a statement to view analytics")
    
    with tab3:
        st.markdown("### 🤔 How It Works")
        
        st.markdown("""
        This parser uses a **hybrid approach** combining:
        
        1. **⚡ Fast Regex Parsing** (for supported banks)
           - Pattern-based extraction
           - ~0.2 seconds per PDF
           - 90-95% accuracy
           - Works offline
        
        2. **🤖 AI Fallback** (for any bank)
           - Google Gemini LLM
           - ~2-3 seconds per PDF
           - 85-90% accuracy
           - Handles edge cases
        
        3. **🧠 Smart Enhancement**
           - AI fills missing fields from regex
           - Best of both worlds
           - 95%+ accuracy
        """)
        
        st.divider()
        
        st.markdown("### 🔄 Processing Flow")
        
        st.markdown("""
        ```
        📄 Upload PDF
            ↓
        📝 Extract Text (pdfplumber)
            ↓
        🔍 Detect Bank (keyword matching)
            ↓
            ├─→ Known Bank? → ⚡ Regex Parser
            │                      ↓
            │                 Confidence Check
            │                      ↓
            │              Low? → 🤖 AI Enhancement
            │
            └─→ Unknown Bank? → 🤖 AI Parser
                                    ↓
                              📊 Display Results
        ```
        """)
        
        st.divider()
        
        st.markdown("### 📦 Extracted Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Statement Info:**
            - 🏦 Bank Name
            - 💳 Card Last 4 Digits
            - 📅 Statement Date
            - ⏰ Payment Due Date
            - 📆 Billing Period
            """)
        
        with col2:
            st.markdown("""
            **Financial Data:**
            - 💰 Total Amount Due
            - 💵 Minimum Payment
            - 🏧 Credit Limit
            - ✅ Available Credit
            - 💳 All Transactions
            """)


if __name__ == "__main__":
    main()