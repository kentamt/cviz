import asyncio
import logging
from libs.zmq_relay_server import ZMQWebSocketRelay

def main():
    relay = ZMQWebSocketRelay()
    relay.add_subscriber(topic_name="polygon")
    relay.add_subscriber(topic_name="point")
    relay.add_subscriber(topic_name="linestring")
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()    