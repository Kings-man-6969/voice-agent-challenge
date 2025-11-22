import json
import os
from datetime import datetime

# Order state
order = {
    "drinkType": "",
    "size": "",
    "milk": "",
    "extras": [],
    "name": ""
}

def get_missing_field():
    for field in ["drinkType", "size", "milk", "name"]:
        if not order[field]:
            return field
    return None

def update_order(field, value):
    if field == "extras":
        if isinstance(value, list):
            order["extras"].extend(value)
        else:
            order["extras"].append(value)
    else:
        order[field] = value

    return {
        "order": order,
        "missing": get_missing_field()
    }

def finalize_order():
    # Create folder for saving orders
    folder = os.path.join(os.path.dirname(__file__), "..", "..", "orders")
    folder = os.path.abspath(folder)

    if not os.path.exists(folder):
        os.makedirs(folder)

    safe_name = (order["name"] or "anon").replace(" ", "_")
    filename = f"{datetime.now().timestamp()}_{safe_name}.json"
    file_path = os.path.join(folder, filename)

    # Save JSON file
    with open(file_path, "w") as f:
        json.dump(order, f, indent=4)

    saved = order.copy()
    saved["savedFile"] = file_path

    # Reset state for next customer
    for key in order:
        order[key] = "" if key != "extras" else []

    return saved