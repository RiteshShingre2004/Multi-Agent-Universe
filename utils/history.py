import json
import os
import datetime
from typing import List, Dict, Any

HISTORY_FILE = "outputs/history.json"

def save_to_history(goal: str, output: str):
    """Saves a mission result to the history JSON file."""
    os.makedirs("outputs", exist_ok=True)
    
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
            
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": goal[:50] + "..." if len(goal) > 50 else goal,
        "goal": goal,
        "result": output
    }
    
    history.insert(0, entry) # Most recent first
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def load_history() -> List[Dict[str, Any]]:
    """Loads all mission history."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []
