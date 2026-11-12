import asyncio
import logging
import os
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, List, Literal, Optional

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from assistant_core import (
    AssistantConfigurationError,
    AssistantProviderError,
    Brain,
    assistant_router,
)
from language_parser import language_parser
from system_monitor import collect_daily_snapshot_if_missing, collect_system_report, get_daily_history, save_daily_snapshot


app = FastAPI(title="LISA Personal AI")
daily_monitor_task: Optional[asyncio.Task] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class AssistantMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: List[ChatTurn] = Field(default_factory=list)


class MemoryCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MemoryUpdate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ActionPreview(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    params: Dict = Field(default_factory=dict)


class ActionApproval(BaseModel):
    preview_id: str


class MemorySearch(BaseModel):
    query: str = Field(default="", max_length=500)


action_previews: Dict[str, Dict] = {}
logger = logging.getLogger(__name__)
APP_ALLOWLIST = {
    "chrome": ("chrome", {"chrome.exe"}),
    "notepad": ("notepad.exe", {"notepad.exe"}),
    "edge": ("msedge", {"msedge.exe"}),
    "vscode": ("code", {"code.exe"}),
    "calculator": ("calc", {"calculator.exe", "calculatorapp.exe"}),
}


async def run_daily_monitor():
    while True:
        try:
            await asyncio.get_running_loop().run_in_executor(None, collect_daily_snapshot_if_missing)
        except (OSError, sqlite3.Error, psutil.Error, ValueError):
            logger.exception("Daily system snapshot failed")
        await asyncio.sleep(3600)


@app.on_event("startup")
async def start_daily_monitor():
    global daily_monitor_task
    daily_monitor_task = asyncio.create_task(run_daily_monitor())


@app.on_event("shutdown")
async def stop_daily_monitor():
    if daily_monitor_task is not None:
        daily_monitor_task.cancel()
        try:
            await daily_monitor_task
        except asyncio.CancelledError:
            pass


@app.get("/api/v1/status")
async def get_status():
    model = bool(os.environ.get("LISA_AI_MODEL", "").strip())
    endpoint = os.environ.get("LISA_OLLAMA_BASE_URL", "").strip()
    loopback = False
    if endpoint:
        try:
            Brain.configured_base_url()
            loopback = True
        except AssistantConfigurationError:
            loopback = False
    return {
        "status": "online",
        "mode": "local_assistant",
        "local_model_configured": model and loopback,
        "remote_fallback": False,
    }


@app.post("/api/v1/parse")
async def parse_text(request: Dict):
    text = str(request.get("text", "")).strip()
    result = language_parser.parse_command(text)
    result["response"] = language_parser.get_response_message(
        result["intent"], result["entities"], language="thai"
    )
    return result


@app.post("/api/v1/assistant")
async def assistant_message(request: AssistantMessage):
    if len(request.history) > 10:
        raise HTTPException(status_code=400, detail="At most 10 recent chat messages are accepted.")
    try:
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            assistant_router.respond,
            request.message,
            [turn.model_dump() if hasattr(turn, "model_dump") else turn.dict() for turn in request.history],
        )
        return {"response": response}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AssistantConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AssistantProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/v1/skills")
async def list_skills():
    return {"skills": [
        {"id": "local-chat", "name": "Local chat", "permissions": ["model-context"], "mutates": False},
        {"id": "local-memory", "name": "SQLite memory", "permissions": ["read", "create", "edit", "delete"], "mutates": True},
        {"id": "approved-app-control", "name": "Approved app open/close", "permissions": ["preview", "approve", "execute"], "mutates": True},
    ]}


@app.get("/api/v1/memory")
async def list_memory():
    return {"memories": assistant_router.memory.list()}


@app.post("/api/v1/memory/search")
async def search_memory(request: MemorySearch):
    return {"matches": assistant_router.memory.search(request.query)}


@app.post("/api/v1/memory")
async def create_memory(request: MemoryCreate):
    raise HTTPException(
        status_code=409,
        detail="Use /api/v1/actions/preview, /approve, and /execute for explicit memory approval.",
    )

@app.put("/api/v1/memory/{memory_id}")
async def update_memory(memory_id: int, request: MemoryUpdate):
    raise HTTPException(
        status_code=409,
        detail="Use /api/v1/actions/preview, /approve, and /execute for explicit memory approval.",
    )

@app.delete("/api/v1/memory/{memory_id}")
async def delete_memory(memory_id: int):
    raise HTTPException(
        status_code=409,
        detail="Use /api/v1/actions/preview, /approve, and /execute for explicit memory approval.",
    )


