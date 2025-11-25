import logging
import json
import pathlib
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

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

logger = logging.getLogger("day4-tutor")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --- Data Structures ---

@dataclass
class TutorContent:
    id: str
    title: str
    summary: str
    sample_question: str

@dataclass
class UserData:
    """Stores data and agents to be shared across the session"""
    personas: dict[str, Agent] = field(default_factory=dict)
    prev_agent: Optional[Agent] = None
    ctx: Optional[JobContext] = None
    content: List[TutorContent] = field(default_factory=list)
    current_concept_index: int = 0

    def get_current_concept(self) -> Optional[TutorContent]:
        if 0 <= self.current_concept_index < len(self.content):
            return self.content[self.current_concept_index]
        return None
    
    def summarize(self) -> str:
        concept = self.get_current_concept()
        concept_title = concept.title if concept else "None"
        return f"Current Concept: {concept_title}. Available Concepts: {[c.title for c in self.content]}"

RunContext_T = RunContext[UserData]

# --- Base Agent ---

class BaseAgent(Agent):
    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name}")

        userdata: UserData = self.session.userdata
        if userdata.ctx and userdata.ctx.room:
            # Update room attributes to reflect current agent (optional, for UI/Debug)
            await userdata.ctx.room.local_participant.set_attributes({"agent": agent_name})

        chat_ctx = self.chat_ctx.copy()

        # Context Preservation: Copy recent history from previous agent
        if userdata.prev_agent:
            items_copy = self._truncate_chat_ctx(
                userdata.prev_agent.chat_ctx.items, keep_function_call=True
            )
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in items_copy if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)

        # Inject System Prompt with Context
        concept = userdata.get_current_concept()
        concept_info = ""
        if concept:
            concept_info = f"""
            Current Concept: {concept.title}
            Concept Summary: {concept.summary}
            Sample Question: {concept.sample_question}
            """

        chat_ctx.add_message(
            role="system",
            content=f"{self.instructions}\n\n{userdata.summarize()}\n{concept_info}"
        )
        await self.update_chat_ctx(chat_ctx)
        
        # Generate a reply to greet or continue the conversation
        await self.session.generate_reply()

    def _truncate_chat_ctx(
        self,
        items: list,
        keep_last_n_messages: int = 6,
        keep_system_message: bool = False,
        keep_function_call: bool = False,
    ) -> list:
        """Truncate the chat context to keep the last n messages."""
        def _valid_item(item) -> bool:
            if not keep_system_message and item.type == "message" and item.role == "system":
                return False
            if not keep_function_call and item.type in ["function_call", "function_call_output"]:
                return False
            return True

        new_items = []
        for item in reversed(items):
            if _valid_item(item):
                new_items.append(item)
            if len(new_items) >= keep_last_n_messages:
                break
        new_items = new_items[::-1]

        # Ensure we don't start with a function output without its call (basic cleanup)
        while new_items and new_items[0].type in ["function_call_output"]:
             new_items.pop(0)

        return new_items

    async def _transfer_to_agent(self, name: str, context: RunContext_T) -> Agent:
        """Transfer to another agent while preserving context"""
        userdata = context.userdata
        current_agent = context.session.current_agent
        next_agent = userdata.personas.get(name)
        
        if not next_agent:
            logger.error(f"Agent {name} not found!")
            return current_agent # Fallback

        userdata.prev_agent = current_agent
        return next_agent

    @function_tool
    async def switch_concept(self, context: RunContext_T, concept_name: str):
        """Switch the current learning concept."""
        userdata = context.userdata
        concept_name_lower = concept_name.lower()
        
        found_index = -1
        for i, c in enumerate(userdata.content):
            if c.title.lower() in concept_name_lower or c.id in concept_name_lower:
                found_index = i
                break
        
        if found_index != -1:
            userdata.current_concept_index = found_index
            new_concept = userdata.content[found_index]
            return f"Switched concept to {new_concept.title}. You should now proceed with the current mode for this new concept."
        else:
            return f"Concept '{concept_name}' not found. Available concepts: {[c.title for c in userdata.content]}"


