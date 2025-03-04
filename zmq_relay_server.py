import logging
import asyncio
import websockets
import json

from subscriber import Subscriber

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

class ZMQWebSocketRelay:
    """
    Relay ZMQ messages to WebSocket clients. 

    127.0.0.1:5555 -> ZMQ Publisher and Subscriber
    127.0.0.1:6789 -> WebSocket Server
    """
        
    def __init__(self, zmq_endpoint="tcp://127.0.0.1:5555", websocket_port=6789):
        # subscriber setup
        # TODO: We want to add subscriber dynamically via GUI or API
        self.sub_list = []

        # WebSocket Clients
        self.clients = set()
        self.websocket_port = websocket_port

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
                        message = _sub.get_message()
                        logging.debug(f"Message: {message}, Topic: {topic}")


                        if message is not None:       
                            # FIXME: for now, JS client can handle only polygon data
                            if topic == "polygon":
                                websocket_message = json.dumps(message)
                                
                                # send message to all clients connected
                                await asyncio.gather(
                                    *[client.send(websocket_message) for client in self.clients]
                                )

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
            ping_timeout=20
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
    relay = ZMQWebSocketRelay()
    relay.add_subscriber(topic_name="polygon")
    relay.add_subscriber(topic_name="message")
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()