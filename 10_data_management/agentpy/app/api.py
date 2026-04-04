# api.py
# HTTP surface (FastAPI) for the disaster situational brief agent — pairs with loop.py and guardrails.py
# Tim Fraser

import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .guardrails import MAX_AUTONOMOUS_TURNS, clamp_turns, min_completion_turns
from .loop import run_research_loop
from .logging_setup import configure_agent_logging

# 0. CONFIGURATION ############################################################

load_dotenv()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    configure_agent_logging()
    yield


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com").rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nemotron-3-nano:30b-cloud")

_API_DESCRIPTION = """
Teaching API for a **disaster situational brief agent**: short, structured open-source summaries aimed at
**coordination / resilience** audiences (e.g. morning-style snapshots of a named incident and follow-up questions).

> Built for **Cornell SYSEN 5381** — [**Module 10 (Data Management)**](https://github.com/timothyfraser/dsai/tree/main/10_data_management) (weekly module sequence in the course).
> <br>Author: Tim Fraser <tmf77@cornell.edu>
> <br>GitHub: [@timothyfraser](https://github.com/timothyfraser)


---

### Runtime behavior

- **Tools:** Ollama-native function calling; **web_search** uses CrewAI **SerperDevTool** (Serper API).
- **Sessions:** omit `session_id` on the first request—the server **generates** a UUID and returns it.
Reuse that `session_id` **only** when resuming after `paused_for_human`, together with the `resume_token`
from that same response. Successful (`ok`) runs clear server-side session state, so the next brief starts fresh
unless you send a new task in a resume flow.

### Intended deployment

- Primary target is **Posit Connect** as a **FastAPI** content item. 
- Deploy with **`app.api:app`** (see the module’s `manifestme.sh` / `deployme.sh` and `rsconnect deploy api` workflow).
- Environment variables such as `OLLAMA_API_KEY`, optional `SERPER_API_KEY`, and Connect server settings are set on the Connect host.

""".strip()

app = FastAPI(
    title="Disaster Situational Brief Agent",
    description=_API_DESCRIPTION,
    version="0.1.0",
    lifespan=_lifespan,
    contact={
        "name": "Tim Fraser",
        "email": "tmf77@cornell.edu",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Liveness and runtime flags.",
        },
        {
            "name": "agent",
            "description": "JSON POST endpoints for control and situational briefs (no shared-secret header).",
        },
    ],
)
app.state.run_enabled = True  # toggled via /hooks/control (single-worker demos)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    """Send browsers from the app root to the interactive OpenAPI UI."""
    return RedirectResponse(url="/docs", status_code=307)


@dataclass
class SessionState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    paused: bool = False
    resume_token: str | None = None


sessions: dict[str, SessionState] = {}


# 1. MODELS ##################################################################


