import sys
import os
import logging
import asyncio
import argparse
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


# Get topics from environment variable
def get_topics_from_env():
    topics_str = os.environ.get('CVIZ_TOPICS', "multipolygon,point,linestring,multilinestring,feature_collection")
    return [topic.strip() for topic in topics_str.split(',')]


# Get example script from environment variable
def get_example_from_env():
    return os.environ.get('CVIZ_EXAMPLE', "example/geojson_london_example.py")


# Configure topics for swarm example
def setup_topics():
    # Get topics from environment
    topics = get_topics_from_env()
    logging.info(f"Setting up topics: {topics}")

    # Add subscribers with history limits where needed
    for topic_name in topics:
        cviz_manager.add_subscriber(topic_name=topic_name, permanent=True)
        logging.info(f"Added subscriber for topic: {topic_name}")


# Use lifespan to start and stop background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up the subscribers
    setup_topics()

    # Start the task
    subscriber_tasks, broadcast_task = await cviz_manager.start()
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
    return {
        "status": "ok",
        "topics": get_topics_from_env(),
        "example": get_example_from_env(),
        "available_topics": list(sorted(cviz_manager.get_active_topics()))
    }


@app.get("/topics")
async def list_topics():
    return {
        "topics": list(sorted(cviz_manager.get_active_topics()))
    }


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await cviz_manager.register_client(websocket)
    try:
        while True:
            # Just wait for the connection to close
            data = await websocket.receive_text()
            await cviz_manager.handle_client_message(websocket, data)

    except WebSocketDisconnect:
        await cviz_manager.remove_client(websocket)

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await cviz_manager.remove_client(websocket)


# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")

# Serve the main application
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn

    # Parse command line args when run directly
    parser = argparse.ArgumentParser(description='Cviz server arguments')
    parser.add_argument('--topics', type=str, help='Comma-separated list of topics to subscribe to')
    parser.add_argument('--host', type=str, default="127.0.0.1", help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')

    args = parser.parse_args()

    # Set environment variables from command line args if provided
    if args.topics:
        os.environ['CVIZ_TOPICS'] = args.topics

    # Run the server
    uvicorn.run("app:app", host=args.host, port=args.port, reload=True)
