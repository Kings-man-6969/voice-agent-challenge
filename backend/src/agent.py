import logging
import sqlite3
import pathlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

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

logger = logging.getLogger("day6-fraud-agent")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --- Data Structures ---

@dataclass
class FraudCase:
    username: str
    security_identifier: str
    card_ending: str
    transaction_name: str
    transaction_amount: str
    transaction_time: str
    transaction_category: str
    transaction_source: str
    transaction_location: str
    security_question: str
    security_answer: str
    status: str
    outcome_note: str

@dataclass
class SessionData:
    fraud_case: Optional[FraudCase] = None
    verified: bool = False

RunContext_T = RunContext[SessionData]

# --- Database Helper ---

def get_db_path():
    return pathlib.Path(__file__).parent.parent / "fraud_cases.db"

def get_fraud_case(username: str) -> Optional[FraudCase]:
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fraud_cases WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return FraudCase(*row)
        return None
    except Exception as e:
        logger.error(f"Error fetching fraud case: {e}")
        return None

def update_fraud_case_status(username: str, status: str, note: str):
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("UPDATE fraud_cases SET status = ?, outcome_note = ? WHERE username = ?", (status, note, username))
        conn.commit()
        conn.close()
        logger.info(f"Updated case for {username}: {status} - {note}")
    except Exception as e:
        logger.error(f"Error updating fraud case: {e}")

# --- Fraud Agent ---

class FraudAgent(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-miles", style="Promo"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def update_case_status(self, context: RunContext_T, status: str, outcome_note: str):
        """
        Update the status of the fraud case in the database.
        status options: 'confirmed_safe', 'confirmed_fraud', 'verification_failed'
        outcome_note: A brief summary of the call outcome.
        """
        case = context.userdata.fraud_case
        if case:
            update_fraud_case_status(case.username, status, outcome_note)
            return "Case updated successfully."
        else:
            return "No active case to update."

# --- Entrypoint ---

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    # Pre-load a case for the demo (Simulating outbound call)
    # Randomly select a user to simulate different scenarios
    import random
    available_users = ["John", "Jane", "Alice", "Bob", "Charlie"]
    target_username = random.choice(available_users)
    
    logger.info(f"Starting fraud alert call for: {target_username}")
    
    case = get_fraud_case(target_username)
    
    if not case:
        logger.error(f"Could not find case for {target_username}")
        return

    userdata = SessionData(fraud_case=case)
    
    # Inject dynamic instructions with case details
    initial_instructions = f"""
        You are a Fraud Detection Representative for I.C.I.C.I. Bank.

        Context:
        You are calling the customer, {case.username}, regarding a suspicious transaction on their account ending in {case.card_ending}.

        Your Objective:
        1. Begin speaking immediately. Do not wait for the customer to respond first.
        2. Introduce yourself using this exact sentence:
        "Hello, this is the Fraud Department at I.C.I.C.I. Bank. Am I speaking with {case.username}?"
        3. Confirm that you are speaking to the correct person Say "Can you answer a security question to confirm your identity?".
        4. Conduct a security verification by asking the security question:
        "{case.security_question}".
        5. If the customer's answer matches "{case.security_answer}" (allowing minor natural variations), continue.
        6. If the answer does not match, politely end the call.
        7. After successful verification, clearly read out the suspicious transaction details:
            - Merchant: {case.transaction_name}
            - Amount: {case.transaction_amount}
            - Time: {case.transaction_time}
            - Location: {case.transaction_location}
        8. Ask the customer: "Did you authorize this transaction?"
        9. If the customer says YES (authorized):
            - Mark the case as "confirmed_safe".
            - Say: "Thank you. I've marked this as safe. You can continue using your card."
            - End the call.
        10. If the customer says NO (unauthorized):
            - Mark the case as "confirmed_fraud".
            - Say: "I've marked this as fraudulent. Your card is now blocked and a new one will be mailed to you."
            - End the call.

        Tone:
        Maintain a professional, calm, reassuring, and efficient style. Never ask for the customer's name; you already know it.
        Note: Make sure you follow this step by step and not miss any instructions

    """
    
    agent = FraudAgent(instructions=initial_instructions)

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
    await session.response.create()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
