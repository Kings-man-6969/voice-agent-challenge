import logging
import json
import pathlib
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    RoomInputOptions,
    cli,
    function_tool,
    RunContext
)
from livekit.plugins import murf, silero, deepgram, google, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("day7-ordering-agent")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --- Constants ---

RECIPES = {
    "peanut butter sandwich": [
        "Whole Wheat Bread",
        "Peanut Butter",
        "Strawberry Jam"
    ],
    "peanut butter toast": [
        "Whole Wheat Bread",
        "Peanut Butter"
    ],
    "pasta": [
        "Spaghetti Pasta",
        "Marinara Sauce",
        "Cheddar Cheese"
    ],
    "cheese sandwich": [
        "Whole Wheat Bread",
        "Cheddar Cheese"
    ],
    "breakfast": [
        "Eggs",
        "Whole Wheat Bread",
        "Orange Juice"
    ],
    "pizza night": [
        "Margherita Pizza",
        "Cola",
        "Potato Chips"
    ],
    "snack": [
        "Potato Chips",
        "Cola",
        "Chocolate Bar"
    ],
    "pasta arrabbiata": [
        "Penne Pasta",
        "Arrabbiata Sauce",
        "Parmesan Cheese",
        "Olive Oil"
    ],
    "vegetable stir fry": [
        "Basmati Rice",
        "Mixed Vegetables",
        "Soy Sauce",
        "Tofu"
    ],
    "caprese salad": [
        "Tomatoes",
        "Mozzarella Cheese",
        "Basil",
        "Olive Oil"
    ],
    "chocolate cake": [
        "Flour",
        "Sugar",
        "Cocoa Powder",
        "Eggs",
        "Butter"
    ],
    "maggi noodles": [
        "Instant Noodles",
        "Water",
        "Vegetables"
    ],
    "grilled cheese": [
        "Whole Wheat Bread",
        "Cheddar Cheese",
        "Butter"
    ],
    "fried rice": [
        "Rice",
        "Mixed Vegetables",
        "Soy Sauce",
        "Oil"
    ],
    "omelette": [
        "Eggs",
        "Onion",
        "Tomato",
        "Salt",
        "Oil"
    ],
    "salad bowl": [
        "Lettuce",
        "Cucumber",
        "Tomatoes",
        "Olive Oil",
        "Lemon"
    ],
    "dal rice": [
        "Rice",
        "Lentils",
        "Turmeric",
        "Salt",
        "Oil"
    ],
    "paneer curry": [
        "Paneer",
        "Onion",
        "Tomato",
        "Spices",
        "Oil"
    ],
    "veg sandwich": [
        "Whole Wheat Bread",
        "Cucumber",
        "Tomatoes",
        "Cheese"
    ],
    "fruit smoothie": [
        "Banana",
        "Milk",
        "Honey"
    ],
    "pancakes": [
        "Flour",
        "Milk",
        "Eggs",
        "Sugar"
    ]
}

# --- Data Structures ---

@dataclass
class CatalogItem:
    id: str
    name: str
    category: str
    price: float
    tags: List[str]

@dataclass
class CartItem:
    item: CatalogItem
    quantity: int
    notes: str = ""

@dataclass
class Cart:
    items: List[CartItem] = field(default_factory=list)

    def add(self, item: CatalogItem, quantity: int, notes: str = ""):
        for cart_item in self.items:
            if cart_item.item.id == item.id and cart_item.notes == notes:
                cart_item.quantity += quantity
                return
        self.items.append(CartItem(item=item, quantity=quantity, notes=notes))

    def update_quantity(self, item_name: str, quantity: int):
        for cart_item in self.items:
            if cart_item.item.name.lower() == item_name.lower():
                if quantity <= 0:
                    self.remove(item_name)
                else:
                    cart_item.quantity = quantity
                return True
        return False

    def remove(self, item_name: str):
        self.items = [i for i in self.items if i.item.name.lower() != item_name.lower()]

    def clear(self):
        self.items = []

    def total(self) -> float:
        return sum(i.item.price * i.quantity for i in self.items)

    def to_string(self) -> str:
        if not self.items:
            return "Your cart is empty."
        
        lines = ["Here is what you have in your cart:"]
        for i in self.items:
            note_str = f" ({i.notes})" if i.notes else ""
            lines.append(f"- {i.quantity}x {i.item.name}{note_str}: ${i.item.price * i.quantity:.2f}")
        lines.append(f"Total: ${self.total():.2f}")
        return "\n".join(lines)

@dataclass
class Order:
    id: str
    timestamp: float
    items: List[Dict[str, Any]]
    total: float
    status: str
    customer_info: Dict[str, str] = field(default_factory=dict)

@dataclass
class SessionData:
    cart: Cart = field(default_factory=Cart)
    catalog: List[CatalogItem] = field(default_factory=list)

