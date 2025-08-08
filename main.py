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
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, engine
from models import Base, Member, Contribution, Month
from schemas import MemberCreate, ContributionCreate, MonthCreate
from services import WhatsAppService, FinancialService

# Load environment variables
load_dotenv()

# Create database tables (only if not in production or if database doesn't exist)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create database tables: {e}")

app = FastAPI(title="Financial Tracker App", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Initialize services
whatsapp_service = WhatsAppService()
financial_service = FinancialService()

# Admin phone numbers (replace with actual admin phone numbers)
ADMIN_PHONES = ["+254741065862"]  # Your WhatsApp number with country code and + prefix

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        # Return a simple error page if database is not available
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Database connection error: {str(e)}"
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

@app.get("/webhook")
async def webhook_test():
    """Test endpoint to verify webhook is accessible"""
    return {"message": "Webhook endpoint is accessible", "status": "ok"}

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
        print(f"🔍 Checking if {from_number} is in admin list: {ADMIN_PHONES}")
        
        # Check if sender is admin
        is_admin = from_number in ADMIN_PHONES
        
        if not is_admin:
            print(f"❌ Phone number {from_number} not found in admin list: {ADMIN_PHONES}")
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
        
        if command == "addmember" or command == "1a":
            await handle_add_member(phone_number, parts[1:])
        elif command == "markpaid" or command == "2a":
            await handle_mark_paid(phone_number, parts[1:])
        elif command == "report" or command == "2r":
            await handle_report(phone_number, parts[1:])
        elif command == "addmonth" or command == "3a":
            await handle_add_month(phone_number, parts[1:])
        elif command in ["help", "5", "menu"]:
            await handle_help(phone_number)
        elif command == "initdb" or command == "4i":
            await handle_init_db(phone_number)
        elif command in ["listmembers", "1", "members"]:
            await handle_list_members(phone_number)
        elif command == "2":
            await handle_list_contributions(phone_number)
        elif command == "3":
            await handle_list_months(phone_number)
        elif command == "4" or command == "dashboard":
            await handle_dashboard(phone_number)
        elif command == "4s":
            await handle_statistics(phone_number)
        elif command == "5c":
            await handle_examples(phone_number)
        else:
            await whatsapp_service.send_message(
                phone_number,
                "❓ Unknown command. Type `menu` or `5` for the interactive menu."
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
🤖 *WhatsApp Financial Tracker - Interactive Menu*

*Main Menu Options:*
1️⃣ *Members Management*
   • `1` - List all members
   • `1a <Name> <Category>` - Add new member
   • `1e <Name>` - Edit member
   • `1d <Name>` - Delete member

2️⃣ *Contributions*
   • `2` - View all contributions
   • `2a <Name> <Month> [Amount]` - Mark payment
   • `2r <Month>` - Monthly report

3️⃣ *Months Management*
   • `3` - List all months
   • `3a <MonthName>` - Add new month

4️⃣ *Quick Actions*
   • `4` - Dashboard overview
   • `4i` - Initialize database
   • `4s` - Statistics summary

5️⃣ *Help & Support*
   • `5` - Show this menu
   • `5c` - Command examples

*Quick Commands:*
• `menu` - Show main menu
• `dashboard` - Quick overview
• `members` - List all members
• `report <Month>` - Monthly report

*Examples:*
• `1a Pauline Parents` - Add Pauline to Parents category
• `2a Pauline August 500` - Mark Pauline paid for August
• `2r August` - August monthly report
• `4` - Dashboard overview
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

async def handle_list_contributions(phone_number: str):
    """Handle ListContributions command - show all contributions"""
    try:
        db = next(get_db())
        contributions = db.query(Contribution).join(Member).join(Month).order_by(Contribution.paid_at.desc()).all()
        
        if not contributions:
            await whatsapp_service.send_message(phone_number, "📊 No contributions found in the database.")
            return
        
        message = "💰 *ALL CONTRIBUTIONS*\n\n"
        
        for i, contribution in enumerate(contributions[:10], 1):  # Show last 10
            message += f"{i}. {contribution.member.name} - {contribution.month.name} - {contribution.amount} KES\n"
        
        if len(contributions) > 10:
            message += f"\n... and {len(contributions) - 10} more contributions"
        
        await whatsapp_service.send_message(phone_number, message)
        
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error listing contributions: {str(e)}")

async def handle_list_months(phone_number: str):
    """Handle ListMonths command - show all months"""
    try:
        db = next(get_db())
        months = db.query(Month).order_by(Month.name).all()
        
        if not months:
            await whatsapp_service.send_message(phone_number, "📅 No months found in the database.")
            return
        
        message = "📅 *ALL MONTHS*\n\n"
        
        for i, month in enumerate(months, 1):
            message += f"{i}. {month.name}\n"
        
        await whatsapp_service.send_message(phone_number, message)
        
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error listing months: {str(e)}")

async def handle_dashboard(phone_number: str):
    """Handle Dashboard command - show overview"""
    try:
        db = next(get_db())
        
        # Get statistics
        total_members = db.query(Member).count()
        total_months = db.query(Month).count()
        total_contributions = db.query(Contribution).count()
        
        # Calculate total amount
        total_amount_result = db.query(Contribution).with_entities(
            func.sum(Contribution.amount)
        ).scalar()
        total_amount = total_amount_result if total_amount_result is not None else 0
        
        # Get recent contributions
        recent_contributions = db.query(Contribution).join(Member).join(Month).order_by(Contribution.paid_at.desc()).limit(3).all()
        
        message = f"""
📊 *DASHBOARD OVERVIEW*

*Statistics:*
👥 Total Members: {total_members}
📅 Total Months: {total_months}
💰 Total Contributions: {total_contributions}
💵 Total Amount: {total_amount:,} KES

*Recent Contributions:*
"""
        
        for contribution in recent_contributions:
            message += f"• {contribution.member.name} - {contribution.month.name} - {contribution.amount} KES\n"
        
        if not recent_contributions:
            message += "No recent contributions"
        
        message += "\n*Quick Actions:*\n• `1` - View all members\n• `2` - View contributions\n• `2r <Month>` - Monthly report"
        
        await whatsapp_service.send_message(phone_number, message)
        
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error generating dashboard: {str(e)}")

async def handle_statistics(phone_number: str):
    """Handle Statistics command - show detailed statistics"""
    try:
        db = next(get_db())
        
        # Get statistics by category
        categories = db.query(Member.category, func.count(Member.id)).group_by(Member.category).all()
        
        # Get total contributions by month
        monthly_contributions = db.query(Month.name, func.sum(Contribution.amount)).join(Contribution).group_by(Month.name).all()
        
        message = "📈 *DETAILED STATISTICS*\n\n"
        
        message += "*Members by Category:*\n"
        for category, count in categories:
            message += f"• {category}: {count} members\n"
        
        message += "\n*Contributions by Month:*\n"
        for month, amount in monthly_contributions:
            if amount:
                message += f"• {month}: {amount:,} KES\n"
            else:
                message += f"• {month}: 0 KES\n"
        
        await whatsapp_service.send_message(phone_number, message)
        
    except Exception as e:
        await whatsapp_service.send_message(phone_number, f"Error generating statistics: {str(e)}")

async def handle_examples(phone_number: str):
    """Handle Examples command - show command examples"""
    examples = """
📝 *COMMAND EXAMPLES*

*Adding Members:*
• `1a Pauline Parents` - Add Pauline to Parents category
• `1a John GenMillennial` - Add John to GenMillennial category
• `1a Sarah GenAlpha` - Add Sarah to GenAlpha category

*Marking Payments:*
• `2a Pauline August 500` - Mark Pauline paid 500 KES for August
• `2a John July 300` - Mark John paid 300 KES for July
• `2a Sarah September 50` - Mark Sarah paid 50 KES for September

*Reports:*
• `2r August` - Get August monthly report
• `2r July` - Get July monthly report

*Quick Actions:*
• `4` - Dashboard overview
• `1` - List all members
• `2` - List all contributions
• `3` - List all months

*Navigation:*
• `menu` or `5` - Show main menu
• `dashboard` - Quick overview
"""
    await whatsapp_service.send_message(phone_number, examples)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Broadcast the message to all connected clients
            await manager.broadcast(json.dumps({
                "type": "chat_message",
                "message": message_data.get("message", ""),
                "timestamp": datetime.now().isoformat(),
                "user": message_data.get("user", "Anonymous")
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_left",
            "message": "A user left the chat",
            "timestamp": datetime.now().isoformat()
        }))

@app.get("/manifest.json")
async def get_manifest():
    """Serve PWA manifest"""
    manifest = {
        "name": "Financial Tracker App",
        "short_name": "FinTracker",
        "description": "A modern financial tracking application with real-time chat",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#25d366",
        "theme_color": "#25d366",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JSONResponse(content=manifest)