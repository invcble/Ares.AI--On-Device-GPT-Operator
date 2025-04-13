import asyncio
import websockets

async def test_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        message = "Hello from client!"
        print(f"Sending: {message}")
        await websocket.send(message)

        response = await websocket.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(test_client())
