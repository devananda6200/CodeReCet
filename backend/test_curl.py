import urllib.request
import json
import urllib.error

req = urllib.request.Request(
    'http://localhost:8000/api/streams',
    data=json.dumps({'stream_id': 'cam3', 'source': '0'}).encode('utf-8'),
    headers={'content-type': 'application/json'}
)
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())
except Exception as e:
    print(e)
