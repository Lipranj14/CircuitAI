# debug_store.py
# Simple in-memory store for last parse result
# Used by /api/debug/last-parse endpoint

_last_parse_result = {
    "raw_response": None,
    "timestamp": None
}

def store_last_parse_result(raw: str):
    from datetime import datetime
    _last_parse_result["raw_response"] = raw
    _last_parse_result["timestamp"] = datetime.now().isoformat()

def get_last_parse_result() -> dict:
    return _last_parse_result
