import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class InsightsGenerator:
    """Generate financial insights and recommendations"""
    
    def __init__(self):
        self.category_budgets = {
            'Food & Dining': 0.15,  # 15% of income
            'Groceries': 0.10,      # 10% of income
            'Transportation': 0.15,  # 15% of income
            'Shopping': 0.10,       # 10% of income
            'Entertainment': 0.05,  # 5% of income
            'Utilities': 0.08,      # 8% of income
            'Healthcare': 0.05,     # 5% of income
        }
    
    def analyze_spending_patterns(self, df):
        """Analyze spending patterns and identify trends"""
        insights = []
        
        if df.empty or 'category' not in df.columns:
            return insights
        
        # Recent vs previous month comparison
        current_date = df['date'].max()
        current_month_start = current_date.replace(day=1)
        previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        current_month_df = df[df['date'] >= current_month_start]
        previous_month_df = df[(df['date'] >= previous_month_start) & (df['date'] < current_month_start)]
        
        if not current_month_df.empty and not previous_month_df.empty:
            current_spending = current_month_df[current_month_df['type'] == 'debit']['amount'].sum()
            previous_spending = previous_month_df[previous_month_df['type'] == 'debit']['amount'].sum()
            
            if previous_spending > 0:
                change_pct = ((current_spending - previous_spending) / previous_spending) * 100
                
                if change_pct > 20:
                    insights.append({
                        'type': 'warning',
                        'message': f"Your spending increased by {change_pct:.1f}% this month compared to last month. Consider reviewing your expenses."
                    })
                elif change_pct < -10:
                    insights.append({
                        'type': 'success',
                        'message': f"Great job! Your spending decreased by {abs(change_pct):.1f}% this month compared to last month."
                    })
        
        # Category-wise trend analysis
        expenses_df = df[df['type'] == 'debit']
        
        if not expenses_df.empty:
            # Find fastest growing categories
            df_with_month = expenses_df.copy()
            df_with_month['month'] = df_with_month['date'].dt.to_period('M')
            
            monthly_category = df_with_month.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)
            
            if len(monthly_category) >= 2:
                category_growth = monthly_category.pct_change().iloc[-1] * 100
                fastest_growing = category_growth.sort_values(ascending=False).head(3)
                
                for category, growth in fastest_growing.items():
                    if growth > 50:
                        insights.append({
                            'type': 'warning',
                            'message': f"Your {category} spending increased by {growth:.1f}% this month. Consider monitoring this category."
                        })
        
        return insights
    
    def analyze_budget_categories(self, df):
        """Analyze spending against budget recommendations"""
        budget_analysis = []
        
        if df.empty or 'category' not in df.columns:
            return budget_analysis
        
        # Calculate monthly income and expenses
        current_date = df['date'].max()
        current_month_start = current_date.replace(day=1)
        current_month_df = df[df['date'] >= current_month_start]
        
        monthly_income = current_month_df[current_month_df['type'] == 'credit']['amount'].sum()
        
        if monthly_income <= 0:
            return budget_analysis
        
        expenses_df = current_month_df[current_month_df['type'] == 'debit']
        category_spending = expenses_df.groupby('category')['amount'].sum()
        
        for category, recommended_pct in self.category_budgets.items():
            if category in category_spending.index:
                actual_amount = category_spending[category]
                recommended_amount = monthly_income * recommended_pct
                variance_pct = ((actual_amount - recommended_amount) / recommended_amount) * 100
                
                if variance_pct > 20:  # 20% over budget
                    budget_analysis.append({
                        'Category': category,
                        'Actual Spending': f"${actual_amount:.2f}",
                        'Recommended Budget': f"${recommended_amount:.2f}",
                        'Variance': f"+{variance_pct:.1f}%",
                        'Status': 'Over Budget',
                        'Suggestion': f"Consider reducing {category.lower()} expenses by ${actual_amount - recommended_amount:.2f}"
                    })
                elif variance_pct < -20:  # 20% under budget
                    budget_analysis.append({
                        'Category': category,
                        'Actual Spending': f"${actual_amount:.2f}",
                        'Recommended Budget': f"${recommended_amount:.2f}",
                        'Variance': f"{variance_pct:.1f}%",
                        'Status': 'Under Budget',
                        'Suggestion': "Great job staying within budget!"
                    })
        
        return budget_analysis
    
    def flag_unusual_transactions(self, df, threshold_multiplier=2.0):
        """Flag unusually large transactions"""
        if df.empty:
            return pd.DataFrame()
        
        # Calculate monthly income average
        monthly_income = df[df['type'] == 'credit'].groupby(df['date'].dt.to_period('M'))['amount'].sum()
        avg_monthly_income = monthly_income.mean() if not monthly_income.empty else 0
        
        if avg_monthly_income <= 0:
            return pd.DataFrame()
        
        # Flag transactions that are more than 20% of monthly income
        large_transaction_threshold = avg_monthly_income * 0.2
        
        unusual_transactions = df[
            (df['type'] == 'debit') & 
            (df['amount'] > large_transaction_threshold)
        ].copy()
        
        # Also flag transactions that are statistical outliers within their category
        if 'category' in df.columns:
            expenses_df = df[df['type'] == 'debit']
            category_stats = expenses_df.groupby('category')['amount'].agg(['mean', 'std']).fillna(0)
            
            outlier_transactions = []
            for _, transaction in expenses_df.iterrows():
                category = transaction['category']
                amount = transaction['amount']
                
                if category in category_stats.index:
                    mean_amount = category_stats.loc[category, 'mean']
                    std_amount = category_stats.loc[category, 'std']
                    
                    if std_amount > 0:
                        z_score = (amount - mean_amount) / std_amount
                        if z_score > threshold_multiplier:
                            outlier_transactions.append(transaction)
            
            if outlier_transactions:
                outlier_df = pd.DataFrame(outlier_transactions)
                unusual_transactions = pd.concat([unusual_transactions, outlier_df]).drop_duplicates()
        
        return unusual_transactions.sort_values('amount', ascending=False) if not unusual_transactions.empty else pd.DataFrame()
    
    def generate_recommendations(self, df):
        """Generate personalized financial recommendations"""
        recommendations = []
        
        if df.empty:
            return recommendations
        
        # Calculate basic financial metrics
        total_income = df[df['type'] == 'credit']['amount'].sum()
        total_expenses = df[df['type'] == 'debit']['amount'].sum()
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        
        # Savings rate recommendations
        if savings_rate < 10:
            recommendations.append("Your savings rate is below 10%. Try to reduce discretionary spending and aim for at least 20% savings rate.")
        elif savings_rate < 20:
            recommendations.append("Your savings rate is good but could be improved. Consider the 50/30/20 rule: 50% needs, 30% wants, 20% savings.")
        else:
            recommendations.append("Excellent savings rate! Consider investing your surplus for long-term wealth building.")
        
        # Category-specific recommendations
        if 'category' in df.columns:
            expenses_df = df[df['type'] == 'debit']
            category_totals = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=False)
            
            # Food & Dining recommendations
            if 'Food & Dining' in category_totals.index:
                food_spending = category_totals['Food & Dining']
                food_pct = (food_spending / total_expenses) * 100 if total_expenses > 0 else 0
                
                if food_pct > 25:
                    recommendations.append("You're spending over 25% of your budget on dining out. Consider meal planning and cooking at home more often.")
            
            # Transportation recommendations
            if 'Transportation' in category_totals.index:
                transport_spending = category_totals['Transportation']
                transport_pct = (transport_spending / total_expenses) * 100 if total_expenses > 0 else 0
                
                if transport_pct > 20:
                    recommendations.append("Transportation costs are high. Consider carpooling, public transport, or working from home if possible.")
            
            # Shopping recommendations
            if 'Shopping' in category_totals.index:
                shopping_spending = category_totals['Shopping']
                shopping_pct = (shopping_spending / total_expenses) * 100 if total_expenses > 0 else 0
                
                if shopping_pct > 15:
                    recommendations.append("Consider implementing a 24-hour rule before making non-essential purchases to reduce impulse buying.")
        
        # Emergency fund recommendation
        monthly_expenses = total_expenses / max(1, len(df['date'].dt.to_period('M').unique()))
        emergency_fund_target = monthly_expenses * 6
        
        recommendations.append(f"Build an emergency fund of ${emergency_fund_target:,.2f} (6 months of expenses) for financial security.")
        
        # Investment recommendations
        if savings_rate > 20:
            recommendations.append("Consider diversifying your savings into investment accounts, retirement funds, or index funds for long-term growth.")
        
        return recommendations
    
    def calculate_financial_health_score(self, df):
        """Calculate a financial health score from 0-100"""
        if df.empty:
            return 0
        
        score = 0
        max_score = 100
        
        # Savings rate (30 points)
        total_income = df[df['type'] == 'credit']['amount'].sum()
        total_expenses = df[df['type'] == 'debit']['amount'].sum()
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        
        if savings_rate >= 20:
            score += 30
        elif savings_rate >= 10:
            score += 20
        elif savings_rate >= 5:
            score += 10
        
        # Budget adherence (25 points)
        if 'category' in df.columns:
            current_date = df['date'].max()
            current_month_start = current_date.replace(day=1)
            current_month_df = df[df['date'] >= current_month_start]
            
            monthly_income = current_month_df[current_month_df['type'] == 'credit']['amount'].sum()
            
            if monthly_income > 0:
                budget_adherence_score = 0
                categories_checked = 0
                
                expenses_df = current_month_df[current_month_df['type'] == 'debit']
                category_spending = expenses_df.groupby('category')['amount'].sum()
                
                for category, recommended_pct in self.category_budgets.items():
                    if category in category_spending.index:
                        actual_amount = category_spending[category]
                        recommended_amount = monthly_income * recommended_pct
                        
                        if actual_amount <= recommended_amount * 1.2:  # Within 20% of budget
                            budget_adherence_score += 1
                        
                        categories_checked += 1
                
                if categories_checked > 0:
                    score += (budget_adherence_score / categories_checked) * 25
        
        # Transaction regularity (20 points)
        transaction_days = df['date'].dt.day.nunique()
        if transaction_days >= 20:  # Regular transactions throughout the month
            score += 20
        elif transaction_days >= 15:
            score += 15
        elif transaction_days >= 10:
            score += 10
        
        # Income stability (25 points)
        income_df = df[df['type'] == 'credit']
        if not income_df.empty:
            monthly_income = income_df.groupby(income_df['date'].dt.to_period('M'))['amount'].sum()
            income_cv = monthly_income.std() / monthly_income.mean() if monthly_income.mean() > 0 else float('inf')
            
            if income_cv < 0.1:  # Very stable income
                score += 25
            elif income_cv < 0.2:
                score += 20
            elif income_cv < 0.3:
                score += 15
            elif income_cv < 0.5:
                score += 10
        
        return min(score, max_score)

