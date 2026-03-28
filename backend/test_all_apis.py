import requests
import json
import time

base_url = "http://localhost:8000/api"

print("=" * 60)
print("TEST 1: Health Check")
print("=" * 60)
try:
    resp = requests.get(f"{base_url}/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST 2: Add Webcam Stream (cam1)")
print("=" * 60)
try:
    payload = {
        "stream_id": "cam1",
        "source": "0",
        "name": "Webcam 1"
    }
    resp = requests.post(f"{base_url}/streams", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST 3: List Active Streams")
print("=" * 60)
try:
    resp = requests.get(f"{base_url}/streams")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\nWaiting 5 seconds for stream to process frames...")
time.sleep(5)

print("\n" + "=" * 60)
print("TEST 4: Get Performance Metrics")
print("=" * 60)
try:
    resp = requests.get(f"{base_url}/metrics")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST 5: Get Recent Alerts")
print("=" * 60)
try:
    resp = requests.get(f"{base_url}/alerts")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST 6: Remove the Webcam Stream")
print("=" * 60)
try:
    resp = requests.delete(f"{base_url}/streams/cam1")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
