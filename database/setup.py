"""
Database setup and initialization script for Finance Tracker
"""

import os
import sys
from sqlalchemy import create_engine, text
from .models import Base, init_database
from .operations import get_default_user

def setup_database():
    """Setup database tables and initial data"""
    print("Setting up Finance Tracker database...")
    
    try:
        # Initialize database tables
        init_database()
        print("✅ Database tables created successfully")
        
        # Create default user
        user = get_default_user()
        print(f"✅ Default user created: {user.username}")
        
        # Verify database connection
        engine = create_engine(os.getenv('DATABASE_URL'))
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"✅ Database connection verified. Users: {user_count}")
        
        print("\n🎉 Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def reset_database():
    """Reset database (DROP and recreate all tables)"""
    print("⚠️  Resetting Finance Tracker database...")
    
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped")
        
        # Recreate tables
        setup_database()
        
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

def check_database_status():
    """Check database connection and table status"""
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        
        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            print("📊 Database Status:")
            print(f"  Tables found: {len(tables)}")
            for table in sorted(tables):
                print(f"    - {table}")
            
            # Check record counts
            if 'users' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                print(f"  Users: {result.scalar()}")
            
            if 'transactions' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM transactions"))
                print(f"  Transactions: {result.scalar()}")
            
            if 'bank_accounts' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM bank_accounts"))
                print(f"  Bank Accounts: {result.scalar()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "setup":
            setup_database()
        elif command == "reset":
            reset_database()
        elif command == "status":
            check_database_status()
        else:
            print("Usage: python -m database.setup [setup|reset|status]")
    else:
        setup_database()
