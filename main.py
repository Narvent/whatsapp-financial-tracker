from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
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

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page"""
    try:
        # Get statistics
        total_members = db.query(Member).count()
        total_months = db.query(Month).count()
        total_contributions = db.query(Contribution).count()
        
        # Calculate total amount from all contributions
        total_amount_result = db.query(Contribution).with_entities(
            func.sum(Contribution.amount)
        ).scalar()
        total_amount = total_amount_result if total_amount_result is not None else 0
        
        recent_contributions = db.query(Contribution).order_by(Contribution.paid_at.desc()).limit(5).all()
        
        # Get members and months for forms
        members = db.query(Member).all()
        months = db.query(Month).all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "total_members": total_members,
            "total_months": total_months,
            "total_contributions": total_contributions,
            "total_amount": total_amount,
            "recent_contributions": recent_contributions,
            "members": members,
            "months": months
        })
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/members", response_class=HTMLResponse)
async def members_page(request: Request, db: Session = Depends(get_db)):
    """Members management page"""
    try:
        members = db.query(Member).order_by(Member.category, Member.name).all()
        
        return templates.TemplateResponse("members.html", {
            "request": request,
            "members": members
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/contributions", response_class=HTMLResponse)
async def contributions_page(request: Request, db: Session = Depends(get_db)):
    """Contributions management page"""
    try:
        contributions = db.query(Contribution).join(Member).join(Month).all()
        members = db.query(Member).all()
        months = db.query(Month).all()
        
        return templates.TemplateResponse("contributions.html", {
            "request": request,
            "contributions": contributions,
            "members": members,
            "months": months
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, db: Session = Depends(get_db)):
    """Reports page"""
    try:
        months = db.query(Month).all()
        members = db.query(Member).all()
        contributions = db.query(Contribution).all()
        
        return templates.TemplateResponse("reports.html", {
            "request": request,
            "months": months,
            "members": members,
            "contributions": contributions
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

# API endpoints for AJAX calls
@app.post("/api/members")
async def create_member_api(
    name: str = Form(...),
    category: str = Form(...),
    default_amount: int = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new member via API"""
    try:
        member = financial_service.add_member(db, name, category, default_amount)
        return {"success": True, "member": {"id": member.id, "name": member.name, "category": member.category}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/members/{member_id}")
async def get_member_api(member_id: int, db: Session = Depends(get_db)):
    """Get member details via API"""
    try:
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Get member's contributions
        contributions = db.query(Contribution).filter(Contribution.member_id == member_id).all()
        contribution_data = []
        for contrib in contributions:
            month = db.query(Month).filter(Month.id == contrib.month_id).first()
            contribution_data.append({
                "month": month.name if month else "Unknown",
                "amount": contrib.amount,
                "paid": contrib.paid,
                "paid_at": contrib.paid_at.isoformat() if contrib.paid_at else None
            })
        
        return {
            "success": True, 
            "member": {
                "id": member.id,
                "name": member.name,
                "category": member.category,
                "default_amount": member.default_amount,
                "contributions": contribution_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/members/{member_id}")
async def update_member_api(
    member_id: int,
    name: str = Form(...),
    category: str = Form(...),
    default_amount: int = Form(...),
    db: Session = Depends(get_db)
):
    """Update member via API"""
    try:
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        member.name = name
        member.category = category
        member.default_amount = default_amount
        db.commit()
        
        return {"success": True, "message": "Member updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/members/{member_id}")
async def delete_member_api(member_id: int, db: Session = Depends(get_db)):
    """Delete member via API"""
    try:
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Check if member has contributions
        contributions = db.query(Contribution).filter(Contribution.member_id == member_id).count()
        if contributions > 0:
            raise HTTPException(status_code=400, detail="Cannot delete member with existing contributions")
        
        db.delete(member)
        db.commit()
        
        return {"success": True, "message": "Member deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/contributions")
async def create_contribution_api(
    member_id: int = Form(...),
    month_id: int = Form(...),
    amount: int = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new contribution via API"""
    try:
        member = db.query(Member).filter(Member.id == member_id).first()
        month = db.query(Month).filter(Month.id == month_id).first()
        
        if not member or not month:
            raise HTTPException(status_code=404, detail="Member or month not found")
        
        contribution = financial_service.mark_paid(db, member.name, month.name, amount)
        return {"success": True, "contribution": {"id": contribution.id, "amount": contribution.amount}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/contributions/{contribution_id}")
async def delete_contribution_api(contribution_id: int, db: Session = Depends(get_db)):
    """Delete contribution via API"""
    try:
        contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
        if not contribution:
            raise HTTPException(status_code=404, detail="Contribution not found")
        
        # Get member and month names for the response
        member = db.query(Member).filter(Member.id == contribution.member_id).first()
        month = db.query(Month).filter(Month.id == contribution.month_id).first()
        
        member_name = member.name if member else "Unknown"
        month_name = month.name if month else "Unknown"
        
        db.delete(contribution)
        db.commit()
        
        return {
            "success": True, 
            "message": f"Contribution deleted successfully",
            "details": {
                "member": member_name,
                "month": month_name,
                "amount": contribution.amount
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/months")
async def create_month_api(
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new month via API"""
    try:
        month = financial_service.add_month(db, name)
        return {"success": True, "month": {"id": month.id, "name": month.name}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/reports/{month_name}")
async def get_report_api(month_name: str, db: Session = Depends(get_db)):
    """Get report for a specific month"""
    try:
        report = financial_service.generate_report(db, month_name)
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming WhatsApp messages via Twilio webhook"""
    try:
        # Get form data from Twilio webhook
        form_data = await request.form()
        
        # Extract message details from Twilio format
        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        message_body = form_data.get("Body", "").strip()
        
        # Remove "whatsapp:" prefix if present
        if from_number.startswith("whatsapp:"):
            from_number = from_number[9:]  # Remove "whatsapp:" prefix
        
        print(f"📱 Received message from {from_number}: {message_body}")
        
        # Check if sender is admin
        if from_number not in ADMIN_PHONES:
            await whatsapp_service.send_message(
                from_number,
                "❌ Sorry, you don't have permission to use this bot. Contact the administrator."
            )
            return {"success": True}
        
        # Process the message
        await process_message({
            "from": from_number,
            "body": message_body
        })
        
        return {"success": True}
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"success": False, "error": str(e)}

async def process_message(message):
    """Process incoming WhatsApp messages"""
    try:
        phone_number = message["from"]
        text = message["body"].strip()
        
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