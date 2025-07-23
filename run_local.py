#!/usr/bin/env python3
"""
Local development runner for Finance Tracker
This script sets up the environment and runs the application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'pdfplumber', 
        'numpy', 'sqlalchemy', 'psycopg2'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_database():
    """Check database connectivity"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable is not set")
        print("Create a .env file or set the environment variable")
        return False
    
    try:
        from database.models import create_engine_instance
        engine = create_engine_instance()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def setup_environment():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Loading .env file")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print("⚠️  .env file not found. Using system environment variables")

def initialize_database():
    """Initialize database tables"""
    try:
        from database.setup import setup_database
        print("🔧 Initializing database...")
        if setup_database():
            print("✅ Database initialized successfully")
            return True
        else:
            print("❌ Database initialization failed")
            return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

def run_application():
    """Run the Streamlit application"""
    port = os.getenv('STREAMLIT_SERVER_PORT', '5000')
    address = os.getenv('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')
    
    print(f"🚀 Starting Finance Tracker on {address}:{port}")
    print(f"Open your browser to: http://localhost:{port}")
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        subprocess.run([
            'streamlit', 'run', 'app.py',
            '--server.port', port,
            '--server.address', address
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except FileNotFoundError:
        print("❌ Streamlit not found. Install with: pip install streamlit")

def main():
    """Main function to run all checks and start the application"""
    print("🏦 Finance Tracker - Local Development Setup")
    print("=" * 50)
    
    # Load environment
    setup_environment()
    
    # Run checks
    if not check_python_version():
        return
    
    if not check_dependencies():
        print("\nInstall dependencies with:")
        print("pip install -r project_requirements.txt")
        return
    
    if not check_database():
        print("\nDatabase setup required. Check COMPLETE_SETUP_GUIDE.md")
        return
    
    # Initialize database
    if not initialize_database():
        return
    
    print("\n🎉 All checks passed! Starting application...")
    print("-" * 50)
    
    # Run application
    run_application()

if __name__ == "__main__":
    main()
