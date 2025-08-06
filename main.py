from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

from database import get_db, engine
from models import Base, Member, Contribution, Month
from schemas import MemberCreate, ContributionCreate, MonthCreate
from services import WhatsAppService, FinancialService

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WhatsApp Financial Tracker", version="1.0.0")

# Initialize services
whatsapp_service = WhatsAppService()
financial_service = FinancialService()

# Admin phone numbers (replace with actual admin phone numbers)
ADMIN_PHONES = ["254700000000", "254711111111"]  # Add your admin phone numbers here

@app.get("/")
async def root():
    return {"message": "WhatsApp Financial Tracker API"}

@app.post("/webhook")
async def webhook(request: Request):
    """Handle WhatsApp webhook events"""
    try:
        body = await request.json()
        
        # Handle WhatsApp verification
        if "hub_mode" in body and body["hub_mode"] == "subscribe":
            if body["hub_verify_token"] == os.getenv("WHATSAPP_VERIFY_TOKEN"):
                return int(body["hub_challenge"])
            else:
                raise HTTPException(status_code=403, detail="Invalid verify token")
        
        # Handle incoming messages
        if "entry" in body:
            for entry in body["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change["value"].get("messages"):
                            for message in change["value"]["messages"]:
                                await process_message(message)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

async def process_message(message):
    """Process incoming WhatsApp messages"""
    try:
        phone_number = message["from"]
        text = message["text"]["body"].strip()
        
        # Check if sender is admin
        if phone_number not in ADMIN_PHONES:
            await whatsapp_service.send_message(
                phone_number, 
                "You are not authorized to use this system. Please contact an admin."
            )
            return
        
        # Parse command
        parts = text.split()
        if not parts:
            return
        
        command = parts[0].lower()
        
        if command == "addmember":
            await handle_add_member(phone_number, parts[1:])
        elif command == "markpaid":
            await handle_mark_paid(phone_number, parts[1:])
        elif command == "report":
            await handle_report(phone_number, parts[1:])
        elif command == "addmonth":
            await handle_add_month(phone_number, parts[1:])
        elif command == "help":
            await handle_help(phone_number)
        elif command == "initdb":
            await handle_init_db(phone_number)
        elif command == "listmembers":
            await handle_list_members(phone_number)
        else:
            await whatsapp_service.send_message(
                phone_number,
                "Unknown command. Type 'help' for available commands."
            )
    
    except Exception as e:
        print(f"Error processing message: {e}")
        await whatsapp_service.send_message(
            message["from"],
            "An error occurred while processing your request. Please try again."
        )

async def handle_add_member(phone_number: str, args: List[str]):
    """Handle AddMember command"""
    if len(args) < 2:
        await whatsapp_service.send_message(
            phone_number,
            "Usage: AddMember <Name> <Category> [Amount]\nCategories: Parents, GenMillennial, GenAlpha"
        )
        return
    
    name = args[0]
    category = args[1]
    amount = None
    
    if len(args) > 2:
        try:
            amount = int(args[2])
        except ValueError:
            await whatsapp_service.send_message(phone_number, "Invalid amount. Please provide a number.")
            return
    
    # Set default amounts based on category
    if amount is None:
        if category.lower() == "parents":
            amount = 500
        elif category.lower() in ["genmillennial", "genz"]:
            amount = 300
        elif category.lower() == "genalpha":
            amount = 50
        else:
            await whatsapp_service.send_message(
                phone_number,
                "Invalid category. Use: Parents, GenMillennial, or GenAlpha"
            )
            return
    
    try:
        db = next(get_db())
        member = financial_service.add_member(db, name, category, amount)
        await whatsapp_service.send_message(
            phone_number,
            f"✅ Member added successfully!\nName: {member.name}\nCategory: {member.category}\nDefault Amount: {member.default_amount} KES"
        )
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error adding member: {str(e)}")

async def handle_mark_paid(phone_number: str, args: List[str]):
    """Handle MarkPaid command"""
    if len(args) < 2:
        await whatsapp_service.send_message(
            phone_number,
            "Usage: MarkPaid <Name> <Month> [Amount]"
        )
        return
    
    name = args[0]
    month_name = args[1]
    amount = None
    
    if len(args) > 2:
        try:
            amount = int(args[2])
        except ValueError:
            await whatsapp_service.send_message(phone_number, "Invalid amount. Please provide a number.")
            return
    
    try:
        db = next(get_db())
        contribution = financial_service.mark_paid(db, name, month_name, amount)
        await whatsapp_service.send_message(
            phone_number,
            f"✅ Payment recorded!\nMember: {contribution.member.name}\nMonth: {contribution.month.name}\nAmount: {contribution.amount} KES"
        )
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error marking payment: {str(e)}")

async def handle_report(phone_number: str, args: List[str]):
    """Handle Report command"""
    if not args:
        await whatsapp_service.send_message(
            phone_number,
            "Usage: Report <Month>"
        )
        return
    
    month_name = args[0]
    
    try:
        db = next(get_db())
        report = financial_service.generate_report(db, month_name)
        await whatsapp_service.send_message(phone_number, report)
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error generating report: {str(e)}")

async def handle_add_month(phone_number: str, args: List[str]):
    """Handle AddMonth command"""
    if not args:
        await whatsapp_service.send_message(
            phone_number,
            "Usage: AddMonth <MonthName>"
        )
        return
    
    month_name = args[0]
    
    try:
        db = next(get_db())
        month = financial_service.add_month(db, month_name)
        await whatsapp_service.send_message(
            phone_number,
            f"✅ Month added successfully!\nMonth: {month.name}"
        )
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error adding month: {str(e)}")

async def handle_help(phone_number: str):
    """Handle Help command"""
    help_text = """
🤖 *WhatsApp Financial Tracker Commands*

*Admin Commands:*
• `AddMember <Name> <Category> [Amount]` - Add new member
  Categories: Parents (500 KES), GenMillennial/GenZ (300 KES), GenAlpha (50 KES)

• `MarkPaid <Name> <Month> [Amount]` - Mark contribution as paid

• `Report <Month>` - Generate monthly report

• `AddMonth <MonthName>` - Add new month

• `InitDB` - Initialize database with all members

• `ListMembers` - Show all members by category

• `Help` - Show this help message

*Examples:*
• `AddMember Pauline Parents`
• `MarkPaid Pauline August 500`
• `Report August`
• `AddMonth September`
• `InitDB`
• `ListMembers`
"""
    await whatsapp_service.send_message(phone_number, help_text)

async def handle_init_db(phone_number: str):
    """Handle InitDB command - initialize database with members"""
    try:
        from init_db import init_database
        init_database()
        await whatsapp_service.send_message(
            phone_number,
            "✅ Database initialized successfully!\n\n📊 Members added:\n- Parents: 4 members\n- GenMillennial: 4 members\n- GenAlpha: 7 members\n- Total: 15 members\n\nMonths: July to December"
        )
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error initializing database: {str(e)}")

async def handle_list_members(phone_number: str):
    """Handle ListMembers command - show all members"""
    try:
        db = next(get_db())
        members = db.query(Member).order_by(Member.category, Member.name).all()
        
        if not members:
            await whatsapp_service.send_message(phone_number, "No members found in the database.")
            return
        
        # Group by category
        categories = {}
        for member in members:
            if member.category not in categories:
                categories[member.category] = []
            categories[member.category].append(member)
        
        message = "📋 *ALL MEMBERS*\n\n"
        
        for category, category_members in categories.items():
            message += f"*{category}*\n"
            for i, member in enumerate(category_members, 1):
                message += f"{i}. {member.name} - {member.default_amount} KES\n"
            message += "\n"
        
        await whatsapp_service.send_message(phone_number, message)
        
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error listing members: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 