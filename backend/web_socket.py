import asyncio
import json
import websockets
import base64
from PIL import Image
from io import BytesIO
from grid_marker import apply_grid_overlay
from gem_orch import process_request
from grid_utils import get_coordinate

async def echo_handler(websocket):
    async for message in websocket:
        print(f"Received from client: {message}", flush=True)

        try:
            data = json.loads(message)

            input_payload = {}

            if "imageb64" in data:
                image_data = base64.b64decode(data["imageb64"])
                image = Image.open(BytesIO(image_data)).convert("RGB")
                image = image.resize((720, 1600))
                image_with_grid = apply_grid_overlay(image)

                # Save to buffer and encode as base64
                buffer = BytesIO()
                image_with_grid.save(buffer, format="PNG")
                encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
                input_payload["imageb64"] = encoded_image

            if "prompt" in data:
                print(f"Prompt from client: {data['prompt']}")
                input_payload["instruction"] = data["prompt"]

            # 🔄 Get the auto-generated server response
            response = process_request(input_payload, client_id="test")
            print(response)

            # If it's a tap action with a box_id, compute coordinates
            if "command" in response:
                command = response["command"]
                if command.get("action") == "tap" and "box_id" in command:
                    try:
                        box_id = command["box_id"]
                        x, y = get_coordinate(box_id)
                        command["x_cord"] = x
                        command["y_cord"] = y
                        response["command"] = command  # 🔁 Explicitly re-assign back to response
                    except Exception as e:
                        print(f"Failed to get coordinates for box_id '{box_id}': {e}")
            # Send to client

            print(response)
            await websocket.send(json.dumps(response))

        except json.JSONDecodeError:
            print("Received non-JSON message")


async def main():
    async with websockets.serve(echo_handler, "0.0.0.0", 8765):
        print("WebSocket server running on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())