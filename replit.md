# AI Voice Agents Challenge - LiveKit Application

## Overview
This is a full-stack voice AI agent application built with LiveKit, featuring:
- **Frontend**: Next.js React application for real-time voice interaction
- **Backend**: Python-based LiveKit Agents with Murf Falcon TTS
- **Infrastructure**: LiveKit server for real-time communication

## Project Structure
```
/
├── backend/          # Python LiveKit Agents backend
│   ├── src/         # Agent source code
│   └── tests/       # Backend tests
├── frontend/        # Next.js React frontend
│   ├── app/         # Next.js app router pages
│   ├── components/  # React components
│   └── hooks/       # Custom React hooks
└── challenges/      # Daily challenge tasks
```

## Recent Changes
- **2024-12-01**: Initial Replit setup
  - Configured Next.js to run on port 5000 with 0.0.0.0 host
  - Set up allowed origins for Replit proxy compatibility
  - Created environment configuration files
  - Installed Python 3.11 and Node.js 20 dependencies

## Environment Setup

### Frontend Environment Variables
Located in `frontend/.env.local`:
- `LIVEKIT_API_KEY`: API key for LiveKit authentication
- `LIVEKIT_API_SECRET`: Secret for LiveKit authentication
- `LIVEKIT_URL`: LiveKit server WebSocket URL

### Backend Environment Variables
Located in `backend/.env.local`:
- `LIVEKIT_URL`: LiveKit server WebSocket URL
- `LIVEKIT_API_KEY`: API key for LiveKit
- `LIVEKIT_API_SECRET`: Secret for LiveKit
- `GOOGLE_API_KEY`: Google Gemini API key (for LLM)
- `MURF_API_KEY`: Murf Falcon API key (for TTS)
- `DEEPGRAM_API_KEY`: Deepgram API key (for STT)

## Running the Application

### Frontend Only (Default)
The Replit workflow automatically runs the frontend on port 5000:
- The frontend will be available in the Replit webview
- To fully use the voice agent, you need to also run the backend and LiveKit server

### Full Stack (Manual)
To run all services together:

1. **Terminal 1 - LiveKit Server**:
   ```bash
   livekit-server --dev
   ```

2. **Terminal 2 - Backend Agent**:
   ```bash
   cd backend
   uv run python src/agent.py dev
   ```

3. **Terminal 3 - Frontend** (already running in workflow):
   The frontend workflow is already configured and running

Alternatively, use the convenience script:
```bash
chmod +x start_app.sh
./start_app.sh
```

## Key Technologies
- **LiveKit**: Real-time voice and video communication platform
- **Murf Falcon**: Ultra-fast text-to-speech API
- **Google Gemini**: Large language model for agent intelligence
- **Deepgram**: Speech-to-text transcription
- **Next.js 15**: React framework with Turbopack
- **Python 3.11**: Backend runtime with uv package manager

## Development Notes

### Port Configuration
- **Frontend**: Port 5000 (0.0.0.0) - exposed via Replit webview
- **Backend**: Auto-assigned by LiveKit agent
- **LiveKit Server**: Port 7880 (default dev mode)

### Replit-Specific Configuration
- Next.js configured to accept all origins for Replit proxy
- Frontend runs on 0.0.0.0:5000 for proper Replit routing
- Backend uses localhost for internal services

### API Keys Required
To use the full voice agent functionality, you need to obtain:
1. **Google API Key**: For Gemini LLM - [Get key](https://aistudio.google.com/app/apikey)
2. **Murf API Key**: For Falcon TTS - [Get key](https://murf.ai/api)
3. **Deepgram API Key**: For STT - [Get key](https://deepgram.com/)

Alternatively, you can use LiveKit Cloud which includes hosted models.

## Project Architecture

### Frontend Components
- **Session View**: Main interface for voice interactions
- **Control Bar**: Audio/video controls and chat input
- **Theme Toggle**: Light/dark mode switcher
- **Chat Transcript**: Message history display

### Backend Agent
- **Voice Pipeline**: STT → LLM → TTS chain
- **Turn Detection**: Multilingual speaker detection
- **Noise Cancellation**: Background voice filtering
- **Metrics Collection**: Performance tracking

## Testing
Run backend tests:
```bash
cd backend
uv run pytest
```

## Resources
- [LiveKit Documentation](https://docs.livekit.io/)
- [Murf Falcon API](https://murf.ai/api/docs/text-to-speech/streaming)
- [Original Backend Template](https://github.com/livekit-examples/agent-starter-python)
- [Original Frontend Template](https://github.com/livekit-examples/agent-starter-react)
