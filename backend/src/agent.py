import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    # llm,
    function_tool,
    RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from typing import Annotated
import wellness

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self, initial_context: str = "", current_date: str = "", day_number: int = 1) -> None:
        self.current_date = current_date
        super().__init__(
            instructions=f"""You are a supportive, grounded health and wellness voice companion.
            Your goal is to check in with the user about their mood and intentions for the day.
            
            Current Date: {current_date}
            Day Number: {day_number}
            {initial_context}

            Conversation Flow:
            1. **Greet First**: Warmly welcome the user with "Welcome to Day {day_number}!". If there's context from a previous day, reference it (e.g., "Last time you were feeling...").
            2. **Mood Check**: Ask about their mood and energy (e.g., "How are you feeling today?", "What's your energy like?"). Avoid medical diagnosis.
            3. **Intentions**: Ask about 1-3 objectives for the day (e.g., "What would you like to get done?", "Any self-care plans?").
            4. **Advice**: Offer simple, grounded, non-medical advice (e.g., "Remember to take breaks", "Maybe a short walk would help").
            5. **Recap & Confirm**: Summarize what they said (Mood + Objectives) and ask "Does this sound right?".
            6. **Persist**: Once confirmed, use the `save_checkin` tool to save the entry. Then wish them a great day and say goodbye.
            """,
        )

    @function_tool
    async def save_checkin(
        self, 
        ctx: RunContext,
        mood: Annotated[str, "The user's self-reported mood or energy level"],
        objectives: Annotated[list[str], "A list of 1-3 objectives or intentions for the day"],
        summary: Annotated[str, "A brief summary of the check-in"]
    ):
        """Saves the daily wellness check-in data."""
        logger.info(f"Saving check-in: mood={mood}, objectives={objectives}, date={self.current_date}")
        wellness.save_wellness_entry(mood, objectives, summary, timestamp=self.current_date)
        return "Check-in saved successfully. You can now wish the user a great day."

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Load past wellness data
    latest_entry = wellness.get_latest_entry()
    current_date = wellness.get_next_simulated_date()
    day_number = wellness.get_day_number()
    
    initial_context = ""
    if latest_entry:
        initial_context = f"Context from previous check-in ({latest_entry['timestamp']}): Mood was '{latest_entry['mood']}', Objectives were {latest_entry['objectives']}. Use this to warmly welcome the user back."

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(initial_context=initial_context, current_date=current_date, day_number=day_number),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()

    # Trigger the agent to speak first
    logger.info("Triggering initial greeting")
    await session.response.create()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
