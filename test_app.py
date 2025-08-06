#!/usr/bin/env python3
"""
Test script for WhatsApp Financial Tracker
Run this to test the application functionality
"""

import asyncio
from database import SessionLocal, engine
from models import Base, Member, Month, Contribution
from services import FinancialService
from init_db import init_database

def test_database():
    """Test database functionality"""
    print("🧪 Testing WhatsApp Financial Tracker...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize database
    print("\n📊 Initializing database...")
    init_database()
    
    # Test financial service
    db = SessionLocal()
    financial_service = FinancialService()
    
    try:
        # Test adding a contribution
        print("\n💰 Testing contribution recording...")
        contribution = financial_service.mark_paid(db, "Pauline Nthenya", "August", 500)
        print(f"✅ Payment recorded: {contribution.member.name} - {contribution.amount} KES for {contribution.month.name}")
        
        # Test generating report
        print("\n📈 Testing report generation...")
        report = financial_service.generate_report(db, "August")
        print("✅ Report generated successfully!")
        print("\n" + "="*50)
        print("REPORT PREVIEW:")
        print("="*50)
        print(report)
        print("="*50)
        
        # Test listing members
        print("\n👥 Testing member listing...")
        members = db.query(Member).order_by(Member.category, Member.name).all()
        print(f"✅ Found {len(members)} members:")
        
        categories = {}
        for member in members:
            if member.category not in categories:
                categories[member.category] = []
            categories[member.category].append(member)
        
        for category, category_members in categories.items():
            print(f"\n{category}:")
            for member in category_members:
                print(f"  - {member.name} ({member.default_amount} KES)")
        
        print("\n🎉 All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database() 