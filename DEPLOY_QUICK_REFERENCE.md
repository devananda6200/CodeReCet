# Deployment Quick Reference

## Render Backend

### Environment Variables
```
OPS_DEMO_MODE=false
OPS_DEFAULT_BACKEND=pytorch
OPS_DEFAULT_CPU_THREADS=4
OPS_DEFAULT_FRAME_SKIP=2
OPS_ALERT_PERSISTENCE_FRAMES=3
OPS_ADAPTIVE_RESOLUTION=true
```

### Health Check
```
GET /health
```

### Key Endpoints
- `GET /` - Root
- `GET /health` - Health status
- `GET /streams` - List all streams
- `POST /streams/add` - Add a new stream
- `POST /streams/{id}/start` - Start stream processing
- `POST /streams/{id}/stop` - Stop stream processing
- `GET /alerts` - List recent alerts
- `GET /metrics/summary` - Summary metrics
- `WS /ws/streams` - Live stream updates
- `WS /ws/alerts` - Live alert updates
- `WS /ws/metrics` - Live metrics updates

---

## Vercel Frontend

### Environment Variable
```
VITE_API_BASE_URL=https://ops-safety-backend-xxxxx.onrender.com
```

### Build Configuration
- **Framework**: Vite
- **Build Command**: `npm install && npm run build`
- **Output Directory**: `dist`
- **Node Version**: 20 LTS

### Deployment Steps
1. Connect GitHub repo
2. Set framework to Vite
3. Root directory: `frontend`
4. Add `VITE_API_BASE_URL` env var
5. Deploy

---

## Testing Deployed Services

### Backend Health
```powershell
curl https://ops-safety-backend-xxxxx.onrender.com/health
```

### Add Demo Stream
```powershell
curl -X POST https://ops-safety-backend-xxxxx.onrender.com/streams/add `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Demo Camera\",\"source_type\":\"demo\"}"
```

### Start Stream
```powershell
curl -X POST https://ops-safety-backend-xxxxx.onrender.com/streams/<stream_id>/start
```

### List Streams
```powershell
curl https://ops-safety-backend-xxxxx.onrender.com/streams
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Frontend can't reach backend | Check `VITE_API_BASE_URL` env var, redeploy |
| 504 timeout on first request | Cold start. Wait and retry. Consider upgrading plan |
| Build fails due to model size | Use smaller model or fetch from cloud storage |
| Vercel build fails | Clear cache: **Settings** → **Deployments** → **Clear cache** |
| Render won't deploy | Check logs, verify Dockerfile path, check env vars |

---

## Scaling

For production:
- Upgrade Render from free to paid plan
- Enable auto-scaling in Render settings
- Use Vercel Pro for higher bandwidth
- Consider CDN for model downloads
- Set up load balancer if needed
