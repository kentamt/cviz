import time
import logging
import asyncio
import websockets
import json

from libs.subscriber import Subscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

class CvizServer:
    """
    Relay ZMQ messages to WebSocket clients. 

    127.0.0.1:5555 -> ZMQ Publisher and Subscriber
    127.0.0.1:6789 -> WebSocket Server
    """
        
    def __init__(self, zmq_endpoint="tcp://127.0.0.1:5555", websocket_port=8675):
        # subscriber setup
        # TODO: We want to add subscriber dynamically via GUI or API
        self.sub_list = []

        # WebSocket Clients
        self.clients = set()
        self.websocket_port = websocket_port

        self.last_time = {}

    def add_subscriber(self, topic_name):
        """Add a new subscriber."""
        new_sub = Subscriber(topic_name=topic_name)
        self.sub_list.append(new_sub)

    async def websocket_handler(self, websocket, path=None):
        """Handle individual WebSocket connections."""
        logging.info("New WebSocket client connected")
        
        try:
            self.clients.add(websocket)
            logging.info(f"New WebSocket client. Total: {len(self.clients)}")
        
            await websocket.wait_closed()  # Keep connection open
            
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            
        finally:
            self.clients.remove(websocket)
            logging.info(f"Client disconnected. Remaining: {len(self.clients)}")
    
    
    async def send_message_to_clients(self):
        """Send a message to all WebSocket clients"""
        
        while True:
            try:
                if self.clients:

                    # TODO: We want to add multiple subscribers dynamically                                        
                    for _sub in self.sub_list:
                        topic = _sub.topic
                        self.last_time[topic] = time.time()
                        message = _sub.get_message()

                        if message is not None:       
                            websocket_message = json.dumps(message)
                            for client in self.clients:
                                await client.send(websocket_message)

                # Yield control to allow other async operations
                await asyncio.sleep(0)
                    
            except Exception as e:
                logging.error(f"Error sending message to clients: {e}")
                await asyncio.sleep(1)

    async def start_server(self):
        """Start WebSocket server and ZMQ listener."""
        
        server = await websockets.serve(
            self.websocket_handler, 
            "127.0.0.1", 
            self.websocket_port,
            ping_interval=20,
            ping_timeout=20,
            path="/ws"
        )
        
        logging.info(f"WebSocket server started on ws://127.0.0.1:{self.websocket_port}")
        
        # Run WebSocket server
        server_task = asyncio.create_task(server.wait_closed())
        
        # Subscribe to ZMQ messages from simulator
        # subscribe_task = asyncio.create_task(self.polygon_sub.subscribe())
        subscribe_tasks = []
        for _sub in self.sub_list:
            subscribe_tasks.append(asyncio.create_task(_sub.subscribe()))
        
        # Send messages to JS clients
        message_task = asyncio.create_task(self.send_message_to_clients())

        await server_task
        for subscribe_task in subscribe_tasks:
            await subscribe_task
        await message_task

def main():
    cviz = CvizServer()
    cviz.add_subscriber(topic_name="polygon")
    cviz.add_subscriber(topic_name="point")
    cviz.add_subscriber(topic_name="linestring")
    
    try:
        asyncio.run(cviz.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()