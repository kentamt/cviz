# recorder.py
import argparse
import json
import logging
import os
import time
import zmq
import asyncio
import signal
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)


class DataRecorder:
    """Records data from ZMQ publishers to a file."""

    def __init__(self, topics=None, zmq_endpoint="tcp://127.0.0.1:5555", output_dir="recordings"):
        """Initialize the DataRecorder.

        Args:
            topics (list): List of topics to subscribe to. If None, subscribes to all topics.
            zmq_endpoint (str): ZMQ endpoint to connect to.
            output_dir (str): Directory to save recordings.
        """
        self.topics = topics if topics else []
        self.zmq_endpoint = zmq_endpoint
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.zmq_endpoint)

        # Data storage for recording
        self.recorded_data = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "topics": self.topics.copy() if self.topics else ["all"],
                "zmq_endpoint": zmq_endpoint
            },
            "messages": []
        }

        # Flag to control recording
        self.is_recording = False
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        self.setup_subscriptions()
        logging.info(f"DataRecorder initialized. Will record topics: {self.topics if self.topics else 'all'}")

    def setup_subscriptions(self):
        """Set up ZMQ subscriptions based on topics."""
        if not self.topics:
            # Subscribe to all topics
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logging.info("Subscribing to all topics")
        else:
            # Subscribe to specific topics
            for topic in self.topics:
                self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
                logging.info(f"Subscribing to topic: {topic}")

    def generate_filename(self):
        """Generate a filename for the recording."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topics_str = "_".join(self.topics) if self.topics else "all_topics"
        if len(topics_str) > 100:  # Limit filename length
            topics_str = topics_str[:97] + "..."
        return f"cviz_recording_{timestamp}_{topics_str}.json"

    async def record(self):
        """Start recording data from ZMQ publishers."""
        self.is_recording = True
        start_time = time.time()
        message_count = 0

        logging.info(f"Starting recording. Output will be saved to {self.output_dir}")

        try:
            while self.is_recording:
                # Poll for messages with a timeout
                socks = dict(self.poller.poll(100))  # 100ms timeout

                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    # Receive a multipart message: [topic, message]
                    topic, message = self.socket.recv_multipart()
                    topic_str = topic.decode('utf-8')
                    data = json.loads(message.decode('utf-8'))

                    # Add timestamp and store the message
                    message_entry = {
                        "timestamp": time.time(),
                        "topic": topic_str,
                        "data": data
                    }
                    self.recorded_data["messages"].append(message_entry)

                    message_count += 1
                    if message_count % 100 == 0:
                        logging.info(
                            f"Recorded {message_count} messages ({len(self.topics) if self.topics else 'all'} topics)")

                # Yield control to allow other async operations
                await asyncio.sleep(0.001)

        except Exception as e:
            logging.error(f"Error during recording: {e}")
        finally:
            # Add recording metadata
            duration = time.time() - start_time
            self.recorded_data["metadata"]["end_time"] = datetime.now().isoformat()
            self.recorded_data["metadata"]["duration_seconds"] = duration
            self.recorded_data["metadata"]["message_count"] = message_count

            # Save the recording
            self.save_recording()
            logging.info(f"Recording stopped after {duration:.2f} seconds. Recorded {message_count} messages.")

    def save_recording(self):
        """Save the recorded data to a file."""
        filename = self.generate_filename()
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w') as f:
                json.dump(self.recorded_data, f, indent=2)
            logging.info(f"Recording saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving recording: {e}")
            # Try to save to a backup location
            backup_path = Path(f"cviz_recording_backup_{int(time.time())}.json")
            try:
                with open(backup_path, 'w') as f:
                    json.dump(self.recorded_data, f, indent=2)
                logging.info(f"Backup recording saved to {backup_path}")
            except Exception as backup_e:
                logging.error(f"Error saving backup recording: {backup_e}")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}. Stopping recording...")
        self.is_recording = False

    def cleanup(self):
        """Clean up resources."""
        try:
            self.socket.close()
            self.context.term()
            logging.info("ZMQ resources cleaned up")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


async def main():
    """Main function to run the recorder."""
    parser = argparse.ArgumentParser(description='Cviz Data Recorder')
    parser.add_argument('--topics', type=str, help='Comma-separated list of topics to record')
    parser.add_argument('--endpoint', type=str, default="tcp://127.0.0.1:5555", help='ZMQ endpoint to connect to')
    parser.add_argument('--output-dir', type=str, default="recordings", help='Directory to save recordings')
    args = parser.parse_args()

    # Parse topics if provided
    topics = None
    if args.topics:
        topics = [topic.strip() for topic in args.topics.split(',')]

    # Create and start the recorder
    recorder = DataRecorder(
        topics=topics,
        zmq_endpoint=args.endpoint,
        output_dir=args.output_dir
    )

    try:
        await recorder.record()
    finally:
        recorder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())