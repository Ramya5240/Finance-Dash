"""
Database models for the Finance Tracker application
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    """User model for multi-user support"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    bank_accounts = relationship("BankAccount", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

class BankAccount(Base):
    """Bank account model"""
    __tablename__ = 'bank_accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    bank_name = Column(String(100), nullable=False)  # chase, wells_fargo, etc.
    account_name = Column(String(100), nullable=False)  # Checking, Savings, etc.
    account_number_last4 = Column(String(4))  # Last 4 digits for identification
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="bank_accounts")
    transactions = relationship("Transaction", back_populates="bank_account", cascade="all, delete-orphan")

class Transaction(Base):
    """Transaction model"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    bank_account_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=False)
    
    # Transaction details
    date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(10), nullable=False)  # credit, debit
    category = Column(String(50), default='Other')
    
    # Metadata
    original_file_name = Column(String(255))
    imported_at = Column(DateTime, default=datetime.utcnow)
    is_duplicate = Column(Boolean, default=False)
    
    # Hash for duplicate detection
    transaction_hash = Column(String(64), index=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    bank_account = relationship("BankAccount", back_populates="transactions")

class UploadedFile(Base):
    """Track uploaded files to prevent re-processing"""
    __tablename__ = 'uploaded_files'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    bank_detected = Column(String(50))
    transactions_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(20), default='pending')  # pending, processed, failed

class Category(Base):
    """Category management for customization"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7))  # Hex color code
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserPreference(Base):
    """User preferences and settings"""
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    preference_key = Column(String(50), nullable=False)
    preference_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class FinancialGoal(Base):
    """Financial goals and budgets"""
    __tablename__ = 'financial_goals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category = Column(String(50), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    goal_type = Column(String(20), nullable=False)  # monthly_budget, savings_goal
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection and session management

def get_database_url():
    """Get database URL from environment variables, default to SQLite"""
    return os.getenv('DATABASE_URL', 'sqlite:///finance.db')

def create_engine_instance():
    """Create SQLAlchemy engine"""
    database_url = get_database_url()
    return create_engine(database_url, echo=True)

def get_session():
    """Get a database session"""
    engine = create_engine_instance()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def init_database():
    """Initialize database schema and return session factory"""
    engine = create_engine_instance()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)    
    # Create default categories
    session = get_session()
    try:
        default_categories = [
            {'name': 'Food & Dining', 'color': '#FF6B6B'},
            {'name': 'Groceries', 'color': '#4ECDC4'},
            {'name': 'Transportation', 'color': '#45B7D1'},
            {'name': 'Shopping', 'color': '#96CEB4'},
            {'name': 'Entertainment', 'color': '#FFEAA7'},
            {'name': 'Utilities', 'color': '#DDA0DD'},
            {'name': 'Healthcare', 'color': '#98D8C8'},
            {'name': 'Banking & Finance', 'color': '#F7DC6F'},
            {'name': 'Education', 'color': '#BB8FCE'},
            {'name': 'Travel', 'color': '#85C1E9'},
            {'name': 'Salary/Income', 'color': '#58D68D'},
            {'name': 'Other', 'color': '#BDC3C7'}
        ]
        
        for cat_data in default_categories:
            existing = session.query(Category).filter_by(name=cat_data['name']).first()
            if not existing:
                category = Category(**cat_data)
                session.add(category)
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error initializing categories: {e}")
    finally:
        session.close()
