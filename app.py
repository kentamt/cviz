import sys
import os
import logging
import asyncio
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from libs.subscriber import Subscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

class CvizServerManager:
    """Manages WebSocket connections and ZMQ subscriptions for Cviz"""
    
    def __init__(self):
        self.clients = set()
        self.sub_list = []
        self.last_time = {}
        self.running = False
        self.task = None
    
    def add_subscriber(self, topic_name):
        """Add a new subscriber."""
        new_sub = Subscriber(topic_name=topic_name)
        self.sub_list.append(new_sub)
        return new_sub
    
    async def register_client(self, websocket: WebSocket):
        """Register a new WebSocket client"""
        await websocket.accept()
        self.clients.add(websocket)
        logging.info(f"New WebSocket client connected. Total: {len(self.clients)}")
    
    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        self.clients.remove(websocket)
        logging.info(f"Client disconnected. Remaining: {len(self.clients)}")
    
    async def broadcast_messages(self):
        """Send messages from subscribers to all connected WebSocket clients"""
        self.running = True
        
        try:
            while self.running:
                if self.clients:
                    for _sub in self.sub_list:
                        topic = _sub.topic
                        self.last_time[topic] = time.time()
                        message = _sub.get_message()
                        
                        if message is not None:
                            logging.info(f"Sending topic: {topic}")
                            websocket_message = json.dumps(message)
                            
                            # Send to all connected clients
                            disconnected_clients = set()
                            for client in self.clients:
                                try:
                                    await client.send_text(websocket_message)
                                except Exception as e:
                                    logging.error(f"Error sending to client: {e}")
                                    disconnected_clients.add(client)
                            
                            # Remove any disconnected clients
                            for client in disconnected_clients:
                                self.remove_client(client)
                
                # Yield control to allow other async operations
                await asyncio.sleep(0)
                
        except Exception as e:
            logging.error(f"Error in broadcast task: {e}")
        finally:
            self.running = False
    
    async def start(self):
        """Start the subscription and broadcasting tasks"""
        # Start subscriber tasks
        subscriber_tasks = []
        for _sub in self.sub_list:
            subscriber_tasks.append(asyncio.create_task(_sub.subscribe()))
        
        # Start broadcast task
        self.task = asyncio.create_task(self.broadcast_messages())
        
        return subscriber_tasks, self.task
    
    async def stop(self):
        """Stop all running tasks"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

# Create a Cviz server manager instance
cviz_manager = CvizServerManager()

# Configure default topics for swarm example
def setup_swarm_example():
    cviz_manager.add_subscriber(topic_name="polygon_vector")
    cviz_manager.add_subscriber(topic_name="boundary")
    cviz_manager.add_subscriber(topic_name="trajectory_vector")

# Use lifespan to start and stop background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup the subscribers
    setup_swarm_example()
    
    # Start the task
    subscriber_tasks, broadcast_task = await cviz_manager.start()
    
    # Run any startup scripts asynchronously
    if Path("example/swarm_example.py").exists():
        logging.info("🚀 Starting Swarm Simulator...")
        # Create a subprocess using asyncio
        proc = await asyncio.create_subprocess_shell(
            f"{sys.executable} example/swarm_example.py",
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
            # You could handle incoming messages here if needed
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