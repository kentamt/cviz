import subprocess
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
import threading
import uvicorn

app = FastAPI()
app.mount("/", StaticFiles(directory="web", html=True), name="weba")

if __name__ == "__main__":
    
    SWARM_SCRIPT = Path("example/swarm_example.py")
    CVIZ_SCRIPT = Path("example/cviz_example.py")

    # Start the cviz server
    cviz_process = subprocess.Popen(["python", CVIZ_SCRIPT], shell=False)
    print("🚀 Started Cviz Server")

    # Start the swarm simulator
    swarm_process = subprocess.Popen(["python", SWARM_SCRIPT], shell=False)
    print("🚀 Started Swarm Simulator")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)