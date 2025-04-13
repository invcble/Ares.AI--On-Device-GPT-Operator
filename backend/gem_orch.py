import os
import json
import base64
import hashlib
import time
from typing import List, Dict, Optional, Union, Literal, Annotated, Any

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

class TypeCommand(BaseModel):
    action: Literal["type"]
    text: str
    box_id: str


class SwipeUpCommand(BaseModel):
    action: Literal["swipeUp"]

class SwipeDownCommand(BaseModel):
    action: Literal["swipeDown"]

class CommandResponse(BaseModel):
    command: Union[TapCommand, TypeCommand, SwipeUpCommand, SwipeDownCommand]
    isDone: bool

# ---------------------------------------------------------------------------
# 🔨 Utility helpers
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def create_command_response(action: str, *, box_id: Optional[str] = None, text: Optional[str] = None) -> dict:
    if action == "tap" and box_id:
        return CommandResponse(
            command=TapCommand(action="tap", box_id=box_id),
            isDone=False
        ).model_dump()
    elif action == "type" and text is not None and box_id:
        return CommandResponse(
            command=TypeCommand(action="type", text=text, box_id=box_id),
            isDone=False
        ).model_dump()
    elif action == "swipeUp":
        return CommandResponse(
            command=SwipeUpCommand(action="swipeUp"),
            isDone=False
        ).model_dump()
    elif action == "swipeDown":
        return CommandResponse(
            command=SwipeDownCommand(action="swipeDown"),
            isDone=False
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
    resp = client.chat.completions.create(
        model="gemini-2.5-pro-preview-03-25",
        tools=goal_tools,
        tool_choice={"type": "function", "function": {"name": "extract_goals"}},
        messages=[
            {
                "role": "user",
                "content": f"""
You are an android assistant which runs on android to do basic chores on behalf of user and that breaks down user instructions into concrete, modular mobile UI goals to automate workflows on Android apps.

Each goal should be written like a command and must reflect specific UI actions such as:
- Tapping buttons, icons, or menu items (e.g., "Tap element ")
- Typing into text fields (e.g., "Type something into search bar")
- Navigating through the interface (e.g., "Open LinkedIn app", "Scroll down", "Swipe left")
- Selecting or confirming actions (e.g., "Tap 'Connect'", "Tap 'Allow'", "Select first result")
- Waiting for or verifying UI changes if implied by flow (e.g., "Wait for connection confirmation")

Ensure that:
- Goals are atomic (one action per step)
- The order reflects how a user would logically complete the task in the UI
- Multi-step flows (e.g., searching, connecting, posting) are decomposed clearly


### Knowledge Base:


⏰ **Clock App**
- Clock app has 5 bottom tabs: **Alarm, Clock, Timer, Stopwatch, Bedtime**.
- If the desired alarm exists, toggle it.
- Otherwise:
    1. Tap the **plus (+)** button.
    2. Set **hour**, **minute**, and **AM/PM**.
    3. Tap **OK** to confirm.

Return only the modular goals in the `goals` field as a **list of strings**.
Instruction: \"{instruction}\"
""",
            }
        ],
        temperature=0,
    )

    return json.loads(resp.choices[0].message.tool_calls[0].function.arguments)["goals"]

def select_box(goal: str, img_b64: str) -> str:
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
                        "text": f"""You are shown a screenshot with bounding boxes labelled a1, b2, etc.
Return the single best box that fully contains the UI element needed for this goal: **{goal}**
Return "N/A" ONLY if the element is definitely not visible in the current screen.
No explanations.""",
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
# 🗂️ SessionState to manage each instruction's lifecycle with improved state tracking
# ---------------------------------------------------------------------------

class SessionState:
    def __init__(self, instruction: str):
        self.instruction = instruction
        self.goals = extract_goals(instruction)
        print(f"Goals extracted: {self.goals}")
        self.goal_index = 0
        self.last_hashes: List[str] = []
        self.consecutive_failed_attempts = 0
        self.max_consecutive_fails = 3
        self.swipe_attempts = 0
        self.max_swipe_attempts = 5
        self.alternative_actions = ["swipeUp", "swipeDown"]
        self.action_index = 0
        self.last_action = None
        self.goal_timestamps = {}  # Track when we started working on each goal
        self.goal_timeout = 20  # seconds before we consider a goal stuck

    def current_goal(self) -> Optional[str]:
        if self.goal_index < len(self.goals):
            return self.goals[self.goal_index]
        return None

    def advance_goal(self):
        print(f"✅ Completed goal: {self.current_goal()}")
        self.goal_index += 1
        # Reset counters when progressing to a new goal
        self.consecutive_failed_attempts = 0
        self.swipe_attempts = 0
        if self.goal_index < len(self.goals):
            # Start tracking time for the new goal
            self.goal_timestamps[self.goal_index] = time.time()
            print(f"📋 Now working on: {self.current_goal()}")

    def register_goal_attempt(self, success: bool, action: str):
        """Track success/failure of attempts to achieve current goal"""
        self.last_action = action
        
        if not success:
            self.consecutive_failed_attempts += 1
            if action in ["swipeUp", "swipeDown"]:
                self.swipe_attempts += 1
        else:
            # Reset failure counters on success
            self.consecutive_failed_attempts = 0
            self.swipe_attempts = 0
    
    def get_next_alternative_action(self) -> str:
        """Cycle through alternative actions when stuck"""
        action = self.alternative_actions[self.action_index % len(self.alternative_actions)]
        self.action_index += 1
        return action

    def is_goal_stuck(self) -> bool:
        """Check if we've been trying to achieve the same goal for too long"""
        if self.goal_index not in self.goal_timestamps:
            self.goal_timestamps[self.goal_index] = time.time()
            return False
            
        time_on_goal = time.time() - self.goal_timestamps[self.goal_index]
        return time_on_goal > self.goal_timeout or self.consecutive_failed_attempts >= self.max_consecutive_fails

    def handle_stuck_goal(self) -> None:
        """Try to recover when stuck on a goal"""
        print(f"⚠️ Stuck on goal: {self.current_goal()}. Attempting recovery...")
        # If we've tried swiping too many times without finding the element, try the next goal
        if self.swipe_attempts >= self.max_swipe_attempts:
            print("Exhausted swipe attempts, moving to next goal")
            self.advance_goal()
            return
            
        # Reset counters but stay on same goal
        self.consecutive_failed_attempts = 0

    def is_all_done(self) -> bool:
        return self.goal_index >= len(self.goals)

    def is_duplicate(self, img_bytes: bytes) -> bool:
        h = sha256(img_bytes)
        duplicate = (len(self.last_hashes) > 0 and h == self.last_hashes[-1])
        self.last_hashes.append(h)
        if len(self.last_hashes) > 2:
            self.last_hashes.pop(0)
        return duplicate

# ---------------------------------------------------------------------------
# 🌍 Store multiple sessions keyed by some identifier (like a client ID)
# ---------------------------------------------------------------------------

sessions: Dict[str, SessionState] = {}

# ---------------------------------------------------------------------------
# 📝 Structured logging helper
# ---------------------------------------------------------------------------

def log_action(client_id: str, message: str, data: Any = None) -> None:
    """Structured logging for debugging and tracing execution flow"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "client_id": client_id,
        "message": message
    }
    if data:
        log_entry["data"] = data
    print(json.dumps(log_entry))

# ---------------------------------------------------------------------------
# 🎯 Main function for external call: process_automation_request
# ---------------------------------------------------------------------------

def process_request(data: dict, client_id: str) -> dict:
    log_action(client_id, "Processing request", {"request_type": "instruction" if "instruction" in data else "step"})
    
    # Initialize a new session if this is a new instruction
    if "instruction" in data:
        instruction = data["instruction"].strip()
        sessions[client_id] = SessionState(instruction)
        log_action(client_id, f"New session created for instruction: {instruction}")

    # Validate session
    if client_id not in sessions:
        return {"error": "No active session for this client_id. Send 'instruction' first."}

    state = sessions[client_id]

    # Validate image input
    if "imageb64" not in data:
        return {"error": "No 'imageb64' field provided"}

    img_b64 = data["imageb64"]
    img_bytes = base64.b64decode(img_b64)

    # Skip duplicate screenshots to avoid loops
    if state.is_duplicate(img_bytes):
        log_action(client_id, "Duplicate screenshot detected")
        return {"warning": "Duplicate screenshot received"}

    # Check if all goals are completed
    if state.is_all_done():
        log_action(client_id, "All goals completed")
        return {"info": "All goals already completed", "isDone": True}

    # Get current goal
    goal = state.current_goal()
    if not goal:
        log_action(client_id, "No goal to process")
        return {"info": "No goal to process. Possibly done."}
    
    log_action(client_id, f"Working on goal: {goal}", {"goal_index": state.goal_index})

    # Check if we're stuck on the current goal
    if state.is_goal_stuck():
        log_action(client_id, "Detected stuck state")
        state.handle_stuck_goal()
        # Get updated goal after handling stuck state
        goal = state.current_goal()
        if not goal:
            return {"info": "Recovery completed all goals", "isDone": True}

    # Handle special "Type" prefix goals
    if goal.lower().startswith("type "):
        match = re.search(r"[\"'](.+?)[\"']|type (.+?)(?: in| on| into| to|$)", goal, re.IGNORECASE)
        typed_text = match.group(1) or match.group(2) if match else goal[5:].strip()
        log_action(client_id, f"Executing type command: {typed_text}")

        box_id = select_box(goal, img_b64)
        log_action(client_id, f"Box selected for typing: {box_id}")

        if box_id != "N/A":
            state.advance_goal()
            state.register_goal_attempt(success=True, action="type")
            return create_command_response("type", text=typed_text, box_id=box_id)
        else:
            if state.swipe_attempts < state.max_swipe_attempts:
                action = state.get_next_alternative_action()
                log_action(client_id, f"Text input target not found. Trying {action}", {"swipe_attempt": state.swipe_attempts + 1})
                state.register_goal_attempt(success=False, action=action)
                return create_command_response(action)
            else:
                log_action(client_id, "Max scroll attempts reached for text input, skipping")
                state.advance_goal()
                return create_command_response("swipeUp")

    # Select box for current goal
    log_action(client_id, f"Analyzing screenshot to find element for: {goal}")
    box_id = select_box(goal, img_b64)
    log_action(client_id, f"Box selection result", {"box_id": box_id})

    # Execute taps if box is found
    if box_id != "N/A":
        log_action(client_id, f"Element found. Tapping box: {box_id}")
        state.advance_goal()
        state.register_goal_attempt(success=True, action="tap")
        return create_command_response("tap", box_id=box_id)
    else:
        # Element not found, try scrolling
        if state.swipe_attempts < state.max_swipe_attempts:
            action = state.get_next_alternative_action()
            log_action(client_id, f"Element not found. Trying {action}", {"swipe_attempt": state.swipe_attempts + 1})
            state.register_goal_attempt(success=False, action=action)
            return create_command_response(action)
        else:
            # If we've scrolled too much without finding the element, skip this goal
            log_action(client_id, "Max scroll attempts reached, skipping goal")
            state.advance_goal()
            return create_command_response("swipeUp")  # One more scroll before next goal
        