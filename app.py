import sys
import os
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from libs.cviz_server import CvizServerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

# Create a Cviz server manager instance
cviz_manager = CvizServerManager()

# Configure default topics for swarm example
def setup_swarm_example():
    # Add subscribers with history limits where needed
    cviz_manager.add_subscriber(topic_name="multipolygon")
    cviz_manager.add_subscriber(topic_name="point")
    cviz_manager.add_subscriber(topic_name="linestring")
    cviz_manager.add_subscriber(topic_name="multilinestring")
    cviz_manager.add_subscriber(topic_name="feature_collection")

# Use lifespan to start and stop background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up the subscribers
    setup_swarm_example()

    # Start the task
    subscriber_tasks, broadcast_task = await cviz_manager.start()

    # Run any startup scripts asynchronously
    # script_path = "example/geojson_example.py"
    script_path = "example/geojson_london_example.py"

    if Path(script_path).exists():
        logging.info("🚀 Starting Swarm Simulator...")

        # Create a subprocess using asyncio
        proc = await asyncio.create_subprocess_shell(
            f"{sys.executable} {script_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logging.info("🚀 Started Swarm Simulator")

    yield

    # Cleanup
    logging.info("Shutting down...")
    await cviz_manager.stop()


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await cviz_manager.register_client(websocket)
    try:
        while True:
            # Just wait for the connection to close
            data = await websocket.receive_text()

    except WebSocketDisconnect:
        cviz_manager.remove_client(websocket)

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        cviz_manager.remove_client(websocket)


# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")

# Serve the main application
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
