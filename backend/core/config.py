import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    debug_mode: bool = os.environ.get("DEBUG_MODE", "false").lower() == "true"
    use_fallback_detection: bool = os.environ.get("USE_FALLBACK_DETECTION", "false").lower() == "true"

settings = Settings()
