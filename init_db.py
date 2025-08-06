from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Member, Month
from services import FinancialService
from datetime import datetime

def init_database():
    """Initialize database with members and initial months"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    financial_service = FinancialService()
    
    try:
        # Add initial months (July to December)
        months = ["July", "August", "September", "October", "November", "December"]
        for month_name in months:
            try:
                financial_service.add_month(db, month_name)
                print(f"✅ Added month: {month_name}")
            except ValueError as e:
                print(f"Month {month_name} already exists: {e}")
        
        # Define members with their categories and default amounts
        members_data = [
            # Parents (500 KES default)
            {"name": "Pauline Nthenya", "category": "Parents", "default_amount": 500},
            {"name": "Jeniffer Wayua", "category": "Parents", "default_amount": 500},
            {"name": "Agnes Mwende", "category": "Parents", "default_amount": 500},
            {"name": "Cynthia Nzilani", "category": "Parents", "default_amount": 500},
            
            # Gen Millennial/Z (300 KES default)
            {"name": "Sharon Mwende", "category": "GenMillennial", "default_amount": 300},
            {"name": "Ian Kyalo", "category": "GenMillennial", "default_amount": 300},
            {"name": "Yvonne Wanza", "category": "GenMillennial", "default_amount": 300},
            {"name": "Churchill Omariba", "category": "GenMillennial", "default_amount": 300},
            
            # Gen Alpha (50 KES default)
            {"name": "Oscar Mandela", "category": "GenAlpha", "default_amount": 50},
            {"name": "Martin Mutua", "category": "GenAlpha", "default_amount": 50},
            {"name": "Shannel Nthenya", "category": "GenAlpha", "default_amount": 50},
            {"name": "Victor Mutua", "category": "GenAlpha", "default_amount": 50},
            {"name": "Wayne Wambua", "category": "GenAlpha", "default_amount": 50},
            {"name": "Varsha Mutheu", "category": "GenAlpha", "default_amount": 50},
            {"name": "Angel Wanza", "category": "GenAlpha", "default_amount": 50},
        ]
        
        # Add members
        for member_data in members_data:
            try:
                financial_service.add_member(
                    db, 
                    member_data["name"], 
                    member_data["category"], 
                    member_data["default_amount"]
                )
                print(f"✅ Added member: {member_data['name']} ({member_data['category']})")
            except ValueError as e:
                print(f"Member {member_data['name']} already exists: {e}")
        
        print("\n🎉 Database initialization completed!")
        print("\n📊 Summary:")
        print("- Parents: 4 members (500 KES each)")
        print("- GenMillennial: 4 members (300 KES each)")
        print("- GenAlpha: 7 members (50 KES each)")
        print("- Total: 15 members")
        print("- Months: July to December")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 