# Procurement AI Deployment Guide

## Prerequisites
1. GitHub account
2. Render account (render.com) - Sign up with GitHub
3. Vercel account (vercel.com) - Sign up with GitHub
4. OpenAI API key

---

## Step 1: Push to GitHub

```bash
cd c:\Users\HP\OneDrive\Desktop\bot
git init
git add .
git commit -m "Initial commit - Procurement AI Chatbot"
# Create new repo on GitHub, then:
git remote add origin https://github.com/hasanshahidd/procurement-bot.git
git push -u origin main
```

---

## Step 2: Deploy Database & Backend on Render

### A. Create PostgreSQL Database
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Settings:
   - Name: `procurement-bot-db`
   - Database: `procurement_bot`
   - User: `postgres`
   - Region: Choose closest to you
   - Instance Type: **Free**
4. Click **"Create Database"**
5. **Copy the Internal Database URL** (starts with `postgresql://`)

### B. Deploy Backend
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Settings:
   - Name: `procurement-bot-api`
   - Region: Same as database
   - Branch: `main`
   - Root Directory: Leave blank
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: **Free**

4. **Environment Variables** (click "Add Environment Variable"):
   ```
   OPENAI_API_KEY = your_actual_openai_key
   DATABASE_URL = (paste the Internal Database URL from step A)
   PYTHONPATH = .
   ```

5. Click **"Create Web Service"**
6. Wait 5-10 minutes for deployment
7. **Copy your backend URL**: `https://procurement-bot-api.onrender.com`

### C. Load Database Data
Once deployed, go to your web service → **Shell** tab:
```bash
python
from backend.services.excel_loader import ExcelLoader
from backend.services.database import DatabaseService

db = DatabaseService()
loader = ExcelLoader()
# Upload your Excel file first, then load it
```

---

## Step 3: Deploy Frontend on Vercel

### A. Update Frontend Config
1. Create `client/.env.production`:
```
VITE_API_URL=https://procurement-bot-api.onrender.com
```

2. Commit changes:
```bash
git add client/.env.production
git commit -m "Add production API URL"
git push
```

### B. Deploy to Vercel
1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Settings:
   - Framework Preset: **Vite**
   - Root Directory: `client`
   - Build Command: `npm run build`
   - Output Directory: `dist/public`
   
4. **Environment Variables**:
   ```
   VITE_API_URL = https://procurement-bot-api.onrender.com
   ```

5. Click **"Deploy"**
6. Your app will be live at: `https://your-app.vercel.app`

---

## Step 4: Configure CORS

Update `backend/main.py` with your Vercel URL:

```python
origins = [
    "http://localhost:5173",
    "https://your-app.vercel.app",  # Add this
]
```

Commit and push → Render will auto-redeploy.

---

## Testing Deployment

1. Visit your Vercel URL
2. Login with: hassan@liztek.com / 1234
3. Test queries:
   - "What is the total budget?"
   - "Show pending CEO approvals"

---

## Troubleshooting

**Backend not starting?**
- Check Render logs for errors
- Verify DATABASE_URL is correct
- Ensure OPENAI_API_KEY is set

**Frontend can't connect?**
- Check VITE_API_URL matches backend URL
- Verify CORS origins include Vercel URL
- Check browser console for errors

**Database empty?**
- Load Excel data via Render Shell
- Or use pgAdmin to connect and import

---

## Costs

- **Render Free Tier**: Backend + Database (sleeps after 15 min inactivity)
- **Vercel Free Tier**: Frontend (unlimited bandwidth)
- **Total**: $0/month (OpenAI API costs separately)

---

## Next Steps

1. Set up custom domain (optional)
2. Configure automatic database backups
3. Set up monitoring/alerts
4. Enable HTTPS (automatic on both platforms)
