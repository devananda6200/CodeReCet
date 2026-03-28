import asyncio
import websockets
import json

async def test_ws():
    async with websockets.connect("ws://localhost:8000/ws/detections") as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        print(json.dumps(data, indent=2))
        
asyncio.run(test_ws())
