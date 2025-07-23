import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

from parser.bank_parser import BankParser
from utils.categorizer import TransactionCategorizer
from utils.analyzer import FinancialAnalyzer
from dashboard.visualizations import DashboardVisualizations
from dashboard.insights import InsightsGenerator
from database.models import init_database
from database.operations import (
    UserManager, BankAccountManager, TransactionManager, 
    FileManager, AnalyticsManager, get_default_user
)
from database.models import get_session
from sqlalchemy import desc

# Page configuration
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def initialize_database():
    """Initialize database connection and tables"""
    try:
        init_database()
        return True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return False

# Initialize session state
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = initialize_database()
if 'current_user' not in st.session_state:
    if st.session_state.db_initialized:
        st.session_state.current_user = get_default_user()
    else:
        st.session_state.current_user = None
if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = pd.DataFrame()
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Upload"

# Initialize components
bank_parser = BankParser()
categorizer = TransactionCategorizer()
analyzer = FinancialAnalyzer()
visualizations = DashboardVisualizations()
insights = InsightsGenerator()

def main():
    st.title("💰 Comprehensive Finance Tracker")
    st.markdown("### Supporting major US and international banks with database persistence")
    
    # Check database status
    if not st.session_state.db_initialized:
        st.error("❌ Database connection failed. Some features may not work properly.")
    elif st.session_state.current_user:
        username = st.session_state.current_user.username if hasattr(st.session_state.current_user, 'username') else 'default_user'
        st.success(f"✅ Connected as user: {username}")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Upload Files", "Dashboard", "Insights", "Database Management", "Export Data"]
    )
    
    if page == "Upload Files":
        upload_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Insights":
        insights_page()
    elif page == "Database Management":
        database_management_page()
    elif page == "Export Data":
        export_page()

def upload_page():
    st.header("📁 Upload Bank Statements")
    
    # Supported banks info
    with st.expander("Supported Banks & Formats"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**US Banks:**")
            st.write("• Chase Bank (CSV/PDF)")
            st.write("• Wells Fargo (CSV/PDF)")
            st.write("• Bank of America (CSV/PDF)")
            st.write("• Citibank (CSV/PDF)")
        
        with col2:
            st.write("**International Banks:**")
            st.write("• HDFC Bank (CSV/PDF)")
            st.write("• Axis Bank (CSV/PDF)")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload your bank statements",
        type=['csv', 'pdf'],
        accept_multiple_files=True,
        help="Upload CSV or PDF files from supported banks"
    )
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) uploaded**")
        
        if st.button("Process Files", type="primary"):
            process_uploaded_files(uploaded_files)