@app.post("/api/v1/actions/preview")
async def preview_action(request: ActionPreview):
    now = time.time()
    for preview_id, preview in list(action_previews.items()):
        if preview["expires"] < now:
            action_previews.pop(preview_id, None)

    action = request.action.strip().lower()
    params = request.params

    if action in {"app_open", "app_close"}:
        app_name = str(params.get("app", "")).strip().lower()
        if app_name not in APP_ALLOWLIST:
            raise HTTPException(status_code=400, detail="That app is not in the approved allowlist.")
        if action == "app_open":
            description = f"Open the local application {app_name}."
        else:
            description = (
                f"Close every running {app_name} process in the approved allowlist. "
                "Unsaved work in that app may be lost."
            )
        normalized = {"app": app_name}
    elif action == "memory_create":
        text = str(params.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="Memory text is required.")
        description = f"Save this memory in local SQLite: {text}"
        normalized = {"text": text}
    elif action == "memory_edit":
        memory_id = params.get("id")
        text = str(params.get("text", "")).strip()
        if (
            isinstance(memory_id, bool)
            or not isinstance(memory_id, int)
            or memory_id < 1
            or not text
        ):
            raise HTTPException(status_code=400, detail="Memory id and text are required.")
        existing = assistant_router.memory.get(memory_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Memory not found.")
        description = (
            f"Replace memory #{memory_id}.\n"
            f"Current text: {existing['text']}\nNew text: {text}"
        )
        normalized = {"id": memory_id, "text": text}
    elif action == "memory_delete":
        memory_id = params.get("id")
        if isinstance(memory_id, bool) or not isinstance(memory_id, int) or memory_id < 1:
            raise HTTPException(status_code=400, detail="Memory id is required.")
        existing = assistant_router.memory.get(memory_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Memory not found.")
        description = (
            f"Permanently delete memory #{memory_id} from local SQLite:\n"
            f"{existing['text']}"
        )
        normalized = {"id": memory_id}
    else:
        raise HTTPException(status_code=400, detail="That action is not in the reviewed allowlist.")

    if len(action_previews) >= 100:
        raise HTTPException(
            status_code=429,
            detail="Too many pending action previews. Wait for them to expire and try again.",
        )

    preview_id = str(uuid.uuid4())
    action_previews[preview_id] = {
        "action": action,
        "params": normalized,
        "description": description,
        "expires": time.time() + 60,
        "approved": False,
    }
    return {"preview_id": preview_id, "description": description, "expires_in_seconds": 60}


@app.post("/api/v1/actions/approve")
async def approve_action(request: ActionApproval):
    preview = action_previews.get(request.preview_id)
    if not preview:
        raise HTTPException(status_code=409, detail="Preview is missing or already used.")
    if time.time() > preview["expires"]:
        action_previews.pop(request.preview_id, None)
        raise HTTPException(status_code=410, detail="Preview expired.")
    preview["approved"] = True
    return {"preview_id": request.preview_id, "approved": True}


@app.post("/api/v1/actions/execute")
async def execute_action(request: ActionApproval):
    preview = action_previews.pop(request.preview_id, None)
    if not preview:
        raise HTTPException(status_code=409, detail="Preview is missing or already used.")
    if time.time() > preview["expires"]:
        raise HTTPException(status_code=410, detail="Preview expired.")
    if not preview["approved"]:
        raise HTTPException(status_code=403, detail="Explicit approval is required.")

    action = preview["action"]
    params = preview["params"]
    if action == "memory_create":
        try:
            assistant_router.memory.create(params["text"])
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"status": "success", "message": "Memory saved locally."}
    if action == "memory_edit":
        try:
            assistant_router.memory.update(params["id"], params["text"])
        except KeyError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="That memory already exists.") from error
        return {"status": "success", "message": "Memory updated locally."}
    if action == "memory_delete":
        try:
            assistant_router.memory.delete(params["id"])
        except KeyError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"status": "success", "message": "Memory deleted locally."}
    if action == "app_open":
        app_name = params["app"]
        executable = APP_ALLOWLIST[app_name][0]
        try:
            subprocess.Popen([executable], shell=False)
        except OSError as error:
            raise HTTPException(
                status_code=424,
                detail=f"Could not open the approved application {app_name}.",
            ) from error
        return {"status": "success", "message": f"Opened {app_name}."}
    if action == "app_close":
        app_name = params["app"]
        names = APP_ALLOWLIST[app_name][1]
        count = 0
        access_denied = 0
        for proc in psutil.process_iter():
            try:
                if (proc.name() or "").lower() in names:
                    proc.kill()
                    count += 1
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                access_denied += 1
        if access_denied:
            return {
                "status": "partial",
                "message": (
                    f"Closed {count} approved {app_name} process(es); "
                    f"could not close {access_denied} due to Windows permissions."
                ),
            }
        return {"status": "success", "message": f"Closed {count} approved {app_name} process(es)."}
    raise HTTPException(status_code=400, detail="Unsupported approved action.")


@app.post("/api/v1/control")
async def control_disabled():
    raise HTTPException(
        status_code=410,
        detail="Direct control is disabled. Use the approved action preview API.",
    )


@app.post("/api/v1/system/report")
async def create_system_report():
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(None, collect_system_report)
    await loop.run_in_executor(None, save_daily_snapshot, report)
    return {"report": report, "saved": True}


@app.get("/api/v1/system/history")
async def system_history(days: int = 30):
    if not 1 <= days <= 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    return {"reports": get_daily_history(days)}


ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent


@app.get("/")
@app.get("/app")
async def serve_index():
    return FileResponse(ROOT_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(ROOT_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
