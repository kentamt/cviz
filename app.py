import sys
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import threading
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], 
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# Dedicated health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")
# Serve the main application
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

