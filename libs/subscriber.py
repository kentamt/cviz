import time 
import zmq
import json
import asyncio
import logging

class Subscriber:
    def __init__(self,
                 topic_name: str,
                 zmq_endpoint="tcp://127.0.0.1:5555"):
        """Initialise Subscriber."""
        
        self.topic = topic_name
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.SUB)
        self.zmq_socket.connect(zmq_endpoint)
        self.zmq_socket.setsockopt_string(zmq.SUBSCRIBE, topic_name)
        self.topic = topic_name
        self.received_messages = []
        
    def get_message(self):
        """Get the latest message."""
        if self.received_messages:
            return self.received_messages[-1]
        else:
            return None

    async def subscribe(self):    
        """Subscribe to the ZMQ socket."""
        poller = zmq.Poller()
        poller.register(self.zmq_socket, zmq.POLLIN)
        
        while True:
            try:
                # Non-blocking poll for messages
                socks = dict(poller.poll(1))  # 1ms timeout
                
                if self.zmq_socket in socks and socks[self.zmq_socket] == zmq.POLLIN:
                    # Receive a multipart message: [topic, message]
                    topic, message = self.zmq_socket.recv_multipart()
                    topic = topic.decode('utf-8')
                    data = json.loads(message.decode('utf-8'))
                    
                    self.received_messages.append(data)
                    if len(self.received_messages) > 10:
                        self.received_messages.pop(0)
                
                # Yield control to allow other async operations
                await asyncio.sleep(0)
                

            except zmq.Again:
                # No message available, just continue
                await asyncio.sleep(0)
            except Exception as e:
                logging.error(f"Error in ZMQ listener: {e}")
                await asyncio.sleep(1)


# test
async def main():

    subscriber_1 = Subscriber(topic_name="test_data_1")
    subscriber_2 = Subscriber(topic_name="test_data_2")    
    await subscriber_1.get_message()
    await subscriber_2.get_message()
    
    
if __name__ == "__main__":
    asyncio.run(main())


