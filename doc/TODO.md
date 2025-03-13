# Development

## API
In your Python code:

```python

from cviz import Client

# define cviz_client
cviz_client = Client()
cviz_client.connect('0.0.0.0', port=8000)
# ==> Client ID: XXXX-XXXX-XXXX
# ==> Visit 0.0.0.0:8000 and type the Client ID
```

```python
cviz_client.add_data(topic='agent_group', data_type="MultiPolygon")
cviz_client.add_data(topic='trajectory', data_type="LineString")
```

```python
while True:
    ...

    # prepare data (GeoJson format)    
    polygon_data = ...
    trajectory-data = ...

    # Send data to the Cviz server
    cviz_client.publish(topic='agent_group', polygon_data)
    cviz_client.publish(topic='trajectory', trajectory_data)ß
```

## TODO

### Simulation

### Backend
- Store clients in a hash map and send data to corresponding destinations


### Frontend
- Use Mapbox instead of own js implementation
- Keep canvas renderer for now
- Follow GeoJson format

