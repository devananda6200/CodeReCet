# Quick Start: Deploy Both on Render (15 Minutes)

## Pre-Flight Check
- [ ] `git push origin main` (latest code on GitHub)
- [ ] Have Render account: https://render.com
- [ ] GitHub connected to Render

---

## Backend (Web Service) - 8 minutes

### 1. Create Web Service
```
https://render.com → New + → Web Service → Select repo
```

| Field | Value |
|-------|-------|
| Name | `ops-safety-backend` |
| Environment | `Docker` |
| Dockerfile path | `backend/Dockerfile` |
| Region | `Oregon` |

### 2. Environment Variables
```
OPS_DEMO_MODE=false
OPS_DEFAULT_BACKEND=pytorch
OPS_ENVIRONMENT=production
OPS_ALLOWED_ORIGINS=["http://localhost:3000"]
```

### 3. Deploy
- Click **Create Web Service**
- Wait 5-10 min for build
- **Save Backend URL**: `https://ops-safety-backend-xxxxx.onrender.com`
- Test: `curl https://ops-safety-backend-xxxxx.onrender.com/health`

---

## Frontend (Static Site) - 5 minutes

### 1. Create Static Site
```
https://render.com → New + → Static Site → Select repo
```

| Field | Value |
|-------|-------|
| Name | `ops-safety-frontend` |
| Build Command | `cd frontend && npm install && npm run build` |
| Publish directory | `frontend/dist` |

### 2. Environment Variables
```
VITE_API_BASE_URL=https://ops-safety-backend-xxxxx.onrender.com
```
*(Use backend URL from previous step)*

### 3. Deploy
- Click **Create Static Site**
- Wait 3-5 min for build
- **Open URL**: `https://ops-safety-frontend-xxxxx.onrender.com`
- You should see the dashboard

---

## Integration - 2 minutes

### 1. Update Backend CORS
On Render Web Service dashboard:
```
Environment → OPS_ALLOWED_ORIGINS
```
Change to:
```
["https://ops-safety-frontend-xxxxx.onrender.com"]
```

### 2. Verify
1. Open frontend URL
2. Press F12 (DevTools)
3. Should see successful WebSocket connection
4. Dashboard should load without errors

---

## ✅ Done!

| Component | Status | URL |
|-----------|--------|-----|
| Backend API | ✅ Running | `https://ops-safety-backend-xxxxx.onrender.com` |
| Frontend Dashboard | ✅ Running | `https://ops-safety-frontend-xxxxx.onrender.com` |
| WebSocket Connection | ✅ OK | Live streaming |

**Total deployment time: ~15 minutes**

---

## Auto-Deploy on Push

```powershell
git add .
git commit -m "Update config"
git push origin main
```

Render will automatically rebuild and deploy within 2-3 minutes.

---

## Troubleshooting

### Problem: Frontend shows "Connecting..."
**Solution**: Wait 10 seconds. If still stuck:
1. Check backend health: `https://backend-url/health`
2. Check browser console (F12) for errors
3. Verify CORS environment variable is set

### Problem: Build fails with "Model not found"
**Solution**: Ensure Git LFS is enabled:
1. Backend Dockerfile has: `RUN apt-get install git-lfs && git lfs install && git lfs pull`
2. Rebuild: Render → Manual Deploy

### Problem: 502 Bad Gateway from backend
**Solution**: 
1. Check backend logs (Render dashboard)
2. Restart: Render Web Service → Settings → Restart Instance
3. Rebuild: Render → Manual Deploy

---

## Next: Custom Domain (Optional)

```
Render Dashboard → Select Service → Settings → Custom Domain
```

Add your domain (e.g., `myapp.com`).

---

For detailed guide, see: [DEPLOY_BOTH_ON_RENDER.md](DEPLOY_BOTH_ON_RENDER.md)
