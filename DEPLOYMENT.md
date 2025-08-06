# Deployment Guide for WhatsApp Financial Tracker

## Prerequisites

1. **GitHub Account**: Push your code to GitHub
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **WhatsApp Business API**: Set up WhatsApp Business API access

## Step 1: Prepare Your Repository

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: WhatsApp Financial Tracker"
   git branch -M main
   git remote add origin https://github.com/yourusername/whatsapp-financial-tracker.git
   git push -u origin main
   ```

## Step 2: Set Up WhatsApp Business API

1. **Create Meta Developer Account**:
   - Go to [developers.facebook.com](https://developers.facebook.com)
   - Create a new app
   - Add WhatsApp Business API product

2. **Configure WhatsApp Business API**:
   - Get your `WHATSAPP_ACCESS_TOKEN`
   - Get your `WHATSAPP_PHONE_NUMBER_ID`
   - Create a custom `WHATSAPP_VERIFY_TOKEN`

## Step 3: Deploy on Render

### 3.1 Create PostgreSQL Database

1. **In Render Dashboard**:
   - Click "New" → "PostgreSQL"
   - Name: `whatsapp-financial-tracker-db`
   - Database: `financial_tracker`
   - User: `financial_tracker_user`
   - Note the connection string

### 3.2 Deploy Web Service

1. **Connect Repository**:
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Name: `whatsapp-financial-tracker`

2. **Configure Build Settings**:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**:
   ```
   DATABASE_URL=postgresql://... (from your PostgreSQL database)
   WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   WHATSAPP_VERIFY_TOKEN=your_verify_token
   ENVIRONMENT=production
   ```

4. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Note your app URL (e.g., `https://your-app.onrender.com`)

## Step 4: Configure WhatsApp Webhook

1. **In Meta Developer Console**:
   - Go to your WhatsApp Business API
   - Navigate to "Configuration" → "Webhooks"
   - Click "Configure"

2. **Set Webhook URL**:
   - **Callback URL**: `https://your-app.onrender.com/webhook`
   - **Verify Token**: Use the same value as `WHATSAPP_VERIFY_TOKEN`
   - **Webhook Fields**: Subscribe to `messages`

3. **Test Webhook**:
   - Click "Verify and Save"
   - Ensure verification is successful

## Step 5: Update Admin Phone Numbers

1. **Edit main.py**:
   ```python
   ADMIN_PHONES = ["254700000000", "254711111111"]  # Add actual admin numbers
   ```

2. **Redeploy**:
   - Push changes to GitHub
   - Render will automatically redeploy

## Step 6: Initialize Database

1. **Send WhatsApp Message**:
   - Send `InitDB` to your WhatsApp number
   - This will add all 15 members and 6 months

2. **Verify Setup**:
   - Send `ListMembers` to see all members
   - Send `Report August` to test reporting

## Step 7: Test the System

### Test Commands:

1. **Initialize Database**:
   ```
   InitDB
   ```

2. **List All Members**:
   ```
   ListMembers
   ```

3. **Mark Payments**:
   ```
   MarkPaid Pauline August 500
   MarkPaid Sharon August 300
   MarkPaid Oscar August 50
   ```

4. **Generate Report**:
   ```
   Report August
   ```

5. **Add New Month**:
   ```
   AddMonth September
   ```

## Troubleshooting

### Common Issues:

1. **Database Connection Error**:
   - Check `DATABASE_URL` environment variable
   - Ensure PostgreSQL database is running

2. **WhatsApp API Errors**:
   - Verify `WHATSAPP_ACCESS_TOKEN` is correct
   - Check `WHATSAPP_PHONE_NUMBER_ID` format
   - Ensure webhook URL is accessible

3. **Admin Access Denied**:
   - Update `ADMIN_PHONES` in `main.py`
   - Use full international format (e.g., "254700000000")

4. **Deployment Failures**:
   - Check build logs in Render dashboard
   - Verify all dependencies in `requirements.txt`
   - Ensure Python version compatibility

### Logs and Monitoring:

1. **View Logs**:
   - Go to your Render service dashboard
   - Click "Logs" tab
   - Monitor for errors

2. **Health Check**:
   - Visit `https://your-app.onrender.com/`
   - Should return: `{"message": "WhatsApp Financial Tracker API"}`

## Security Considerations

1. **Environment Variables**:
   - Never commit `.env` files to Git
   - Use Render's environment variable system
   - Rotate tokens regularly

2. **Admin Access**:
   - Only add trusted phone numbers to `ADMIN_PHONES`
   - Use strong verify tokens

3. **Database Security**:
   - Use strong database passwords
   - Enable SSL connections
   - Regular backups

## Maintenance

1. **Regular Updates**:
   - Keep dependencies updated
   - Monitor for security patches
   - Test after updates

2. **Backup Strategy**:
   - Enable automatic PostgreSQL backups
   - Export data regularly
   - Test restore procedures

3. **Monitoring**:
   - Set up alerts for downtime
   - Monitor API usage
   - Track error rates

## Support

For issues or questions:
1. Check Render documentation
2. Review WhatsApp Business API docs
3. Check application logs
4. Test locally before deploying changes 