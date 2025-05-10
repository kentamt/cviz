# run_recorder.py
import argparse
import asyncio
from recorder import DataRecorder


async def run_recorder(topics, endpoint, output_dir, duration):
    """Run the recorder for a specified duration."""
    recorder = DataRecorder(
        topics=topics,
        zmq_endpoint=endpoint,
        output_dir=output_dir
    )

    try:
        if duration:
            print(f"Recording for {duration} seconds...")
            await asyncio.wait_for(recorder.record(), timeout=duration)
        else:
            print("Recording until interrupted (Ctrl+C to stop)...")
            await recorder.record()
    except asyncio.TimeoutError:
        print(f"Recording completed after {duration} seconds.")
    finally:
        recorder.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Cviz Data Recorder')
    parser.add_argument('--topics', type=str, help='Comma-separated list of topics to record')
    parser.add_argument('--endpoint', type=str, default="tcp://127.0.0.1:5555", help='ZMQ endpoint')
    parser.add_argument('--output-dir', type=str, default="recordings", help='Output directory')
    parser.add_argument('--duration', type=int, help='Recording duration in seconds (optional)')

    args = parser.parse_args()

    # Parse topics
    topics = None
    if args.topics:
        topics = [topic.strip() for topic in args.topics.split(',')]

    asyncio.run(run_recorder(topics, args.endpoint, args.output_dir, args.duration))