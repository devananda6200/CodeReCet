# Deploy Both Frontend & Backend on Render

This guide covers deploying both the API backend and React frontend on Render.

---

## Architecture

```
Render Web Service (Backend)
  └─ FastAPI on port 8000
    └─ /health, /streams, /alerts, /config endpoints

Render Static Site (Frontend)
  └─ React + Vite built app
    └─ Communicates with backend via VITE_API_BASE_URL
```

---

## Pre-Deployment Checklist

- [ ] GitHub repository is public or connected to Render
- [ ] All code committed to GitHub (run `git status`)
- [ ] Model file is tracked with Git LFS (`backend/models/best.pt.zip`)
- [ ] Tests pass locally:
  ```powershell
  # Backend
  cd backend
  pytest tests/

  # Frontend
  cd frontend
  npm run build
  ```
- [ ] No secrets hardcoded in source code

---

## Step 1: Deploy Backend to Render

### 1.1 Create a Web Service

1. Go to [https://render.com](https://render.com) and sign in
2. Click **New +** button
3. Select **Web Service**
4. Under "Connect a repository":
   - Select your GitHub repo
   - If not listed, click "Connect account" to authorize GitHub
5. Fill in the Web Service details:
   - **Name**: `ops-safety-backend`
   - **Environment**: `Docker`
   - **Region**: `Oregon` (recommended) or your preferred region
   - **Branch**: `main`
   - **Dockerfile path**: `backend/Dockerfile`
   - **Docker context**: `./` (root)

### 1.2 Configure Build & Deploy Settings

- **Instance Type**: `Free` (for testing) or `Standard` (for production)
- **Auto-deploy**: Enabled (auto-redeploy on `main` branch push)

### 1.3 Set Environment Variables

Click **Environment** and add these variables:

```
OPS_DEMO_MODE=false
OPS_DEFAULT_BACKEND=pytorch
OPS_DEFAULT_CPU_THREADS=4
OPS_DEFAULT_FRAME_SKIP=2
OPS_ALERT_PERSISTENCE_FRAMES=3
OPS_ADAPTIVE_RESOLUTION=true
OPS_ENVIRONMENT=production
OPS_ALLOWED_ORIGINS=["http://localhost:3000"]
```

*Note: We'll update `OPS_ALLOWED_ORIGINS` after frontend is deployed*

### 1.4 Deploy

1. Click **Create Web Service**
2. Wait for build to complete (5-10 minutes)
   - View build logs in the **Logs** tab
   - Common issues:
     - Model file not found → Git LFS not installed on Render (configure in next section)
     - Port already in use → Render auto-assigns port 8000
3. Once deployed, note your backend URL:
   ```
   https://ops-safety-backend-xxxxx.onrender.com
   ```

### 1.5 Verify Backend is Running

Test the health endpoint:
```powershell
$backendUrl = "https://ops-safety-backend-xxxxx.onrender.com"
Invoke-WebRequest -Uri "$backendUrl/health"
```

Expected response:
```json
{"status": "ok", "model_path": "/app/backend/models/best.pt"}
```

---

### Enable Git LFS on Render (if model file not loading)

If you see "Model not found" errors:

1. In Render Web Service settings, add build command:
   ```bash
   git lfs install && git lfs pull && bash backend/scripts/setup.sh
   ```
   (Render will execute this before building)

2. Or add to `backend/Dockerfile` before `COPY` commands:
   ```dockerfile
   RUN apt-get update && apt-get install -y git-lfs
   RUN git lfs install && git lfs pull
   ```

---

## Step 2: Deploy Frontend to Render (Static Site)

### 2.1 Create a Static Site

1. Go to [https://render.com](https://render.com)
2. Click **New +** button
3. Select **Static Site**
4. Under "Connect a repository":
   - Select your GitHub repo
5. Fill in the Static Site details:
   - **Name**: `ops-safety-frontend`
   - **Branch**: `main`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish directory**: `frontend/dist`

### 2.2 Set Environment Variables

Click **Environment** and add:

```
VITE_API_BASE_URL=https://ops-safety-backend-xxxxx.onrender.com
```

*Use the backend URL from Step 1.5*

### 2.3 Deploy

1. Click **Create Static Site**
2. Wait for build to complete (3-5 minutes)
   - View build logs in the **Logs** tab
3. Once deployed, note your frontend URL:
   ```
   https://ops-safety-frontend-xxxxx.onrender.com
   ```

### 2.4 Verify Frontend is Running

1. Open your frontend URL in browser: `https://ops-safety-frontend-xxxxx.onrender.com`
2. You should see the dashboard with empty streams list
3. To test connection to backend:
   - Open browser DevTools (F12)
   - Go to **Network** or **Console** tab
   - You should see WebSocket connection attempts to your backend URL

---

## Step 3: Update Backend CORS Configuration

Now that both are deployed, update the backend's `OPS_ALLOWED_ORIGINS`:

1. Go to Render Web Service dashboard: `ops-safety-backend-xxxxx`
2. Click **Environment**
3. Update `OPS_ALLOWED_ORIGINS`:
   ```
   ["https://ops-safety-frontend-xxxxx.onrender.com"]
   ```
4. Click **Save** → This triggers automatic redeploy

---

## Step 4: Verify Full Integration

### 4.1 Check Backend Health

```powershell
$backendUrl = "https://ops-safety-backend-xxxxx.onrender.com"
Invoke-WebRequest -Uri "$backendUrl/health" | ConvertFrom-Json
```

### 4.2 Check Frontend

1. Open frontend URL in browser
2. Wait 2-3 seconds for dashboard to load
3. Check browser console for errors (F12)

### 4.3 Test WebSocket Connection

In browser console:
```javascript
const ws = new WebSocket('wss://ops-safety-backend-xxxxx.onrender.com/ws');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.log('Error:', e);
```

---

## Step 5: Monitor Deployments

### View Logs
- **Backend**: Go to Web Service → **Logs** → Select timestamp or "Tail logs"
- **Frontend**: Go to Static Site → **Logs** → Select timestamp or "Tail logs"

### Auto-Redeploy
Both services will automatically redeploy when you push code to `main` branch:
```powershell
git push origin main
```

---

## Troubleshooting

### Frontend keeps showing "connecting..."
**Problem**: Frontend can't reach backend API
**Solution**:
1. Verify `VITE_API_BASE_URL` environment variable is set correctly
2. Check backend health endpoint: `https://backend-url/health`
3. Verify CORS configuration in backend environment variables
4. Force redeploy frontend: Render → **Manual Deploy**

### Backend returns 502 Bad Gateway
**Problem**: Backend service crashed or took too long to start
**Solutions**:
1. Check backend logs: Render → **Logs**
2. Verify model file exists: Look for `Model loaded from...` in logs
3. If Git LFS issue: Enable Git LFS (see section above)
4. Increase timeout in frontend WebSocket config

### Model Not Found Error
**Problem**: PyTorch model not loading
**Solutions**:
1. Verify Git LFS is installed on Render
2. Check backend logs for `Model loaded from...` message
3. Check file size: `du -sh backend/models/best.pt`
4. Re-push code to trigger rebuild: `git commit --allow-empty && git push`

### WebSocket Connection Refused
**Problem**: Frontend can't establish WebSocket
**Solutions**:
1. Verify both services are deployed and running
2. Check CORS headers in backend logs
3. Ensure firewall/security allows WebSocket connections
4. Try HTTP requests first to test basic connectivity

---

## Cost Estimation (Render Free Tier)

| Component | Tier | Cost | Notes |
|-----------|------|------|-------|
| Backend Web Service | Free | $0 (first 750 hrs/month) | Spins down after 15 min inactivity |
| Frontend Static Site | Free | $0 (unlimited) | Always available |
| Bandwidth | Free | 100 GB/month included | Usage beyond 100GB is charged |
| **Total** | - | **$0** | Great for prototyping/demos |

**For Production** (Always-on, high performance):
- Backend: `Standard` (~$12/month)
- Frontend: Free static site
- **Total: ~$12/month**

---

## Next Steps

After successful deployment:

1. **Add custom domain** (optional):
   - Frontend: Render → Settings → Custom Domain
   - Backend: Render → Settings → Custom Domain

2. **Set up monitoring**:
   - Render → Blueprints → Add alerts for CPU/memory

3. **Connect to database** (if needed):
   - Render offers PostgreSQL, MySQL, Redis services
   - See Render docs for integration

4. **Enable automatic backups** (for production):
   - Render → Settings → Backups

---

## Deploy Script (Optional)

Create `deploy.sh` to automate deployment:

```bash
#!/bin/bash
set -e

echo "🚀 Deploying to Render..."

# Commit and push
git add .
git commit -m "Deploy updates" || true
git push origin main

echo "✅ Pushed to GitHub"
echo "ℹ️ Render will auto-deploy from main branch"
echo "📊 Check build status:"
echo "   Backend: https://dashboard.render.com"
echo "   Frontend: https://dashboard.render.com"
```

Save as `deploy.sh`, then:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Summary

| Step | Time | Status |
|------|------|--------|
| Backend deployment | 5-10 min | ✅ Running |
| Frontend deployment | 3-5 min | ✅ Running |
| Integration testing | 5 min | ✅ Complete |
| **Total** | **~20 min** | **✅ Live on Production** |

Your application is now live and ready to use!
