import requests
import json

try:
    # First get streams
    resp = requests.get('http://localhost:8000/api/streams')
    streams = resp.json()
    print("Streams active:", streams)
    
    if streams:
        sid = streams[0]['id']
        url = f'http://localhost:8000/api/streams/{sid}/feed'
        print(f"Connecting to MJPEG feed: {url}")
        
        # Stream response
        with requests.get(url, stream=True) as r:
            if r.status_code == 200:
                bytes_received = 0
                frame_count = 0
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        bytes_received += len(chunk)
                        if b'--frame' in chunk:
                            frame_count += 1
                        if frame_count > 5:
                            print(f"Successfully received {frame_count} frames, {bytes_received} bytes!")
                            break
            else:
                print(f"Failed to connect to MJPEG feed: HTTP {r.status_code}")
                print(r.text)
    else:
        print("No streams active. Please add one first.")
except Exception as e:
    print(f"Error: {e}")
