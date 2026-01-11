# Render Deployment Guide

Deploy your procurement bot so the client can access it from **one permanent link** without your PC running.

## What You'll Get
- **Frontend URL**: `https://procurement-bot-frontend.onrender.com` (for client)
- **Backend URL**: `https://procurement-bot-backend.onrender.com` (API)
- **Database**: PostgreSQL hosted on Render

---

## Step 1: Push to GitHub (5 minutes)

1. Create a new repo at https://github.com/new
2. In your project folder, run:

```bash
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/procurement-bot.git
git push -u origin main
```

---

## Step 2: Create PostgreSQL Database (2 minutes)

1. Go to https://render.com (sign up if needed)
2. Click **New +** → **PostgreSQL**
3. Settings:
   - **Name**: `procurement-bot-db`
   - **Database**: `procurement_bot`
   - **User**: `postgres` (auto-filled)
   - **Region**: Choose closest to you
   - **Plan**: **Free** (256MB RAM, 1GB storage)
4. Click **Create Database**
5. **IMPORTANT**: Copy the **Internal Database URL** (looks like: `postgresql://user:pass@hostname/dbname`)
   - Save this for Step 3!

---

## Step 3: Create Backend Service (5 minutes)

1. Click **New +** → **Web Service**
2. Connect your GitHub account and select your repo
3. Settings:
   - **Name**: `procurement-bot-backend`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: (leave blank)
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m backend.main`
   - **Plan**: **Free** (512MB RAM)
   
4. **Environment Variables** (click "Add Environment Variable"):
   ```
   DATABASE_URL = <paste Internal Database URL from Step 2>
   OPENAI_API_KEY = your_actual_openai_api_key_here
   ```

5. Click **Create Web Service**
6. Wait 5-10 minutes for deployment
7. **Copy the URL** (e.g., `https://procurement-bot-backend.onrender.com`)

---

## Step 4: Load Data into Database (3 minutes)

After backend deploys successfully:

1. Go to your backend service → **Shell** tab (or use local terminal)
2. Run this command to upload your Excel data:

```bash
curl -X POST https://procurement-bot-backend.onrender.com/api/load-data
```

3. Wait ~30 seconds for 500 records to load
4. Verify: `https://procurement-bot-backend.onrender.com/api/health` should show `"recordCount": 500`

---

## Step 5: Update Frontend Config (2 minutes)

1. Edit `client/.env.production`:
   ```
   VITE_API_URL=https://procurement-bot-backend.onrender.com
   ```
   (Replace with YOUR actual backend URL from Step 3)

2. Commit and push:
   ```bash
   git add client/.env.production
   git commit -m "Update production API URL"
   git push
   ```

---

## Step 6: Create Frontend Service (5 minutes)

1. Click **New +** → **Static Site**
2. Connect the same GitHub repo
3. Settings:
   - **Name**: `procurement-bot-frontend`
   - **Branch**: `main`
   - **Root Directory**: `client`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Plan**: **Free**

4. Click **Create Static Site**
5. Wait 5-10 minutes for deployment

---

## Step 7: Share with Client

**Client Access URL**: `https://procurement-bot-frontend.onrender.com`

Login credentials:
- **Email**: hassan@liztek.com
- **Password**: 1234

---

## Important Notes

### Free Tier Limitations
- Backend/frontend sleep after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds to wake up
- Database free for 90 days, then $7/month

### Keep Services Active (Optional)
Use a service like **UptimeRobot** (free) to ping your backend every 5 minutes:
- Add monitor: `https://procurement-bot-backend.onrender.com/api/health`

### Troubleshooting

**Backend won't start?**
- Check Render logs for errors
- Verify DATABASE_URL is correct
- Ensure OpenAI API key is valid

**Frontend shows errors?**
- Verify VITE_API_URL matches backend URL
- Check browser console for CORS errors
- Ensure backend is deployed and healthy

**Database empty?**
- Re-run: `curl -X POST <backend-url>/api/load-data`
- Check backend logs during data load

---

## Total Time: ~25 minutes
## Total Cost: $0/month (first 90 days), then $7/month for database
