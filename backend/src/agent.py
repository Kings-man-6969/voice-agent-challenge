import logging
import json
import random
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

logger = logging.getLogger("day8-gamemaster")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --- Data Structures for World State ---

@dataclass
class Character:
    name: str
    hp: int
    max_hp: int
    class_name: str
    stats: Dict[str, int]  # e.g., {"STR": 14, "DEX": 12}
    status: str = "Healthy"

@dataclass
class InventoryItem:
    name: str
    description: str
    quantity: int = 1

@dataclass
class Location:
    name: str
    description: str
    known_paths: List[str]

@dataclass
class WorldState:
    character: Character
    location: Location
    inventory: List[InventoryItem] = field(default_factory=list)
    quest_log: List[str] = field(default_factory=list)
    history_summary: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

RunContext_T = RunContext[WorldState]

# --- Game Master Agent ---

class GameMasterAgent(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-jordan",style="Narration"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def roll_dice(self, context: RunContext_T, sides: int = 20, count: int = 1, modifier: int = 0, reason: str = ""):
        """
        Roll dice for a check or action.
        sides: Number of sides on the die (default 20).
        count: Number of dice to roll (default 1).
        modifier: Bonus or penalty to add to the total.
        reason: What the roll is for (e.g., "Attack check", "Perception check").
        """
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        
        roll_str = f"Rolled {count}d{sides}: {rolls}"
        if modifier != 0:
            roll_str += f" + {modifier}"
        roll_str += f" = {total}"
        
        logger.info(f"Dice Roll ({reason}): {roll_str}")
        return f"[Dice Roll for {reason}] {roll_str}"

    @function_tool
    async def update_character_status(self, context: RunContext_T, hp_change: int = 0, status: Optional[str] = None):
        """
        Update the player character's HP or status.
        hp_change: Amount to change HP by (negative for damage, positive for healing).
        status: New status condition (e.g., "Injured", "Poisoned").
        """
        char = context.userdata.character
        
        if hp_change != 0:
            old_hp = char.hp
            char.hp = max(0, min(char.max_hp, char.hp + hp_change))
            logger.info(f"HP Update: {old_hp} -> {char.hp}")
        
        if status:
            char.status = status
            logger.info(f"Status Update: {status}")
            
        return f"Character updated: HP is now {char.hp}/{char.max_hp}. Status: {char.status}."

    @function_tool
    async def update_inventory(self, context: RunContext_T, item_name: str, quantity_change: int, description: str = ""):
        """
        Add or remove items from the player's inventory.
        item_name: Name of the item.
        quantity_change: Positive to add, negative to remove.
        description: Description of the item (only needed when adding new items).
        """
        inventory = context.userdata.inventory
        item = next((i for i in inventory if i.name.lower() == item_name.lower()), None)
        
        if item:
            item.quantity += quantity_change
            if item.quantity <= 0:
                inventory.remove(item)
                return f"Removed {item_name} from inventory."
            return f"Updated {item_name} quantity to {item.quantity}."
        elif quantity_change > 0:
            new_item = InventoryItem(name=item_name, description=description, quantity=quantity_change)
            inventory.append(new_item)
            return f"Added {quantity_change}x {item_name} to inventory."
        else:
            return f"Item {item_name} not found in inventory to remove."

    @function_tool
    async def update_location(self, context: RunContext_T, name: str, description: str, paths: List[str]):
        """
        Update the current location when the player moves.
        name: New location name.
        description: Short description of the new area.
        paths: List of visible paths or exits.
        """
        loc = context.userdata.location
        loc.name = name
        loc.description = description
        loc.known_paths = paths
        logger.info(f"Moved to: {name}")
        return f"Location updated to: {name}"

    @function_tool
    async def check_world_state(self, context: RunContext_T):
        """
        Check the current state of the character, inventory, and location.
        Useful for the GM to remind themselves of the context.
        """
        return context.userdata.to_json()

# --- Entrypoint ---

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    logger.info("Starting Game Master agent...")
    
    # Initialize World State
    initial_state = WorldState(
        character=Character(
            name="Traveler",
            hp=20,
            max_hp=20,
            class_name="Adventurer",
            stats={"STR": 12, "DEX": 14, "INT": 10, "CHA": 13},
            status="Healthy"
        ),
        location=Location(
            name="The Crossroads",
            description="A dusty intersection of dirt roads. To the North lies the Dark Forest. To the East, the village of Oakhaven.",
            known_paths=["North (Dark Forest)", "East (Oakhaven)"]
        ),
        inventory=[
            InventoryItem(name="Rusty Dagger", description="A simple iron dagger.", quantity=1),
            InventoryItem(name="Water Skin", description="Full of fresh water.", quantity=1)
        ],
        quest_log=["Find shelter before nightfall."]
    )
    
    system_prompt = """
   You are the Game Master guiding the player through a fast-paced, voice-friendly fantasy adventure set in Eldoria. Your job is to create a responsive, cinematic experience while using the game mechanics and tool functions accurately.

    --- CORE BEHAVIOR ---
    • Keep narration vivid but compact—aim for 2–3 punchy sentences per scene unless tension rises.
    • Always react to the player's tone, urgency, or confusion. Shape your narration to that emotional context.
    • When describing the world, use sensory hooks: sound, motion, atmosphere. Avoid overlong descriptions.
    • Maintain continuity using the world state (character HP, items, status, location, quest log, and history summary).

    --- GAME MECHANICS ---
    • Use dice rolls ONLY when the player's action has a meaningful risk or uncertainty.
    • Before rolling, think through difficulty:
    - Easy: DC 10
    - Standard: DC 15
    - Hard: DC 20+
    • After rolling, narrate outcomes with clarity:
    - Success: describe the advantage or progress.
    - Failure: impose a setback, complication, or partial consequence.
    • Never reveal the raw dice totals unless the player explicitly asks.

    --- CHARACTER MANAGEMENT ---
    • Apply injuries, exhaustion, poison, or conditions using update_character_status.
    • When players acquire or lose items, use update_inventory.
    • When moving between areas, use update_location.
    • If unclear, imagine naturalistic consequences based on Eldoria’s logic.

    --- NARRATIVE STYLE ---
    • Keep Eldoria’s tone adventurous and slightly mystical. Treat magic as powerful but risky.
    • NPCs have personality, motives, and quirks—improvise their voices, moods, and reactions.
    • Use dynamic pacing:
    - Slow and detailed during tension or mystery.
    - Quick and punchy during action, combat, or escapes.

    --- MEMORY MANAGEMENT ---
    • Summarize important story events into the world state's history_summary when helpful.
    • Reference past actions naturally. Build continuity.

    --- PLAYER FLOW ---
    1. Describe the scene clearly.
    2. Present meaningful choices if the player is silent or unsure.
    3. Ask “What do you do?” naturally—but not after every single turn.
    4. Interpret the player's intention even if phrased vaguely.
    5. Make rulings fairly; embrace emergent storytelling.

    --- VOICE OPTIMIZATION ---
    You are speaking via TTS, so:
    • Avoid overly long paragraphs—break scenes into clean, audible chunks.
    • Use pacing words like “suddenly,” “quietly,” “as you turn,” to create tempo.
    • Never list too many items at once; group them narratively.

    --- COMBAT BEHAVIOR ---
    If combat begins:
    • Describe the enemy briefly but strikingly.
    • Roll initiative with roll_dice if appropriate.
    • Keep turns fast: describe threat → player action → result → enemy reaction.
    • Don’t drag fights; push toward resolution within a few exchanges.

    --- PLAYER AGENCY ---
    Respect and adapt to ANY creative player idea, even unusual ones.
    Reward clever thinking.
    Allow partial successes.
    Give consequences that feel organic, not punitive.

    You are here to make Eldoria come alive with momentum, tension, and imagination.
    **Important:**
    - Keep descriptions punchy (2-3 sentences max usually) so the game moves fast.
    - Be fair but firm with dice rolls.
    - Immerse the player in the story.
    """
    
    agent = GameMasterAgent(instructions=system_prompt)

    session = AgentSession[WorldState](
        userdata=initial_state,
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    await ctx.connect()
    
    # Initial narration
    intro = (
        "Welcome to Eldoria. You stand at a lonely crossroads where four dirt paths meet. "
        "The sun hangs low, bleeding orange light across the ground and stretching the shadows long. "
        "To the North, the Dark Forest watches you with a stillness that feels alive. "
        "To the East, thin smoke rises from the chimneys of Oakhaven, promising warmth—or trouble. "
        "Your hand rests on a rusty dagger at your side, and a water skin taps against your belt. "
        "The wind shifts, carrying the scent of pine and something faintly metallic. "
        "What do you do?"
    )
    await session.say(intro)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
