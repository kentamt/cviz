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
        self.client_topics = {}
        self.topic_clients = defaultdict(set)
        self.subscribers = {}
        self.subscriber_tasks = {}
        self.static_topics = set()
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

    def add_subscriber(self, topic_name, history_limit=1, permanent=False):
        """Add a new subscriber with optional history retention."""
        if topic_name in self.subscribers:
            self.history_limits[topic_name] = history_limit
            if permanent:
                self.static_topics.add(topic_name)
            return self.subscribers[topic_name]

        new_sub = Subscriber(topic_name=topic_name, zmq_endpoint=self.zmq_endpoint)
        self.subscribers[topic_name] = new_sub
        self.history_limits[topic_name] = history_limit
        if permanent:
            self.static_topics.add(topic_name)

        # If the server is already running, start this subscriber immediately.
        if self.running and topic_name not in self.subscriber_tasks:
            self.subscriber_tasks[topic_name] = asyncio.create_task(new_sub.subscribe())

        return new_sub

    async def ensure_subscriber_running(self, topic_name, history_limit=1):
        """Ensure a topic subscriber exists and its task is running."""
        subscriber = self.subscribers.get(topic_name)
        if subscriber is None:
            subscriber = self.add_subscriber(topic_name, history_limit=history_limit)

        if topic_name not in self.subscriber_tasks or self.subscriber_tasks[topic_name].done():
            self.subscriber_tasks[topic_name] = asyncio.create_task(subscriber.subscribe())

        return subscriber

    async def register_client(self, websocket: WebSocket):
        """Register a new WebSocket client and send cached data"""
        await websocket.accept()
        self.clients.add(websocket)
        self.client_topics[websocket] = set()
        logging.info(f"New WebSocket client connected. Total: {len(self.clients)}")

    async def send_cached_messages_for_topic(self, websocket: WebSocket, topic: str):
        """Send cached messages for a specific topic to a client."""
        try:
            if topic in self.message_cache:
                logging.info(f"Sending cached message for topic: {topic}")
                await websocket.send_text(json.dumps(self.message_cache[topic]))

            if topic in self.geometry_history:
                for message in self.geometry_history[topic]:
                    await websocket.send_text(json.dumps(message))
        except Exception as e:
            logging.error(f"Error sending cached messages for topic {topic}: {e}")

    async def subscribe_client_to_topics(self, websocket: WebSocket, topics, history_limit=1):
        """Subscribe a client to the provided topics."""
        if websocket not in self.clients:
            return

        client_topic_set = self.client_topics.setdefault(websocket, set())

        for topic in topics:
            if not topic:
                continue

            await self.ensure_subscriber_running(topic, history_limit=history_limit)

            if topic not in client_topic_set:
                client_topic_set.add(topic)
                self.topic_clients[topic].add(websocket)
                await self.send_cached_messages_for_topic(websocket, topic)

    async def unsubscribe_client_from_topics(self, websocket: WebSocket, topics):
        """Unsubscribe a client from the provided topics."""
        client_topic_set = self.client_topics.get(websocket)
        if not client_topic_set:
            return

        for topic in topics:
            if topic not in client_topic_set:
                continue

            client_topic_set.remove(topic)
            if topic in self.topic_clients:
                self.topic_clients[topic].discard(websocket)
            await self._cleanup_topic_if_unused(topic)

    async def _cleanup_topic_if_unused(self, topic: str):
        """Stop tracking a topic if no clients are listening and it's not permanent."""
        if topic in self.static_topics:
            return

        if self.topic_clients[topic]:
            return

        logging.info(f"No clients subscribed to topic {topic}. Stopping subscriber.")
        task = self.subscriber_tasks.pop(topic, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.subscribers.pop(topic, None)
        self.history_limits.pop(topic, None)
        self.geometry_history.pop(topic, None)
        self.message_cache.pop(topic, None)
        self.topic_clients.pop(topic, None)

    async def handle_client_message(self, websocket: WebSocket, message_text: str):
        """Process subscription commands sent by a client."""
        try:
            payload = json.loads(message_text)
        except json.JSONDecodeError:
            logging.warning("Received invalid JSON from client")
            return

        action = payload.get("action")
        topics = payload.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]
        if not isinstance(topics, list):
            logging.warning("Topics must be a list or string in client requests")
            return

        history_limit = payload.get("history_limit", 1)

        if action == "subscribe":
            await self.subscribe_client_to_topics(websocket, topics, history_limit=history_limit)
        elif action == "unsubscribe":
            await self.unsubscribe_client_from_topics(websocket, topics)
        elif action == "set_topics":
            # Replace client's subscriptions with the provided list
            existing = list(self.client_topics.get(websocket, set()))
            await self.unsubscribe_client_from_topics(websocket, existing)
            await self.subscribe_client_to_topics(websocket, topics, history_limit=history_limit)
        else:
            logging.warning(f"Unknown client action: {action}")

    def get_active_topics(self):
        """Return topics that have delivered at least one message."""
        return set(self.message_cache.keys())

    async def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        if websocket in self.clients:
            topics = list(self.client_topics.get(websocket, set()))
            if topics:
                await self.unsubscribe_client_from_topics(websocket, topics)
            self.client_topics.pop(websocket, None)
            self.clients.remove(websocket)
            logging.info(f"Client disconnected. Remaining: {len(self.clients)}")
        else:
            logging.warning(f"Attempted to remove a client that wasn't registered")

    async def broadcast_messages(self):
        """Send messages from subscribers to all connected WebSocket clients"""
        self.running = True

        try:
            while self.running:
                for topic, subscriber in self.subscribers.items():
                    self.last_time[topic] = time.time()
                    message = subscriber.get_message()

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

                        interested_clients = self.topic_clients.get(topic, set())

                        if interested_clients:
                            logging.info(f"Broadcasting topic: {topic} to {len(interested_clients)} clients")

                            disconnected_clients = set()
                            for client in interested_clients.copy():
                                try:
                                    await client.send_text(websocket_message)
                                except Exception as e:
                                    logging.error(f"Error sending to client: {e}")
                                    disconnected_clients.add(client)

                            # Remove any disconnected clients
                            for client in disconnected_clients:
                                await self.remove_client(client)
                        else:
                            logging.debug(f"No clients subscribed to topic: {topic}. Caching message.")

                # Yield control to allow other async operations
                await asyncio.sleep(0.01)

        except Exception as e:
            logging.error(f"Error in broadcast task: {e}")
        finally:
            self.running = False

    async def start(self):
        """Start the subscription and broadcasting tasks"""
        self.running = True

        # Start subscriber tasks for any configured topics
        subscriber_tasks = []
        for topic, subscriber in self.subscribers.items():
            if topic not in self.subscriber_tasks or self.subscriber_tasks[topic].done():
                self.subscriber_tasks[topic] = asyncio.create_task(subscriber.subscribe())
            subscriber_tasks.append(self.subscriber_tasks[topic])

        # Start broadcast task
        self.task = asyncio.create_task(self.broadcast_messages())

        return subscriber_tasks, self.task

    async def stop(self):
        """Stop all running tasks"""
        self.running = False

        # Cancel subscriber tasks
        for task in list(self.subscriber_tasks.values()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.subscriber_tasks.clear()

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
