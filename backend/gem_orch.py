import os
import json
import base64
import hashlib

from typing import List, Dict, Optional, Union, Literal, Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, StringConstraints
from openai import OpenAI

# ---------------------------------------------------------------------------
# 🔧 Environment & Gemini client setup
# ---------------------------------------------------------------------------
load_dotenv()
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),  # You must define GEMINI_API_KEY in your .env
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

# ---------------------------------------------------------------------------
# 📝 Pydantic models (mirrors the schema your mobile client expects)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# 🔨 Utility helpers
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_command_response(action: str, *, box_id: Optional[str] = None, text: Optional[str] = None, done: bool = False) -> dict:
    """
    Returns a dict representation of CommandResponse.
    Example:
        {
          "command": {
            "action": "tap",
            "box_id": "b2"
          },
          "isDone": false
        }
    """
    if action == "tap" and box_id:
        return CommandResponse(
            command=TapCommand(action="tap", box_id=box_id),
            isDone=done
        ).model_dump()
    elif action == "scroll":
        return CommandResponse(
            command=ScrollCommand(action="scroll"),
            isDone=done
        ).model_dump()
    elif action == "type" and text is not None:
        return CommandResponse(
            command=TypeCommand(action="type", text=text),
            isDone=done
        ).model_dump()
    else:
        return {"error": "Invalid command parameters"}

# ---------------------------------------------------------------------------
# 🤖 Gemini function-calling wrappers
# ---------------------------------------------------------------------------

goal_tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_goals",
            "description": "Extract actionable goals from a user instruction.",
            "parameters": GoalExtractionResponse.model_json_schema(),
        },
    }
]

box_tools = [
    {
        "type": "function",
        "function": {
            "name": "select_best_box",
            "description": "Identify the box ID covering the target UI element.",
            "parameters": IconBoxResponse.model_json_schema(),
        },
    }
]

def extract_goals(instruction: str) -> List[str]:
    """Use Gemini to break the instruction into a list of UI goals."""
    resp = client.chat.completions.create(
        model="gemini-2.5-pro-preview-03-25",
        tools=goal_tools,
        tool_choice={"type": "function", "function": {"name": "extract_goals"}},
        messages=[
            {
                "role": "user",
                "content": f"""
Break down this instruction into detailed, modular UI goals as if you are automating a mobile interface.
Each goal should be command-like and concrete. Include tapping, typing, and navigation as needed.
Return the result under `goals`.
Instruction: \"{instruction}\"
""",
            }
        ],
        temperature=0,
    )

    print(resp.choices[0].message.tool_calls[0].function.arguments)

    return json.loads(resp.choices[0].message.tool_calls[0].function.arguments)["goals"]


def select_box(goal: str, img_b64: str) -> str:
    """Use Gemini to locate the bounding-box that contains the target goal."""
    resp = client.chat.completions.create(
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
You are shown a screenshot with bounding boxes labelled a1, b2 …\nReturn the single best box that fully contains **{goal}**, or \"N/A\" if not visible.\nNo explanations.
""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                ],
            }
        ],
        temperature=0.4,
    )
    return json.loads(resp.choices[0].message.tool_calls[0].function.arguments)["box_id"]

# ---------------------------------------------------------------------------
# 🗂️ SessionState to manage each instruction's lifecycle
# ---------------------------------------------------------------------------

class SessionState:
    def __init__(self, instruction: str):
        self.instruction = instruction
        self.goals = extract_goals(instruction)
        self.goal_index = 0
        self.last_hashes: List[str] = []  # store up to 2 screenshot hashes

    def current_goal(self) -> Optional[str]:
        if self.goal_index < len(self.goals):
            return self.goals[self.goal_index]
        return None

    def advance_goal(self):
        self.goal_index += 1

    def is_all_done(self) -> bool:
        return self.goal_index >= len(self.goals)

    def is_duplicate(self, img_bytes: bytes) -> bool:
        h = sha256(img_bytes)
        # check if same as the last stored hash
        duplicate = (len(self.last_hashes) > 0 and h == self.last_hashes[-1])
        # update queue of last 2
        self.last_hashes.append(h)
        if len(self.last_hashes) > 2:
            self.last_hashes.pop(0)
        return duplicate

# ---------------------------------------------------------------------------
# 🌍 Store multiple sessions keyed by some identifier (like a client ID)
# ---------------------------------------------------------------------------

sessions: Dict[str, SessionState] = {}

# ---------------------------------------------------------------------------
# 🎯 Main function for external call: process_automation_request
# ---------------------------------------------------------------------------

def process_request(data: dict, client_id: str) -> dict:
    """
    This function is meant to be called from your existing websocket code.
    1. If data has 'instruction', start or reset a session.
    2. If data has 'imageb64', process the next goal.
    Returns a dict with the next command or an error.
    """
    # 1) Start or update session on new instruction
    if "instruction" in data:
        instruction = data["instruction"].strip()
        sessions[client_id] = SessionState(instruction)

    if client_id not in sessions:
        return {"error": "No active session for this client_id. Send 'instruction' first."}

    state = sessions[client_id]

    # 2) Check we have an image for processing
    if "imageb64" not in data:
        return {"error": "No 'imageb64' field provided"}

    img_b64 = data["imageb64"]
    img_bytes = base64.b64decode(img_b64)

    # detect duplicates
    if state.is_duplicate(img_bytes):
        return {"warning": "Duplicate screenshot received"}

    # 3) If all done, we can just say so
    if state.is_all_done():
        return {"info": "All goals already completed"}

    goal = state.current_goal()
    if not goal:
        return {"info": "No goal to process. Possibly done."}

    # handle a 'type ...' goal locally
    if goal.lower().startswith("type "):
        typed_text = goal[5:].strip("'\" ")
        done = (state.goal_index + 1 == len(state.goals))
        state.advance_goal()
        return create_command_response("type", text=typed_text, done=done)

    # otherwise, ask gemini for bounding box
    box_id = select_box(goal, img_b64)

    if box_id != "N/A":
        done = (state.goal_index + 1 == len(state.goals))
        state.advance_goal()
        return create_command_response("tap", box_id=box_id, done=done)
    else:
        return create_command_response("scroll", done=False)
