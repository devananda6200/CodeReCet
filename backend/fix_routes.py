#!/usr/bin/env python3
"""Fix the metrics endpoint in routes.py"""

file_path = r'd:\arakkunnam-99\backend\app\api\routes.py'

with open(file_path, 'r') as f:
    content = f.read()

# Replace the entire get_metrics function
old_func = '''@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_metrics():
    """Return current performance metrics."""
    metrics_snap = metrics_collector.get_snapshot()
    return SystemMetricsResponse(
        fps=metrics_snap.total_fps,
        latency=0.0,
        cpu=metrics_snap.cpu_percent,
        ram=metrics_snap.ram_mb,
        healthy=True
    )'''

new_func = '''@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_metrics():
    """Return current performance metrics."""
    metrics_snap = await asyncio.to_thread(metrics_collector.get_snapshot)
    return SystemMetricsResponse(
        fps=round(metrics_snap.get("total_fps", 0.0), 1),
        latency=0.0,
        cpu=round(metrics_snap.get("cpu_percent", 0.0), 1),
        ram=round(metrics_snap.get("ram_mb", 0.0), 1),
        healthy=True
    )'''

content = content.replace(old_func, new_func)

with open(file_path, 'w') as f:
    f.write(content)

print('✓ Successfully fixed routes.py metrics endpoint')
