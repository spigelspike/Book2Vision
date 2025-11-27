# Book2Vision Deployment Guide

## Quick Deploy Options

### Option 1: Render (Recommended - Easiest)

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** book2vision
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python src/server.py`
     
3. **Add Environment Variables:**
   In Render dashboard, go to Environment and add:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   ```

4. **Deploy:** Click "Create Web Service"

### Option 2: Railway

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy:**
   ```bash
   railway login
   railway init
   railway up
   ```

3. **Set Environment Variables:**
   ```bash
   railway variables set GEMINI_API_KEY=your_gemini_api_key_here
   railway variables set ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   railway variables set DEEPSEEK_API_KEY=your_deepseek_api_key_here
   ```

### Option 3: Fly.io (Docker-based)

1. **Install Fly CLI:**
   - Windows: https://fly.io/docs/hands-on/install-flyctl/

2. **Deploy:**
   ```bash
   fly auth signup
   fly launch
   ```

3. **Set Secrets:**
   ```bash
   fly secrets set GEMINI_API_KEY=your_gemini_api_key_here
   fly secrets set ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   fly secrets set DEEPSEEK_API_KEY=your_deepseek_api_key_here
   fly deploy
   ```

### Option 4: Heroku (Classic)

1. **Install Heroku CLI**

2. **Deploy:**
   ```bash
   heroku login
   heroku create book2vision-app
   ```

3. **Set Config:**
   ```bash
   heroku config:set GEMINI_API_KEY=your_gemini_api_key_here
   heroku config:set ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   heroku config:set DEEPSEEK_API_KEY=your_deepseek_api_key_here
   git push heroku main
   ```

## Important Notes

- ⚠️ **Free tier limitations:** Most free tiers have limited uptime/resources
- 💾 **File uploads:** Uploaded files are temporary on most platforms (files get deleted on restart)
- 🔒 **Security:** Never commit `.env` file to Git (it's already in `.gitignore`)
- 📊 **Monitoring:** Check platform logs if something doesn't work

## Free Tier Comparisons

| Platform | Free Tier | Sleep Time | Best For |
|----------|-----------|------------|----------|
| **Render** | 750 hrs/mo | After 15min inactive | Easiest setup |
| **Railway** | $5 credit | No sleep | Good DX |
| **Fly.io** | 3 VMs | No sleep | Docker users |
| **Heroku** | Limited | After 30min inactive | Traditional |

## My Recommendation

**Start with Render** - it's the easiest and has the best free tier for beginners!
