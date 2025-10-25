# Streamlit app
# Copy content from artifact
"""
Streamlit UI for Credit Card Statement Parser
UPDATED to use new unified_parser backend (NO FRONTEND CHANGES)
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Import new unified parser
from unified_parser import UnifiedCreditCardParser

# Configure page (UNCHANGED)
st.set_page_config(
    page_title="Universal Credit Card Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (UNCHANGED)
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
    .success-box { background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 10px 0; }
    .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)


def main():
    # Header (UNCHANGED)
    st.markdown('<div class="main-header">💳 Universal Credit Card Statement Parser</div>', unsafe_allow_html=True)
    
    # Sidebar (UNCHANGED)
    st.sidebar.title("About")
    st.sidebar.info("""
    **Supported Banks:**
    - 🇮🇳 Indian: HDFC, ICICI, SBI, Axis, IDFC
    - 🌍 AI Fallback: Any other bank
    
    **Features:**
    - Automatic bank detection
    - Fast regex extraction
    - AI fallback for edge cases
    - Transaction categorization
    """)
    
    # Initialize parser (NEW - single line change)
    parser = UnifiedCreditCardParser()
    
    # File upload (UNCHANGED)
    st.markdown("### 📤 Upload Your Credit Card Statement")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.write({"Filename": uploaded_file.name, "File size": f"{uploaded_file.size / 1024:.2f} KB"})
        
        # Parse button
        if st.button("🚀 Parse Statement", type="primary"):
            with st.spinner("Processing your statement..."):
                # NEW: Use unified parser instead of old parser
                bytes_data = io.BytesIO(uploaded_file.getvalue())
                result = parser.parse(bytes_data)
                
                # Display results (UNCHANGED logic, just adapted to new data structure)
                if result.get("status") in ["SUCCESS", "PARTIAL"]:
                    st.markdown('<div class="success-box">✅ Statement parsed successfully!</div>', unsafe_allow_html=True)
                    
                    # Display bank info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**Bank:** {result.get('bank_name', 'N/A')}")
                    with col2:
                        st.info(f"**Method:** {result.get('extraction_method', 'N/A')}")
                    with col3:
                        st.info(f"**Confidence:** {result.get('confidence_score', 0):.1%}")
                    
                    # Statement summary (UNCHANGED)
                    st.markdown("### 📊 Statement Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Card Last 4", result.get('card_last_4', 'N/A'))
                        st.metric("Statement Date", result.get('statement_date', 'N/A'))
                    with col2:
                        st.metric("Due Date", result.get('payment_due_date', 'N/A'))
                        st.metric("Credit Limit", result.get('credit_limit', 'N/A'))
                    with col3:
                        st.metric("Total Due", result.get('total_amount_due', 'N/A'))
                        st.metric("Min Payment", result.get('minimum_payment', 'N/A'))
                    with col4:
                        st.metric("Available Credit", result.get('available_credit', 'N/A'))
                        st.metric("Period", f"{result.get('statement_period_start', 'N/A')}")
                    
                    # Transactions table (UNCHANGED)
                    transactions = result.get('transactions', [])
                    if transactions:
                        st.markdown(f"### 💳 Transactions ({len(transactions)})")
                        df = pd.DataFrame(transactions)
                        st.dataframe(df, use_container_width=True)
                        
                        # Category breakdown
                        if 'category' in df.columns:
                            st.markdown("#### 📈 Spending by Category")
                            category_counts = df['category'].value_counts()
                            st.bar_chart(category_counts)
                    else:
                        st.warning("No transactions found")
                    
                else:
                    st.error(f"❌ Parsing failed: {result.get('reason', 'Unknown error')}")


if __name__ == "__main__":
    main()