# --- Specific Agents ---

class LearnAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are the 'Learn' mode tutor (Voice: Matthew). 
            Your goal is to EXPLAIN the current concept clearly and concisely using the provided summary.
            
            Behavior:
            1. If the user just joined, welcome them to the Active Recall Coach and ask what they want to learn (Variables or Loops).
            2. Explain the current concept using the 'Concept Summary'.
            3. After explaining, ask if they are ready to take a quiz or if they want to try teaching it back.
            4. If they ask to switch modes, use the transfer tools.
            """,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-matthew", style="Conversation"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def start_quiz(self, context: RunContext_T) -> Agent:
        """Switch to Quiz mode."""
        await self.session.say("Great! Let's test your knowledge. Switching to Quiz mode.")
        return await self._transfer_to_agent("quiz", context)

    @function_tool
    async def start_teach_back(self, context: RunContext_T) -> Agent:
        """Switch to Teach-Back mode."""
        await self.session.say("Alright, it's your turn to be the teacher. Switching to Teach-Back mode.")
        return await self._transfer_to_agent("teach_back", context)


class QuizAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are the 'Quiz' mode tutor (Voice: Alicia).
            Your goal is to TEST the user's knowledge.
            
            Behavior:
            1. Ask the 'Sample Question' for the current concept.
            2. Evaluate the user's answer.
            3. If correct, praise them. If incorrect, gently correct them.
            4. Ask if they want to switch to Learn mode or Teach-Back mode.
            """,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-alicia", style="Conversation"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def go_to_learn_mode(self, context: RunContext_T) -> Agent:
        """Switch to Learn mode."""
        await self.session.say("Okay, let's review the concept again. Switching to Learn mode.")
        return await self._transfer_to_agent("learn", context)

    @function_tool
    async def start_teach_back(self, context: RunContext_T) -> Agent:
        """Switch to Teach-Back mode."""
        await self.session.say("Ready to explain it yourself? Switching to Teach-Back mode.")
        return await self._transfer_to_agent("teach_back", context)


class TeachBackAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are the 'Teach-Back' mode tutor (Voice: Ken).
            Your goal is to LISTEN to the user's explanation and give feedback.
            
            Behavior:
            1. Ask the user to explain the current concept as if THEY were the teacher.
            2. Listen to their explanation.
            3. Give qualitative feedback:
               - Did they cover the main points in the summary?
               - Was it clear?
            4. Ask if they want to switch to Learn mode or Quiz mode.
            """,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-ken", style="Conversation"),
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def go_to_learn_mode(self, context: RunContext_T) -> Agent:
        """Switch to Learn mode."""
        await self.session.say("Let's go back to the explanation. Switching to Learn mode.")
        return await self._transfer_to_agent("learn", context)

    @function_tool
    async def start_quiz(self, context: RunContext_T) -> Agent:
        """Switch to Quiz mode."""
        await self.session.say("Let's see how you do on a quiz. Switching to Quiz mode.")
        return await self._transfer_to_agent("quiz", context)


# --- Entrypoint ---

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    # Load Content
    content_path = pathlib.Path(__file__).parent.parent / "shared-data" / "day4_tutor_content.json"
    try:
        with open(content_path, "r") as f:
            data = json.load(f)
            content_list = [TutorContent(**item) for item in data]
    except Exception as e:
        logger.error(f"Failed to load content: {e}")
        content_list = []

    userdata = UserData(ctx=ctx, content=content_list)
    
    # Initialize Agents
    learn_agent = LearnAgent()
    quiz_agent = QuizAgent()
    teach_back_agent = TeachBackAgent()

    # Register agents
    userdata.personas.update({
        "learn": learn_agent,
        "quiz": quiz_agent,
        "teach_back": teach_back_agent
    })

    session = AgentSession[UserData](
        userdata=userdata,
    )

    # Start with Learn Agent
    await session.start(
        agent=learn_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    await ctx.connect()
    
    # Trigger initial greeting
    logger.info("Triggering initial greeting")
    await session.response.create()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
