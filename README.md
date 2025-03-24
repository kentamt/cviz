# Cviz 
Web-based visualisation tool for Python. Cviz has two visualisation modes: canvas and Map. 

<table>
  <tr>
    <td>
      <img src="https://github.com/user-attachments/assets/2da16f6a-b033-4fb3-9f5f-024ff07f5005" controls width="100%"></video>
    </td>
    <td>
      <img src="https://github.com/user-attachments/assets/945ca631-0b93-406d-89e8-fe586d11c841" controls width="100%"></video>
    </td>
  </tr>
</table>

## Demo
For map-app:

```bash
pip install zmq json numpy websockets
npm install pixi.js
```
Run app:
```bash
uvicorn app:app --host 0.0.0.0 --reload --port 8000
```
and visit `localhost:8000`

For canvas-app, change `canvas_index.html` to `index.html`, and the below in `app.py`:
```python
# app.py
# Run any startup scripts asynchronously
script_path = "example/geojson_example.py"  # <-- canvas app
# script_path = "example/geojson_london_example.py"  # <-- map app
```

## Data type
Cviz supports GeoJson format. See https://geojson.org/.

- [ ] Position
- [x] Point
- [x] MultiPoint
- [x] LineString
- [x] MultiLineString
- [x] Polygon
- [x] MultiPolygon
- [ ] GeometryCollection
- [ ] Antimeridian Cutting
- [ ] Uncertainty and Precision 

## Property
Supported properties for GeoJson data for visualisation:
```python
{
  # For visualisation
  "color": "#ff0000",
  "history_limit": 1,  # the number of geometries you keep to visualise
  "life_time": 5,      # the life time of this geometry [sec]
  # You can add properties  
  "id": f"agent_{i}",  
  "type": "vehicle",
  "velocity": v,
  "yaw": yaw,
  "description": f"Vehicle {i} in London"
   ...
}
```

## Mapbox
Cviz renders geometries based on Mapbox. You can use your own Mapbox token by replacing the placeholder in `map-app.js` with your token.
```javascript
 mapboxAccessToken = 'YOUR_MAPBOX_TOKEN';
```

## How it works
You can send topics to the Cviz server, and Cviz sends data via Websockets to the frontend. 

In your Python code

```python
# define your publisher
multipolygon_pub = Publisher(topic_name="multipolygon", data_type="GeoJSON")

while True:
  ...
  # prepare data
  ...
  
  # publish data
  agent_collection = gh.create_feature_collection(agent_polygons)
  multipolygon_pub.publish(agent_collection)
```
and add the topic name to cviz server.

```python
# Create a Cviz server manager instance
cviz_manager = CvizServerManager()

# Add subscribers with history limits where needed
cviz_manager.add_subscriber(topic_name="multipolygon")

# Start the server
await cviz_manager.start()
```

finally, run HTML server and visit inidex.html.
