with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'r') as f:
    content = f.read()

# Replace the problematic lines
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

with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'w') as f:
    f.write(content)

print('✓ Fixed metrics endpoint')
