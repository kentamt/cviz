import sys
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import threading

app = FastAPI()

app.mount("/", StaticFiles(directory="web", html=True), name="web")

SWARM_SCRIPT = Path("example/swarm_example.py")
CVIZ_SCRIPT = Path("example/cviz_example.py")

def run_script(script_path: Path):
    process = subprocess.Popen(
        ["python", script_path],
        stdout=sys.stdout, 
        stderr=sys.stderr, 
        text=True,  
        bufsize=1  
    )

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting scripts...", flush=True)
    
    threading.Thread(target=run_script, args=(CVIZ_SCRIPT,), daemon=True).start()
    print("🚀 Started Cviz Server", flush=True)

    threading.Thread(target=run_script, args=(SWARM_SCRIPT,), daemon=True).start()
    print("🚀 Started Swarm Simulator", flush=True)

@app.get("/")
def root():
    return {"message": "FastAPI is running, and scripts have been started"}

