import asyncio
import logging

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.zmq_relay_server import ZMQWebSocketRelay

def main():
    relay = ZMQWebSocketRelay()
    relay.add_subscriber(topic_name="polygon_1")
    relay.add_subscriber(topic_name="polygon_2")
    relay.add_subscriber(topic_name="point")
    relay.add_subscriber(topic_name="linestring_1")
    relay.add_subscriber(topic_name="linestring_2")
    relay.add_subscriber(topic_name="text_1")
    relay.add_subscriber(topic_name="text_2")
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()    