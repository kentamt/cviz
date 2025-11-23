import os
import time
import logging
import asyncio
from collections import defaultdict
import json

from fastapi import WebSocket

from libs.subscriber import Subscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)


class CvizServerManager:
    """Manages WebSocket connections and ZMQ subscriptions for Cviz"""

    def __init__(self, zmq_endpoint=None):
        self.clients = set()
        self.sub_list = []
        self.last_time = {}
        self.running = False
        self.task = None
        self.zmq_endpoint = zmq_endpoint or os.environ.get("CVIZ_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")

        # Message cache to store the latest message for each topic
        # This ensures new clients can receive the current state immediately
        self.message_cache = {}

        # Store geometry history per topic (for topics that need history)
        self.geometry_history = defaultdict(list)
        self.history_limits = defaultdict(lambda: 1)  # Default to keep only the latest message

    def add_subscriber(self, topic_name, history_limit=1):
        """Add a new subscriber with optional history retention."""
        new_sub = Subscriber(topic_name=topic_name, zmq_endpoint=self.zmq_endpoint)
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
                        logging.debug(f"Received message for topic: {topic}")
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
