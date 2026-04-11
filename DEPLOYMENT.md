# Deployment Guide: Render + Vercel

This guide walks through deploying the Ops Safety System to production using:
- **Backend**: Render (Python/Docker)
- **Frontend**: Vercel (Static + SPA)

---

## Prerequisites

1. **GitHub repository** with this code committed
2. **Render account** (https://render.com)
3. **Vercel account** (https://vercel.com)
4. `backend/models/best.pt` is present in your repo (or add via symlink/volume)

---

## Step 1: Deploy Backend to Render

### A) Create a Render Web Service

1. Go to **https://dashboard.render.com**
2. Click **New +** → **Web Service**
3. Select **Deploy from Git Repository**
4. Connect your GitHub repo
5. Fill in the following:

| Field | Value |
|-------|-------|
| **Name** | `ops-safety-backend` |
| **Environment** | `Docker` |
| **Region** | `Oregon` (or your choice) |
| **Branch** | `main` |
| **Dockerfile Path** | `backend/Dockerfile` |
| **Auto-Deploy** | Yes |

### B) Add Environment Variables

In the Render dashboard, add these under **Environment**:

```
OPS_DEMO_MODE=false
OPS_DEFAULT_BACKEND=pytorch
OPS_DEFAULT_CPU_THREADS=4
OPS_DEFAULT_FRAME_SKIP=2
OPS_ALERT_PERSISTENCE_FRAMES=3
OPS_ADAPTIVE_RESOLUTION=true
```

### C) Deploy

Click **Create Web Service**. Render will:
1. Build the Docker image
2. Deploy it
3. Provide a URL like: `https://ops-safety-backend-xxxxx.onrender.com`

**Keep this URL for Step 3.**

---

## Step 2: Deploy Frontend to Vercel

### A) Push frontend folder to GitHub

Ensure the entire `frontend/` directory is committed.

### B) Create a Vercel Project

1. Go to **https://vercel.com/dashboard**
2. Click **Add New...** → **Project**
3. Import your GitHub repository
4. Select the repo
5. Under **Framework Preset**, choose **Vite**
6. Configure:

| Setting | Value |
|---------|-------|
| **Framework** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Output Directory** | `dist` |

### C) Add Environment Variable

Under **Environment Variables**, add:

```
VITE_API_BASE_URL = https://ops-safety-backend-xxxxx.onrender.com
```

(Replace with your actual Render backend URL from Step 1)

### D) Deploy

Click **Deploy**. Vercel will:
1. Build the frontend
2. Deploy to their CDN
3. Provide a URL like: `https://ops-safety-frontend-xxxxx.vercel.app`

---

## Step 3: Connect Frontend to Backend

After both deployments:

1. Get your **Render backend URL**
2. In Vercel dashboard → **Settings** → **Environment Variables**
3. Update `VITE_API_BASE_URL` to your Render URL
4. Trigger a redeploy by pushing a commit or clicking **Redeploy**

---

## Verify the Deployment

### Test Backend
```
curl https://ops-safety-backend-xxxxx.onrender.com/health
```

Should return:
```json
{"status":"ok","app_name":"Ops Safety System API",...}
```

### Test Frontend
Open `https://ops-safety-frontend-xxxxx.vercel.app` in your browser. The dashboard should load and connect to the backend.

---

## Add a Demo Stream

Once deployed, test with a demo stream:

```powershell
curl -X POST https://ops-safety-backend-xxxxx.onrender.com/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Demo Camera\",\"source_type\":\"demo\"}"
```

Then start it:
```powershell
curl -X POST https://ops-safety-backend-xxxxx.onrender.com/streams/<stream_id>/start
```

---

## Important Notes

### Model File Size
- `best.pt` is a large PyTorch model (~500MB+)
- Render has limits on build size and image size
- If the build fails, consider:
  1. Downloading the model at runtime (not recommended)
  2. Using a lighter model (e.g., ONNX quantized)
  3. Using a cloud storage bucket (GCS/S3) to fetch the model on startup

### Cold Starts
- Render's free tier may experience cold starts
- The model will take time to load on first inference
- Consider upgrading to a paid Render plan for production

### Alternative: Google Cloud Run
If Render deployment fails due to model size, use Google Cloud Run instead:

```powershell
gcloud run deploy ops-safety-backend `
  --source . `
  --entry-point app.main:app `
  --region us-central1 `
  --allow-unauthenticated
```

---

## Troubleshooting

### Frontend can't reach backend
- Check `VITE_API_BASE_URL` in Vercel environment variables
- Ensure it's the correct Render URL
- Redeploy the frontend after changing the env var

### Backend won't start
- Check Render logs: **Dashboard** → **Service** → **Logs**
- Verify `backend/models/best.pt` exists
- Check environment variables are correct

### 504 Gateway Timeout
- Likely a cold start. Wait 1-2 minutes and try again
- Upgrade the Render plan or switch to Cloud Run

---

## Next Steps

1. Set up a custom domain on Vercel/Render
2. Add error tracking (Sentry)
3. Set up monitoring and alerts
4. Consider integrating Google AI (Gemini/Vertex AI) for crisis response
