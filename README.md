# Cviz 

https://github.com/user-attachments/assets/c6f3035d-b04b-4908-bbc8-ee11873b7e14


```
pip install zmq json numpy 
```

Run simulator (random geometry publisher)
```
python example/polygon_publisher.py
```
Run relay server 
```
python example/cviz_server.py
```

Run HTTP server
```
python -m http.server 8000 --directory web
```

Visit `localhost:8000`

