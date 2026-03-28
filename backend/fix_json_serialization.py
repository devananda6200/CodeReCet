#!/usr/bin/env python3
"""Fix JSON serialization of NumPy float32 types in routes.py"""

with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace frame dimension assignments to convert to int
old_code = '''    stream_data = {
        "id": packet.stream_id,
        "name": stream_name,
        "status": "active",
        "frame_width": packet.current_size[1],
        "frame_height": packet.current_size[0],
        "detections": detections_payload,
        "metrics": metrics_payload
    }'''

new_code = '''    stream_data = {
        "id": packet.stream_id,
        "name": stream_name,
        "status": "active",
        "frame_width": int(packet.current_size[1]),
        "frame_height": int(packet.current_size[0]),
        "detections": detections_payload,
        "metrics": metrics_payload
    }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✓ Fixed JSON serialization - converted frame dimensions to int')
else:
    print('Code pattern not found, trying alternative approach...')
    # Try a simpler replacement
    content = content.replace(
        '"frame_width": packet.current_size[1],',
        '"frame_width": int(packet.current_size[1]),'
    )
    content = content.replace(
        '"frame_height": packet.current_size[0],',
        '"frame_height": int(packet.current_size[0]),'
    )
    with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✓ Fixed JSON serialization using alternative approach')
