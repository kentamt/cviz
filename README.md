# Cviz 
Visualisation tool for Python simulator.
https://github.com/user-attachments/assets/f1e7431e-fa74-42c8-94ed-3c19645f5573

## Demo
tested with Python3.12
```bash
pip install zmq json numpy 
npm install pixi.js
```

Run simulator
```bash
python example/polygon_publisher.py
```

Run relay server 
```bash
python example/cviz_server.py
```

Run HTTP server
```bash
python -m http.server 8000 --directory web
```

Visit `localhost:8000`

## How it works

In your simulator:
```python
polygon_pub = Publisher(topic_name="polygon", data_type='Polygon')
data = {'points': [{'x': 0, 'y':0}, ...]}
polygon_pub.publish(data)
```

In Cviz server, add the topic you want to visualise:
```python
def main():
    relay = ZMQWebSocketRelay()
    relay.add_subscriber(topic_name="polygon")
    # relay.add_subscriber(topic_name="point")
    # relay.add_subscriber(topic_name="linestring")
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")
```

