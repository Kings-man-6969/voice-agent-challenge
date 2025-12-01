import logging
import random
import asyncio
from typing import List, Dict, Optional

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
    llm,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# ---------------------------------------------------------
#  GAME: Scenarios and Logic
# ---------------------------------------------------------

SCENARIOS = [
    "You are a time-travelling tour guide explaining modern smartphones to someone from the 1800s.",
    "You are a restaurant waiter who must calmly tell a customer that their order has escaped the kitchen.",
    "You are a customer trying to return an obviously cursed object to a very skeptical shop owner.",
    "You are a superhero whose only power is making things slightly damp, trying to join the Avengers.",
    "You are a cat trying to convince a dog to let you share its bed.",
    "You are an alien trying to order a pizza but you only know what you've seen in 90s cartoons.",
    "You are a ghost trying to haunt a house, but the new owners are really into it and think you're cool.",
    "You are a detective interrogating a suspect who is clearly a mime.",
]


# ---------------------------------------------------------
#  IMPROVED GAME STATE
# ---------------------------------------------------------

class ImprovGame:
    def __init__(self, player_name: str, max_rounds: int = 3, max_user_turns_per_round: int = 3):
        self.player_name = player_name
        self.max_rounds = max_rounds
        self.current_round = 0
        self.rounds: List[Dict[str, str]] = []  # each: {"scenario": str, "host_reaction": str, "transcript": str}
        self.phase = "intro"  # intro | awaiting_improv | reacting | done
        self.current_scenario: Optional[str] = None
        # per-round tracking
        self.current_user_turns = 0
        self.max_user_turns_per_round = max_user_turns_per_round
        self.current_transcript: List[str] = []

    def next_scenario(self) -> Optional[str]:
        if self.current_round >= self.max_rounds:
            return None
        # choose a scenario; could be expanded to avoid repeats
        choice = random.choice(SCENARIOS)
        self.current_scenario = choice
        self.current_round += 1
        self.current_user_turns = 0
        self.current_transcript = []
        return self.current_scenario

    def add_user_utterance(self, text: str):
        self.current_transcript.append(text or "")

    def add_round_result(self, scenario: str, host_reaction: str):
        transcript = " ".join(self.current_transcript).strip()
        self.rounds.append({"scenario": scenario, "host_reaction": host_reaction, "transcript": transcript})
        # clear per-round transcript (already done by next_scenario when called)


# ---------------------------------------------------------
#  HOST AGENT (improved instructions)
# ---------------------------------------------------------

class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
You are Chip Chatter, the high-energy host of a TV improv show called "Improv Battle".

Persona:
- Charismatic, playful, slightly theatrical.
- Witty teasing is allowed but never mean or abusive.
- Sound like a live TV host who hypes the crowd.

Primary duties:
- Introduce the show and explain the simple rules at the start.
- For each round: announce the scenario, invite improvisation, listen, then react with a short, constructive critique.
- Reactions should be varied: sometimes supportive, sometimes neutral, sometimes mildly critical — chosen randomly but always constructive and kind.
- Keep remarks short and punchy (1–3 sentences). Mention a specific moment from the player's performance when possible.
- When the game ends, give a warm, concise summary highlighting strengths and one quick area to improve, and sign off.

