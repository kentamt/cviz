# topic_list.py - List all available topics
import argparse
import asyncio
import json
import time
import zmq
from collections import defaultdict
from datetime import datetime


class TopicLister:
    """List available topics with their information."""

    def __init__(self, zmq_endpoint="tcp://127.0.0.1:5555"):
        self.zmq_endpoint = zmq_endpoint
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.zmq_endpoint)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics

        self.topic_info = defaultdict(lambda: {
            'count': 0,
            'data_type': None,
            'last_seen': None,
            'avg_size': 0,
            'total_size': 0
        })

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    async def scan_topics(self, duration=5, show_progress=True):
        """Scan for topics for the specified duration."""
        print(f"[INFO] Scanning for topics for {duration} seconds...")

        start_time = time.time()
        last_progress = 0

        while time.time() - start_time < duration:
            socks = dict(self.poller.poll(100))

            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                try:
                    topic_bytes, message_bytes = self.socket.recv_multipart(zmq.NOBLOCK)
                    topic = topic_bytes.decode('utf-8')

                    # Update statistics
                    info = self.topic_info[topic]
                    info['count'] += 1
                    info['last_seen'] = time.time()
                    info['total_size'] += len(message_bytes)
                    info['avg_size'] = info['total_size'] / info['count']

                    # Try to extract data type
                    try:
                        data = json.loads(message_bytes.decode('utf-8'))
                        if 'data_type' in data:
                            info['data_type'] = data['data_type']
                    except:
                        pass

                except zmq.Again:
                    pass

            # Show progress
            if show_progress:
                elapsed = time.time() - start_time
                progress = int((elapsed / duration) * 100)
                if progress > last_progress:
                    print(f"\rProgress: {progress}% ({len(self.topic_info)} topics found)", end='', flush=True)
                    last_progress = progress

            await asyncio.sleep(0.01)

        if show_progress:
            print()  # New line after progress

    def display_topics(self, sort_by='name', filter_type=None):
        """Display discovered topics."""
        print("\n" + "=" * 80)
        print("DISCOVERED TOPICS")
        print("=" * 80)

        # Filter by type if requested
        topics_to_show = self.topic_info.items()
        if filter_type:
            topics_to_show = [(topic, info) for topic, info in topics_to_show
                              if info.get('data_type') == filter_type]

        # Sort topics
        if sort_by == 'name':
            topics_to_show = sorted(topics_to_show, key=lambda x: x[0])
        elif sort_by == 'count':
            topics_to_show = sorted(topics_to_show, key=lambda x: x[1]['count'], reverse=True)
        elif sort_by == 'type':
            topics_to_show = sorted(topics_to_show, key=lambda x: x[1].get('data_type', 'unknown'))

        # Display header
        print(f"{'Topic Name':<25} {'Type':<15} {'Count':<8} {'Avg Size':<10} {'Rate (Hz)':<10} {'Last Seen'}")
        print("-" * 80)

        current_time = time.time()
        for topic, info in topics_to_show:
            # Calculate rate
            if info['last_seen']:
                rate = info['count'] / max(1, info['last_seen'] - (current_time - 5))
                last_seen = datetime.fromtimestamp(info['last_seen']).strftime("%H:%M:%S")
            else:
                rate = 0
                last_seen = "Never"

            print(f"{topic:<25} {info.get('data_type', 'unknown'):<15} "
                  f"{info['count']:<8} {info['avg_size']:<10.1f} "
                  f"{rate:<10.1f} {last_seen}")

        print(f"\nTotal: {len(topics_to_show)} topics")

        # Show unique data types
        data_types = set(info.get('data_type') for _, info in self.topic_info.items() if info.get('data_type'))
        if data_types:
            print(f"Data Types: {', '.join(sorted(data_types))}")

    def cleanup(self):
        """Clean up resources."""
        try:
            self.socket.close()
            self.context.term()
        except Exception as e:
            print(f"[WARNING] Error during cleanup: {e}")


async def main():
    parser = argparse.ArgumentParser(description='List available topics')
    parser.add_argument('--endpoint', '-e', type=str, default="tcp://127.0.0.1:5555",
                        help='ZMQ endpoint to connect to')
    parser.add_argument('--duration', '-d', type=int, default=5,
                        help='Duration to scan for topics (seconds)')
    parser.add_argument('--sort', '-s', choices=['name', 'count', 'type'], default='name',
                        help='Sort topics by name, count, or type')
    parser.add_argument('--filter-type', '-t', type=str,
                        help='Show only topics of specific data type')
    parser.add_argument('--no-progress', action='store_true',
                        help='Don\'t show progress during scanning')

    args = parser.parse_args()

    lister = TopicLister(zmq_endpoint=args.endpoint)

    try:
        await lister.scan_topics(duration=args.duration, show_progress=not args.no_progress)
        lister.display_topics(sort_by=args.sort, filter_type=args.filter_type)
    finally:
        lister.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")