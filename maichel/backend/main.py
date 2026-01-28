from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pyautogui
import os
import subprocess
import psutil
from pydantic import BaseModel
from typing import Optional, Dict
from pathlib import Path
from language_parser import language_parser
from safety import safety_guardian
from logger import command_logger

# GOD MODE CONFIGURATION
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False 

app = FastAPI(title="Lisa AI - God Mode")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Command(BaseModel):
    action: str
    params: Optional[dict] = None

# --- API V1 ROUTES ---
# We use /api/v1 prefix to avoid any collisions

@app.get("/api/v1/status")
async def get_status():
    return {"status": "online", "mode": "god_mode"}

@app.post("/api/v1/parse")
async def parse_text(request: Request):
    data = await request.json()
    text = data.get("text", "")
    result = language_parser.parse_command(text)
    # Add localized response message
    result['response'] = language_parser.get_response_message(result['intent'], result['entities'])
    return result

@app.post("/api/v1/control")
async def control(cmd: Command):
    action = cmd.action
    params = cmd.params or {}
    
    # 1. Logging Initialization
    log_context = {
        "action": action,
        "params": params,
        "result": "success",
        "message": ""
    }
    
    try:
        # 2. Safety Validations
        if action == "terminal":
            cmd_text = params.get("command", "")
            safety_check = safety_guardian.validate_system_command(cmd_text)
            if not safety_check['safe']:
                log_context.update({"result": "blocked", "message": safety_check['blocked_reason']})
                command_logger.log_command(**log_context)
                return {"status": "blocked", "message": safety_check['blocked_reason']}

        # 3. Execution Logic
        if action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            log_context["message"] = "System Locked"
        
        elif action == "launch_app":
            app_name = params.get("app", "")
            app_cmd = {
                'chrome': 'start chrome',
                'notepad': 'start notepad',
                'explorer': 'explorer .',
                'cmd': 'start cmd'
            }.get(app_name.lower(), f'start {app_name}')
            
            subprocess.Popen(app_cmd, shell=True)
            log_context["message"] = f"Launched {app_name}"

        elif action == "app_close":
            app_name = params.get("app", "")
            count = 0
            for proc in psutil.process_iter(['name']):
                if app_name.lower() in proc.info['name'].lower():
                    proc.kill()
                    count += 1
            log_context["message"] = f"Closed {count} instances of {app_name}"

        elif action == "system_shutdown":
            os.system("shutdown /s /t 60") # 1 minute delay
            log_context["message"] = "System shutdown scheduled in 60 seconds"
        
        elif action == "system_restart":
            os.system("shutdown /r /t 60")
            log_context["message"] = "System restart scheduled in 60 seconds"

        elif action == "system_sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            log_context["message"] = "System entering sleep mode"

        elif action == "file_create":
            filename = params.get("filename", "new_file.txt")
            filepath = ROOT_DIR / filename
            # Safety check
            safety_check = safety_guardian.validate_file_operation(str(filepath), "create")
            if not safety_check['safe']:
                log_context.update({"result": "blocked", "message": safety_check['blocked_reason']})
                command_logger.log_command(**log_context)
                return {"status": "blocked", "message": safety_check['blocked_reason']}
            
            with open(filepath, 'w') as f:
                f.write("Created by Lisa AI")
            log_context["message"] = f"File created: {filename}"

        elif action == "file_delete":
            filename = params.get("filename", "")
            filepath = ROOT_DIR / filename
            # Safety check
            safety_check = safety_guardian.validate_file_operation(str(filepath), "delete")
            if not safety_check['safe']:
                log_context.update({"result": "blocked", "message": safety_check['blocked_reason']})
                command_logger.log_command(**log_context)
                return {"status": "blocked", "message": safety_check['blocked_reason']}
            
            if os.path.exists(filepath):
                os.remove(filepath)
                log_context["message"] = f"File deleted: {filename}"
            else:
                log_context.update({"result": "error", "message": "File not found"})
                command_logger.log_command(**log_context)
                return {"status": "error", "message": "File not found"}

        elif action == "volume":
            direction = params.get("direction", "up")
            if direction == "up":
                pyautogui.press("volumeup")
            elif direction == "down":
                pyautogui.press("volumedown")
            elif direction == "mute":
                pyautogui.press("volumemute")
            log_context["message"] = f"Volume {direction}"

        elif action == "brightness":
            level = params.get("level")
            direction = params.get("direction")
            
            if level is not None:
                cmd_pwr = f"powershell (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(0, {level})"
                subprocess.run(cmd_pwr, shell=True)
                log_context["message"] = f"Brightness set to {level}%"
            elif direction == "up":
                pyautogui.press("brightnessup")
                log_context["message"] = "Brightness increased"
            elif direction == "down":
                pyautogui.press("brightnessdown")
                log_context["message"] = "Brightness decreased"

        elif action == "settings":
            page = params.get("page", "")
            uri_map = {
                'display': 'display',
                'apps': 'appsfeatures',
                'volume': 'apps-volume',
                'wifi': 'network-wifi',
                'bluetooth': 'bluetooth',
                'personalization': 'personalization'
            }
            target = uri_map.get(page.lower(), page)
            subprocess.Popen(f"start ms-settings:{target}", shell=True)
            log_context["message"] = f"Opening {page} settings"
            
        elif action == "terminal":
            command = params.get("command", "")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            log_context["message"] = "Terminal command executed"
            # Log success but return stdout separately
            command_logger.log_command(**log_context)
            return {"status": "success", "stdout": result.stdout}
            
        # Final success log for all other actions
        command_logger.log_command(**log_context)
        return {"status": "success", "message": log_context["message"] or f"Action {action} processed"}

    except Exception as e:
        log_context.update({"result": "error", "message": str(e)})
        command_logger.log_command(**log_context)
        return {"status": "error", "message": str(e)}

# --- UI & STATIC FILES ---
ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent

@app.get("/")
@app.get("/app")
async def serve_index():
    return FileResponse(ROOT_DIR / "index.html")

# Static files mount at the bottom
# Everything else in the directory (app.js, style.css, etc.) will be served here
app.mount("/static", StaticFiles(directory=str(ROOT_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
