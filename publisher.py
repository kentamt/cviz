import zmq
import json
import time

zmq_endpoint="tcp://127.0.0.1:5555"
zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.PUB)
zmq_socket.bind(zmq_endpoint)

class Publisher:
    def __init__(self,  topic_name: str, data_type: str):
        """Initialise Publisher."""
        self.topic = topic_name
        
        # TODO: Data type should be a class
        self.data_type = data_type

    # destructor
    def __del__(self):
        try:
            zmq_socket.close()
            zmq_context.term()

        except Exception as e:
            print(f"Error: {e}")

    def publish(self, message: dict):
        """Publish a message to the ZMQ socket."""
        # TODO: message should be a class object. e.g. Polygon, Message
        
        message['data_type'] = self.data_type        
        message = json.dumps(message)

        
        zmq_socket.send_multipart([self.topic.encode('utf-8'), 
                                        message.encode('utf-8')])
        
        print(f"Sent {self.topic}")
        
        
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