Behavioral rules:
- Always remain in character as Chip Chatter.
- Never insult or belittle the player.
- Do not give long technical lectures on improv — keep feedback actionable and brief.
"""
        )


# ---------------------------------------------------------
#  PREWARM (Load VAD)
# ---------------------------------------------------------

def prewarm(proc: JobProcess):
    # Load silero VAD once per worker process for reuse
    proc.userdata["vad"] = silero.VAD.load()


# ---------------------------------------------------------
#  HELPERS: end-of-scene detection and LLM prompt construction
# ---------------------------------------------------------

END_SCENE_PHRASES = {
    "end scene",
    "endscene",
    "end the scene",
    "okay",
    "done",
    "that's it",
    "that's all",
    "finished",
    "i'm done",
    "im done",
}

def choose_tone() -> str:
    return random.choice(["supportive", "neutral", "mildly_critical"])

def make_reaction_prompt(scenario: str, player_utterances: str, tone: str, round_no: int, player_name: str) -> str:
    return (
        f"You are Chip Chatter, host of 'Improv Battle'.\n"
        f"Round {round_no} for contestant {player_name}.\n"
        f"Scenario: {scenario}\n"
        f"Player performance transcript (short): \"{player_utterances}\"\n\n"
        f"Tone: {tone}.\n"
        "Produce a short spoken reaction (1–3 sentences) that:\n"
        " (1) references a specific moment from the performance,\n"
        " (2) gives a brief micro-critique or praise (constructive),\n"
        " (3) ends with a hype line to move to the next round.\n"
        "Keep it lively, playful, and never insulting. Output only the reaction text."
    )

def make_final_summary_prompt(player_name: str, rounds_summary: str) -> str:
    return (
        f"You are Chip Chatter. Give a warm, punchy final show summary for contestant {player_name}.\n"
        f"Use the following rounds as reference: {rounds_summary}\n"
        "Mention strengths (character commitment, comedic timing or emotional range), call out one short area for improvement, "
        "thank the contestant, and sign off with a TV-style closing line. Keep it to 3-4 sentences."
    )


# ---------------------------------------------------------
#  MAIN ENTRYPOINT
# ---------------------------------------------------------

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    # Wait for the player to join
    participant = await ctx.wait_for_participant()
    player_name = participant.name or "Contestant"
    logger.info(f"Player joined: {player_name}")

    # Game state
    game = ImprovGame(player_name=player_name, max_rounds=5, max_user_turns_per_round=1)

    # Voice AI Pipeline
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    # ---------------------------------------------------------
    #  GAME LOOP / TURN HANDLER (improved)
    # ---------------------------------------------------------

    async def game_turn(turn: llm.TurnContext):
        agent = session.agent
        user_text_raw = (turn.input_text or "").strip()
        user_text = user_text_raw.lower()

        # Early exit phrases (explicit)
        if any(keyword in user_text for keyword in ["stop game", "end show", "quit show", "exit"]):
            game.phase = "done"
            await agent.say("Got it — ending the show. Thanks so much for playing Improv Battle!", allow_interruptions=False)
            return

        # --- INTRO PHASE ---
        if game.phase == "intro":
            game.phase = "awaiting_improv"
            intro_text = (
                f"Welcome to Improv Battle! I'm your host, Chip Chatter. "
                f"You are the contestant: {game.player_name}. We'll run {game.max_rounds} rounds. "
                "Here's how it works: I'll give you a short scenario, you act it out in-character, "
                "and when you're done say 'End scene' or just pause — I'll react and then give the next one. "
                "Be bold, commit to choices, and have fun. Let's begin!\n"
            )
            scenario = game.next_scenario()
            await agent.say(intro_text + f"Round {game.current_round}: {scenario}. Action!", allow_interruptions=True)
            return

        # --- AWAITING IMPROV: collect utterances and detect end-of-scene ---
        if game.phase == "awaiting_improv":
            # record utterance for transcript
            if user_text_raw:
                game.add_user_utterance(user_text_raw)

            game.current_user_turns += 1

            # End-of-scene if user says a phrase or reaches max turn count
            if any(p in user_text for p in END_SCENE_PHRASES) or game.current_user_turns >= game.max_user_turns_per_round:
                game.phase = "reacting"
            else:
                # still waiting for more improv; do not interrupt
                return

        # --- REACTING PHASE: generate reaction and advance ---
        if game.phase == "reacting":
            tone = choose_tone()
            player_utterances = " ".join(game.current_transcript) or "(no transcript captured)"
            reaction_prompt = make_reaction_prompt(
                scenario=game.current_scenario or "unknown scenario",
                player_utterances=player_utterances[:800],  # cap length to be safe
                tone=tone,
                round_no=game.current_round,
                player_name=game.player_name,
            )

            # Build chat context and request a short reaction from the LLM
            chat_ctx = agent.chat_ctx.copy()
            chat_ctx.append(role="system", text=reaction_prompt)

            stream = session.llm.chat(chat_ctx)
            # speak the reaction (streaming if supported)
            await agent.say(stream, allow_interruptions=False)

            # attempt to capture reaction text for state storage
            reaction_text = None
            try:
                if isinstance(stream, str):
                    reaction_text = stream
                else:
                    # try common attributes for stream-like objects
                    reaction_text = getattr(stream, "text", None) or getattr(stream, "content", None)
                    # if still none, attempt to coerce to str (may be placeholder)
                    if reaction_text is None:
                        reaction_text = str(stream)
            except Exception:
                reaction_text = f"[reaction generated: tone={tone}]"

            # store round result
            game.add_round_result(game.current_scenario or "unknown", reaction_text)

            # Move to next scenario or finish
            next_scenario = game.next_scenario()
            if next_scenario:
                game.phase = "awaiting_improv"
                await asyncio.sleep(0.8)
                await agent.say(f"Nice! Onward — Round {game.current_round}: {next_scenario}. Action!", allow_interruptions=True)
            else:
                game.phase = "done"
                await asyncio.sleep(1.0)

                # Create a short summary source from stored rounds
                summary_lines = []
                for i, r in enumerate(game.rounds, start=1):
                    # truncate stored transcript and reaction for brevity
                    t = (r.get("transcript") or "")[:120]
                    hr = (r.get("host_reaction") or "")[:140]
                    summary_lines.append(f"R{i}: {r.get('scenario')} → \"{t}\" → Host: \"{hr}\"")
                rounds_summary = " || ".join(summary_lines[:6])

                final_prompt = make_final_summary_prompt(game.player_name, rounds_summary)
                chat_ctx = agent.chat_ctx.copy()
                chat_ctx.append(role="system", text=final_prompt)
                final_stream = session.llm.chat(chat_ctx)
                await agent.say(final_stream, allow_interruptions=False)

            return

        # --- If reacting or done, ignore stray speech ---
        if game.phase in ["reacting", "done"]:
            return

    # Attach handler
    session.agent.on_user_turn = game_turn


# ---------------------------------------------------------
#  START THE AGENT
# ---------------------------------------------------------

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
