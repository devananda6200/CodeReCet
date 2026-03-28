#!/usr/bin/env python3
"""Add frame_width and frame_height to WebSocket payload"""

with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and update the stream_data dictionary
updated = False
for i in range(len(lines)):
    if '"status": "active",' in lines[i] and 'stream_data' in ''.join(lines[max(0, i-5):i]):
        # Insert frame dimensions after status
        if 'frame_width' not in lines[i+1]:
            lines.insert(i+1, '        "frame_width": packet.current_size[1],\n')
            lines.insert(i+2, '        "frame_height": packet.current_size[0],\n')
            updated = True
            break

if updated:
    with open(r'd:\arakkunnam-99\backend\app\api\routes.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('✓ Added frame_width and frame_height to WebSocket payload')
else:
    print('Frame dimensions already present or not found')
