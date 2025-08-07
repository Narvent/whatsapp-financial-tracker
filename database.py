from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Import psycopg2 explicitly to ensure it's available
try:
    import psycopg2
except ImportError:
    print("Warning: psycopg2 not available, falling back to SQLite")

load_dotenv()

# Database URL - will use environment variable or default to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./financial_tracker.db")

# Handle PostgreSQL URL for Render deployment
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif DATABASE_URL.startswith("postgresql+pg8000://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+pg8000://", "postgresql://", 1)

# Create engine with better error handling and SSL support for Render
try:
    if DATABASE_URL.startswith("postgresql://"):
        # Add SSL parameters for Render PostgreSQL
        if "?" not in DATABASE_URL:
            DATABASE_URL += "?sslmode=require"
        else:
            DATABASE_URL += "&sslmode=require"
    
    engine = create_engine(
        DATABASE_URL, 
        echo=False, 
        pool_pre_ping=True,
        connect_args={
            "sslmode": "require"
        } if DATABASE_URL.startswith("postgresql://") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Warning: Could not create database engine: {e}")
    # Fallback to SQLite if PostgreSQL fails
    DATABASE_URL = "sqlite:///./financial_tracker.db"
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 