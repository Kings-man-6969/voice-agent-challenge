import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

WELLNESS_FILE = "wellness_log.json"

def load_wellness_data() -> List[Dict]:
    """Loads the wellness log from the JSON file."""
    if not os.path.exists(WELLNESS_FILE):
        return []
    try:
        with open(WELLNESS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_wellness_entry(mood: str, objectives: List[str], summary: str, timestamp: Optional[str] = None) -> None:
    """Saves a new wellness entry to the JSON file."""
    data = load_wellness_data()
    
    entry = {
        "timestamp": timestamp or datetime.now().isoformat(),
        "mood": mood,
        "objectives": objectives,
        "summary": summary
    }
    
    data.append(entry)
    
    with open(WELLNESS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_latest_entry() -> Optional[Dict]:
    """Retrieves the most recent wellness entry."""
    data = load_wellness_data()
    if not data:
        return None
    return data[-1]

def get_next_simulated_date() -> str:
    """Returns the next simulated date based on the last entry."""
    latest = get_latest_entry()
    if not latest:
        return datetime.now().strftime("%Y-%m-%d")
    
    try:
        last_date_str = latest["timestamp"]
        # Handle both full isoformat and simple date
        if "T" in last_date_str:
            last_date = datetime.fromisoformat(last_date_str)
        else:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            
        next_date = last_date + timedelta(days=1)
        return next_date.strftime("%Y-%m-%d")
    except (ValueError, KeyError):
        return datetime.now().strftime("%Y-%m-%d")

def get_day_number() -> int:
    """Returns the current day number (1-based)."""
    data = load_wellness_data()
    return len(data) + 1
