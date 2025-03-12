import time
import logging
import asyncio
import websockets
import json
import socket

from libs.subscriber import Subscriber

# Configure more detailed logging
logging.basicConfig(
    level=logging.INFO,  # Changed from INFO to DEBUG for more details
    format='%(asctime)s - %(levelname)s: %(message)s'
)

class CvizServer:
    """
    Relay ZMQ messages to WebSocket clients. 

    127.0.0.1:5555 -> ZMQ Publisher and Subscriber
    0.0.0.0:8765 -> WebSocket Server (changed to listen on all interfaces)
    """
        
    def __init__(self, zmq_endpoint="tcp://127.0.0.1:5555", websocket_port=8765):
        # subscriber setup
        self.sub_list = []

        # WebSocket Clients
        self.clients = set()
        self.websocket_port = websocket_port

        self.last_time = {}
        
        # Log server information
        self._log_server_info()
    
    def _log_server_info(self):
        """Log information about the server environment to help with debugging."""
        logging.info("=== CvizServer Initialization ===")
        logging.info(f"WebSocket port: {self.websocket_port}")
        
        # Log hostname and IP
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logging.info(f"Hostname: {hostname}")
            logging.info(f"Local IP: {local_ip}")
        except Exception as e:
            logging.error(f"Error getting host info: {e}")
        
        # Log network interfaces
        try:
            import netifaces
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    for addr in addresses[netifaces.AF_INET]:
                        logging.info(f"Interface {interface}: {addr['addr']}")
        except ImportError:
            logging.info("netifaces not installed, skipping network interface detection")
        
        logging.info("===============================")

    def add_subscriber(self, topic_name):
        """Add a new subscriber."""
        new_sub = Subscriber(topic_name=topic_name)
        self.sub_list.append(new_sub)
        logging.info(f"Added subscriber for topic: {topic_name}")

    async def websocket_handler(self, websocket, path=None):
        """Handle individual WebSocket connections."""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if hasattr(websocket, 'remote_address') else "Unknown"
        logging.info(f"New WebSocket client connected from {client_info}")
        
        try:
            self.clients.add(websocket)
            logging.info(f"New WebSocket client. Total: {len(self.clients)}")
            
            # Send initial confirmation message
            try:
                await websocket.send(json.dumps({
                    "type": "connection_established",
                    "message": "Successfully connected to CvizServer"
                }))
                logging.info(f"Sent welcome message to client {client_info}")
            except Exception as e:
                logging.error(f"Error sending welcome message: {e}")
        
            await websocket.wait_closed()  # Keep connection open
            
        except Exception as e:
            logging.error(f"WebSocket error for {client_info}: {e}")
            
        finally:
            self.clients.remove(websocket)
            logging.info(f"Client {client_info} disconnected. Remaining: {len(self.clients)}")
    
    
    async def send_message_to_clients(self):
        """Send a message to all WebSocket clients"""
        message_count = 0
        last_stats_time = time.time()
        
        while True:
            try:
                current_time = time.time()
                # Print stats every 10 seconds
                if current_time - last_stats_time > 10:
                    logging.info(f"WebSocket stats: {len(self.clients)} clients, {message_count} messages sent in last 10s")
                    message_count = 0
                    last_stats_time = current_time
                
                if self.clients:
                    for _sub in self.sub_list:
                        topic = _sub.topic
                        self.last_time[topic] = time.time()
                        message = _sub.get_message()
                        
                        if message is not None:
                            logging.debug(f"Topic: {topic}, sending to {len(self.clients)} clients")
                            websocket_message = json.dumps(message)
                            
                            # Send to all clients
                            for client in self.clients:
                                try:
                                    await client.send(websocket_message)
                                    message_count += 1
                                except websockets.exceptions.ConnectionClosed:
                                    logging.warning("Client connection already closed")
                                    # Will be removed in the next iteration or when wait_closed() completes
                                except Exception as e:
                                    logging.error(f"Error sending to client: {e}")

                # Short sleep to yield control
                await asyncio.sleep(0.01)
                    
            except Exception as e:
                logging.error(f"Error in send_message_to_clients: {e}")
                await asyncio.sleep(1)

    async def start_server(self):
        """Start WebSocket server and ZMQ listener."""
        
        try:
            server = await websockets.serve(
                self.websocket_handler, 
                "0.0.0.0",  # Changed from 127.0.0.1 to listen on all interfaces
                self.websocket_port,
                ping_interval=20,
                ping_timeout=20
            )
            
            logging.info(f"WebSocket server started on ws://0.0.0.0:{self.websocket_port}")
            
            # Run WebSocket server
            server_task = asyncio.create_task(server.wait_closed())
            
            # Subscribe to ZMQ messages from simulator
            subscribe_tasks = []
            for _sub in self.sub_list:
                subscribe_tasks.append(asyncio.create_task(_sub.subscribe()))
                logging.info(f"Started subscription task for topic: {_sub.topic}")
            
            # Send messages to JS clients
            message_task = asyncio.create_task(self.send_message_to_clients())
            logging.info("Started task to send messages to clients")

            # Wait for all tasks
            await server_task
            for subscribe_task in subscribe_tasks:
                await subscribe_task
            await message_task
            
        except Exception as e:
            logging.error(f"Error starting WebSocket server: {e}")
            raise

def main():
    try:
        # Add netifaces for better network debugging if available
        try:
            import pip
            pip.main(['install', 'netifaces'])
            logging.info("Installed netifaces for better network debugging")
        except Exception as e:
            logging.warning(f"Could not install netifaces: {e}")
        
        cviz = CvizServer()
        logging.info("Created CvizServer instance")
        
        cviz.add_subscriber(topic_name="polygon")
        cviz.add_subscriber(topic_name="point")
        cviz.add_subscriber(topic_name="linestring")
        
        logging.info("Starting WebSocket server...")
        asyncio.run(cviz.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped by KeyboardInterrupt")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}")

if __name__ == "__main__":
    main()