RunContext_T = RunContext[SessionData]

# --- Helper Functions ---

def get_data_path(filename: str):
    return pathlib.Path(__file__).parent / filename

def load_catalog() -> List[CatalogItem]:
    try:
        path = get_data_path("food_catalog.json")
        with open(path, "r") as f:
            data = json.load(f)
            return [CatalogItem(**item) for item in data]
    except Exception as e:
        logger.error(f"Error loading catalog: {e}")
        return []

def load_order_history() -> List[Dict[str, Any]]:
    try:
        path = get_data_path("order_history.json")
        if not path.exists():
            return []
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading order history: {e}")
        return []

def save_order(order: Order):
    try:
        history = load_order_history()
        history.append(asdict(order))
        path = get_data_path("order_history.json")
        with open(path, "w") as f:
            json.dump(history, f, indent=2)
        logger.info(f"Order {order.id} saved.")
    except Exception as e:
        logger.error(f"Error saving order: {e}")

def find_item_by_name(catalog: List[CatalogItem], name: str) -> Optional[CatalogItem]:
    # Exact match
    for item in catalog:
        if item.name.lower() == name.lower():
            return item
    # Partial match
    for item in catalog:
        if name.lower() in item.name.lower():
            return item
    return None

# --- Ordering Agent ---

