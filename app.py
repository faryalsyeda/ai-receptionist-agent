"""FastAPI demo for the AI Receptionist Agent.

Run:
    uvicorn app:app --reload

POST /message with JSON {"message": "...", "session_id": "optional"}
returns the agent's action and reply. Sessions are kept in memory
per session_id. No LLM is used.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from receptionist import answer, new_session

app = FastAPI(title="AI Receptionist Agent")

_sessions = {}


class MessageRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.post("/message")
def message(request: MessageRequest):
    session = _sessions.setdefault(request.session_id, new_session())
    result = answer(request.message, session)
    _sessions[request.session_id] = result["session"]
    return {"action": result["action"], "reply": result["reply"],
            "record": result.get("record")}


@app.get("/")
def root():
    return {"service": "AI Receptionist Agent",
            "usage": "POST /message with {\"message\": \"...\", \"session_id\": \"...\"}"}
