# topic_monitor.py
import os
import argparse
import asyncio
import json
import time
import zmq
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging

DEFAULT_ZMQ_ENDPOINT = os.environ.get("CVIZ_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")


class TopicMonitor:
    """A command-line tool to monitor topics published via ZMQ."""

    def __init__(self, zmq_endpoint=DEFAULT_ZMQ_ENDPOINT, verbose=False):
        self.zmq_endpoint = zmq_endpoint
        self.verbose = verbose
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.zmq_endpoint)

        # Data storage
        self.topic_stats = defaultdict(lambda: {
            'count': 0,
            'last_seen': None,
            'data_type': None,
            'size_bytes': 0
        })
        self.last_messages = {}

        # Control flags
        self.running = False
        self.show_all_topics = False
        self.filter_topics = []

        # Install signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        # Create poller for non-blocking message receiving
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n[INFO] Shutting down topic monitor...")
        self.running = False

    def setup_subscriptions(self, topics: Optional[List[str]] = None):
        """Set up ZMQ subscriptions."""
        if topics is None or len(topics) == 0:
            # Subscribe to all topics
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.show_all_topics = True
            print(f"[INFO] Subscribing to all topics on {self.zmq_endpoint}")
        else:
            # Subscribe to specific topics
            self.filter_topics = topics
            for topic in topics:
                self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
                print(f"[INFO] Subscribing to topic: {topic}")

    async def list_topics(self, duration=3):
        """List all available topics for a specified duration."""
        print(f"[INFO] Scanning for topics for {duration} seconds...")
        discovered_topics = set()

        start_time = time.time()
        while time.time() - start_time < duration:
            socks = dict(self.poller.poll(100))

            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                try:
                    topic_bytes, message_bytes = self.socket.recv_multipart(zmq.NOBLOCK)
                    topic = topic_bytes.decode('utf-8')
                    discovered_topics.add(topic)

                    # Try to parse the message to get data type
                    try:
                        data = json.loads(message_bytes.decode('utf-8'))
                        data_type = data.get('data_type', 'unknown')
                        self.topic_stats[topic]['data_type'] = data_type
                    except:
                        pass

                except zmq.Again:
                    pass

            await asyncio.sleep(0.01)

        # Display discovered topics
        print("\n[INFO] Discovered topics:")
        print("-" * 70)
        print(f"{'Topic Name':<30} {'Data Type':<20} {'Count'}")
        print("-" * 70)

        for topic in sorted(discovered_topics):
            stats = self.topic_stats[topic]
            print(f"{topic:<30} {stats.get('data_type', 'unknown'):<20} {stats['count']}")

        print(f"\nTotal: {len(discovered_topics)} topics")

    def format_message(self, topic: str, data: dict, timestamp: float) -> str:
        """Format a message for display."""
        if self.verbose:
            # Show full message
            return json.dumps(data, indent=2, sort_keys=True)
        else:
            # Show compact version
            summary = {}

            # Add key information
            if 'data_type' in data:
                summary['data_type'] = data['data_type']

            # For GeoJSON data, show geometry type and coordinates count
            if data.get('data_type') == 'GeoJSON':
                geojson = data.get('geojson', data)
                if geojson.get('type'):
                    summary['geojson_type'] = geojson['type']

                    # Count coordinates/features
                    if 'coordinates' in geojson:
                        if isinstance(geojson['coordinates'], list):
                            summary['coord_points'] = len(geojson['coordinates'])
                    elif 'features' in geojson:
                        summary['features'] = len(geojson['features'])

                # Show properties if available
                if 'properties' in geojson and geojson['properties']:
                    summary['properties'] = geojson['properties']

            # Show other relevant fields
            for key in ['id', 'type', 'color', 'velocity', 'count']:
                if key in data:
                    summary[key] = data[key]

            return json.dumps(summary, indent=1)

    def display_stats(self):
        """Display topic statistics."""
        print("\n" + "=" * 70)
        print("TOPIC STATISTICS")
        print("=" * 70)
        print(f"{'Topic':<30} {'Count':<10} {'Type':<15} {'Last Seen'}")
        print("-" * 70)

        for topic, stats in sorted(self.topic_stats.items()):
            last_seen = "Never"
            if stats['last_seen']:
                last_seen = datetime.fromtimestamp(stats['last_seen']).strftime("%H:%M:%S")

            print(f"{topic:<30} {stats['count']:<10} "
                  f"{stats.get('data_type', 'unknown'):<15} {last_seen}")

    async def monitor_topics(self, max_messages: Optional[int] = None):
        """Monitor topics in real-time."""
        self.running = True
        message_count = 0

        print(f"[INFO] Starting topic monitor...")
        print(f"[INFO] Use Ctrl+C to stop monitoring\n")

        if self.filter_topics:
            print(f"[INFO] Monitoring topics: {', '.join(self.filter_topics)}\n")
        else:
            print("[INFO] Monitoring all topics\n")

        try:
            while self.running and (max_messages is None or message_count < max_messages):
                socks = dict(self.poller.poll(100))

                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    try:
                        topic_bytes, message_bytes = self.socket.recv_multipart(zmq.NOBLOCK)
                        topic = topic_bytes.decode('utf-8')
                        timestamp = time.time()

                        # Parse message
                        try:
                            data = json.loads(message_bytes.decode('utf-8'))
                        except json.JSONDecodeError:
                            data = {'raw': message_bytes.decode('utf-8', errors='replace')}

                        # Update statistics
                        self.topic_stats[topic]['count'] += 1
                        self.topic_stats[topic]['last_seen'] = timestamp
                        self.topic_stats[topic]['size_bytes'] += len(message_bytes)

                        if 'data_type' in data:
                            self.topic_stats[topic]['data_type'] = data['data_type']

                        # Store last message
                        self.last_messages[topic] = data

                        # Display message
                        dt_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
                        print(f"\n--- {topic} [{dt_str}] ---")
                        print(self.format_message(topic, data, timestamp))
                        print("-" * 50)

                        message_count += 1

                    except zmq.Again:
                        pass

                await asyncio.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            self.display_stats()

    def cleanup(self):
        """Clean up resources."""
        try:
            self.socket.close()
            self.context.term()
            print("[INFO] Cleanup completed")
        except Exception as e:
            print(f"[WARNING] Error during cleanup: {e}")


async def main():
    parser = argparse.ArgumentParser(description='Topic Monitor - Similar to rostopic echo')
    parser.add_argument('command', nargs='?', choices=['echo', 'list'], default='echo',
                        help='Command to run (echo or list)')
    parser.add_argument('topics', nargs='*', help='Topics to monitor (if not specified, monitors all)')
    parser.add_argument('--endpoint', '-e', type=str, default=DEFAULT_ZMQ_ENDPOINT,
                        help='ZMQ endpoint to connect to')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show full message content')
    parser.add_argument('--max-messages', '-m', type=int,
                        help='Maximum number of messages to display before stopping')
    parser.add_argument('--duration', '-d', type=int, default=3,
                        help='Duration to scan for topics (list command only)')

    args = parser.parse_args()

    # Create monitor instance
    monitor = TopicMonitor(
        zmq_endpoint=args.endpoint,
        verbose=args.verbose
    )

    try:
        if args.command == 'list':
            # Setup subscription to all topics
            monitor.setup_subscriptions()
            await monitor.list_topics(duration=args.duration)
        else:  # echo
            # Setup subscriptions
            monitor.setup_subscriptions(topics=args.topics if args.topics else None)
            await monitor.monitor_topics(max_messages=args.max_messages)
    finally:
        monitor.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
