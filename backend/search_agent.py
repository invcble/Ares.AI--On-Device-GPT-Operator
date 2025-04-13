import os
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Union, Optional, Literal, Annotated
from pydantic import StringConstraints
import json
import base64
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")

# ---------- Initialize Gemini client ----------
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),  # Add your Gemini API key here
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

# ---------- Pydantic Models ----------
class GoalExtractionResponse(BaseModel):
    goals: List[str]

class IconBoxResponse(BaseModel):
    box_id: Annotated[str, StringConstraints(pattern=r"^([a-z][0-9]|N/A)$")]

class TapCommand(BaseModel):
    action: Literal["tap"]
    box_id: str

class ScrollCommand(BaseModel):
    action: Literal["scroll"]

class TypeCommand(BaseModel):
    action: Literal["type"]
    text: str

class CommandResponse(BaseModel):
    command: Union[TapCommand, ScrollCommand, TypeCommand]
    isDone: bool

# ---------- Utils ----------
def create_command_response(action: str, box_id: Optional[str] = None, text: Optional[str] = None, done: bool = False) -> CommandResponse:
    if action == "tap" and box_id:
        return CommandResponse(command=TapCommand(action="tap", box_id=box_id), isDone=done)
    elif action == "scroll":
        return CommandResponse(command=ScrollCommand(action="scroll"), isDone=done)
    elif action == "type" and text:
        return CommandResponse(command=TypeCommand(action="type", text=text), isDone=done)
    else:
        raise ValueError("Invalid command parameters")

# ---------- Input ----------
instruction = "Open WhatsApp and send text message to subhrato som"
screenshot_paths = ["content/1.jpeg", "content/2.jpeg", "content/3.jpeg", "content/4.jpeg","content/5.jpeg"]

# ---------- Goal Extraction Tool ----------
goal_tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_goals",
            "description": "Extract actionable goals from a user instruction.",
            "parameters": GoalExtractionResponse.model_json_schema()
        }
    }
]

# ---------- Extract Goals ----------
goal_response = client.chat.completions.create(
    model="gemini-2.5-pro-preview-03-25",
    tools=goal_tools,
    tool_choice={"type": "function", "function": {"name": "extract_goals"}},
    messages=[
        {
            "role": "user",
            "content": f"""
Break down this instruction into detailed, modular UI goals as if you are automating a mobile interface.

Each goal should be command-like and concrete. Include tapping, typing, and interface navigation as needed. If the instruction includes a query (like "search for ..."), you must break it into:
- tapping the search bar
- typing the query (e.g., "Type 'capital of France'")
- tapping the search or enter button.

Return the result under the field `goals` as a list of strings.

Instruction: "{instruction}"
"""
        }
    ],
    temperature=0
)

goals = json.loads(goal_response.choices[0].message.tool_calls[0].function.arguments)["goals"]
print("📋 Extracted Goals:", goals)

# ---------- Box Detection Tool ----------
box_tools = [
    {
        "type": "function",
        "function": {
            "name": "select_best_box",
            "description": "Identify the box ID (like a1, b2...) covering the target area of interest",
            "parameters": IconBoxResponse.model_json_schema()
        }
    }
]

# ---------- Loop Logic ----------
box_results = []
screenshot_index = 0
goal_index = 0

while goal_index < len(goals) and screenshot_index < len(screenshot_paths):
    goal = goals[goal_index]
    current_ss = screenshot_paths[screenshot_index]

    # Handle typing steps directly
    if goal.lower().startswith("type "):
        typed_text = goal[5:].strip("'\" ")
        is_last_goal = (goal_index + 1 == len(goals))
        response_json = create_command_response("type", text=typed_text, done=is_last_goal)
        print("⌨️ Typing Response:\n", response_json.model_dump_json(indent=2))
        goal_index += 1
        continue

    with open(current_ss, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")

    print(f"\n🔍 Step {goal_index+1}: Looking for '{goal}' in {current_ss}")

    box_response = client.chat.completions.create(
        model="gemini-2.5-pro-preview-03-25",
        tools=box_tools,
        tool_choice={"type": "function", "function": {"name": "select_best_box"}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
You are shown a screenshot of a phone screen with several bounding boxes labeled (e.g., a1, b2...).

Your task is to locate the most accurate box that contains the visual area corresponding to **{goal}**. This may refer to:
- An app icon (like Spotify or Gmail) on the home screen
- A section inside an app (like "My Network" inside LinkedIn)

Guidelines:
- Carefully check all visible UI elements inside the boxes.
- If you are **very confident** that one box contains the full target area of interest ({goal}), return its label (e.g., "g4").
- If the target is not visible, partially visible, or you're unsure, return **"N/A"**.
- Do not return multiple boxes — only one best match or "N/A".
- Do not explain. Only return a box label like "b3" or exactly "N/A".
                        """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.4
    )

    # Extract box result
    box_id = json.loads(box_response.choices[0].message.tool_calls[0].function.arguments)["box_id"]
    print(f"🟩 Gemini returned: {box_id}")

    is_last_goal = (goal_index + 1 == len(goals))

    if box_id != "N/A":
        box_results.append((goal, current_ss, box_id))
        response_json = create_command_response("tap", box_id, done=is_last_goal)
        goal_index += 1
    else:
        response_json = create_command_response("scroll", None, done=False)

    print("📦 Structured Response:\n", response_json.model_dump_json(indent=2))
    screenshot_index += 1

# ---------- Final Output ----------
print("\n🎯 Final Goal-to-Box Mapping:")
for goal, path, box in box_results:
    print(f"→ '{goal}' in {path} => {box}")

if goal_index < len(goals):
    print(f"\n⚠️ Some goals were not completed due to no matching box:")
    for i in range(goal_index, len(goals)):
        print(f"→ '{goals[i]}' = [NOT FOUND]")
