import os
import json
import time
import threading

import zmq

DEFAULT_ZMQ_ENDPOINT = os.environ.get("CVIZ_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")

# PUB sockets keyed by endpoint so we only bind once per process.
_endpoint_contexts = {}
_endpoint_sockets = {}
_endpoint_ref_counts = {}
_endpoint_lock = threading.Lock()


def _get_pub_socket(endpoint: str):
    """Return a PUB socket bound to the requested endpoint."""
    with _endpoint_lock:
        if endpoint not in _endpoint_sockets:
            context = zmq.Context()
            socket = context.socket(zmq.PUB)
            socket.bind(endpoint)
            _endpoint_contexts[endpoint] = context
            _endpoint_sockets[endpoint] = socket
            _endpoint_ref_counts[endpoint] = 0
        _endpoint_ref_counts[endpoint] += 1
        return _endpoint_contexts[endpoint], _endpoint_sockets[endpoint]


def _release_pub_socket(endpoint: str):
    """Release the PUB socket when no instances still reference it."""
    with _endpoint_lock:
        if endpoint not in _endpoint_sockets:
            return

        _endpoint_ref_counts[endpoint] -= 1

        if _endpoint_ref_counts[endpoint] <= 0:
            socket = _endpoint_sockets.pop(endpoint)
            context = _endpoint_contexts.pop(endpoint)
            _endpoint_ref_counts.pop(endpoint)
            try:
                socket.close(0)
            finally:
                context.term()


class Publisher:
    def __init__(self, topic_name: str, data_type: str, zmq_endpoint: str = None):
        """Initialise Publisher."""
        self.topic = topic_name
        self.endpoint = zmq_endpoint or DEFAULT_ZMQ_ENDPOINT

        # TODO: Data type should be a class
        self.data_type = data_type
        self._context, self._socket = _get_pub_socket(self.endpoint)

    # destructor
    def __del__(self):
        try:
            _release_pub_socket(self.endpoint)
        except Exception as e:
            print(f"Error: {e}")

    def publish(self, message: dict):
        """Publish a message to the ZMQ socket."""
        # TODO: message should be a class object. e.g. Polygon, Message

        message['data_type'] = self.data_type
        message['topic'] = self.topic
        message = json.dumps(message)

        self._socket.send_multipart([self.topic.encode('utf-8'),
                                     message.encode('utf-8')])


# test
def main():
    # Socket to publish messages
    publisher_1 = Publisher(topic_name="test_data_1", data_type='text')
    publisher_2 = Publisher(topic_name="test_data_2", data_type='text')

    while True:
        message_1 = {
            'type': 'test_1',
            'timestamp': time.time(),
            'data': 'Hello, World!'
        }

        message_2 = {
            'type': 'test_2',
            'timestamp': time.time(),
            'data': 'Meow!'
        }

        publisher_1.publish(message_1)
        print(f'Sent: {message_1}')
        publisher_2.publish(message_2)
        print(f'Sent: {message_2}')
        time.sleep(1)


if __name__ == "__main__":
    main()
