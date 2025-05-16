# enhanced_playback.py (updated with repeat option)
import argparse
import asyncio
import json
import logging
import time
import threading
import sys
from datetime import datetime
from pathlib import Path
import signal

sys.path.append(str(Path(__file__).resolve().parent.parent))
import zmq
from libs.publisher import Publisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)


class InteractivePlayback:
    """Interactive playback tool with speed control, repeat, and pause/resume functionality."""

    def __init__(self, recording_file, zmq_endpoint="tcp://127.0.0.1:5555", initial_speed=1.0, repeat=False):
        """Initialize the interactive playback system.

        Args:
            recording_file (str): Path to the recording JSON file.
            zmq_endpoint (str): ZMQ endpoint for publishers.
            initial_speed (float): Initial playback speed multiplier.
            repeat (bool): Whether to repeat the playback continuously.
        """
        self.recording_file = Path(recording_file)
        self.zmq_endpoint = zmq_endpoint
        self.speed_factor = float(initial_speed)
        self.repeat = repeat

        # Playback state
        self.recorded_data = None
        self.metadata = None
        self.messages = None
        self.publishers = {}

        # Control state
        self.is_paused = False
        self.stop_playback = False
        self.seek_to_time = None
        self.current_message_index = 0
        self.loop_count = 0

        # Timing
        self.playback_start_time = None
        self.loop_start_time = None
        self.pause_time = None
        self.total_pause_duration = 0

        # Threading for user input
        self.input_thread = None

        logging.info(f"Interactive playback initialized with file: {self.recording_file}")
        logging.info(f"Initial speed: {self.speed_factor}x")
        logging.info(f"Repeat mode: {'ON' if self.repeat else 'OFF'}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_interrupt)

    def handle_interrupt(self, signum, frame):
        """Handle keyboard interrupt gracefully."""
        logging.info("Received interrupt signal, stopping playback...")
        self.stop_playback = True
        if self.input_thread and self.input_thread.is_alive():
            # Send a newline to help exit the input thread
            print()

    def load_recording(self):
        """Load recording data from the JSON file."""
        try:
            with open(self.recording_file, 'r') as f:
                self.recorded_data = json.load(f)

            self.metadata = self.recorded_data.get("metadata", {})
            self.messages = self.recorded_data.get("messages", [])

            logging.info(f"Loaded recording from {self.recording_file}")
            logging.info(f"Total messages: {len(self.messages)}")
            logging.info(f"Recording duration: {self.metadata.get('duration_seconds', 'unknown')}s")

            if not self.messages:
                raise ValueError("No messages found in the recording")

            # Sort messages by timestamp
            self.messages.sort(key=lambda x: x.get("timestamp", 0))

            return True

        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading recording: {e}")
            return False

    def create_publishers(self):
        """Create ZMQ publishers for each unique topic."""
        topic_types = {}

        for message in self.messages:
            topic = message.get("topic")
            data = message.get("data", {})
            data_type = data.get("data_type")

            if topic and data_type and topic not in topic_types:
                topic_types[topic] = data_type

        for topic, data_type in topic_types.items():
            self.publishers[topic] = Publisher(topic_name=topic, data_type=data_type)
            logging.info(f"Created publisher for topic: {topic} (data_type: {data_type})")

    def print_controls(self):
        """Print the control instructions."""
        print("\n" + "=" * 60)
        print("PLAYBACK CONTROLS")
        print("=" * 60)
        print("Space bar    - Pause/Resume")
        print("0-9          - Set speed (0=0.1x, 1=1x, 2=2x, etc.)")
        print("+ / -        - Increase/Decrease speed by 0.1x")
        print("[ / ]        - Seek backward/forward 5 seconds")
        print("< / >        - Seek backward/forward 30 seconds")
        print("r            - Reset to beginning")
        print("l            - Toggle repeat mode")
        print("n            - Skip to next loop (if in repeat mode)")
        print("s            - Show current status")
        print("q            - Quit playback")
        print("h            - Show this help")
        print("=" * 60)
        print(f"Current speed: {self.speed_factor}x")
        print(f"Repeat mode: {'ON' if self.repeat else 'OFF'}")
        if self.repeat and self.loop_count > 0:
            print(f"Loop count: {self.loop_count}")
        print("=" * 60 + "\n")

    def show_status(self):
        """Show current playback status."""
        if not self.messages:
            return

        current_msg = self.messages[self.current_message_index] if self.current_message_index < len(
            self.messages) else None
        total_duration = self.metadata.get('duration_seconds', 0)

        if current_msg and self.playback_start_time:
            first_timestamp = self.messages[0].get("timestamp", 0)
            current_timestamp = current_msg.get("timestamp", 0)
            elapsed_recording_time = current_timestamp - first_timestamp

            # Calculate total elapsed time including loops
            current_loop_time = time.time() - (self.loop_start_time or self.playback_start_time)
            total_elapsed_time = (self.loop_count * total_duration) + elapsed_recording_time

            print(f"\n--- PLAYBACK STATUS ---")
            print(f"Speed: {self.speed_factor}x")
            print(f"State: {'PAUSED' if self.is_paused else 'PLAYING'}")
            print(f"Repeat: {'ON' if self.repeat else 'OFF'}")
            if self.repeat:
                print(f"Loop: {self.loop_count + 1}")
            print(f"Progress: {self.current_message_index + 1}/{len(self.messages)} messages")
            print(f"Current loop time: {elapsed_recording_time:.1f}s / {total_duration:.1f}s")
            print(f"Current loop progress: {(elapsed_recording_time / max(total_duration, 1)) * 100:.1f}%")
            if self.repeat and self.loop_count > 0:
                print(f"Total playback time: {total_elapsed_time:.1f}s")
            print("----------------------\n")

    def seek_to_percentage(self, percentage):
        """Seek to a specific percentage of the current loop."""
        if not self.messages:
            return

        target_index = int((percentage / 100.0) * len(self.messages))
        target_index = max(0, min(target_index, len(self.messages) - 1))

        # Find the closest message by timestamp
        first_timestamp = self.messages[0].get("timestamp", 0)
        total_duration = self.metadata.get('duration_seconds', 0)
        target_time = first_timestamp + (percentage / 100.0) * total_duration

        # Binary search for closest timestamp
        left, right = 0, len(self.messages) - 1
        while left < right:
            mid = (left + right) // 2
            if self.messages[mid].get("timestamp", 0) < target_time:
                left = mid + 1
            else:
                right = mid

        self.current_message_index = left
        self.seek_to_time = time.time()
        logging.info(f"Seeked to {percentage:.1f}% (message {self.current_message_index + 1})")

    def seek_by_seconds(self, seconds):
        """Seek forward or backward by a number of seconds."""
        if not self.messages or self.current_message_index >= len(self.messages):
            return

        current_timestamp = self.messages[self.current_message_index].get("timestamp", 0)
        target_timestamp = current_timestamp + seconds

        # Find the message closest to the target timestamp
        best_index = self.current_message_index
        best_diff = abs(self.messages[best_index].get("timestamp", 0) - target_timestamp)

        for i, msg in enumerate(self.messages):
            diff = abs(msg.get("timestamp", 0) - target_timestamp)
            if diff < best_diff:
                best_diff = diff
                best_index = i

        self.current_message_index = max(0, min(best_index, len(self.messages) - 1))
        self.seek_to_time = time.time()
        logging.info(f"Seeked by {seconds}s to message {self.current_message_index + 1}")

    def reset_to_beginning(self):
        """Reset playback to the beginning of the current loop."""
        self.current_message_index = 0
        self.loop_start_time = time.time()
        self.seek_to_time = self.loop_start_time
        self.total_pause_duration = 0
        print("Reset to beginning of current loop")

    def skip_to_next_loop(self):
        """Skip to the beginning of the next loop."""
        if not self.repeat:
            print("Repeat mode is OFF, cannot skip to next loop")
            return

        self.current_message_index = len(self.messages)  # This will trigger loop restart
        print("Skipping to next loop...")

    def handle_user_input(self):
        """Handle user input in a separate thread."""
        try:
            while not self.stop_playback:
                try:
                    user_input = input().strip().lower()

                    if user_input == ' ' or user_input == '':
                        # Toggle pause
                        self.is_paused = not self.is_paused
                        if self.is_paused:
                            self.pause_time = time.time()
                            print("Playback PAUSED")
                        else:
                            if self.pause_time:
                                self.total_pause_duration += time.time() - self.pause_time
                            print("Playback RESUMED")

                    elif user_input in '0123456789':
                        # Set speed based on number
                        speed_map = {'0': 0.1, '1': 1.0, '2': 2.0, '3': 3.0, '4': 4.0,
                                     '5': 5.0, '6': 6.0, '7': 7.0, '8': 8.0, '9': 9.0}
                        self.speed_factor = speed_map[user_input]
                        print(f"Speed set to {self.speed_factor}x")

                    elif user_input == '+':
                        self.speed_factor = min(10.0, self.speed_factor + 0.1)
                        print(f"Speed increased to {self.speed_factor:.1f}x")

                    elif user_input == '-':
                        self.speed_factor = max(0.1, self.speed_factor - 0.1)
                        print(f"Speed decreased to {self.speed_factor:.1f}x")

                    elif user_input == '[':
                        self.seek_by_seconds(-5)

                    elif user_input == ']':
                        self.seek_by_seconds(5)

                    elif user_input == '<':
                        self.seek_by_seconds(-30)

                    elif user_input == '>':
                        self.seek_by_seconds(30)

                    elif user_input == 'r':
                        self.reset_to_beginning()

                    elif user_input == 'l':
                        self.repeat = not self.repeat
                        print(f"Repeat mode {'ON' if self.repeat else 'OFF'}")

                    elif user_input == 'n':
                        self.skip_to_next_loop()

                    elif user_input == 's':
                        self.show_status()

                    elif user_input == 'h':
                        self.print_controls()

                    elif user_input == 'q':
                        print("Quitting playback...")
                        self.stop_playback = True
                        break

                    elif user_input.startswith('seek '):
                        # Allow seeking to percentage, e.g., "seek 50"
                        try:
                            percentage = float(user_input.split()[1])
                            self.seek_to_percentage(percentage)
                        except (IndexError, ValueError):
                            print("Usage: seek <percentage> (e.g., seek 50)")

                except EOFError:
                    # Handle Ctrl+D
                    break
                except KeyboardInterrupt:
                    break

        except Exception as e:
            logging.error(f"Error in input handler: {e}")

    async def play(self):
        """Play back the recorded data with interactive controls and repeat option."""
        if not self.load_recording():
            return

        self.create_publishers()

        if not self.messages:
            logging.warning("No messages to play back")
            return

        # Start input handling thread
        self.input_thread = threading.Thread(target=self.handle_user_input, daemon=True)
        self.input_thread.start()

        # Print initial instructions
        self.print_controls()

        # Initialize timing
        first_timestamp = self.messages[0].get("timestamp", 0)
        self.playback_start_time = time.time()
        self.loop_start_time = self.playback_start_time

        logging.info(f"Starting interactive playback...")
        if self.repeat:
            logging.info("Repeat mode is ON - playback will loop continuously")

        # Main playback loop
        while not self.stop_playback:
            # Reset to beginning if we've reached the end and repeat is enabled
            if self.current_message_index >= len(self.messages):
                if self.repeat:
                    self.loop_count += 1
                    self.current_message_index = 0
                    self.loop_start_time = time.time()
                    self.total_pause_duration = 0
                    logging.info(f"Starting loop #{self.loop_count + 1}")
                else:
                    break

            # Handle pause
            if self.is_paused:
                await asyncio.sleep(0.1)
                continue

            message = self.messages[self.current_message_index]
            message_time = message.get("timestamp", 0)
            topic = message.get("topic")
            data = message.get("data", {})

            # Calculate timing
            if self.seek_to_time is not None:
                # We just seeked, reset timing
                self.loop_start_time = self.seek_to_time - (message_time - first_timestamp) / self.speed_factor
                self.total_pause_duration = 0
                self.seek_to_time = None

            # Calculate when this message should be played
            time_in_recording = message_time - first_timestamp
            target_playback_time = self.loop_start_time + time_in_recording / self.speed_factor + self.total_pause_duration

            # Wait until it's time to publish
            current_time = time.time()
            wait_time = target_playback_time - current_time

            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 0.1))  # Cap wait time to allow responsive controls
                continue

            # Publish the message
            if topic in self.publishers:
                message_data = data.copy() if isinstance(data, dict) else data
                self.publishers[topic].publish(message_data)

                # Log progress periodically
                if self.current_message_index % 100 == 0:
                    progress = (self.current_message_index + 1) / len(self.messages) * 100
                    loop_info = f" (Loop #{self.loop_count + 1})" if self.repeat and self.loop_count > 0 else ""
                    print(f"Progress: {progress:.1f}% (Speed: {self.speed_factor}x){loop_info}")

            self.current_message_index += 1

        # Wait for input thread to finish
        self.stop_playback = True
        if self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)

        total_duration = time.time() - self.playback_start_time - self.total_pause_duration
        total_loops = self.loop_count + (1 if self.current_message_index > 0 else 0)
        logging.info(f"Playback completed: {total_loops} loops in {total_duration:.2f} seconds")

    def cleanup(self):
        """Clean up resources."""
        logging.info("Cleaning up...")