class ControlBody(BaseModel):
    """Toggle whether new `/hooks/agent` work is accepted."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"action": "start"},
                {"action": "stop"},
            ]
        }
    )

    action: Literal["start", "stop"] = Field(
        ...,
        description=(
            "**`start`** — allow new agent runs (`POST /hooks/agent` returns 200 when other checks pass). "
            "**`stop`** — reject new runs with **503** until you `start` again. "
            "Case-insensitive: `Start` and `STOP` are accepted."
        ),
        examples=["start"],
    )

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class AgentBody(BaseModel):
    """Run one situational brief or continue a **paused** thread only."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "task": (
                        "Morning snapshot: flooding along the Cedar River in eastern Iowa, "
                        "last 24 hours — shelters, road closures, and river stage if reported."
                    ),
                },
                {
                    "task": "Drill-down: any evacuation or boil-water notices for Riverside neighborhood since 6am local?",
                    "session_id": "8f1c2b3a-4d5e-6f70-89ab-c0def1234567",
                    "resume_token": "paste-token-from-paused-response",
                },
            ]
        }
    )

    task: str = Field(
        ...,
        description=(
            "What you want the model to produce: usually a **disaster snapshot** (name the incident and region) "
            "or a **follow-up** (neighborhood, jurisdiction, time window, lifeline). "
            "On **resume**, this is the next user instruction appended to the saved thread (e.g. “continue” or a narrower question)."
        ),
        examples=[
            "Morning brief: wildfire perimeter and evacuation zones near [county], last 12 hours.",
        ],
        min_length=1,
    )
    session_id: str | None = Field(
        None,
        description=(
            "**First request:** omit this field (or send `null`). The server creates a **new UUID** and returns it as `session_id`. "
            "**Resume after pause:** send the **same** `session_id` you received when the prior response was `paused_for_human`. "
            "**After `ok`:** the server drops that session; your next standalone brief should omit `session_id` again."
        ),
        examples=["8f1c2b3a-4d5e-6f70-89ab-c0def1234567"],
    )
    resume_token: str | None = Field(
        None,
        description=(
            "Omit unless you are **resuming** a paused session. When the last response had `status: paused_for_human`, "
            "copy the `resume_token` from **that** JSON body and send it with the matching `session_id`. "
            "The server returns **403** if `resume_token` is wrong or missing for a paused session."
        ),
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    max_turns: int | None = Field(
        None,
        ge=1,
        le=MAX_AUTONOMOUS_TURNS,
        description=(
            "Optional ceiling on **Ollama /api/chat** round-trips for **this** request (including tool follow-ups). "
            f"Must be between **1** and **`{MAX_AUTONOMOUS_TURNS}`** (the server-wide maximum). "
            "Omit to use the default (**full** server cap). Values above the cap are rejected by validation (not clamped silently)."
        ),
        examples=[6],
    )


ControlBodyDep = Annotated[
    ControlBody,
    Body(
        openapi_examples={
            "start_accepting_work": {
                "summary": "Start — process new agent tasks",
                "description": "After this, `POST /hooks/agent` can run (subject to Ollama and other checks).",
                "value": {"action": "start"},
            },
            "stop_new_tasks": {
                "summary": "Stop — reject new agent tasks with 503",
                "description": "Useful for maintenance or demos. Existing paused sessions are unchanged until you interact again.",
                "value": {"action": "stop"},
            },
        },
    ),
]

AgentBodyDep = Annotated[
    AgentBody,
    Body(
        openapi_examples={
            "new_brief": {
                "summary": "New brief (server assigns session_id)",
                "description": "Omit `session_id` and `resume_token`. The response includes a generated `session_id` for correlation.",
                "value": {
                    "task": (
                        "Situational snapshot: major winter storm in [state], focus on power outages and "
                        "state EOC messaging in the last 24 hours."
                    ),
                    "max_turns": 6,
                },
            },
            "resume_after_pause": {
                "summary": "Resume after paused_for_human",
                "description": (
                    "Use the `session_id` and `resume_token` from the paused response. "
                    "`task` is your continuation instruction."
                ),
                "value": {
                    "task": "Add detail for the west-side river wards since yesterday 18:00 local.",
                    "session_id": "8f1c2b3a-4d5e-6f70-89ab-c0def1234567",
                    "resume_token": "paste-the-resume_token-from-previous-response",
                },
            },
        },
    ),
]


# 2. ROUTES ##################################################################


@app.get("/health", tags=["health"], summary="Health check")
async def health() -> dict[str, Any]:
    """Returns `ok`, whether new agent runs are allowed, Ollama model name, and max autonomous turn cap."""
    return {
        "ok": True,
        "run_enabled": app.state.run_enabled,
        "model": OLLAMA_MODEL,
        "max_autonomous_turns": MAX_AUTONOMOUS_TURNS,
        "min_completion_turns": min_completion_turns(),
    }


@app.post(
    "/hooks/control",
    tags=["agent"],
    summary="Start or stop accepting new agent work",
    response_description="`ok` and current `run_enabled` flag.",
)
async def hooks_control(body: ControlBodyDep) -> JSONResponse:
    """
    **`start`** — flip the server into accepting `POST /hooks/agent` (default after startup).

    **`stop`** — new `POST /hooks/agent` requests receive **503** until you call `start` again.
    """
    act = body.action
    if act == "start":
        app.state.run_enabled = True
        return JSONResponse({"ok": True, "run_enabled": True})
    app.state.run_enabled = False
    return JSONResponse({"ok": True, "run_enabled": False})


@app.post(
    "/hooks/agent",
    tags=["agent"],
    summary="Run a situational brief (or resume a paused thread)",
    response_description=(
        "JSON with `status` (`ok` | `paused_for_human` | `error`), `reply`, `turns_used`, `session_id`, "
        "`prefetch_search_used` (whether the server ran its one automatic Serper search before the LLM). "
        "`turns_used` counts **Ollama /api/chat** round-trips only (tool follow-ups included); it does not count prefetch or the optional server-injected read_skill round. "
        "`turn_cap` is the effective ceiling for this request (from optional `max_turns` or the server default). "
        "`min_completion_turns` is the minimum LLM rounds before `END_BRIEF` is accepted (may trigger a verification nudge). "
        "`resume_token` is present only when paused. `detail` explains errors or pause reason."
    ),
)
async def hooks_agent(body: AgentBodyDep) -> JSONResponse:
    """
    Runs the bounded Ollama loop for one user **`task`**.

    **Typical flow**

    1. Send **`task`** only → server assigns **`session_id`** in the response.
    2. If **`status`** is **`ok`**, the brief is done; session state is cleared.
    3. If **`status`** is **`paused_for_human`** (turn budget hit), send **`session_id`**, **`resume_token`**, and a new **`task`** to continue the same thread.
    """
    turn_cap = clamp_turns(body.max_turns)

    if not app.state.run_enabled:
        return JSONResponse(
            {
                "status": "error",
                "reply": "",
                "turns_used": 0,
                "turn_cap": turn_cap,
                "min_completion_turns": min(min_completion_turns(), turn_cap),
                "session_id": None,
                "detail": "Agent is stopped; POST /hooks/control with start.",
            },
            status_code=503,
        )
    if not OLLAMA_API_KEY:
        return JSONResponse(
            {
                "status": "error",
                "reply": "",
                "turns_used": 0,
                "turn_cap": turn_cap,
                "min_completion_turns": min(min_completion_turns(), turn_cap),
                "session_id": body.session_id,
                "detail": "OLLAMA_API_KEY is not set. Add it to .env for Ollama Cloud.",
            },
            status_code=500,
        )

    sid = body.session_id or str(uuid.uuid4())
    state = sessions.get(sid)

    if state and state.paused:
        if not body.resume_token or body.resume_token != state.resume_token:
            raise HTTPException(status_code=403, detail="Invalid or missing resume_token for paused session")
        result = run_research_loop(
            body.task,
            ollama_host=OLLAMA_HOST,
            ollama_api_key=OLLAMA_API_KEY,
            model=OLLAMA_MODEL,
            max_turns=body.max_turns,
            existing_messages=state.messages,
            continue_thread=True,
        )
    else:
        if body.resume_token and not state:
            raise HTTPException(status_code=404, detail="Unknown session_id for resume_token")
        result = run_research_loop(
            body.task,
            ollama_host=OLLAMA_HOST,
            ollama_api_key=OLLAMA_API_KEY,
            model=OLLAMA_MODEL,
            max_turns=body.max_turns,
            existing_messages=None,
            continue_thread=False,
        )

    payload: dict[str, Any] = {
        "status": result["status"],
        "reply": result["reply"],
        "turns_used": result["turns_used"],
        "turn_cap": turn_cap,
        "session_id": sid,
        "prefetch_search_used": result.get("prefetch_search_used", False),
        "forced_tool_round": result.get("forced_tool_round", False),
        "min_completion_turns": result.get("min_completion_turns", 1),
    }
    if result.get("detail"):
        payload["detail"] = result["detail"]

    if result["status"] == "paused_for_human":
        resume = result.get("resume_token")
        sessions[sid] = SessionState(messages=result.get("messages") or [], paused=True, resume_token=resume)
        payload["resume_token"] = resume
    elif result["status"] == "ok":
        sessions.pop(sid, None)
        payload["resume_token"] = None
    else:
        sessions.pop(sid, None)

    code = 200 if result["status"] != "error" else 500
    return JSONResponse(payload, status_code=code)


# Run locally (from the agentpy/ folder):
#   python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
