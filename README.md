# WhatsApp Financial Tracker

A WhatsApp-based financial tracking system for managing birthday contributions with member categorization and monthly reporting.

## Features

- **Member Management**: Add members with categories (Parents, GenMillennial/Z, GenAlpha)
- **Contribution Tracking**: Track monthly contributions with default amounts
- **WhatsApp Integration**: Full WhatsApp Cloud API integration for admin commands
- **Monthly Reports**: Generate formatted reports grouped by category
- **Admin Controls**: Add members, mark payments, generate reports via WhatsApp
- **PostgreSQL Database**: Scalable database for production use

## Member Categories & Default Amounts

- **Parents**: 500 KES
  - Pauline Nthenya
  - Jeniffer Wayua
  - Agnes Mwende
  - Cynthia Nzilani

- **GenMillennial/GenZ**: 300 KES
  - Sharon Mwende
  - Ian Kyalo
  - Yvonne Wanza
  - Churchill Omariba

- **GenAlpha**: 50 KES
  - Oscar Mandela
  - Martin Mutua
  - Shannel Nthenya
  - Victor Mutua
  - Wayne Wambua
  - Varsha Mutheu
  - Angel Wanza

## WhatsApp Commands

### Admin Commands

- `AddMember <Name> <Category> [Amount]` - Add new member
- `MarkPaid <Name> <Month> [Amount]` - Mark contribution as paid
- `Report <Month>` - Generate monthly report
- `AddMonth <MonthName>` - Add new month
- `InitDB` - Initialize database with all members
- `ListMembers` - Show all members by category
- `Help` - Show help message

### Examples

```
AddMember Pauline Parents
MarkPaid Pauline August 500
Report August
AddMonth September
InitDB
ListMembers
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- WhatsApp Business API access

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd whatsapp-financial-tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

4. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/financial_tracker

# WhatsApp Cloud API Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here

# Application Configuration
ENVIRONMENT=development
```

## Deployment on Render

### 1. Database Setup

1. Create a new PostgreSQL database on Render
2. Note the connection string

### 2. Application Deployment

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Configure the following:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `DATABASE_URL`: Your PostgreSQL connection string
     - `WHATSAPP_ACCESS_TOKEN`: Your WhatsApp access token
     - `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp phone number ID
     - `WHATSAPP_VERIFY_TOKEN`: Your custom verify token

### 3. WhatsApp Webhook Configuration

1. In your WhatsApp Business API dashboard:
   - Set webhook URL to: `https://your-app-name.onrender.com/webhook`
   - Set verify token to match your `WHATSAPP_VERIFY_TOKEN`
   - Subscribe to `messages` events

2. Update admin phone numbers in `main.py`:
   ```python
   ADMIN_PHONES = ["254700000000", "254711111111"]  # Add actual admin numbers
   ```

## Database Schema

### Members Table
- `id`: Primary key
- `name`: Member name (unique)
- `category`: Member category (Parents, GenMillennial, GenAlpha)
- `default_amount`: Default contribution amount
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Months Table
- `id`: Primary key
- `name`: Month name (unique)
- `created_at`: Creation timestamp

### Contributions Table
- `id`: Primary key
- `member_id`: Foreign key to members
- `month_id`: Foreign key to months
- `amount`: Contribution amount
- `paid`: Payment status
- `paid_at`: Payment timestamp
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## API Endpoints

- `GET /` - Health check
- `POST /webhook` - WhatsApp webhook endpoint

## Report Format

Reports are generated in the following format:

```
🎂💃🏽 SHOSHO'S BIRTHDAY CONTRIBUTION

August Contributions:

Parents
1. Pauline Nthenya - 500/= ✅
2. Jeniffer Wayua - 500/= ✅

GenMillennial
1. John Doe - 300/= ✅

GenAlpha
1. Baby Smith - 50/= ✅

TOTAL: KES 1,350
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License. 