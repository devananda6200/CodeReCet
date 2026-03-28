import sys

with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Simple string replacements
content = content.replace(
    'metrics_snap = metrics_collector.get_snapshot()',
    'metrics_snap = await asyncio.to_thread(metrics_collector.get_snapshot)'
)
content = content.replace(
    'fps=metrics_snap.total_fps,',
    'fps=round(metrics_snap.get("total_fps", 0.0), 1),'
)
content = content.replace(
    'cpu=metrics_snap.cpu_percent,',
    'cpu=round(metrics_snap.get("cpu_percent", 0.0), 1),'
)
content = content.replace(
    'ram=metrics_snap.ram_mb,',
    'ram=round(metrics_snap.get("ram_mb", 0.0), 1),'
)

with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed metrics endpoint in routes.py')
