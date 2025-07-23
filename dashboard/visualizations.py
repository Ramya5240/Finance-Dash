import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DashboardVisualizations:
    """Create various visualizations for the financial dashboard"""
    
    def __init__(self):
        self.color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
    
    def create_monthly_trends_chart(self, df):
        """Create monthly income vs expense trends chart"""
        if df.empty:
            return go.Figure()
        
        df = df.copy()
        df['month'] = df['date'].dt.to_period('M').astype(str)
        
        monthly_data = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
        
        if monthly_data.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        if 'credit' in monthly_data.columns:
            fig.add_trace(go.Scatter(
                x=monthly_data.index,
                y=monthly_data['credit'],
                mode='lines+markers',
                name='Income',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(size=8)
            ))
        
        if 'debit' in monthly_data.columns:
            fig.add_trace(go.Scatter(
                x=monthly_data.index,
                y=monthly_data['debit'],
                mode='lines+markers',
                name='Expenses',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ))
        
        # Add savings line
        if 'credit' in monthly_data.columns and 'debit' in monthly_data.columns:
            savings = monthly_data['credit'] - monthly_data['debit']
            fig.add_trace(go.Scatter(
                x=monthly_data.index,
                y=savings,
                mode='lines+markers',
                name='Net Savings',
                line=dict(color='#45B7D1', width=3, dash='dash'),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            title='Monthly Financial Trends',
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            hovermode='x unified',
            height=400
        )
        
        return fig
    
    def create_expense_category_pie(self, df):
        """Create pie chart for expense categories"""
        if df.empty or 'category' not in df.columns:
            return go.Figure()
        
        expenses_df = df[df['type'] == 'debit']
        
        if expenses_df.empty:
            return go.Figure()
        
        category_totals = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        
        # Group smaller categories into "Other"
        top_categories = category_totals.head(8)
        other_amount = category_totals.tail(-8).sum()
        
        if other_amount > 0:
            top_categories['Other'] = other_amount
        
        fig = px.pie(
            values=top_categories.values,
            names=top_categories.index,
            title='Expense Distribution by Category',
            color_discrete_sequence=self.color_palette
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
        )
        
        fig.update_layout(height=400)
        
        return fig
    
    def create_category_bar_chart(self, df):
        """Create horizontal bar chart for top expense categories"""
        if df.empty or 'category' not in df.columns:
            return go.Figure()
        
        expenses_df = df[df['type'] == 'debit']
        
        if expenses_df.empty:
            return go.Figure()
        
        category_totals = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=True).tail(10)
        
        fig = go.Figure(go.Bar(
            x=category_totals.values,
            y=category_totals.index,
            orientation='h',
            marker_color=self.color_palette[0],
            text=[f'${x:,.0f}' for x in category_totals.values],
            textposition='outside'
        ))
        
        fig.update_layout(
            title='Top Spending Categories',
            xaxis_title='Amount ($)',
            yaxis_title='Category',
            height=400,
            margin=dict(l=150)
        )
        
        return fig
    
    def create_time_comparison_chart(self, df):
        """Create comparison chart for different time periods"""
        if df.empty:
            return go.Figure()
        
        current_date = df['date'].max()
        
        periods = {
            'Last 1 Month': current_date - timedelta(days=30),
            'Last 3 Months': current_date - timedelta(days=90),
            'Last 6 Months': current_date - timedelta(days=180),
            'Last 12 Months': current_date - timedelta(days=365)
        }
        
        comparison_data = []
        
        for period_name, start_date in periods.items():
            period_df = df[df['date'] >= start_date]
            
            if not period_df.empty:
                total_income = period_df[period_df['type'] == 'credit']['amount'].sum()
                total_expenses = period_df[period_df['type'] == 'debit']['amount'].sum()
                net_savings = total_income - total_expenses
                
                comparison_data.append({
                    'Period': period_name,
                    'Income': total_income,
                    'Expenses': total_expenses,
                    'Net Savings': net_savings
                })
        
        if not comparison_data:
            return go.Figure()
        
        comparison_df = pd.DataFrame(comparison_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Income',
            x=comparison_df['Period'],
            y=comparison_df['Income'],
            marker_color='#4ECDC4'
        ))
        
        fig.add_trace(go.Bar(
            name='Expenses',
            x=comparison_df['Period'],
            y=comparison_df['Expenses'],
            marker_color='#FF6B6B'
        ))
        
        fig.add_trace(go.Scatter(
            name='Net Savings',
            x=comparison_df['Period'],
            y=comparison_df['Net Savings'],
            mode='lines+markers',
            marker_color='#45B7D1',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Financial Comparison Across Time Periods',
            xaxis_title='Time Period',
            yaxis_title='Amount ($)',
            yaxis2=dict(
                title='Net Savings ($)',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=400
        )
        
        return fig
    
    def create_daily_spending_chart(self, df, days=30):
        """Create daily spending chart for recent days"""
        if df.empty:
            return go.Figure()
        
        recent_date = df['date'].max() - timedelta(days=days)
        recent_df = df[df['date'] >= recent_date]
        
        if recent_df.empty:
            return go.Figure()
        
        daily_spending = recent_df[recent_df['type'] == 'debit'].groupby('date')['amount'].sum()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_spending.index,
            y=daily_spending.values,
            mode='lines+markers',
            name='Daily Spending',
            line=dict(color='#FF6B6B', width=2),
            marker=dict(size=6),
            fill='tonexty'
        ))
        
        # Add average line
        avg_spending = daily_spending.mean()
        fig.add_hline(
            y=avg_spending,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Average: ${avg_spending:.2f}"
        )
        
        fig.update_layout(
            title=f'Daily Spending - Last {days} Days',
            xaxis_title='Date',
            yaxis_title='Amount ($)',
            hovermode='x unified',
            height=300
        )
        
        return fig
    
    def create_savings_rate_chart(self, df):
        """Create savings rate chart over time"""
        if df.empty:
            return go.Figure()
        
        df = df.copy()
        df['month'] = df['date'].dt.to_period('M')
        
        monthly_data = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
        
        if monthly_data.empty or 'credit' not in monthly_data.columns:
            return go.Figure()
        
        monthly_data['savings_rate'] = ((monthly_data.get('credit', 0) - monthly_data.get('debit', 0)) / 
                                       monthly_data['credit'] * 100).fillna(0)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_data.index.astype(str),
            y=monthly_data['savings_rate'],
            mode='lines+markers',
            name='Savings Rate',
            line=dict(color='#45B7D1', width=3),
            marker=dict(size=8),
            fill='tonexty'
        ))
        
        # Add target line at 20%
        fig.add_hline(
            y=20,
            line_dash="dash",
            line_color="green",
            annotation_text="Target: 20%"
        )
        
        fig.update_layout(
            title='Monthly Savings Rate',
            xaxis_title='Month',
            yaxis_title='Savings Rate (%)',
            hovermode='x unified',
            height=300
        )
        
        return fig

