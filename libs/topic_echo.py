# topic_echo.py - A more focused tool similar to rostopic echo
import os
import argparse
import asyncio
import json
import time
import zmq
import signal
from datetime import datetime
from typing import Dict, Optional
import sys

DEFAULT_ZMQ_ENDPOINT = os.environ.get("CVIZ_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")


class TopicEcho:
    """Echo messages from a specific topic, similar to rostopic echo."""

    def __init__(self, topic: str, zmq_endpoint=DEFAULT_ZMQ_ENDPOINT):
        self.topic = topic
        self.zmq_endpoint = zmq_endpoint
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.zmq_endpoint)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)

        # Statistics
        self.message_count = 0
        self.start_time = time.time()
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        # Poller for non-blocking operations
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        self.running = False

    def format_yaml_like(self, data: Dict, indent: int = 0) -> str:
        """Format data in a YAML-like format similar to ROS."""
        result = []
        indent_str = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    result.append(f"{indent_str}{key}:")
                    result.append(self.format_yaml_like(value, indent + 1))
                else:
                    result.append(f"{indent_str}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                result.append(f"{indent_str}- ")
                if isinstance(item, (dict, list)):
                    result.append(self.format_yaml_like(item, indent + 1))
                else:
                    result.append(f"  {item}")
        else:
            result.append(f"{indent_str}{data}")

        return "\n".join(result)

    async def echo(self, output_format="yaml", filter_field=None):
        """Echo messages from the topic."""
        self.running = True

        print(f"[INFO] Echoing topic: {self.topic}")
        print(f"[INFO] ZMQ endpoint: {self.zmq_endpoint}")
        if filter_field:
            print(f"[INFO] Filtering field: {filter_field}")
        print("[INFO] Use Ctrl+C to stop\n")

        try:
            while self.running:
                socks = dict(self.poller.poll(100))

                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    try:
                        topic_bytes, message_bytes = self.socket.recv_multipart(zmq.NOBLOCK)
                        topic = topic_bytes.decode('utf-8')

                        # Parse the message
                        try:
                            data = json.loads(message_bytes.decode('utf-8'))
                        except json.JSONDecodeError:
                            print(f"[WARNING] Could not decode message as JSON")
                            continue

                        # Filter if requested
                        if filter_field and filter_field in data:
                            data = {filter_field: data[filter_field]}

                        # Display message
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        print(f"--- Topic: {topic} [{timestamp}] ---")

                        if output_format == "yaml":
                            print(self.format_yaml_like(data))
                        else:  # json
                            print(json.dumps(data, indent=2))

                        print("---")
                        self.message_count += 1

                    except zmq.Again:
                        pass

                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            duration = time.time() - self.start_time
            print(f"\n[INFO] Received {self.message_count} messages in {duration:.2f} seconds")
            print(f"[INFO] Average rate: {self.message_count / duration:.2f} Hz")

    def cleanup(self):
        """Clean up resources."""
        try:
            self.socket.close()
            self.context.term()
        except Exception as e:
            print(f"[WARNING] Error during cleanup: {e}")


async def main():
    parser = argparse.ArgumentParser(description='Echo messages from a topic (similar to rostopic echo)')
    parser.add_argument('topic', type=str, help='Topic name to echo')
    parser.add_argument('--endpoint', '-e', type=str, default=DEFAULT_ZMQ_ENDPOINT,
                        help='ZMQ endpoint to connect to')
    parser.add_argument('--format', '-f', choices=['yaml', 'json'], default='yaml',
                        help='Output format')
    parser.add_argument('--field', type=str, help='Show only specific field from messages')

    args = parser.parse_args()

    echo_tool = TopicEcho(topic=args.topic, zmq_endpoint=args.endpoint)

    try:
        await echo_tool.echo(output_format=args.format, filter_field=args.field)
    finally:
        echo_tool.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
