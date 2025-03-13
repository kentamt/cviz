import sys
import os
import logging
import asyncio
import json
import time
import signal
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import JSONResponse
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
        
        # Simulation process
        self.simulation_process = None
        self.current_simulation_type = "canvas"  # Default to canvas
        
        # Message cache to store the latest message for each topic
        # This ensures new clients can receive the current state immediately
        self.message_cache = {}
        
        # Store geometry history per topic (for topics that need history)
        self.geometry_history = defaultdict(list)
        self.history_limits = defaultdict(lambda: 1)  # Default to keep only the latest message
    
    def add_subscriber(self, topic_name, history_limit=1):
        """Add a new subscriber with optional history retention."""
        new_sub = Subscriber(topic_name=topic_name)
        self.sub_list.append(new_sub)
        self.history_limits[topic_name] = history_limit
        return new_sub
    
    async def register_client(self, websocket: WebSocket):
        """Register a new WebSocket client and send cached data"""
        await websocket.accept()
        self.clients.add(websocket)
        logging.info(f"New WebSocket client connected. Total: {len(self.clients)}")
        
        # Send cached messages to the new client
        await self.send_cached_messages_to_client(websocket)
    
    async def send_cached_messages_to_client(self, websocket: WebSocket):
        """Send all cached messages to a newly connected client"""
        try:
            # Send the latest state for each topic
            for topic, message in self.message_cache.items():
                logging.info(f"Sending cached message for topic: {topic}")
                await websocket.send_text(json.dumps(message))
                
            # For topics with history, send historical messages in order
            for topic, messages in self.geometry_history.items():
                for message in messages:
                    await websocket.send_text(json.dumps(message))
        except Exception as e:
            logging.error(f"Error sending cached messages: {e}")
    
    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        if websocket in self.clients:
            self.clients.remove(websocket)
            logging.info(f"Client disconnected. Remaining: {len(self.clients)}")
        else:
            logging.warning(f"Attempted to remove a client that wasn't registered")
    
    async def broadcast_messages(self):
        """Send messages from subscribers to all connected WebSocket clients"""
        self.running = True
        
        try:
            while self.running:
                for _sub in self.sub_list:
                    topic = _sub.topic
                    self.last_time[topic] = time.time()
                    message = _sub.get_message()
                    
                    if message is not None:
                        logging.info(f"Received message for topic: {topic}")
                        websocket_message = json.dumps(message)
                        
                        # Store in cache for new clients
                        self.message_cache[topic] = message
                        
                        # Store in history for topics with history enabled
                        if self.history_limits[topic] > 1:
                            self.geometry_history[topic].append(message)
                            # Maintain history limit
                            while len(self.geometry_history[topic]) > self.history_limits[topic]:
                                self.geometry_history[topic].pop(0)
                        
                        # Send to all connected clients
                        if self.clients:
                            logging.info(f"Broadcasting topic: {topic} to {len(self.clients)} clients")
                            
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
                        else:
                            logging.debug(f"No clients connected. Caching message for topic: {topic}")
                
                # Yield control to allow other async operations
                await asyncio.sleep(0.01)
                
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

    async def stop_simulation_process(self):
        """Safely stop a running simulation process"""
        if self.simulation_process:
            logging.info("Stopping current simulation process...")
            try:
                # For asyncio subprocesses
                if hasattr(self.simulation_process, '_transport'):
                    try:
                        # Try to terminate gracefully first
                        self.simulation_process.terminate()
                        # Give it some time to terminate
                        try:
                            await asyncio.wait_for(self.simulation_process.wait(), timeout=3.0)
                        except asyncio.TimeoutError:
                            logging.warning("Process didn't terminate, killing it")
                            self.simulation_process.kill()
                    except ProcessLookupError:
                        logging.warning("Process already gone")
                # For standard subprocesses
                elif hasattr(self.simulation_process, 'terminate'):
                    self.simulation_process.terminate()
                    # Wait without timeout
                    self.simulation_process.wait()
                else:
                    logging.warning("Unknown process type, cannot stop properly")
            except Exception as e:
                logging.error(f"Error stopping process: {e}")
            
            self.simulation_process = None
            logging.info("Current simulation process stopped")
            return True
        return False

    async def change_simulation(self, simulation_type):
        """Change the running simulation"""
        logging.info(f"Changing simulation to: {simulation_type}")
        
        # Stop the current simulation if it's running
        await self.stop_simulation_process()
        
        # Clear existing message cache and history
        self.message_cache.clear()
        self.geometry_history.clear()
        
        # Start the new simulation based on type
        script_path = "example/swarm_example.py" if simulation_type == "canvas" else "example/map_swarm_example.py"
        
        if Path(script_path).exists():
            logging.info(f"🚀 Starting {simulation_type.capitalize()} Simulator: {script_path}")
            try:
                # Create a subprocess using asyncio
                self.simulation_process = await asyncio.create_subprocess_shell(
                    f"{sys.executable} {script_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logging.info(f"🚀 Started {simulation_type.capitalize()} Simulator with PID: {self.simulation_process.pid}")
                
                # Update current simulation type
                self.current_simulation_type = simulation_type
                
                # Notify clients about the simulation change
                simulation_status = {
                    "type": "simulation_status",
                    "status": "started",
                    "simulation_type": simulation_type
                }
                
                # Broadcast to all clients
                disconnected_clients = set()
                for client in self.clients:
                    try:
                        await client.send_text(json.dumps(simulation_status))
                    except Exception as e:
                        logging.error(f"Error notifying client about simulation change: {e}")
                        disconnected_clients.add(client)
                
                # Remove disconnected clients
                for client in disconnected_clients:
                    self.remove_client(client)
                
                return True
            except Exception as e:
                logging.error(f"Error starting simulation: {e}")
                return False
        else:
            logging.error(f"Simulation script not found: {script_path}")
            return False

# Create a Cviz server manager instance
cviz_manager = CvizServerManager()

# Configure topics based on simulation type
def setup_subscribers(simulation_type="canvas"):
    # Clear existing subscribers
    cviz_manager.sub_list = []
    
    if simulation_type == "canvas":
        # Canvas simulation topics (swarm_example.py)
        cviz_manager.add_subscriber(topic_name="polygon_vector")
        cviz_manager.add_subscriber(topic_name="boundary", history_limit=1)
        cviz_manager.add_subscriber(topic_name="trajectory_vector", history_limit=1)
    else:
        # Map simulation topics (map_swarm_example.py)
        cviz_manager.add_subscriber(topic_name="polygon_vector")
        # Add any additional topics specific to the map simulation

# Use lifespan to start and stop background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup the subscribers for the default simulation
    setup_subscribers(simulation_type="canvas")
    
    # Start the task
    subscriber_tasks, broadcast_task = await cviz_manager.start()
    
    # Start the default simulation
    await cviz_manager.change_simulation("canvas")
    
    yield
    
    # Cleanup
    logging.info("Shutting down...")
    await cviz_manager.stop()
    
    # Stop the simulation process if it's running
    await cviz_manager.stop_simulation_process()

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
    return {"status": "ok", "current_demo": cviz_manager.current_simulation_type}

# Endpoint to change the simulation
@app.post("/change_simulation")
async def change_simulation(request: Request):
    try:
        params = dict(request.query_params)
        simulation_type = params.get("type", "canvas")
        
        if simulation_type not in ["canvas", "map"]:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid simulation type. Must be 'canvas' or 'map'"}
            )
        
        # Set up subscribers for the new simulation
        setup_subscribers(simulation_type)
        
        # Change the simulation
        success = await cviz_manager.change_simulation(simulation_type)
        
        if success:
            return {"status": "success", "message": f"Changed to {simulation_type} simulation"}
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Failed to start simulation"}
            )
    except Exception as e:
        logging.exception("Error changing simulation")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error: {str(e)}"}
        )

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

# Serve the main application
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)