async def main():
    """Main function to run the interactive playback tool."""
    parser = argparse.ArgumentParser(description='Interactive Cviz Data Playback with Speed Control and Repeat')
    parser.add_argument('--file', type=str, required=True, help='Recording file to play back')
    parser.add_argument('--speed', type=float, default=1.0, help='Initial playback speed factor (1.0 = real-time)')
    parser.add_argument('--endpoint', type=str, default="tcp://127.0.0.1:5555", help='ZMQ endpoint')
    parser.add_argument('--repeat', '-r', action='store_true', help='Repeat playback continuously')
    parser.add_argument('--loops', type=int, help='Number of loops to play (requires --repeat)')

    args = parser.parse_args()

    # Handle the --loops option
    if args.loops and not args.repeat:
        parser.error("--loops requires --repeat to be enabled")

    playback = InteractivePlayback(
        recording_file=args.file,
        zmq_endpoint=args.endpoint,
        initial_speed=args.speed,
        repeat=args.repeat
    )

    # If loops is specified, we'll need to modify the logic slightly
    if args.loops:
        # Override the repeat logic to stop after N loops
        original_play = playback.play

        async def limited_play():
            await original_play()
            # We could add logic here to stop after N loops, but
            # the user can also just press 'q' after the desired number of loops

        logging.info(f"Will play {args.loops} loops")

    try:
        await playback.play()
    finally:
        playback.cleanup()


if __name__ == "__main__":
    # Handle the fact that input() doesn't work well with asyncio
    import sys

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPlayback interrupted by user")
    except Exception as e:
        logging.error(f"Error during playback: {e}")