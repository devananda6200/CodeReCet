# Deployment Checklist: Render + Vercel

Use this checklist to deploy the Ops Safety System to production.

---

## Pre-Deployment ✓

- [ ] All code committed to GitHub
- [ ] `backend/models/best.pt` is present in the repo (or will be added separately)
- [ ] Tested locally: `npm run dev` and backend running
- [ ] All tests pass: `pytest` in backend/
- [ ] No secrets in code files (use environment variables)

---

## Deploy Backend to Render

### Account & Repo Setup
- [ ] Have a Render account (https://render.com)
- [ ] GitHub repo is public or connected to Render
- [ ] Render can access your GitHub repo

### Create Render Web Service
- [ ] Go to Render dashboard
- [ ] Click **New +** → **Web Service**
- [ ] Select your GitHub repo
- [ ] Enter name: `ops-safety-backend`
- [ ] Set environment: `Docker`
- [ ] Set region: `Oregon` (or preferred)
- [ ] Dockerfile path: `backend/Dockerfile`
- [ ] Enable auto-deploy

### Configure Environment Variables in Render
- [ ] `OPS_DEMO_MODE` = `false`
- [ ] `OPS_DEFAULT_BACKEND` = `pytorch`
- [ ] `OPS_DEFAULT_CPU_THREADS` = `4`
- [ ] `OPS_DEFAULT_FRAME_SKIP` = `2`
- [ ] `OPS_ALERT_PERSISTENCE_FRAMES` = `3`
- [ ] `OPS_ADAPTIVE_RESOLUTION` = `true`
- [ ] `OPS_ENVIRONMENT` = `production`
- [ ] `OPS_ALLOWED_ORIGINS` = `["https://your-vercel-frontend-url"]` (update after Vercel deploy)

### Deploy Backend
- [ ] Click **Create Web Service**
- [ ] Wait for build to complete (5-10 minutes)
- [ ] Verify health endpoint returns 200:
  ```
  curl https://ops-safety-backend-xxxxx.onrender.com/health
  ```
- [ ] **SAVE THE BACKEND URL** for Vercel step

---

## Deploy Frontend to Vercel

### Account & Repo Setup
- [ ] Have a Vercel account (https://vercel.com)
- [ ] GitHub repo is connected to Vercel

### Create Vercel Project
- [ ] Go to Vercel dashboard
- [ ] Click **Add New...** → **Project**
- [ ] Select your GitHub repo
- [ ] Under **Root Directory**, enter: `frontend`
- [ ] Framework preset: **Vite**
- [ ] Build command: `npm install && npm run build`
- [ ] Output directory: `dist`

### Configure Environment Variables in Vercel
- [ ] Add `VITE_API_BASE_URL` = `https://ops-safety-backend-xxxxx.onrender.com`
  (Use the Render URL from previous step)

### Deploy Frontend
- [ ] Click **Deploy**
- [ ] Wait for build to complete (2-5 minutes)
- [ ] Verify frontend loads:
  ```
  https://ops-safety-frontend-xxxxx.vercel.app
  ```
- [ ] **SAVE THE FRONTEND URL**

---

## Post-Deployment Testing

### Test Backend
- [ ] Health check: `curl https://ops-safety-backend-xxxxx.onrender.com/health`
- [ ] List streams: `curl https://ops-safety-backend-xxxxx.onrender.com/streams`
- [ ] View API docs: `https://ops-safety-backend-xxxxx.onrender.com/docs`

### Test Frontend
- [ ] Open frontend URL in browser
- [ ] Dashboard loads
- [ ] Can see streams, alerts, config panels
- [ ] Can add a demo stream via the UI

### Test Integration
- [ ] From frontend, add a demo stream:
  - Click **Add Stream**
  - Name: "Demo"
  - Source Type: "demo"
  - Click **Add**
- [ ] Start the stream from the UI
- [ ] Verify preview image loads
- [ ] Check metrics (FPS, latency, etc.)

---

## Update Backend CORS (if needed)

If frontend can't communicate with backend:

### In Render Dashboard
1. Go to **ops-safety-backend** service
2. Click **Environment**
3. Update `OPS_ALLOWED_ORIGINS`:
   ```
   ["https://ops-safety-frontend-xxxxx.vercel.app"]
   ```
4. Trigger redeploy by pushing a commit or clicking **Redeploy**

---

## Monitoring & Logs

### Render Logs
- Dashboard → **ops-safety-backend** → **Logs**
- Check for errors, model loading issues, etc.

### Vercel Logs
- Dashboard → **ops-safety-frontend** → **Deployments** → latest → **Logs**
- Check for build errors or client-side issues

---

## Troubleshooting

### 504 Timeout
- Likely a cold start (model loading)
- Wait 1-2 minutes and retry
- Upgrade to paid Render plan for faster startup

### Frontend shows "API unreachable"
- Check `VITE_API_BASE_URL` in Vercel environment
- Ensure backend `OPS_ALLOWED_ORIGINS` includes frontend URL
- Check backend logs for CORS errors

### Build fails on Render
- Check Docker build logs
- Verify `backend/models/best.pt` exists
- If model too large, consider alternatives

### Frontend won't load at all
- Check Vercel build logs
- Ensure `npm run build` works locally
- Clear Vercel cache and redeploy

---

## Optional: Custom Domains

### Render
- Go to service → **Custom Domain**
- Add your domain (e.g., `api.mysite.com`)
- Follow DNS instructions

### Vercel
- Project settings → **Domains**
- Add your domain (e.g., `mysite.com`)
- Follow DNS instructions

---

## When Ready for Google Solutions Challenge

You now have:
✓ Production-ready backend (Render)
✓ Production-ready frontend (Vercel)
✓ Live streaming and alerts

**Next:** Integrate Google Gemini AI for crisis response features to meet challenge requirements.

See: [Integration Plan](./INTEGRATION_PLAN.md) (coming soon)
