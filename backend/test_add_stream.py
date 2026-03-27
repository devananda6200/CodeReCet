import requests
import json

# Add a stream
resp = requests.post(
    'http://localhost:8000/api/streams',
    json={"stream_id": "cam1", "source": "0"}
)
print("Add stream response:", resp.status_code, resp.text)

# Check if it's listed
streams = requests.get('http://localhost:8000/api/streams').json()
print("Active streams:", json.dumps(streams, indent=2))
