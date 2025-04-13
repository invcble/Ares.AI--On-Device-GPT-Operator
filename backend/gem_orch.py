import os
import json
import base64
import hashlib
import logging
from typing import List, Dict, Optional, Union, Literal, Annotated, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, StringConstraints, Field
from openai import OpenAI

# ---------------------------------------------------------------------------
# 🔧 Environment & Gemini client setup
# ---------------------------------------------------------------------------
load_dotenv()
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("search_agent")

# ---------------------------------------------------------------------------
# 📝 Pydantic models for commands and responses
# ---------------------------------------------------------------------------

class GoalExtractionResponse(BaseModel):
    goals: List[str]

class IconBoxResponse(BaseModel):
    box_id: Annotated[str, StringConstraints(pattern=r"^([a-z][0-9]|N/A)$")]

class TapCommand(BaseModel):
    action: Literal["tap"]
    box_id: str

class SwipeUpCommand(BaseModel):
    action: Literal["swipeUp"]

class SwipeDownCommand(BaseModel):
    action: Literal["swipeDown"]

class SwipeLeftCommand(BaseModel):
    action: Literal["swipeLeft"]

class SwipeRightCommand(BaseModel):
    action: Literal["swipeRight"]

class TypeCommand(BaseModel):
    action: Literal["type"]
    text: str

class CommandResponse(BaseModel):
    command: Union[TapCommand, SwipeUpCommand, SwipeDownCommand, 
                  SwipeLeftCommand, SwipeRightCommand, TypeCommand]
    isDone: bool
    reasoning: Optional[str] = None

# ---------------------------------------------------------------------------
# 🔨 Utility helpers
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    """Generate SHA-256 hash of input bytes."""
    return hashlib.sha256(data).hexdigest()

