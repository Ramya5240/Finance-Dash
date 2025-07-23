import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FinancialAnalyzer:
    """Analyze financial data and generate insights"""
    
    def __init__(self):
        pass
    
    def generate_monthly_summary(self, df):
        """Generate monthly summary of transactions"""
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['month'] = df['date'].dt.to_period('M')
        
        monthly_summary = df.groupby(['month', 'type']).agg({
            'amount': 'sum'
        }).unstack(fill_value=0)
        
        monthly_summary.columns = ['Credit', 'Debit']
        monthly_summary['Net'] = monthly_summary['Credit'] - monthly_summary['Debit']
        monthly_summary['Savings Rate'] = (monthly_summary['Net'] / monthly_summary['Credit'] * 100).round(2)
        
        monthly_summary.reset_index(inplace=True)
        monthly_summary['month'] = monthly_summary['month'].astype(str)
        
        return monthly_summary
    
    def calculate_spending_trends(self, df, periods=['1M', '3M', '6M', '12M']):
        """Calculate spending trends for different time periods"""
        if df.empty:
            return {}
        
        current_date = df['date'].max()
        trends = {}
        
        for period in periods:
            if period == '1M':
                start_date = current_date - timedelta(days=30)
            elif period == '3M':
                start_date = current_date - timedelta(days=90)
            elif period == '6M':
                start_date = current_date - timedelta(days=180)
            elif period == '12M':
                start_date = current_date - timedelta(days=365)
            else:
                continue
            
            period_df = df[df['date'] >= start_date]
            
            if not period_df.empty:
                total_spending = period_df[period_df['type'] == 'debit']['amount'].sum()
                total_income = period_df[period_df['type'] == 'credit']['amount'].sum()
                
                trends[period] = {
                    'spending': total_spending,
                    'income': total_income,
                    'net': total_income - total_spending,
                    'transaction_count': len(period_df)
                }
        
        return trends
    
    def identify_top_categories(self, df, top_n=5):
        """Identify top spending categories"""
        if df.empty or 'category' not in df.columns:
            return pd.DataFrame()
        
        expenses_df = df[df['type'] == 'debit']
        
        top_categories = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=False).head(top_n)
        
        return top_categories.reset_index()
    
    def calculate_category_trends(self, df):
        """Calculate month-over-month trends for each category"""
        if df.empty or 'category' not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        df['month'] = df['date'].dt.to_period('M')
        
        # Filter for expenses only
        expenses_df = df[df['type'] == 'debit']
        
        category_monthly = expenses_df.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)
        
        # Calculate month-over-month change
        category_trends = category_monthly.pct_change().fillna(0) * 100
        
        return category_trends
    
    def detect_unusual_spending(self, df, threshold_multiplier=2.5):
        """Detect unusual spending patterns"""
        if df.empty or 'category' not in df.columns:
            return pd.DataFrame()
        
        expenses_df = df[df['type'] == 'debit'].copy()
        
        # Calculate mean and std for each category
        category_stats = expenses_df.groupby('category')['amount'].agg(['mean', 'std']).fillna(0)
        
        unusual_transactions = []
        
        for _, transaction in expenses_df.iterrows():
            category = transaction['category']
            amount = transaction['amount']
            
            if category in category_stats.index:
                mean_amount = category_stats.loc[category, 'mean']
                std_amount = category_stats.loc[category, 'std']
                
                if std_amount > 0:
                    z_score = (amount - mean_amount) / std_amount
                    if abs(z_score) > threshold_multiplier:
                        unusual_transactions.append(transaction)
        
        return pd.DataFrame(unusual_transactions) if unusual_transactions else pd.DataFrame()
    
    def calculate_savings_rate(self, df):
        """Calculate savings rate over time"""
        if df.empty:
            return 0.0
        
        total_income = df[df['type'] == 'credit']['amount'].sum()
        total_expenses = df[df['type'] == 'debit']['amount'].sum()
        
        if total_income > 0:
            return ((total_income - total_expenses) / total_income) * 100
        
        return 0.0
    
    def analyze_spending_velocity(self, df):
        """Analyze how quickly money is spent after income"""
        if df.empty:
            return {}
        
        df = df.copy().sort_values('date')
        
        income_dates = df[df['type'] == 'credit']['date'].tolist()
        expense_dates = df[df['type'] == 'debit']['date'].tolist()
        
        if not income_dates or not expense_dates:
            return {}
        
        # Calculate average days between income and next expenses
        velocity_data = []
        
        for income_date in income_dates:
            next_expenses = [exp_date for exp_date in expense_dates if exp_date >= income_date]
            if next_expenses:
                days_to_spend = (next_expenses[0] - income_date).days
                velocity_data.append(days_to_spend)
        
        if velocity_data:
            return {
                'avg_days_to_spend': np.mean(velocity_data),
                'median_days_to_spend': np.median(velocity_data),
                'min_days_to_spend': min(velocity_data),
                'max_days_to_spend': max(velocity_data)
            }
        
        return {}

