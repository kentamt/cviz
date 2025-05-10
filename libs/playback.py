# playback.py
import argparse
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import zmq
from libs.publisher import Publisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)


class DataPlayback:
    """Plays back recorded data by publishing to ZMQ with original timing."""

    def __init__(self, recording_file, zmq_endpoint="tcp://127.0.0.1:5555", speed_factor=1.0):
        """Initialize the data playback system.

        Args:
            recording_file (str): Path to the recording JSON file.
            zmq_endpoint (str): ZMQ endpoint for publishers (usually the same as the recorder).
            speed_factor (float): Speed multiplier for playback (1.0 = real-time, 2.0 = double speed).
        """
        self.recording_file = Path(recording_file)
        self.zmq_endpoint = zmq_endpoint
        self.speed_factor = float(speed_factor)

        # Will be loaded from the recording
        self.recorded_data = None
        self.metadata = None
        self.messages = None

        # Publishers for each topic (created during playback)
        self.publishers = {}

        logging.info(f"Playback initialized with file: {self.recording_file}")
        logging.info(f"Speed factor: {self.speed_factor}x")

    def load_recording(self):
        """Load recording data from the JSON file."""
        try:
            with open(self.recording_file, 'r') as f:
                self.recorded_data = json.load(f)

            self.metadata = self.recorded_data.get("metadata", {})
            self.messages = self.recorded_data.get("messages", [])

            logging.info(f"Loaded recording from {self.recording_file}")
            logging.info(f"Recording metadata: {json.dumps(self.metadata, indent=2)}")
            logging.info(f"Total messages: {len(self.messages)}")

            # Validate the recording
            if not self.messages:
                raise ValueError("No messages found in the recording")

            return True

        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading recording: {e}")
            return False

    def get_topic_data_types(self):
        """Extract unique topic names and their data types from the recording."""
        topic_types = {}

        for message in self.messages:
            topic = message.get("topic")
            data = message.get("data", {})
            data_type = data.get("data_type")

            if topic and data_type and topic not in topic_types:
                topic_types[topic] = data_type

        return topic_types

    def create_publishers(self):
        """Create ZMQ publishers for each unique topic."""
        topic_types = self.get_topic_data_types()

        for topic, data_type in topic_types.items():
            self.publishers[topic] = Publisher(topic_name=topic, data_type=data_type)
            logging.info(f"Created publisher for topic: {topic} (data_type: {data_type})")

    async def play(self):
        """Play back the recorded data with original timing."""
        if not self.load_recording():
            return

        self.create_publishers()

        if not self.messages:
            logging.warning("No messages to play back")
            return

        # Sort messages by timestamp if needed
        self.messages.sort(key=lambda x: x.get("timestamp", 0))

        # Get the first message timestamp as reference
        first_timestamp = self.messages[0].get("timestamp", 0)
        start_time = time.time()

        logging.info(f"Starting playback with {len(self.messages)} messages...")

        message_count = 0
        skipped_count = 0

        for i, message in enumerate(self.messages):
            message_time = message.get("timestamp", 0)
            topic = message.get("topic")
            data = message.get("data", {})

            # Calculate delay based on original timing
            time_diff = message_time - first_timestamp
            target_delay = time_diff / self.speed_factor

            # Calculate how long we should wait
            elapsed = time.time() - start_time
            wait_time = max(0, target_delay - elapsed)

            # Wait until it's time to publish this message
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Publish the message if we have a publisher for this topic
            if topic in self.publishers:
                # Make a clean copy of the data to avoid modifying the original
                message_data = data.copy() if isinstance(data, dict) else data

                # Publish with original topic
                self.publishers[topic].publish(message_data)
                message_count += 1

                # Log progress periodically
                if message_count % 100 == 0 or i == len(self.messages) - 1:
                    progress = (i + 1) / len(self.messages) * 100
                    logging.info(f"Playback progress: {progress:.1f}% ({i + 1}/{len(self.messages)} messages)")
            else:
                skipped_count += 1

        total_duration = time.time() - start_time
        logging.info(f"Playback completed in {total_duration:.2f} seconds")
        logging.info(f"Published {message_count} messages, skipped {skipped_count} messages")

    def cleanup(self):
        """Clean up resources."""
        # Note: The Publisher class already handles cleanup in its __del__ method
        logging.info("Playback cleanup complete")


async def main():
    """Main function to run the playback tool."""
    parser = argparse.ArgumentParser(description='Cviz Data Playback')
    parser.add_argument('--file', type=str, required=True, help='Recording file to play back')
    parser.add_argument('--speed', type=float, default=1.0, help='Playback speed factor (1.0 = real-time)')
    parser.add_argument('--endpoint', type=str, default="tcp://127.0.0.1:5555", help='ZMQ endpoint')
    args = parser.parse_args()

    playback = DataPlayback(
        recording_file=args.file,
        zmq_endpoint=args.endpoint,
        speed_factor=args.speed
    )

    try:
        await playback.play()
    finally:
        playback.cleanup()


if __name__ == "__main__":
    asyncio.run(main())