class OrderingAgent(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-miles", style="Promo"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def add_to_cart(self, context: RunContext_T, item_name: str, quantity: int = 1, notes: Optional[str] = None):
        """
        Add an item to the cart.
        item_name: The name of the item to add.
        quantity: The number of items to add (default 1).
        notes: Any special instructions (e.g., "no onions").
        """
        catalog = context.userdata.catalog
        item = find_item_by_name(catalog, item_name)
        
        if not item:
            return f"Sorry, I couldn't find {item_name} in our catalog. Please check the menu."
        
        context.userdata.cart.add(item, quantity, notes)
        return f"Added {quantity} {item.name} to your cart."

    @function_tool
    async def add_ingredients_for_dish(self, context: RunContext_T, dish_name: str, servings: Optional[int] = 1):
        """
        Add all necessary ingredients for a specific dish to the cart.
        dish_name: The name of the dish (e.g., "peanut butter sandwich", "pasta").
        servings: Number of servings (default 1).
        """
        # Normalize dish name
        dish_key = None
        dish_name_lower = dish_name.lower().strip()
        
        # Sort keys by length descending to match most specific first (e.g. "pasta arrabbiata" before "pasta")
        sorted_keys = sorted(RECIPES.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            if key in dish_name_lower:
                dish_key = key
                break
        
        if not dish_key:
            for key in sorted_keys:
                if dish_name_lower in key:
                    dish_key = key
                    break
        
        if not dish_key:
            return f"I don't have a pre-set recipe for {dish_name}, but I can help you find individual items."

        ingredients = RECIPES[dish_key]
        added_items = []
        missing_items = []
        catalog = context.userdata.catalog
        
        quantity_multiplier = 1
        if servings and servings > 4:
            quantity_multiplier = 2
        
        for item_name in ingredients:
            item = find_item_by_name(catalog, item_name)
            if item:
                qty = quantity_multiplier
                context.userdata.cart.add(item, qty)
                added_items.append(f"{qty}x {item.name}")
            else:
                missing_items.append(item_name)
        
        response = ""
        if added_items:
            serving_str = f" for {servings} people" if servings and servings > 1 else ""
            response = f"I've added the ingredients for {dish_key}{serving_str} to your cart: {', '.join(added_items)}."
        
        if missing_items:
            if response:
                response += f" However, I couldn't find these items in stock: {', '.join(missing_items)}."
            else:
                response = f"Sorry, I couldn't find any of the ingredients for {dish_key} in stock ({', '.join(missing_items)})."
                
        return response

    @function_tool
    async def add_multiple_items_to_cart(self, context: RunContext_T, items: List[Dict[str, Any]]):
        """
        Add multiple items to the cart at once.
        items: A list of items to add. Each item should be a dictionary with:
               - item_name: str (Required)
               - quantity: int (Optional, default 1)
               - notes: str (Optional, default "")
        """
        results = []
        catalog = context.userdata.catalog
        
        for item_data in items:
            item_name = item_data.get("item_name")
            if not item_name:
                continue
                
            quantity = item_data.get("quantity", 1)
            notes = item_data.get("notes", "")
            
            item = find_item_by_name(catalog, item_name)
            if not item:
                results.append(f"Could not find {item_name}")
                continue
            
            context.userdata.cart.add(item, quantity, notes)
            results.append(f"Added {quantity}x {item.name}")
            
        if not results:
            return "No items were added."
            
        return "Summary:\n" + "\n".join(results)

    @function_tool
    async def update_cart_quantity(self, context: RunContext_T, item_name: str, quantity: int):
        """
        Update the quantity of an item already in the cart.
        """
        success = context.userdata.cart.update_quantity(item_name, quantity)
        if success:
            return f"Updated {item_name} quantity to {quantity}."
        else:
            return f"{item_name} is not in your cart."

    @function_tool
    async def remove_from_cart(self, context: RunContext_T, item_name: str):
        """
        Remove an item from the cart.
        """
        context.userdata.cart.remove(item_name)
        return f"Removed {item_name} from your cart."

    @function_tool
    async def view_cart(self, context: RunContext_T):
        """
        List the contents of the cart and the total price.
        """
        return context.userdata.cart.to_string()

    @function_tool
    async def place_order(self, context: RunContext_T):
        """
        Place the order with the current cart contents.
        """
        cart = context.userdata.cart
        if not cart.items:
            return "Your cart is empty. I cannot place an empty order."
        
        order_id = f"ORD-{int(time.time())}"
        order_items = [
            {
                "id": i.item.id,
                "name": i.item.name,
                "quantity": i.quantity,
                "price": i.item.price,
                "notes": i.notes
            }
            for i in cart.items
        ]
        
        order = Order(
            id=order_id,
            timestamp=time.time(),
            items=order_items,
            total=cart.total(),
            status="received"
        )
        
        save_order(order)
        cart.clear()
        
        return f"Order {order_id} has been placed successfully! Total amount: ${order.total:.2f}. We will notify you when it's on the way."

    @function_tool
    async def get_order_status(self, context: RunContext_T, order_id: str = None):
        """
        Get the status of an order. If order_id is not provided, checks the most recent order.
        """
        history = load_order_history()
        if not history:
            return "You haven't placed any orders yet."
        
        if order_id:
            order = next((o for o in history if o["id"] == order_id), None)
            if not order:
                return f"I couldn't find an order with ID {order_id}."
        else:
            # Get most recent
            order = history[-1]
            
        return f"Order {order['id']} is currently: {order['status']}."

    @function_tool
    async def get_order_history(self, context: RunContext_T):
        """
        Get a summary of past orders.
        """
        history = load_order_history()
        if not history:
            return "You have no order history."
        
        summary = "Here are your past orders:\n"
        for order in history[-5:]: # Show last 5
            date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(order['timestamp']))
            summary += f"- {order['id']} ({date_str}): ${order['total']:.2f} - {order['status']}\n"
        return summary

# --- Entrypoint ---

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    logger.info("Starting ordering agent...")
    
    catalog = load_catalog()
    userdata = SessionData(catalog=catalog)
    
    # Create a string representation of the catalog for the system prompt
    catalog_str = "\n".join([f"- {item.name} (${item.price:.2f}): {', '.join(item.tags)}" for item in catalog])
    
    initial_instructions = f"""
        You are a friendly, efficient, and intelligent food & grocery ordering assistant for Zepto (10-minute grocery delivery).
        
        Your Goal: Help users build their cart and place orders quickly and accurately.
        
        Your Capabilities:
        1.  **Catalog Search**: Help users find items. If they ask for something vague like "chips", list the available options (e.g., "Potato Chips").
        2.  **Smart Cart Management**: Add, remove, and update quantities. Always confirm actions clearly (e.g., "I've added 2 packs of Organic Milk to your cart.").
        3.  **Bulk Ordering**: If a user lists multiple items (e.g., "I need milk, bread, and eggs"), use `add_multiple_items_to_cart` to add them all at once.
        4.  **Recipe Assistance**: Handle requests like "ingredients for pasta" using `add_ingredients_for_dish`. If a user asks for a dish you don't know, suggest checking the catalog for individual ingredients.
        5.  **Order Management**: View cart, place order, and check status.
        
        Catalog (STRICTLY LIMITED TO THESE ITEMS):
        {catalog_str}
        
        Critical Rules:
        - **NO HALLUCINATIONS**: You can ONLY sell items listed in the catalog above. If a user asks for "Sushi" or "Steak", politely apologize and say you don't have it. Do NOT pretend to add it.
        - **Clarify Ambiguities**: If a user says "milk", ask if they want "Organic Milk" (since that's what you have). If there's only one match, just add it.
        - **Ingredients**: When adding ingredients for a recipe, list what you are adding.
        - **Closing**: When the user says "that's all" or "place order", ALWAYS summarize the cart (items and total) and ask for final confirmation before calling `place_order`.
        
        Tone:
        - Energetic, helpful, and polite (Zepto style).
        - Keep responses concise. Don't be overly verbose.
    """
    
    agent = OrderingAgent(instructions=initial_instructions)

    session = AgentSession[SessionData](
        userdata=userdata,
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    await ctx.connect()
    
    # Trigger initial greeting
    await session.say("Hello! Welcome to Zepto. I can help you order groceries or find ingredients for your favorite recipes. What can I get for you today?")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
