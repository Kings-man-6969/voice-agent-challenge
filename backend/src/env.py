from dotenv import load_dotenv
import os

load_dotenv(".env.local")

print("LIVEKIT_URL =", os.getenv("LIVEKIT_URL"))
print("LIVEKIT_API_KEY =", os.getenv("LIVEKIT_API_KEY"))
print("LIVEKIT_API_SECRET =", os.getenv("LIVEKIT_API_SECRET"))
print("DEEPGRAM_API_KEY =", os.getenv("DEEPGRAM_API_KEY"))
print("MURF_API_KEY =", os.getenv("MURF_API_KEY"))
