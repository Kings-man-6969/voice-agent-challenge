import logging
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

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

logger = logging.getLogger("day9-ecommerce-agent")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --------------------------------------------------------------------
# DATA MODELS
# --------------------------------------------------------------------

@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    currency: str
    category: str
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float
    currency: str

@dataclass
class Order:
    id: str
    items: List[OrderItem]
    total: float
    currency: str
    created_at: str

# --------------------------------------------------------------------
# FILE HANDLING
# --------------------------------------------------------------------

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"


def load_catalog() -> List[Product]:
    try:
        with open(PRODUCTS_FILE, "r") as f:
            data = json.load(f)
            return [Product(**p) for p in data]
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        return []


def load_orders() -> List[Dict]:
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_order(order: Order):
    orders = load_orders()
    orders.append(asdict(order))
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)


# --------------------------------------------------------------------
# AGENT CLASS
# --------------------------------------------------------------------

class EcommerceAgent(Agent):

    def __init__(self, instructions: str) -> None:
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-IN-anisha", style="Promo"),
            turn_detection=MultilingualModel(),
        )

    # --------------------------------------------------------------
    # LIST PRODUCTS TOOL
    # --------------------------------------------------------------
    @function_tool
    async def list_products(
        self,
        context: RunContext,
        category: str = None,
        max_price: float = None,
        search_query: str = None,
        color: str = None,
        size: str = None,
    ):
        """
        Search the product catalog with flexible filters.
        """
        catalog = load_catalog()
        results = []

        for p in catalog:
            # CATEGORY MATCHING
            if category:
                # Allow natural language like "hoodies", "mugs", etc
                if category.lower().rstrip("s") not in p.category.lower():
                    continue

            # PRICE FILTER
            if max_price is not None and p.price > max_price:
                continue

            # TEXT SEARCH MATCH (name OR description)
            if search_query:
                q = search_query.lower()
                if q not in p.name.lower() and q not in p.description.lower():
                    continue

            # COLOR FILTER
            if color:
                prod_color = p.attributes.get("color", "").lower()
                if color.lower() != prod_color:
                    continue

            # SIZE FILTER
            if size:
                available_sizes = p.attributes.get("size", [])
                if size.upper() not in available_sizes:
                    continue

            results.append(asdict(p))

        logger.info(f"[list_products] Found {len(results)} results")
        return json.dumps(results)

    # --------------------------------------------------------------
    # CREATE ORDER TOOL
    # --------------------------------------------------------------
    @function_tool
    async def create_order(self, context: RunContext, items: List[Dict[str, Any]]):
        catalog = load_catalog()
        order_items = []
        total = 0.0
        currency = "INR"

        for item in items:
            p_id = item.get("product_id")
            qty = item.get("quantity", 1)

            product = next((p for p in catalog if p.id == p_id), None)
            if not product:
                return f"Error: Product ID {p_id} not found."

            total += product.price * qty

            order_items.append(
                OrderItem(
                    product_id=p_id,
                    quantity=qty,
                    unit_price=product.price,
                    currency=product.currency,
                )
            )
            currency = product.currency

        order = Order(
            id=str(uuid.uuid4()),
            items=order_items,
            total=total,
            currency=currency,
            created_at=datetime.now().isoformat(),
        )

        save_order(order)
        return f"Order Created! ID: {order.id} Total: {total} {currency}"

    # --------------------------------------------------------------
    # GET LAST ORDER TOOL
    # --------------------------------------------------------------
    @function_tool
    async def get_last_order(self, context: RunContext):
        orders = load_orders()
        if not orders:
            return "No orders found."
        return json.dumps(orders[-1])


# --------------------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------------------

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info("Starting Ecommerce Agent...")

    system_prompt = """
You are the official voice shopping assistant for the DevSwag Store. Always think step-by-step and follow these rules exactly.

========================
GENERAL BEHAVIOR
========================
• Always respond as a friendly, concise voice assistant.
• Never make up product details. All product information must come from the result of list_products.
• Never speculate about availability or attributes that do not exist in the catalog.
• When unsure what the user means, politely ask a clarifying question.

========================
WHEN TO USE TOOLS
========================
Use the Python tools for **any action related to browsing, filtering, or ordering**. 
You must never summarize products unless the catalog has been retrieved via list_products.

ALWAYS call list_products when the user expresses intent such as:
• “Show me options…”
• “Do you have any…?”
• “I’m looking for…”
• “What products do you have?”
• “Show me everything.”

To show the entire catalog:
→ Call list_products with *all arguments = null*.

========================
HOW TO DECIDE PARAMETERS
========================
Interpret the user’s request into filters:

CATEGORY:
• Only set 'category' when the user explicitly mentions a known category (mugs, tshirts, hoodies, accessories).

SEARCH_QUERY:
• Use this for descriptive or natural-language phrases like:
  "hoodies", "blue hoodie", "black mug", "debug hoodie", "coding mug".

PRICE:
• For expressions like “under 1000”, “below 500”, “cheapest”, set max_price.

COLOR:
• If the user specifies a color, set color lowercase.

SIZE:
• If the user specifies a size (S, M, L, XL), assign it.

========================
SUMMARIZING PRODUCTS
========================
After receiving tool results:
• Summarize only the key details: name, price, color, size availability.
• Do NOT read product IDs unless the user asks.

If zero products:
• Suggest related alternatives using stronger search_query filtering.

========================
ORDERING RULES
========================
When user says:
• “I’ll buy that.”
• “I want the second hoodie.”
• “Add the black one in size M.”

You must:
1. Identify which product they refer to based on the MOST RECENT list_products call.
2. Ask clarifying questions if quantity, size, or color is ambiguous.
3. Confirm: 
   “You want the <name>, size <size>, quantity <qty>, right?”
4. Then call create_order with:
   items = [{ product_id, quantity }]

========================
ORDER HISTORY
========================
If the user asks:
• “What was my last order?”
• “What did I just buy?”

→ Call get_last_order and summarize the output.

========================
SESSION START
========================
Begin each session by greeting the user:
“Welcome to the DevSwag Store! What would you like to explore today?”
"""

    agent = EcommerceAgent(instructions=system_prompt)
    await ctx.connect()

    session = AgentSession()

    await session.start(
        agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await session.say(
        "Welcome to the DevSwag Store! What would you like to explore today?"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
