import asyncio
import websockets
import zmq
import json
import logging
from subscriber import Subscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

class ZMQWebSocketRelay:
    def __init__(self, zmq_endpoint="tcp://127.0.0.1:5555", websocket_port=6789):
        # ZMQ Setup
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.SUB)
        self.zmq_socket.connect(zmq_endpoint)
        self.zmq_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # WebSocket Clients
        self.clients = set()
        self.websocket_port = websocket_port

    async def zmq_listener(self):
        """Listen to ZMQ messages and broadcast to WebSocket clients."""
        poller = zmq.Poller()
        poller.register(self.zmq_socket, zmq.POLLIN)
        
        while True:
            try:
                # Non-blocking poll for messages
                socks = dict(poller.poll(100))  # 100ms timeout
                
                if self.zmq_socket in socks and socks[self.zmq_socket] == zmq.POLLIN:
                    # Message available, receive it
                    message = self.zmq_socket.recv_json(zmq.NOBLOCK)
                    logging.info(f"Received ZMQ message: {message}")
                    
                    # Broadcast to all WebSocket clients
                    if self.clients:
                        websocket_message = json.dumps(message)
                        await asyncio.gather(
                            *[client.send(websocket_message) for client in self.clients]
                        )
                
                # Yield control to allow other async operations
                await asyncio.sleep(0)
            
            except zmq.Again:
                # No message available, just continue
                await asyncio.sleep(0)
            except Exception as e:
                logging.error(f"Error in ZMQ listener: {e}")
                await asyncio.sleep(1)

    async def websocket_handler(self, websocket, path=None):
        """Handle individual WebSocket connections."""
        logging.info("New WebSocket client connected")
        
        try:
            print('try')
            self.clients.add(websocket)
            logging.info(f"New WebSocket client. Total: {len(self.clients)}")
            
            # Keep connection open
            await websocket.wait_closed()
        except Exception as e:
            print('error')
            logging.error(f"WebSocket error: {e}")
        finally:
            print('finally')
            self.clients.remove(websocket)
            logging.info(f"Client disconnected. Remaining: {len(self.clients)}")

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
        
        # Run WebSocket server and ZMQ listener concurrently
        # await asyncio.gather(
        #     self.zmq_listener(),
        #     server.wait_closed(),
        # )
        server_task = asyncio.create_task(server.wait_closed())
        message_task = asyncio.create_task(self.zmq_listener())
        
        await server_task
        await message_task


def main():
    relay = ZMQWebSocketRelay()
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()