def process_uploaded_files(uploaded_files):
    """Process uploaded bank statement files with database storage"""
    if not st.session_state.db_initialized or not st.session_state.current_user:
        st.error("Database not initialized. Cannot save transactions.")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    user_id = st.session_state.current_user.id
    total_saved = 0
    total_duplicates = 0
    
    with TransactionManager() as tx_mgr, BankAccountManager() as bank_mgr, FileManager() as file_mgr:
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing {uploaded_file.name}...")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            try:
                # Check if file was already processed
                file_content = uploaded_file.read()
                uploaded_file.seek(0)  # Reset file pointer
                
                if file_mgr.is_file_processed(file_content):
                    st.warning(f"⚠️ {uploaded_file.name} was already processed before")
                    continue
                
                # Parse the file
                transactions = bank_parser.parse_file(uploaded_file)
                
                if not transactions.empty:
                    # Categorize transactions
                    transactions = categorizer.categorize_transactions(transactions)
                    
                    # Detect bank format for account creation
                    bank_format = bank_parser.detect_bank_format(str(file_content))
                    
                    # Create or get bank account
                    bank_account = bank_mgr.create_or_get_account(
                        user_id=user_id,
                        bank_name=bank_format,
                        account_name="Primary"
                    )
                    
                    # Save transactions to database
                    saved_count, duplicate_count = tx_mgr.save_transactions(
                        transactions_df=transactions,
                        user_id=user_id,
                        bank_account_id=bank_account.id,
                        file_name=uploaded_file.name
                    )
                    
                    # Record file upload
                    file_mgr.record_file_upload(
                        user_id=user_id,
                        file_name=uploaded_file.name,
                        file_content=file_content,
                        bank_detected=bank_format,
                        transactions_count=saved_count
                    )
                    
                    total_saved += saved_count
                    total_duplicates += duplicate_count
                    
                    st.success(f"✅ Processed {uploaded_file.name}: {saved_count} new transactions, {duplicate_count} duplicates skipped")
                else:
                    st.warning(f"⚠️ No transactions found in {uploaded_file.name}")
                    
            except Exception as e:
                st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
    
    if total_saved > 0:
        st.success(f"🎉 Successfully saved {total_saved} new transactions to database!")
        
        # Refresh session data from database
        load_transactions_from_database()
        
        # Show summary
        with st.expander("Processing Summary"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("New Transactions", total_saved)
            with col2:
                st.metric("Duplicates Skipped", total_duplicates)

def load_transactions_from_database():
    """Load transactions from database into session state"""
    if not st.session_state.db_initialized or not st.session_state.current_user:
        return
    
    try:
        with TransactionManager() as tx_mgr:
            df = tx_mgr.get_transactions_as_dataframe(st.session_state.current_user.id)
            st.session_state.transactions_df = df
    except Exception as e:
        st.error(f"Error loading transactions: {e}")

def dashboard_page():
    st.header("📊 Financial Dashboard")
    
    # Load transactions from database
    load_transactions_from_database()
    
    if st.session_state.transactions_df.empty:
        st.warning("No transaction data available. Please upload bank statements first.")
        return
    
    df = st.session_state.transactions_df.copy()
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=df['date'].min() if not df.empty else datetime.now() - timedelta(days=365),
            max_value=datetime.now().date()
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=df['date'].max() if not df.empty else datetime.now().date(),
            max_value=datetime.now().date()
        )
    
    # Filter data by date range
    mask = (df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))
    filtered_df = df.loc[mask]
    
    if filtered_df.empty:
        st.warning("No transactions found in the selected date range.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_income = filtered_df[filtered_df['type'] == 'credit']['amount'].sum()
        st.metric("Total Income", f"${total_income:,.2f}")
    
    with col2:
        total_expenses = abs(filtered_df[filtered_df['type'] == 'debit']['amount'].sum())
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
    
    with col3:
        net_savings = total_income - total_expenses
        st.metric("Net Savings", f"${net_savings:,.2f}")
    
    with col4:
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
        st.metric("Savings Rate", f"{savings_rate:.1f}%")
    
    # Monthly trends
    st.subheader("📈 Monthly Trends")
    monthly_chart = visualizations.create_monthly_trends_chart(filtered_df)
    st.plotly_chart(monthly_chart, use_container_width=True)
    
    # Category breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💸 Expense Categories")
        expense_pie = visualizations.create_expense_category_pie(filtered_df)
        st.plotly_chart(expense_pie, use_container_width=True)
    
    with col2:
        st.subheader("📊 Top Expense Categories")
        category_bar = visualizations.create_category_bar_chart(filtered_df)
        st.plotly_chart(category_bar, use_container_width=True)
    
    # Time period comparison
    st.subheader("📅 Time Period Comparison")
    comparison_chart = visualizations.create_time_comparison_chart(filtered_df)
    st.plotly_chart(comparison_chart, use_container_width=True)
    
    # Recent transactions
    st.subheader("🔍 Recent Transactions")
    recent_transactions = filtered_df.sort_values('date', ascending=False).head(20)
    st.dataframe(
        recent_transactions[['date', 'description', 'category', 'amount', 'type']],
        use_container_width=True
    )

def insights_page():
    st.header("🧠 Financial Insights")
    
    # Load transactions from database
    load_transactions_from_database()
    
    if st.session_state.transactions_df.empty:
        st.warning("No transaction data available. Please upload bank statements first.")
        return
    
    df = st.session_state.transactions_df.copy()
    
    # Generate insights
    spending_insights = insights.analyze_spending_patterns(df)
    budget_analysis = insights.analyze_budget_categories(df)
    unusual_transactions = insights.flag_unusual_transactions(df)
    recommendations = insights.generate_recommendations(df)
    
    # Spending patterns
    st.subheader("📊 Spending Patterns")
    for insight in spending_insights:
        if insight['type'] == 'warning':
            st.warning(insight['message'])
        elif insight['type'] == 'info':
            st.info(insight['message'])
        else:
            st.success(insight['message'])
    
    # Budget analysis
    st.subheader("💰 Budget Analysis")
    if budget_analysis:
        budget_df = pd.DataFrame(budget_analysis)
        st.dataframe(budget_df, use_container_width=True)
    else:
        st.info("No budget overspending detected.")
    
    # Unusual transactions
    st.subheader("⚠️ Unusual Transactions")
    if not unusual_transactions.empty:
        st.dataframe(
            unusual_transactions[['date', 'description', 'amount', 'category']],
            use_container_width=True
        )
    else:
        st.success("No unusual transactions detected.")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    for rec in recommendations:
        st.markdown(f"• {rec}")

def database_management_page():
    """Database management and analytics page"""
    st.header("🗄️ Database Management")
    
    if not st.session_state.db_initialized or not st.session_state.current_user:
        st.error("Database not available.")
        return
    
    user_id = st.session_state.current_user.id
    
    # Database statistics
    st.subheader("📊 Database Statistics")
    
    with TransactionManager() as tx_mgr, BankAccountManager() as bank_mgr, AnalyticsManager() as analytics_mgr:
        # Get transaction count
        all_transactions = tx_mgr.get_user_transactions(user_id)
        transaction_count = len(all_transactions)
        
        # Get bank accounts
        bank_accounts = bank_mgr.get_user_accounts(user_id)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Transactions", transaction_count)
        with col2:
            st.metric("Bank Accounts", len(bank_accounts))
        with col3:
            if all_transactions:
                date_range = abs((all_transactions[0].date - all_transactions[-1].date).days)
                st.metric("Date Range (Days)", date_range)
            else:
                st.metric("Date Range", "No data")
    
    # Bank accounts management
    st.subheader("🏦 Bank Accounts")
    if bank_accounts:
        accounts_data = []
        for account in bank_accounts:
            tx_count = len([tx for tx in all_transactions if tx.bank_account_id == account.id])
            accounts_data.append({
                'Bank': account.bank_name.replace('_', ' ').title(),
                'Account Name': account.account_name,
                'Transactions': tx_count,
                'Last Updated': account.last_updated.strftime('%Y-%m-%d'),
                'Status': 'Active' if account.is_active == True else 'Inactive'
            })
        
        st.dataframe(pd.DataFrame(accounts_data), use_container_width=True)
    else:
        st.info("No bank accounts found. Upload statements to create accounts.")
    
    # Data management actions
    st.subheader("⚙️ Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Data", help="Reload transactions from database"):
            load_transactions_from_database()
            st.success("Data refreshed successfully!")
    
    with col2:
        if st.button("🧹 Clean Duplicates", help="Remove duplicate transactions"):
            with TransactionManager() as tx_mgr:
                # This would need implementation in the database operations
                st.info("Duplicate cleaning feature coming soon!")
    
    # Recent uploads
    st.subheader("📁 Recent File Uploads")
    try:
        from database.models import UploadedFile
        session = get_session()
        recent_files = session.query(UploadedFile).filter_by(user_id=user_id).order_by(UploadedFile.uploaded_at.desc()).limit(10).all()
        session.close()
        
        if recent_files:
            files_data = []
            for file_record in recent_files:
                files_data.append({
                    'File Name': file_record.file_name,
                    'Bank Detected': file_record.bank_detected if file_record.bank_detected is not None else 'Unknown',
                    'Transactions': file_record.transactions_count,
                    'Upload Date': file_record.uploaded_at.strftime('%Y-%m-%d %H:%M'),
                    'Status': file_record.processing_status.title()
                })
            
            st.dataframe(pd.DataFrame(files_data), use_container_width=True)
        else:
            st.info("No file upload history found.")
    except Exception as e:
        st.error(f"Error loading file history: {e}")

def export_page():
    st.header("📤 Export Data")
    
    # Load transactions from database
    load_transactions_from_database()
    
    if st.session_state.transactions_df.empty:
        st.warning("No transaction data available. Please upload bank statements first.")
        return
    
    df = st.session_state.transactions_df.copy()
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Export")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.subheader("Monthly Summary")
        monthly_summary = analyzer.generate_monthly_summary(df)
        
        summary_buffer = io.StringIO()
        monthly_summary.to_csv(summary_buffer, index=False)
        
        st.download_button(
            label="Download Monthly Summary",
            data=summary_buffer.getvalue(),
            file_name=f"monthly_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()

