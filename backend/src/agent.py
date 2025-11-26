import logging
import json
import pathlib
import os
from dataclasses import dataclass, asdict, field
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

logger = logging.getLogger("day5-sdr")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# --- Data Structures ---

@dataclass
class LeadData:
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    use_case: Optional[str] = None
    team_size: Optional[str] = None
    timeline: Optional[str] = None
    summary: Optional[str] = None

@dataclass
class SessionData:
    lead: LeadData = field(default_factory=LeadData)
    company_data: Dict[str, Any] = field(default_factory=dict)
    leads_file_path: str = "day5_leads.json"

RunContext_T = RunContext[SessionData]

# --- SDR Agent ---

class SDRAgent(Agent):
    def __init__(self, company_data: Dict[str, Any]) -> None:
        self.company_data = company_data
        
        # Construct System Prompt
        company_info = company_data.get("company_info", {})
        faq = company_data.get("faq", [])
        pricing = company_data.get("pricing", {})
        
        faq_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in faq])
        pricing_text = json.dumps(pricing, indent=2)
        
        instructions = f"""
        You are an SDR (Sales Development Representative) for {company_info.get('name', 'Zomato')}.
        
        Company Description: {company_info.get('description')}
        Mission: {company_info.get('mission')}
        
        Your Goal:
        1. Greet the visitor warmly and ask what brought them here.
        2. Answer their questions about the company, products, and pricing using the provided FAQ and Pricing data.
        3. QUALIFY the lead by collecting the following information naturally during the conversation:
           - Name
           - Company Name
           - Email Address
           - Role/Job Title
           - Use Case (Why do they need us?)
           - Team Size
           - Timeline (When do they want to start?)
        
        4. Do NOT interrogate the user. Ask for one or two details at a time while answering their questions.
        5. If asked a question NOT in the FAQ, politely say you don't have that specific info but can connect them with a specialist.
        
        FAQ Data:
        {faq_text}
        
        Pricing Data:
        {pricing_text}
        
        When you have collected most of the info or the user indicates they are done, use the 'finish_call' tool to summarize.
        Always update the lead info using 'update_lead_info' as soon as you get new details.
        """
        
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(model="nova-3"),
            llm=google.LLM(model="gemini-2.5-flash"),
            tts=murf.TTS(voice="en-US-miles", style="Promo"), # Miles has a professional tone
            turn_detection=MultilingualModel(),
        )

    @function_tool
    async def update_lead_info(
        self, 
        context: RunContext_T, 
        name: Optional[str] = None,
        company: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        use_case: Optional[str] = None,
        team_size: Optional[str] = None,
        timeline: Optional[str] = None
    ):
        """
        Update the lead information with any new details collected from the user.
        Call this whenever the user provides any of these fields.
        """
        lead = context.userdata.lead
        if name: lead.name = name
        if company: lead.company = company
        if email: lead.email = email
        if role: lead.role = role
        if use_case: lead.use_case = use_case
        if team_size: lead.team_size = team_size
        if timeline: lead.timeline = timeline
        
        # Save to file immediately (append to a list in JSON)
        self._save_lead_to_file(context.userdata)
        
        return "Lead information updated."

    @function_tool
    async def finish_call(self, context: RunContext_T):
        """
        Call this when the user says they are done, or 'that's all', or 'thanks'.
        This will generate a summary and end the conversation.
        """
        lead = context.userdata.lead
        
        # Generate a verbal summary
        summary_text = f"Thanks for chatting, {lead.name or 'there'}. "
        summary_text += f"I've noted that you're from {lead.company or 'your company'} "
        summary_text += f"and looking to use Zomato for {lead.use_case or 'your business'}. "
        summary_text += f"We'll be in touch at {lead.email or 'your email'} soon!"
        
        lead.summary = summary_text
        self._save_lead_to_file(context.userdata)
        
        return summary_text

    def _save_lead_to_file(self, userdata: SessionData):
        # We are only saving the current lead state to a specific file for this session
        current_lead_path = pathlib.Path(__file__).parent.parent / "leads" / "current_lead.json"
        
        # Ensure directory exists
        current_lead_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(current_lead_path, "w") as f:
            json.dump(asdict(userdata.lead), f, indent=2)

# --- Entrypoint ---

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    # Load Company Data
    data_path = pathlib.Path(__file__).parent.parent / "shared-data" / "zomato_data.json"
    try:
        with open(data_path, "r") as f:
            company_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load company data: {e}")
        company_data = {}

    userdata = SessionData(company_data=company_data)
    
    agent = SDRAgent(company_data=company_data)

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
