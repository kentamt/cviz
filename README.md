Python3.12

```
pip install zmq json numpy
```

Run simulator (random geometry publisher)
```
python polygon_publisher.py
```
Run relay server 
```
python zmq_relay_server.py
```

Run http server
```
python -m http.server 8000
```
