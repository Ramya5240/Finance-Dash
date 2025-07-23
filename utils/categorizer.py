import pandas as pd
import re

class TransactionCategorizer:
    """Categorize transactions based on description patterns"""
    
    def __init__(self):
        self.category_patterns = {
            'Food & Dining': [
                'restaurant', 'cafe', 'coffee', 'starbucks', 'mcdonalds', 'subway',
                'pizza', 'burger', 'food', 'dining', 'doordash', 'uber eats',
                'grubhub', 'swiggy', 'zomato', 'dominos', 'kfc', 'taco bell'
            ],
            'Groceries': [
                'walmart', 'target', 'costco', 'kroger', 'safeway', 'whole foods',
                'trader joe', 'grocery', 'supermarket', 'big bazaar', 'dmart',
                'reliance fresh', 'more', 'spencer'
            ],
            'Transportation': [
                'uber', 'lyft', 'taxi', 'metro', 'bus', 'train', 'airline',
                'gas station', 'shell', 'exxon', 'chevron', 'bp', 'ola',
                'autorickshaw', 'parking', 'toll'
            ],
            'Shopping': [
                'amazon', 'ebay', 'flipkart', 'myntra', 'ajio', 'nike',
                'adidas', 'h&m', 'zara', 'uniqlo', 'walmart', 'target',
                'best buy', 'apple store', 'macy', 'nordstrom'
            ],
            'Entertainment': [
                'netflix', 'spotify', 'disney', 'hulu', 'amazon prime',
                'youtube', 'movie', 'theater', 'cinema', 'concert',
                'hotstar', 'zee5', 'sony liv', 'voot'
            ],
            'Utilities': [
                'electric', 'electricity', 'water', 'gas', 'internet',
                'phone', 'mobile', 'broadband', 'wifi', 'cable',
                'bsnl', 'airtel', 'jio', 'vodafone'
            ],
            'Healthcare': [
                'hospital', 'clinic', 'pharmacy', 'medical', 'doctor',
                'dentist', 'cvs', 'walgreens', 'apollo', 'fortis',
                'max healthcare', 'aiims'
            ],
            'Banking & Finance': [
                'bank', 'atm', 'transfer', 'fee', 'interest', 'loan',
                'credit card', 'mortgage', 'insurance', 'premium',
                'mutual fund', 'sip', 'investment'
            ],
            'Education': [
                'school', 'university', 'college', 'tuition', 'course',
                'udemy', 'coursera', 'khan academy', 'byju', 'unacademy'
            ],
            'Travel': [
                'hotel', 'airbnb', 'booking', 'expedia', 'makemytrip',
                'goibibo', 'yatra', 'cleartrip', 'oyo', 'treebo'
            ],
            'Salary/Income': [
                'salary', 'payroll', 'wages', 'income', 'bonus',
                'dividend', 'interest earned', 'refund'
            ]
        }
    
    def categorize_transactions(self, df):
        """Add category column to transactions DataFrame"""
        if df.empty:
            return df
        
        df = df.copy()
        df['category'] = df['description'].apply(self._categorize_transaction)
        return df
    
    def _categorize_transaction(self, description):
        """Categorize a single transaction based on description"""
        if pd.isna(description):
            return 'Other'
        
        description_lower = str(description).lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern.lower() in description_lower:
                    return category
        
        # Additional pattern matching with regex
        if re.search(r'\b(atm|withdrawal)\b', description_lower):
            return 'Banking & Finance'
        elif re.search(r'\b(transfer|payment)\b', description_lower):
            return 'Banking & Finance'
        elif re.search(r'\b(gas|fuel|petrol|diesel)\b', description_lower):
            return 'Transportation'
        elif re.search(r'\b(medical|health|medicine)\b', description_lower):
            return 'Healthcare'
        
        return 'Other'
    
    def get_category_summary(self, df):
        """Get summary of transactions by category"""
        if df.empty or 'category' not in df.columns:
            return pd.DataFrame()
        
        # Filter for expenses only
        expenses_df = df[df['type'] == 'debit'].copy()
        
        category_summary = expenses_df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        
        category_summary.columns = ['Total Amount', 'Transaction Count', 'Average Amount']
        category_summary = category_summary.sort_values('Total Amount', ascending=False)
        
        return category_summary.reset_index()

