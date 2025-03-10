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
        subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_script, args=(CVIZ_SCRIPT,)).start()
    print("🚀 Started Cviz Server")

    threading.Thread(target=run_script, args=(SWARM_SCRIPT,)).start()
    print("🚀 Started Swarm Simulator")

@app.get("/")
def root():
    return {"message": "FastAPI is running, and scripts have been started"}

