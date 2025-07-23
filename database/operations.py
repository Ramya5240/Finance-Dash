"""
Database operations for the Finance Tracker application
"""

import pandas as pd
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, func, desc
from .models import (
    User, BankAccount, Transaction, UploadedFile, Category, 
    UserPreference, FinancialGoal, get_session, init_database
)

class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self):
        self.session = None
    
    def get_session(self):
        """Get or create database session"""
        if not self.session:
            self.session = get_session()
        return self.session
    
    def close_session(self):
        """Close database session"""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_session()

class UserManager(DatabaseManager):
    """Manages user operations"""
    
    def create_or_get_user(self, username="default_user", email="user@example.com"):
        """Create or get existing user"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                user = User(username=username, email=email)
                session.add(user)
                session.commit()
            return user
        except Exception as e:
            session.rollback()
            raise e
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        session = self.get_session()
        return session.query(User).filter_by(id=user_id).first()

class BankAccountManager(DatabaseManager):
    """Manages bank account operations"""
    
    def create_or_get_account(self, user_id, bank_name, account_name="Primary"):
        """Create or get bank account"""
        session = self.get_session()
        try:
            account = session.query(BankAccount).filter_by(
                user_id=user_id, 
                bank_name=bank_name, 
                account_name=account_name
            ).first()
            
            if not account:
                account = BankAccount(
                    user_id=user_id,
                    bank_name=bank_name,
                    account_name=account_name
                )
                session.add(account)
                session.commit()
            
            return account
        except Exception as e:
            session.rollback()
            raise e
    
    def get_user_accounts(self, user_id):
        """Get all accounts for a user"""
        session = self.get_session()
        return session.query(BankAccount).filter_by(user_id=user_id, is_active=True).all()

class TransactionManager(DatabaseManager):
    """Manages transaction operations"""
    
    def generate_transaction_hash(self, date, amount, description):
        """Generate hash for duplicate detection"""
        hash_string = f"{date.strftime('%Y%m%d')}{amount}{description}"
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def save_transactions(self, transactions_df, user_id, bank_account_id, file_name=None):
        """Save transactions to database"""
        session = self.get_session()
        saved_count = 0
        duplicate_count = 0
        
        try:
            for _, row in transactions_df.iterrows():
                # Generate hash for duplicate detection
                tx_hash = self.generate_transaction_hash(row['date'], row['amount'], row['description'])
                
                # Check for existing transaction
                existing = session.query(Transaction).filter_by(
                    user_id=user_id,
                    transaction_hash=tx_hash
                ).first()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                # Create new transaction
                transaction = Transaction(
                    user_id=user_id,
                    bank_account_id=bank_account_id,
                    date=row['date'],
                    description=row['description'],
                    amount=row['amount'],
                    transaction_type=row['type'],
                    category=row.get('category', 'Other'),
                    original_file_name=file_name,
                    transaction_hash=tx_hash
                )
                
                session.add(transaction)
                saved_count += 1
            
            session.commit()
            return saved_count, duplicate_count
            
        except Exception as e:
            session.rollback()
            raise e
    
    def get_user_transactions(self, user_id, start_date=None, end_date=None, limit=None):
        """Get transactions for a user"""
        session = self.get_session()
        query = session.query(Transaction).filter_by(user_id=user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        query = query.order_by(desc(Transaction.date))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_transactions_as_dataframe(self, user_id, start_date=None, end_date=None):
        """Get transactions as pandas DataFrame"""
        transactions = self.get_user_transactions(user_id, start_date, end_date)
        
        if not transactions:
            return pd.DataFrame()
        
        data = []
        for tx in transactions:
            data.append({
                'id': tx.id,
                'date': tx.date,
                'description': tx.description,
                'amount': tx.amount,
                'type': tx.transaction_type,
                'category': tx.category,
                'bank': tx.bank_account.bank_name if tx.bank_account else 'Unknown'
            })
        
        return pd.DataFrame(data)
    
    def update_transaction_category(self, transaction_id, new_category):
        """Update transaction category"""
        session = self.get_session()
        try:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if transaction:
                transaction.category = new_category
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
    
    def delete_transaction(self, transaction_id, user_id):
        """Delete a transaction"""
        session = self.get_session()
        try:
            transaction = session.query(Transaction).filter_by(
                id=transaction_id, 
                user_id=user_id
            ).first()
            if transaction:
                session.delete(transaction)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e

class FileManager(DatabaseManager):
    """Manages uploaded file tracking"""
    
    def generate_file_hash(self, file_content):
        """Generate hash for file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def is_file_processed(self, file_content):
        """Check if file has been processed before"""
        file_hash = self.generate_file_hash(file_content)
        session = self.get_session()
        return session.query(UploadedFile).filter_by(file_hash=file_hash).first() is not None
    
    def record_file_upload(self, user_id, file_name, file_content, bank_detected, transactions_count):
        """Record file upload"""
        session = self.get_session()
        try:
            file_hash = self.generate_file_hash(file_content)
            
            uploaded_file = UploadedFile(
                user_id=user_id,
                file_name=file_name,
                file_hash=file_hash,
                file_size=len(file_content),
                bank_detected=bank_detected,
                transactions_count=transactions_count,
                processing_status='processed'
            )
            
            session.add(uploaded_file)
            session.commit()
            return uploaded_file
        except Exception as e:
            session.rollback()
            raise e

class AnalyticsManager(DatabaseManager):
    """Manages financial analytics and insights"""
    
    def get_monthly_summary(self, user_id, months=12):
        """Get monthly financial summary"""
        session = self.get_session()
        start_date = datetime.now() - timedelta(days=months * 30)
        
        # Get monthly aggregated data
        monthly_data = session.query(
            func.date_trunc('month', Transaction.date).label('month'),
            Transaction.transaction_type,
            func.sum(Transaction.amount).label('total_amount'),
            func.count(Transaction.id).label('transaction_count')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date
        ).group_by(
            func.date_trunc('month', Transaction.date),
            Transaction.transaction_type
        ).all()
        
        return monthly_data
    
    def get_category_summary(self, user_id, start_date=None, end_date=None):
        """Get category-wise spending summary"""
        session = self.get_session()
        query = session.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total_amount'),
            func.count(Transaction.id).label('transaction_count'),
            func.avg(Transaction.amount).label('avg_amount')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'debit'
        )
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        return query.group_by(Transaction.category).order_by(desc('total_amount')).all()
    
    def get_spending_trends(self, user_id, category=None):
        """Get spending trends for analysis"""
        session = self.get_session()
        query = session.query(
            func.date_trunc('week', Transaction.date).label('week'),
            func.sum(Transaction.amount).label('total_amount')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'debit'
        )
        
        if category:
            query = query.filter(Transaction.category == category)
        
        return query.group_by(func.date_trunc('week', Transaction.date)).order_by('week').all()

# Convenience functions
def init_db():
    """Initialize database tables"""
    init_database()

def get_default_user():
    """Get or create default user for single-user setup"""
    user_mgr = UserManager()
    try:
        user = user_mgr.create_or_get_user()
        # Make sure we have a fresh session
        session = user_mgr.get_session()
        session.refresh(user)
        return user
    finally:
        user_mgr.close_session()
