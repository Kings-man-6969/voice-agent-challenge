# Day 5: SDR Voice Agent (Zomato)

I have implemented the Day 5 challenge: a Sales Development Representative (SDR) voice agent for **Zomato**.

## Features
- **Persona:** Acts as a Zomato SDR, professional and helpful.
- **Knowledge Base:** Answers questions about Zomato's business model, restaurant listing, pricing, and Zomato Gold using a loaded JSON dataset.
- **Lead Qualification:** Naturally collects lead information (Name, Company, Email, Role, Use Case, Team Size, Timeline) during the conversation.
- **Data Persistence:** Saves the collected lead information to `backend/leads/current_lead.json` in real-time.
- **Summarization:** Provides a verbal summary at the end of the call.

## Files Created
- `backend/shared-data/zomato_data.json`: Contains Zomato's FAQ and pricing info.
- `backend/src/agent.py`: The main agent code.
- `backend/run_agent.bat`: A helper script to run the agent.

## How to Run
1.  Navigate to the `backend` directory.
2.  Run the batch script:
    ```bat
    run_agent.bat
    ```
    (Or manually: `.venv\Scripts\python.exe src\agent.py dev`)
3.  Open the LiveKit Agent Playground (https://agents-playground.livekit.io/).
4.  Connect to your local instance.

## Verification Steps
1.  **Connect:** Start the conversation. The agent should greet you as a Zomato SDR.
2.  **Ask Questions:**
    - "What does Zomato do?"
    - "How much does it cost to list my restaurant?"
    - "Tell me about Zomato Gold."
3.  **Provide Info:** When asked, provide your details (e.g., "I own a small cafe called Chai Point", "My name is Rahul").
4.  **Finish:** Say "That's all for now" or "Thanks, goodbye".
5.  **Check Output:**
    - The agent should give a verbal summary.
    - Check the file `backend/leads/current_lead.json`. It should contain the details you provided.

## Next Steps
- Record your video demo.
- Post on LinkedIn with the required tags.
