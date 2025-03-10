import asyncio
import logging

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.cviz_server import CvizServer

def main():
    cviz = CvizServer()
    # cviz.add_subscriber(topic_name="polygon_1")
    # cviz.add_subscriber(topic_name="polygon_2")
    # cviz.add_subscriber(topic_name="point")
    # cviz.add_subscriber(topic_name="linestring_1")
    # cviz.add_subscriber(topic_name="linestring_2")
    # cviz.add_subscriber(topic_name="text_1")
    # cviz.add_subscriber(topic_name="text_2")

    # swarm example
    cviz.add_subscriber(topic_name="polygon_vector")
    cviz.add_subscriber(topic_name="boundary")

    try:
        asyncio.run(cviz.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()    