def create_command_response(
    action: str, 
    *, 
    box_id: Optional[str] = None, 
    text: Optional[str] = None, 
    done: bool = False,
    reasoning: Optional[str] = None
) -> dict:
    """
    Create a properly formatted command response based on action type.
    
    Args:
        action: The action to perform (tap, swipeUp, swipeDown, swipeLeft, swipeRight, type)
        box_id: The grid cell identifier for tap actions
        text: The text to type for type actions
        done: Whether this is the final action for the current goal
        reasoning: Optional explanation for the action
        
    Returns:
        A dictionary representing the command response
    """
    try:
        if action == "tap" and box_id:
            return CommandResponse(
                command=TapCommand(action="tap", box_id=box_id),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        elif action == "swipeUp":
            return CommandResponse(
                command=SwipeUpCommand(action="swipeUp"),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        elif action == "swipeDown":
            return CommandResponse(
                command=SwipeDownCommand(action="swipeDown"),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        elif action == "swipeLeft":
            return CommandResponse(
                command=SwipeLeftCommand(action="swipeLeft"),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        elif action == "swipeRight":
            return CommandResponse(
                command=SwipeRightCommand(action="swipeRight"),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        elif action == "type" and text is not None:
            return CommandResponse(
                command=TypeCommand(action="type", text=text),
                isDone=done,
                reasoning=reasoning
            ).model_dump()
        else:
            return {"error": "Invalid command parameters"}
    except Exception as e:
        logger.error(f"Error creating command response: {e}")
        return {"error": f"Failed to create command: {str(e)}"}

# ---------------------------------------------------------------------------
# 🤖 Gemini function-calling definitions
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

# ---------------------------------------------------------------------------
# 🧠 Gemini API interaction functions
# ---------------------------------------------------------------------------

def extract_goals(instruction: str) -> List[str]:
    """
    Use Gemini to break the instruction into a list of UI goals.
    
    Args:
        instruction: The user's instruction to be broken down
        
    Returns:
        A list of specific UI interaction goals
    """
    try:
        logger.info(f"Extracting goals from instruction: {instruction}")
        resp = client.chat.completions.create(
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
""",
                }
            ],
            temperature=0,
        )
        
        goals = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)["goals"]
        logger.info(f"Extracted {len(goals)} goals: {goals}")
        return goals
    except Exception as e:
        logger.error(f"Error extracting goals: {e}")
        return ["Error extracting goals"]

def select_box(goal: str, img_b64: str) -> Tuple[str, str]:
    """
    Use Gemini to locate the bounding-box that contains the target goal.
    
    Args:
        goal: The current UI goal to locate
        img_b64: Base64-encoded screenshot with grid overlay
        
    Returns:
        Tuple of (box_id, reasoning) where box_id is the grid cell containing the target
        or "N/A" if not found, and reasoning explains the selection
    """
    try:
        logger.info(f"Selecting box for goal: {goal}")
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
You are shown a screenshot with bounding boxes labelled a1, b2 …
Return the single best box that fully contains **{goal}**, or \"N/A\" if not visible.
Also provide a brief reasoning for your selection.
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
        
        box_id = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)["box_id"]
        reasoning = resp.choices[0].message.content or "No explanation provided"
        logger.info(f"Selected box: {box_id} with reasoning: {reasoning}")
        return box_id, reasoning
    except Exception as e:
        logger.error(f"Error selecting box: {e}")
        return "N/A", f"Error: {str(e)}"

# ---------------------------------------------------------------------------
# 🗂️ SessionState to manage each instruction's lifecycle
# ---------------------------------------------------------------------------

class SessionState:
    """
    Manages the state of an ongoing instruction session.
    Tracks goals, progress, and prevents duplicate processing.
    """
    
    def __init__(self, instruction: str):
        """Initialize a new session with the given instruction."""
        self.instruction = instruction
        self.goals = extract_goals(instruction)
        self.goal_index = 0
        self.last_hashes: List[str] = []  # store up to 3 screenshot hashes
        self.consecutive_scrolls = 0
        self.max_consecutive_scrolls = 3
        logger.info(f"New session created with {len(self.goals)} goals")
    
    def current_goal(self) -> Optional[str]:
        """Get the current goal being processed or None if all goals are complete."""
        if self.goal_index < len(self.goals):
            return self.goals[self.goal_index]
        return None
    
    def advance_goal(self):
        """Move to the next goal in the sequence."""
        self.goal_index += 1
        self.consecutive_scrolls = 0
        logger.info(f"Advanced to goal {self.goal_index}/{len(self.goals)}")
    
    def is_all_done(self) -> bool:
        """Check if all goals have been completed."""
        return self.goal_index >= len(self.goals)
    
    def is_duplicate(self, img_bytes: bytes) -> bool:
        """
        Check if the current screenshot is a duplicate of recent ones.
        Also updates the hash history.
        """
        h = sha256(img_bytes)
        duplicate = h in self.last_hashes
        
        # Update hash history
        self.last_hashes.append(h)
        if len(self.last_hashes) > 3:
            self.last_hashes.pop(0)
            
        if duplicate:
            logger.info("Duplicate screenshot detected")
        return duplicate
    
    def increment_scroll_count(self) -> int:
        """
        Increment the consecutive scroll counter and return the new count.
        Used to detect when we should try different scroll directions.
        """
        self.consecutive_scrolls += 1
        return self.consecutive_scrolls
    
    def reset_scroll_count(self):
        """Reset the consecutive scroll counter."""
        self.consecutive_scrolls = 0

# ---------------------------------------------------------------------------
# 🌍 Session management
# ---------------------------------------------------------------------------

sessions: Dict[str, SessionState] = {}

def get_session(client_id: str, instruction: Optional[str] = None) -> Optional[SessionState]:
    """
    Get the session for a client, optionally creating a new one.
    
    Args:
        client_id: The unique identifier for the client
        instruction: If provided, creates a new session with this instruction
        
    Returns:
        The SessionState object or None if no session exists and no instruction was provided
    """
    if instruction:
        sessions[client_id] = SessionState(instruction)
    
    return sessions.get(client_id)

# ---------------------------------------------------------------------------
# 🎯 Main function for external call: process_request
# ---------------------------------------------------------------------------

def process_request(data: dict, client_id: str) -> dict:
    """
    Process an automation request from a client.
    
    This function is the main entry point for the search agent. It handles:
    1. Session creation/retrieval
    2. Screenshot processing
    3. Goal execution
    4. Command generation
    
    Args:
        data: Dictionary containing 'instruction' and/or 'imageb64'
        client_id: Unique identifier for the client session
        
    Returns:
        A dictionary with the next command or an error/info message
    """
    try:
        # Handle session creation/retrieval
        instruction = data.get("instruction")
        session = get_session(client_id, instruction)
        
        if not session:
            return {"error": "No active session for this client_id. Send 'instruction' first."}
        
        # Ensure we have an image to process
        if "imageb64" not in data:
            return {"error": "No 'imageb64' field provided"}
        
        img_b64 = data["imageb64"]
        img_bytes = base64.b64decode(img_b64)
        
        # Check for duplicate screenshots
        if session.is_duplicate(img_bytes):
            return {"warning": "Duplicate screenshot received"}
        
        # Check if all goals are completed
        if session.is_all_done():
            return {"info": "All goals already completed", "isDone": True}
        
        # Get current goal
        goal = session.current_goal()
        if not goal:
            return {"info": "No goal to process. Possibly done.", "isDone": True}
        
        # Handle typing goals directly
        if goal.lower().startswith("type "):
            typed_text = goal[5:].strip("'\" ")
            done = (session.goal_index + 1 == len(session.goals))
            session.advance_goal()
            return create_command_response(
                "type", 
                text=typed_text, 
                done=done,
                reasoning=f"Typing text: '{typed_text}'"
            )
        
        # Use Gemini to find the target element
        box_id, reasoning = select_box(goal, img_b64)
        
        if box_id != "N/A":
            # Found the target element
            done = (session.goal_index + 1 == len(session.goals))
            session.advance_goal()
            return create_command_response(
                "tap", 
                box_id=box_id, 
                done=done,
                reasoning=reasoning
            )
        else:
            # Target not found, need to navigate
            scroll_count = session.increment_scroll_count()
            
            # Vary scroll direction based on consecutive scroll count
            if scroll_count > session.max_consecutive_scrolls:
                # We've scrolled too much in one direction, try others
                if scroll_count % 4 == 0:
                    return create_command_response(
                        "swipeUp", 
                        done=False,
                        reasoning=f"Target '{goal}' not found. Trying swipe up after multiple attempts."
                    )
                elif scroll_count % 4 == 1:
                    return create_command_response(
                        "swipeRight", 
                        done=False,
                        reasoning=f"Target '{goal}' not found. Trying swipe right after multiple attempts."
                    )
                elif scroll_count % 4 == 2:
                    return create_command_response(
                        "swipeLeft", 
                        done=False,
                        reasoning=f"Target '{goal}' not found. Trying swipe left after multiple attempts."
                    )
                else:
                    return create_command_response(
                        "swipeDown", 
                        done=False,
                        reasoning=f"Target '{goal}' not found. Trying swipe down after multiple attempts."
                    )
            else:
                # Default to swipe down for initial scrolling
                return create_command_response(
                    "swipeDown", 
                    done=False,
                    reasoning=f"Target '{goal}' not found. Scrolling down to look for it."
                )
    
    except Exception as e:
        logger.error(f"Error in process_request: {e}")
        return {"error": f"Processing error: {str(e)}"}
