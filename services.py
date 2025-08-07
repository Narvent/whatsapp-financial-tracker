import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import Member, Month, Contribution
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

load_dotenv()

class WhatsAppService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            print("⚠️ Warning: Twilio credentials not found. WhatsApp messaging will be disabled.")
    
    async def send_message(self, to: str, message: str):
        """Send WhatsApp message via Twilio"""
        try:
            if not self.client:
                print(f"📱 [SIMULATED] WhatsApp message to {to}: {message}")
                return {"success": True, "message": "Simulated message sent"}
            
            # Format phone number for WhatsApp
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
            
            # Send message via Twilio
            message_obj = self.client.messages.create(
                from_=self.phone_number,
                body=message,
                to=to
            )
            
            print(f"✅ WhatsApp message sent successfully: {message_obj.sid}")
            return {"success": True, "sid": message_obj.sid}
            
        except TwilioException as e:
            print(f"❌ Twilio error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"❌ Error sending WhatsApp message: {e}")
            return {"success": False, "error": str(e)}

class FinancialService:
    def add_member(self, db: Session, name: str, category: str, default_amount: int) -> Member:
        """Add a new member"""
        # Check if member already exists
        existing_member = db.query(Member).filter(Member.name == name).first()
        if existing_member:
            raise ValueError(f"Member '{name}' already exists")
        
        member = Member(
            name=name,
            category=category,
            default_amount=default_amount
        )
        
        db.add(member)
        db.commit()
        db.refresh(member)
        return member
    
    def add_month(self, db: Session, month_name: str) -> Month:
        """Add a new month"""
        # Check if month already exists
        existing_month = db.query(Month).filter(Month.name == month_name).first()
        if existing_month:
            raise ValueError(f"Month '{month_name}' already exists")
        
        month = Month(name=month_name)
        db.add(month)
        db.commit()
        db.refresh(month)
        return month
    
    def mark_paid(self, db: Session, member_name: str, month_name: str, amount: int = None) -> Contribution:
        """Mark a contribution as paid"""
        # Find member
        member = db.query(Member).filter(Member.name == member_name).first()
        if not member:
            raise ValueError(f"Member '{member_name}' not found")
        
        # Find month
        month = db.query(Month).filter(Month.name == month_name).first()
        if not month:
            raise ValueError(f"Month '{month_name}' not found")
        
        # Check if contribution already exists
        contribution = db.query(Contribution).filter(
            Contribution.member_id == member.id,
            Contribution.month_id == month.id
        ).first()
        
        if contribution:
            # Update existing contribution
            contribution.amount = amount or member.default_amount
            contribution.paid = True
            contribution.paid_at = datetime.now()
        else:
            # Create new contribution
            contribution = Contribution(
                member_id=member.id,
                month_id=month.id,
                amount=amount or member.default_amount,
                paid=True,
                paid_at=datetime.now()
            )
            db.add(contribution)
        
        db.commit()
        db.refresh(contribution)
        return contribution
    
    def generate_report(self, db: Session, month_name: str) -> str:
        """Generate monthly report"""
        # Find month
        month = db.query(Month).filter(Month.name == month_name).first()
        if not month:
            raise ValueError(f"Month '{month_name}' not found")
        
        # Get all contributions for the month
        contributions = db.query(Contribution).filter(
            Contribution.month_id == month.id,
            Contribution.paid == True
        ).all()
        
        if not contributions:
            return f"📊 *{month_name} Report*\n\nNo contributions recorded for {month_name}."
        
        # Group by category
        categories = {}
        total_amount = 0
        
        for contribution in contributions:
            category = contribution.member.category
            if category not in categories:
                categories[category] = []
            
            categories[category].append(contribution)
            total_amount += contribution.amount
        
        # Build report
        report = f"🎂💃🏽 *SHOSHO'S BIRTHDAY CONTRIBUTION*\n\n"
        report += f"*{month_name} Contributions:*\n\n"
        
        for category, category_contributions in categories.items():
            report += f"*{category}*\n"
            for i, contribution in enumerate(category_contributions, 1):
                report += f"{i}. {contribution.member.name} - {contribution.amount}/= ✅\n"
            report += "\n"
        
        report += f"*TOTAL: KES {total_amount:,}*"
        
        return report
    
    def get_member_contributions(self, db: Session, member_name: str) -> list:
        """Get all contributions for a member"""
        member = db.query(Member).filter(Member.name == member_name).first()
        if not member:
            raise ValueError(f"Member '{member_name}' not found")
        
        return db.query(Contribution).filter(Contribution.member_id == member.id).all()
    
    def get_month_contributions(self, db: Session, month_name: str) -> list:
        """Get all contributions for a month"""
        month = db.query(Month).filter(Month.name == month_name).first()
        if not month:
            raise ValueError(f"Month '{month_name}' not found")
        
        return db.query(Contribution).filter(Contribution.month_id == month.id).all() 